# Example Python RAG Extension

This is an example of a GitHub Copilot extension that implements a RAG workflow with Python.

# Infra deployment

The backend is deployed with AWS CDK. This assumes that the CDK bootstrap has been run in the account and region where the deployment is to be made.

To deploy the CDK stack, first source the correct env_variables.sh file and then run the following commands:

```bash
cd cdk
pip install -r requirements.txt
cdk deploy
```

# Application deployment

Deployment is done manually, by copying all the relevant code to the EC2 instance.

A conda environment is required to install and run the FAISS pieces (conda handles the compiled packages). First
install miniconda:

wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh

and then run:

bash Miniconda3-latest-Linux-aarch64.sh

After installing, create a new conda environment:

conda create --name copilot python=3.11

Activate the environment:

conda activate copilot

Copy the requirements.txt file from the root of this repo to whereever you want to install the requirements.

Install the required packages:

conda install --file requirements.txt


## building the vector store

To build the vector store, you can use the scripts located in the `vectorstore` folder.

For information on how to use them, consult the [`vectorstore` README](vectorstore/README.md).