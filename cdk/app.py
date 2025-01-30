import os
from aws_cdk import Environment, App
import copilot_stack

app = App()

# Create an Environment object specifying the region
env = Environment(region=os.environ["AWS_REGION"], account=os.environ["AWS_ACCOUNT_NUMBER"])

# Pass the env to the stack
copilot_stack.CopilotApiStack(app, f"CopilotStack", env=env)

app.synth()