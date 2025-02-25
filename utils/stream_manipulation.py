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


