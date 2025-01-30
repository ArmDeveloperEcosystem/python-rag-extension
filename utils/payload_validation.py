from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_public_key
import base64
import requests
import hmac
import hashlib
import os

WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')
if not WEBHOOK_SECRET:
    raise ValueError("WEBHOOK_SECRET environment variable must be set")

def verify_signature(payload_body, signature_header):
    """
    Verify that the payload was sent from GitHub by validating SHA256.
    
    Args:
        payload_body: original request body to verify
        signature_header: header received from GitHub (x-hub-signature-256)
    
    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not signature_header:
        return False
        
    if not signature_header.startswith('sha256='):
        return False
        
    # Calculate expected signature
    hash_object = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = f"sha256={hash_object.hexdigest()}"
    
    # Use hmac.compare_digest to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature_header)


def fetch_public_key():
    url = "https://api.github.com/meta/public_keys/copilot_api"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch public key: {response.status_code}")

    data = response.json()
    current_key = next((pk for pk in data['public_keys'] if pk['is_current']), None)

    if not current_key:
        raise Exception("Could not find current public key")

    raw_key = current_key['key'].replace('\\n', '\n')

    try:
        public_key = load_pem_public_key(raw_key.encode())
    except Exception as e:
        raise Exception(f"Error parsing PEM block with GitHub public key: {e}")

    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise Exception("GitHub key is not ECDSA")

    return public_key

def valid_payload(data, sig, public_key):
    try:
        signature = base64.b64decode(sig)
        public_key.verify(
            signature,
            data,
            ec.ECDSA(hashes.SHA256())
        )
        return True
    except InvalidSignature:
        return False
    except Exception as e:
        print(f"Error validating payload: {e}")
        return False
