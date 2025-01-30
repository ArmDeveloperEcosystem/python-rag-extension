import requests

REPHRASER_SYSTEM_MESSAGE = "You are a rephraser. You are given a conversation and must rephrase the last question that was asked based on the conversation history. You must be very explicit in your rephrasing, replacing all pronouns with their proper nouns. Do not expand acronyms."
def get_chunk_template():
    chunk_template = {
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": ""},
                                "logprobs": None,
                                "finish_reason": None
                            }
                        ],
                        "created": 0,
                        "id": "",
                        "model": "",
                        "system_fingerprint": "",
                        "object": "chat.completion.chunk"
                    }
    return chunk_template



def check_for_github_reference(session_info):
    print(session_info)
    if 'copilot_references' in session_info:
        for ref in session_info['copilot_references']:
            if 'type' in ref and ref['type'] == 'github.current-url':
                return True
    return False


def extract_session_info(messages):
    """
    Extracts session information from messages, returning three pieces of information:

    1. A diction with the datetime and user information.
    2. The item in the messages list that contains the session information.
    3. A new list of messages with the session information removed.
    """
    # Find the dictionary with role='user' and name='_session'
    print(messages)
    session_item = next(
        (item for item in messages 
         if item.get('role') == 'user' and item.get('name') == '_session'),
        None
    )
    
    if not session_item:
        return None
        
    # Extract datetime and user information from the content string
    content = session_item.get('content', '')
    
    # Initialize result dictionary
    session_info = {}
    
    # Parse the content string
    for line in content.split('\n'):
        if line.startswith('Current Date and Time (UTC):'):
            session_info['datetime'] = line.replace('Current Date and Time (UTC):', '').strip()
        elif line.startswith("Current User's Login:"):
            session_info['user'] = line.replace("Current User's Login:", '').strip()

    stripped_messages = [msg for msg in messages 
            if not (msg.get('role') == 'user' and msg.get('name') == '_session')]
            
    return session_info, session_item, stripped_messages


def rephrase_messages(llm_client, headers, messages, system_message, model_name):
    rephrased_message = ""
    system_message = [{
        "role": "system",
        "content": system_message
    }]

    copilot_req = {
        "model": model_name,
        "messages": system_message + messages
    }
    r = requests.post(llm_client, json=copilot_req, headers=headers)
    r.raise_for_status()
    return_dict = r.json()

    rephrased_message = return_dict['choices'][0]['message']['content']
    print()
    print(rephrased_message)
    print()

    rephrased_messages = [{"role": "user", "content": rephrased_message}]

    return rephrased_messages


