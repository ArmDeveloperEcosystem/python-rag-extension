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

    for chunk in copilot_response.iter_content():
            if chunk:
                # To see what the chunk stream looks like, uncomment the line below.
                # print("Streamed Chunk:", chunk.decode('utf-8'))
                yield chunk  # Send the chunk to the client

