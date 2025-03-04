# Example Python RAG Extension

This is an example of a GitHub Copilot extension that implements a RAG workflow with Python.

Arm has created three Learning Paths that will guide your understanding of the application in this repo.

The first Learning Path is [Build a GitHub Copilot Extension in Python](https://learn.arm.com/learning-paths/servers-and-cloud-computing/gh-copilot-simple/). This Learning Path provides a way to create a simple Python Copilot Extension, without any production-level features.

The second Learning Path is [Deploy Graviton Infrastructure for GitHub Copilot Extensions](https://learn.arm.com/learning-paths/servers-and-cloud-computing/copilot-extension-deployment/). This guide walks through the creation of IaC (Infrastructure as Code) for the AWS services suggested for a production deployment of Python. This code is located in the /cdk directory within this repo.

The third Learning Path is [Create a RAG-based GitHub Copilot Extension in Python](https://learn.arm.com/learning-paths/servers-and-cloud-computing/copilot-extension/). This final learning path in the series covers generating a knowledge base and adding Retrieval Augmented Generation to your Extension.

# Infra deployment

The backend is deployed with AWS CDK. This assumes that the CDK bootstrap has been run in the account and region where the deployment is to be made.

To deploy the CDK stack, first fill out the variables in env_variables.sh (ensuring that you have already created a custom domain in Route 53 and certificate in Certificate Manager), source the file, and then run the following commands:

```bash
cd cdk
pip install -r requirements.txt
cdk deploy
```
See [Deploy Graviton Infrastructure for GitHub Copilot Extensions](https://learn.arm.com/learning-paths/servers-and-cloud-computing/copilot-extension-deployment/) for detailed instructions.

# Application deployment

Deployment is done manually, by copying all the relevant code to the EC2 instance.

A conda environment is required to install and run the FAISS pieces (conda handles the compiled packages). First
install miniconda, micromamba, or your preferred conda application.

After installing, create a new conda environment:

conda create --name copilot python=3.11

Activate the environment:

conda activate copilot

Copy the requirements.txt file from the root of this repo to the environment you want to install the requirements.

Install the required packages:

conda install --file requirements.txt

## building the vector store

To build the vector store, you can use the scripts located in the `vectorstore` folder.

For information on how to use them, consult the [`vectorstore` README](vectorstore/README.md).