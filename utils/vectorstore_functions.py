import faiss
import json
import requests
import numpy as np

def load_faiss_index(index_path: str):
    """Load the FAISS index from a file."""
    print(f"Loading FAISS index from {index_path}")
    index = faiss.read_index(index_path)
    print(f"Loaded index containing {index.ntotal} vectors")
    return index


def load_metadata(metadata_path: str):
    """Load metadata from a JSON file."""
    print(f"Loading metadata from {metadata_path}")
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    print(f"Loaded metadata for {len(metadata)} items")
    return metadata


FAISS_INDEX = load_faiss_index("faiss_index.bin")
FAISS_METADATA = load_metadata("metadata.json")
MODEL_NAME = 'text-embedding-ada-002'
DISTANCE_THRESHOLD = 1.1

llm_client = "https://api.githubcopilot.com/embeddings"


def create_embedding(query: str, headers=None):
    print(f"Creating embedding using model: {MODEL_NAME}")
    copilot_req = {
        "model": MODEL_NAME,
        "input": [query]
    }
    r = requests.post(llm_client, json=copilot_req, headers=headers)
    r.raise_for_status()
    return_dict = r.json()

    return return_dict['data'][0]['embedding']


def embedding_search(query: str, k: int = 5, headers=None):
    """
    Search the FAISS index with a text query.

    Args:
    query (str): The text to search for.
    k (int): The number of results to return.

    Returns:
    list: A list of dictionaries containing search results with distances and metadata.
    """
    print(f"Searching for: '{query}'")
    # Convert query to embedding
    query_embedding = create_embedding(query, headers)
    query_array = np.array(query_embedding, dtype=np.float32).reshape(1, -1)

    # Perform the search
    distances, indices = FAISS_INDEX.search(query_array, k)
    print(distances, indices)
    # Prepare results
    results = []
    for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        if idx != -1:  # -1 index means no result found
            if float(dist) < DISTANCE_THRESHOLD:
                result = {
                    "rank": i + 1,
                    "distance": float(dist),
                    "metadata": FAISS_METADATA[idx]
                }
                results.append(result)

    return results

def deduplicate_urls(embedding_results: list):
    """Deduplicate metadata based on the 'url' field."""
    seen_urls = set()
    deduplicated_results = []
    for item in embedding_results:
        url = item["metadata"].get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduplicated_results.append(item)
    return deduplicated_results