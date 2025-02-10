# Vectorstore Database Creation

These scripts will help you generate an example FAISS vector database for use in your flask application.

## Chunk Creation

We have provided scripts to convert an Arm learning path into a series of `chunk.yaml` files for use in our RAG application.

### Chunk script Set up

It is recommended to use a virtual environment to manage dependencies.

To create a new conda environment, use the following command:

```sh
conda create --name vectorstore python=3.11
```

Once set up is complete, activate the new environment:

```sh
conda activate vectorstore
```

Install the required packages:

```sh
conda install --file vectorstore-requirements.txt
```

### Generate Chunk Files

To generate chunks, use the following command:

```sh
python chunk_a_learning_path.py --url <LEARNING_PATH_URL>
```

Replace `<LEARNING_PATH_URL>` with the URL of the learning path you want to process. If no URL is provided, the script will default to a [known learning path URL](https://learn.arm.com/learning-paths/cross-platform/kleidiai-explainer).

The script will process the specified learning path and save the chunks as YAML files in a `./chunks/` directory.

## Combine Chunks into FAISS index

Once you have a `./chunks/` directory full of yaml files, we now need to use FAISS to create our vector database.

### OpenAI Key and Endpoint

Ensure your local environment has your `AZURE_OPENAI_KEY` and `AZURE_OPENAI_ENDPOINT` set.

#### If needed, generate Azure OpenAI keys and deployment 

1. **Create an OpenAI Resource**:
    - Go to the [Azure Portal](https://portal.azure.com/).
    - Click on "Create a resource".
    - Search for "OpenAI" and select "Azure OpenAI Service".
    - Click "Create".

1. **Configure the OpenAI Resource**:
    - Fill in the required details such as Subscription, Resource Group, Region, and Name.
    - Click "Review + create" and then "Create" to deploy the resource.

1. **Generate API Key and Endpoint**:
    - Once the resource is created, navigate to the resource page.
    - Under the "Resource Management->Keys and Endpoint" section, you will find the key and endpoint values.
    - Copy these values and set them in your local environment.

    ```sh
    export AZURE_OPENAI_KEY="<your_openai_key>"
    export AZURE_OPENAI_ENDPOINT="https://<your_openai_endpoint>.openai.azure.com/"
    ```

    You now have the necessary keys to use Azure OpenAI in your application.

1. **Deploy text-embedding-ada-002 model**
    - Go inside Azure AI Foundry for your new deployment
    - Under "Deployments", ensure you have a deployment for "text-embedding-ada-002"

### Generate Vector Database Files

Run the python script to create the FAISS index `.bin` and `.json` files.

**NOTE:** This assumes the chunk files are located in a `chunks` subfolder, as they should automatically be.

```bash
python local_vectorstore_creation.py
```

Copy the generated `bin` and `json` files to the root directory where you deploy your Flask application.
