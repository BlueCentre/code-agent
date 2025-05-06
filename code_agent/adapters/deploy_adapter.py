"""
Deploy Adapter - Provides deployment functionality for agents.

This module provides methods to deploy agents to cloud environments.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Template for cloud run main.py
CLOUD_RUN_MAIN_TEMPLATE = """
import os
import logging
from pathlib import Path

from fastapi import FastAPI
from code_agent.adapters.web_adapter import create_web_app, run_web_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to the agent
AGENT_PATH = Path("{agent_path}")

# Create the app
app = create_web_app(
    agents_dir=str(AGENT_PATH.parent),
    session_db_url="{session_db_url}",
    trace_to_cloud={trace_to_cloud},
    with_ui={with_ui},
)

# Run the app when executed directly
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "{port}"))
    logger.info(f"Starting server on port {port}")
    run_web_server(app=app, port=port)
"""

# Template for requirements.txt
CLOUD_RUN_REQUIREMENTS_TEMPLATE = """
fastapi>=0.111.0
uvicorn>=0.30.0
google-adk==0.4.0
pydantic>=2.7.4
python-dotenv>=1.0.0
"""

# Template for Dockerfile
CLOUD_RUN_DOCKERFILE_TEMPLATE = """
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080

CMD exec python main.py
"""


def deploy_to_cloud_run(
    agent: str,
    project: Optional[str] = None,
    region: Optional[str] = None,
    service_name: str = "adk-default-service-name",
    app_name: str = "",
    temp_folder: str = "",
    port: int = 8000,
    trace_to_cloud: bool = False,
    with_ui: bool = False,
    verbosity: str = "WARNING",
    session_db_url: str = "",
) -> None:
    """
    Deploy an agent to Google Cloud Run.

    Args:
        agent: Path to the agent source code folder
        project: Google Cloud project to deploy the agent
        region: Google Cloud region to deploy the agent
        service_name: The service name to use in Cloud Run
        app_name: App name of the server
        temp_folder: Temp folder for the generated Cloud Run source files
        port: The port of the server
        trace_to_cloud: Whether to enable Cloud Trace
        with_ui: Deploy with Web UI
        verbosity: Logging verbosity level
        session_db_url: Database URL for session storage
    """
    # Validate inputs
    agent_path = Path(agent).resolve()
    if not agent_path.is_dir():
        raise ValueError(f"Agent directory not found: {agent}")

    # Use folder name as app name if not provided
    if not app_name:
        app_name = agent_path.name

    # Create temp folder if it doesn't exist
    if not temp_folder:
        temp_folder = os.path.join(tempfile.gettempdir(), "cloud_run_deploy_src", app_name)

    os.makedirs(temp_folder, exist_ok=True)
    logger.info(f"Using temp folder: {temp_folder}")

    # Generate deployment files
    create_deployment_files(
        agent_path=agent_path,
        output_dir=temp_folder,
        port=port,
        trace_to_cloud=trace_to_cloud,
        with_ui=with_ui,
        session_db_url=session_db_url,
    )

    # Deploy to Cloud Run
    deploy_to_gcp(
        source_dir=temp_folder,
        project=project,
        region=region,
        service_name=service_name,
    )


def create_deployment_files(
    agent_path: Path,
    output_dir: str,
    port: int = 8000,
    trace_to_cloud: bool = False,
    with_ui: bool = False,
    session_db_url: str = "",
) -> None:
    """
    Generate files needed for deployment.

    Args:
        agent_path: Path to the agent source code
        output_dir: Directory to write the files to
        port: Port for the server
        trace_to_cloud: Whether to enable Cloud Trace
        with_ui: Deploy with Web UI
        session_db_url: Database URL for session storage
    """
    # Create main.py
    main_py_content = CLOUD_RUN_MAIN_TEMPLATE.format(
        agent_path=str(agent_path),
        port=port,
        trace_to_cloud=str(trace_to_cloud).lower(),
        with_ui=str(with_ui).lower(),
        session_db_url=session_db_url,
    )

    with open(os.path.join(output_dir, "main.py"), "w") as f:
        f.write(main_py_content)

    # Create requirements.txt
    with open(os.path.join(output_dir, "requirements.txt"), "w") as f:
        f.write(CLOUD_RUN_REQUIREMENTS_TEMPLATE)

    # Create Dockerfile
    with open(os.path.join(output_dir, "Dockerfile"), "w") as f:
        f.write(CLOUD_RUN_DOCKERFILE_TEMPLATE)

    # Copy agent files
    agent_dest_dir = os.path.join(output_dir, agent_path.name)
    os.makedirs(agent_dest_dir, exist_ok=True)

    for item in agent_path.glob("*"):
        if item.is_file():
            shutil.copy2(item, agent_dest_dir)
        elif item.is_dir():
            shutil.copytree(item, os.path.join(agent_dest_dir, item.name), dirs_exist_ok=True)

    logger.info(f"Deployment files created in {output_dir}")


def deploy_to_gcp(
    source_dir: str,
    project: Optional[str] = None,
    region: Optional[str] = None,
    service_name: str = "adk-default-service-name",
) -> None:
    """
    Deploy the application to Google Cloud Run.

    Args:
        source_dir: Directory containing the source files
        project: Google Cloud project ID
        region: Google Cloud region
        service_name: Cloud Run service name
    """
    # Check for gcloud CLI
    try:
        subprocess.run(["gcloud", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("gcloud CLI not found. Please install it from https://cloud.google.com/sdk/docs/install")  # noqa: B904

    # Build and deploy using gcloud
    logger.info("Deploying to Cloud Run...")

    # Build command
    cmd = ["gcloud", "run", "deploy", service_name]

    if project:
        cmd.extend(["--project", project])

    if region:
        cmd.extend(["--region", region])

    cmd.extend(
        [
            "--source",
            source_dir,
            "--allow-unauthenticated",
            "--platform",
            "managed",
        ]
    )

    # Execute command
    try:
        process = subprocess.run(cmd, check=True, text=True, capture_output=True)
        logger.info(f"Deployment successful: {process.stdout}")

        # Extract service URL from output
        for line in process.stdout.splitlines():
            if "Service URL:" in line:
                service_url = line.split("Service URL:")[1].strip()
                logger.info(f"Service deployed at: {service_url}")
                return

    except subprocess.CalledProcessError as e:
        logger.error(f"Deployment failed: {e.stderr}")
        raise RuntimeError(f"Deployment failed: {e.stderr}")  # noqa: B904
