import os
from flask import Flask, redirect, request, session, Response, stream_with_context, url_for, jsonify
from requests_oauthlib import OAuth2Session
from werkzeug.middleware.proxy_fix import ProxyFix
import json
from utils import payload_validation as pv
from pathlib import Path
import uuid
from utils import agent_functions

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.urandom(24)

# GitHub OAuth2 settings
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTHORIZATION_BASE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
PUBLIC_KEY = pv.fetch_public_key()
BUCKET_NAME = os.getenv("BUCKET_NAME")
MODEL_NAME = "gpt-4o"

AMOUNT_OF_CONTEXT_TO_USE = 3
@app.route('/health')
def health():
    return Response(status=200)


@app.route('/agent', methods=['POST'])
def agent():
    # Extract headers
    sig = request.headers.get('Github-Public-Key-Signature')
    api_token = request.headers.get('X-GitHub-Token')
    integration_id = request.headers.get('Copilot-Integration-Id')
    print(f"Received headers: sig={sig}, api_token={api_token}, integration_id={integration_id}")

    # Read request body
    body = request.get_data()

    # Validate payload signature
    if not pv.valid_payload(body, sig, PUBLIC_KEY):
        return "Invalid payload signature", 401

    # Parse request body
    try:
        req = json.loads(body)
        print(req)
    except json.JSONDecodeError:
        return "Invalid JSON in request body", 400

    if 'messages' not in req:
        return "Missing 'messages' field in request body", 400

    messages = req['messages']
    thread_id = req['copilot_thread_id']

    # Prepare the request to GitHub Copilot API
    copilot_url = "https://api.githubcopilot.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_token}",
        "Copilot-Integration-Id": integration_id
    }

    # For many streaming API responses you'd want to return a text/event-stream, but in this case
    # the GitHub Copilot API understands a streamed application/json response as well.
    return app.response_class(agent_functions.agent_flow(
                                AMOUNT_OF_CONTEXT_TO_USE,
                                messages,
                                thread_id,
                                agent_functions.SYSTEM_MESSAGE,
                                MODEL_NAME,
                                copilot_url,
                                headers
                            ),  
                            mimetype='application/json')

@app.route('/marketplace', methods=['POST'])
def marketplace():
    payload_body = request.get_data()
    print(payload_body)

    # Verify request has JSON content
    if not request.is_json:
        return jsonify({
            'error': 'Content-Type must be application/json'
        }), 415

    try:
        # Get JSON payload
        payload = request.get_json()
        
        # Print the payload
        print("Received payload:")
        print(json.dumps(payload, indent=2))
        
        output_dir = Path('marketplace_events')
        
        # Generate unique filename and save
        filename = f"{uuid.uuid4().hex}.json"
        file_path = output_dir / filename
        
        with open(file_path, 'w') as f:
            json.dump(payload, f, indent=2)
            
        print(f"Saved payload to {file_path}")
        
        return jsonify({
            'status': 'success',
            'message': 'Event received and processed',
            'file_path': str(file_path)
        }), 201

    except Exception as e:
        return jsonify({
            'error': f'Failed to process request: {str(e)}'
        }), 500


@app.route("/auth/authorization")
def authorization():
    print("Starting authorization process")
    github = OAuth2Session(CLIENT_ID, redirect_uri="https://copilot.armdevtechapi.com/auth/callback")
    authorization_url, state = github.authorization_url(AUTHORIZATION_BASE_URL)
    session["oauth_state"] = state
    print(f"Generated authorization URL: {authorization_url}")
    print(f"State: {state}")
    return redirect(authorization_url)


@app.route("/auth/callback")
def callback():
    print("Received callback from GitHub")
    print(f"Request URL: {request.url}")
    print(f"Session state: {session.get('oauth_state')}")

    if 'oauth_state' not in session:
        return redirect(url_for('authorization'))

    github = OAuth2Session(CLIENT_ID, state=session["oauth_state"], redirect_uri=request.url)

    try:
        token = github.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, authorization_response=request.url)
        print("Successfully fetched token")
        print(f"Token: {token}")
        session["oauth_token"] = token
        return redirect("https://github.com/arm/copilot-extension/tree/master?tab=readme-ov-file#arm-copilot-extension")
    except Exception as e:
        print(f"Error fetching token: {str(e)}")
        return f"Authentication failed. Error: {str(e)}"