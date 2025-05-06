#!/usr/bin/env python
"""
Deploy the software engineer agent to Agent Engine.

Run:
  python deployment/deploy.py --create
"""

import argparse
import os

from dotenv import load_dotenv
from google.cloud import aiplatform
from google.cloud.aiplatform import Agent as VertexAgent

load_dotenv()  # Load environment variables from .env file

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
STORAGE_BUCKET = os.environ.get("GOOGLE_CLOUD_STORAGE_BUCKET")

# Initialize the Vertex AI SDK
aiplatform.init(project=PROJECT, location=LOCATION)


def deploy_agent(args):
    """Deploy the software engineer agent to Agent Engine."""
    display_name = "Software Engineer Agent"
    description = "An AI software engineer assistant that helps with various software development tasks"

    description_for_human = "The Software Engineer Agent helps with code reviews, design patterns, testing, debugging, documentation, and DevOps."

    agent = VertexAgent.create(
        display_name=display_name,
        description=description,
        description_for_human=description_for_human,
        agent_tools=["function"],
        agent_modules=["gcp"],
        tools_code_path="software_engineer",
        tools_package_name="software_engineer",
        tools_entry_point="root_agent",
        tools_args={},
        reference_files={},
        staging_gcs_bucket=STORAGE_BUCKET,
    )

    print(f"Agent created: {agent.resource_name}")
    return agent


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Deploy the software engineer agent.")
    parser.add_argument("--create", action="store_true", help="Create a new agent in Agent Engine")
    return parser.parse_args()


def main():
    """Main function to deploy the agent."""
    args = parse_args()

    if args.create:
        deploy_agent(args)
    else:
        print("No action specified. Use --create to create a new agent.")


if __name__ == "__main__":
    main()
