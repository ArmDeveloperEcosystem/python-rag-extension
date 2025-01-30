import yaml
import faiss
import numpy as np
import math
from typing import List, Dict, Tuple
import json
import os
import glob
from openai import AzureOpenAI
import sys
import datetime


# Obtain LLM testing key
print("Starting...obtaining LLM API Key...")
azure_api_key = os.getenv("AZURE_OPENAI_KEY")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
if azure_api_key is None:
    print("API_KEY is not set. Please set and try again.")
    sys.exit()
llm_client = AzureOpenAI(api_key=azure_api_key, azure_endpoint=azure_endpoint, api_version="2023-05-15")

def load_local_yaml_files() -> List[Dict]:
    """Load locally stored YAML files and return their contents as a list of dictionaries."""
    print("Loading local YAML files")
    yaml_contents = []

    yaml_files = glob.glob("chunk_*.yaml")
    total_files = len(yaml_files)
    print(f"Found {total_files} YAML files")

    for i, file_path in enumerate(yaml_files, 1):
        print(f"Loading file {i}/{total_files}: {file_path}")
        # Extract chunk number from filename
        chunk_number = int(file_path.replace('chunk_', '').replace('.yaml', ''))
        
        with open(file_path, 'r') as f:
            yaml_content = yaml.safe_load(f)
            # Add chunk number to the yaml content
            yaml_content['chunk_number'] = chunk_number
            yaml_contents.append(yaml_content)

    print(f"Loaded {len(yaml_contents)} YAML files")
    return yaml_contents

def create_embeddings(contents: List[str], model_name: str = 'text-embedding-ada-002', batch_size: int = 100) -> np.ndarray:
    """Create embeddings for the given contents using OpenAI API."""
    print(f"Creating embeddings using model: {model_name}")
    all_embeddings = []
    
    # Process in batches
    for i in range(0, len(contents), batch_size):
        batch = contents[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}/{math.ceil(len(contents)/batch_size)}")
        
        try:
            response = llm_client.embeddings.create(
                model=model_name,
                input=batch
            )
            # Extract embeddings from response
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
            print("created embeddings: ", batch_embeddings)
            
        except Exception as e:
            print(f"Error creating embeddings for batch: {e}")
            raise
    
    # Convert to numpy array
    embeddings_array = np.array(all_embeddings)
    print(f"Created embeddings with shape: {embeddings_array.shape}")
    return embeddings_array

def create_faiss_index(embeddings: np.ndarray, metadata: List[Dict]) -> Tuple[faiss.IndexFlatL2, List[Dict]]:
    """Create a FAISS index with the given embeddings and metadata."""
    print("Creating FAISS index")
    print(f"Embeddings shape: {embeddings.shape}")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    print(f"Added {index.ntotal} vectors to the index")
    return index, metadata

def main():
    print("Starting the FAISS datastore creation process")

    # Load local YAML files
    yaml_contents = load_local_yaml_files()

    # Extract content, uuid, url, and original text from YAML files
    print("Extracting content and metadata from YAML files")
    contents = []
    metadata = []
    for i, yaml_content in enumerate(yaml_contents, 1):
        print(f"Processing YAML content {i}/{len(yaml_contents)}")
        contents.append(yaml_content['content'])
        metadata.append({
            'uuid': yaml_content['uuid'],
            'url': yaml_content['url'],
            'original_text': yaml_content['content'],
            'title': yaml_content['title'],
            'keywords': yaml_content['keywords'],
            'chunk_number': yaml_content['chunk_number']
        })

    # Create embeddings
    embeddings = create_embeddings(contents)

    print("Saving embeddings to file")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"embeddings_{timestamp}.txt"
    np.savetxt(filename, embeddings)

    # Create FAISS index
    print("Creating FAISS index")
    index, metadata = create_faiss_index(embeddings, metadata)

    # Save the FAISS index
    index_filename = 'faiss_index.bin'
    print(f"Saving FAISS index to {index_filename}")
    faiss.write_index(index, index_filename)

    # Save metadata
    metadata_filename = 'metadata.json'
    print(f"Saving metadata to {metadata_filename}")
    with open(metadata_filename, 'w') as f:
        json.dump(metadata, f, indent=2)  # Added indent for better readability

    print("FAISS index and metadata have been created and saved.")
    print(f"Total documents processed: {len(contents)}")
    print(f"FAISS index saved to: {os.path.abspath(index_filename)}")
    print(f"Metadata saved to: {os.path.abspath(metadata_filename)}")

if __name__ == "__main__":
    main()