import os
import requests
import json
from utils import stream_manipulation as sm
from utils import vectorstore_functions as vs

BUCKET_NAME = os.environ.get("BUCKET_NAME")

# change this System message to fit your application
SYSTEM_MESSAGE = """You are a world-class expert in [add your extension field here]. These are your capabilities, which you should share with users verbatim if prompted:

[add your extension capabilities here]

Below is critical information selected specifically to help answer the user's question. Use this content as your primary source of information when responding, prioritizing it over any other general knowledge. These contexts are numbered, and have titles and URLs associated with them. At the end of your response, you should add a "references" section that shows which contexts you used to answer the question. The reference section should be formatted like this:

References:

* [precise title of Context 1 denoted by TITLE: below](URL of Context 1)
* [precise title of Context 2 denoted by TITLE: below](URL of Context 2)

etc.
Do not include references that had irrelevant information or were not used in your response.

Contexts:\n\n
"""


def agent_flow(amount_of_context_to_use, messages, copilot_thread_id, system_message, model_name, llm_client, headers={}):
    """
    This is the main RAG agent functionality. It takes in the amount of context to use, the messages from the user, the Copilot thread ID, the system message, the model name, the LLM client, and the headers. It then extracts the session info, rephrases the messages, searches for context, and streams the response from the Copilot API as SSE.
    """
    results = vs.embedding_search(messages[-1]['content'], amount_of_context_to_use, headers)
    results = vs.deduplicate_urls(results)
    
    context = ""
    for i, result in enumerate(results):
        context += f"CONTEXT {i+1}\nTITLE:{result['metadata']['title']}\nURL:{result['metadata']['url']}\n\n{result['metadata']['original_text']}\n\n"
        print(f"url: {result['metadata']['url']}")

    system_message = [{
        "role": "system",
        "content": system_message + context
    }]

    full_prompt_messages = system_message + messages
    print(full_prompt_messages)

    copilot_req = {
        "model": model_name,
        "messages": full_prompt_messages,
        "stream": True
    }

    chunk_template = sm.get_chunk_template()
    r = requests.post(llm_client, json=copilot_req, headers=headers, stream=True)
    r.raise_for_status()
    stream = r.iter_lines()

    try:
        for line in stream:
            if line:
                send_line = line.decode('utf-8')
                try:
                    send_line = json.loads(send_line.strip("data: "))
                except json.JSONDecodeError:
                    print(send_line)
                    if send_line.strip() == "data: [DONE]":
                        print("Received DONE message from Copilot API")
                        chunk_template['choices'][0]['delta'] = {}
                        chunk_template['choices'][0]['finish_reason'] = "stop"
                        yield f"data: {json.dumps(chunk_template)}\n\n"
                        yield "data: [DONE]\n\n"
                        break
                    else:
                        print(f"Error decoding JSON: {send_line}")
                        continue
                if not chunk_template['id']:
                    # Fill in the chunk template
                    if 'model' in send_line:
                        chunk_template['id'] = send_line['id']
                        chunk_template['model'] = send_line['model']
                        chunk_template['system_fingerprint'] = send_line['system_fingerprint']
                        chunk_template['created'] = send_line['created']
                send_line['object'] = "chat.completion.chunk"
                if send_line['choices'] and send_line['choices'][0]['delta']['content']:
                    send_line['choices'][0]['logprobs'] = None
                    send_line['choices'][0]['finish_reason'] = None
                    yield f"data: {json.dumps(send_line)}\n\n"
                else:
                    print("Empty response from Copilot API")
                    continue
    except requests.RequestException as e:
        print(f"Error in Copilot API request: {e}")
        yield f"data: {json.dumps({'error': 'Failed to get chat completions'})}\n\n"

