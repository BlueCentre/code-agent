"""
Script to run the Software Engineer agent programmatically for E2E testing,
allowing injection of specific SessionService and MemoryService implementations.
"""

import argparse
import asyncio
import logging
import os
import sys

# Import memory services
from google.adk.memory import (
    BaseMemoryService,
    InMemoryMemoryService,
    VertexAiRagMemoryService,
)
from google.adk.runners import Runner

# from google.adk.cli.run import run_stdio_async # REMOVED
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part  # Import genai types

# Import the custom JSON memory service
from code_agent.adk.json_memory_service import JsonFileMemoryService

# Import the agent definition
from code_agent.agent.software_engineer.software_engineer.agent import root_agent

# Setup basic logging - Will be reconfigured in main
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  # Get logger for this module


async def main(log_level_arg: str):
    """Sets up services and runs the agent for a single input from stdin."""

    # Configure logging based on argument
    log_level = getattr(logging, log_level_arg.upper(), logging.INFO)
    # Configure root logger
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # Apply level to our specific logger too (optional, but good practice)
    logger.setLevel(log_level)

    app_name = os.getenv("ADK_E2E_APP_NAME", "e2e_test_app")
    gcp_project = os.getenv("ADK_E2E_GCP_PROJECT")
    gcp_location = os.getenv("ADK_E2E_GCP_LOCATION")
    rag_corpus_id = os.getenv("ADK_E2E_RAG_CORPUS_ID")
    json_path_e2e = os.getenv("ADK_E2E_JSON_MEMORY_PATH")
    memory_service_type = os.getenv("ADK_E2E_MEMORY_SERVICE", "in_memory").lower()

    # Initialize Services
    session_service = InMemorySessionService()
    memory_service: BaseMemoryService  # Use BaseMemoryService for type hint

    if memory_service_type == "vertex_ai_rag" and gcp_project and gcp_location and rag_corpus_id:
        logger.info(f"Using VertexAiRagMemoryService (Corpus ID: {rag_corpus_id}) - NOTE: Ensure constructor is correct")
        try:
            # Attempting initialization without rag_corpus_id first
            # memory_service = VertexAiRagMemoryService(rag_corpus_id=rag_corpus_id) # type: ignore
            # Check ADK documentation for correct VertexAiRagMemoryService constructor arguments
            memory_service = VertexAiRagMemoryService()
        except ImportError:
            logger.error("google-adk[vertexai] is required for VertexAiRagMemoryService.")
            sys.exit(1)
    elif memory_service_type == "json_file" and json_path_e2e:
        logger.info(f"Using JsonFileMemoryService with path: {json_path_e2e}")
        memory_service = JsonFileMemoryService(filepath=json_path_e2e)
    else:  # Default to in_memory
        if memory_service_type != "in_memory":
            logger.warning(f"Invalid or incomplete config for ADK_E2E_MEMORY_SERVICE='{memory_service_type}'. Defaulting to InMemoryMemoryService.")
        logger.info("Using InMemoryMemoryService.")
        memory_service = InMemoryMemoryService()

    # Configure the runner
    runner = Runner(
        agent=root_agent,
        app_name=app_name,
        session_service=session_service,
        memory_service=memory_service,  # Inject the chosen memory service
    )

    # --- Create the session ---
    # Use consistent IDs for piped execution unless overridden
    session_id = os.getenv("ADK_E2E_SESSION_ID", "e2e_piped_session")
    user_id = os.getenv("ADK_E2E_USER_ID", "e2e_piped_user")
    logger.info(f"Ensuring session exists: user='{user_id}', session='{session_id}' for app='{app_name}'")
    session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)

    # --- Process Single Input from Stdin ---
    # logger.info(f"Processing single input for agent '{root_agent.name}', session '{session_id}'...") # Already logged by session creation
    try:
        # Read the first line from stdin directly (blocking)
        first_line = sys.stdin.readline().strip()

        if not first_line or first_line.lower() in ["exit", "quit"]:
            logger.info("No input or exit command received. Exiting.")
            return  # Exit cleanly

        logger.debug(f"Input received: {first_line}")  # Use debug for raw input
        user_message = Content(parts=[Part(text=first_line)], role="user")

        # Call runner.run() once
        # final_text = "(No response found)"
        run_complete = False
        # Change back to regular 'for' loop as runner.run seems to return sync generator
        for event in runner.run(  # type: ignore # Linter struggles with runner.run generator type
            user_id=user_id, session_id=session_id, new_message=user_message
        ):
            run_complete = True
            # Check for the standard event.content attribute
            final_text_found_in_event = False
            if hasattr(event, "content") and event.content and hasattr(event.content, "parts") and event.content.parts:
                try:
                    response_parts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text is not None]  # Ensure p.text is not None
                    response_text = "".join(response_parts)
                    if response_text:
                        # Print final agent response clearly
                        # Use print directly for final output, or logger.info if logs are primary output
                        print(f"{response_text}")  # Keep final output clean
                        # logger.info(f"Agent Response: {response_text}") # Alternative: Log final output
                        # final_text = response_text
                        final_text_found_in_event = True
                except Exception as e:
                    # Log errors and raw event structure at debug level
                    logger.debug(f"Error processing event.content.parts: {e} - Event: {event}", exc_info=True)

            if not final_text_found_in_event:
                # Log raw event structure at debug level if no text found
                logger.debug(f"Agent Event (raw structure): {event}")

        if not run_complete:
            print("Agent: (No response generated)")

    except EOFError:
        logger.info("EOF received, exiting.")
    except KeyboardInterrupt:
        logger.info("Interrupted, exiting.")
    finally:
        # --- Explicitly save memory state ---
        # Retrieve the latest state of the session directly from the session service.
        # Then, update the memory service's internal state and force a save.
        # This bypasses the standard add_session_to_memory flow which might not be
        # correctly triggered or populated by the runner in this non-interactive script context.
        try:
            completed_session = session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
            # --- DETAILED LOGGING ---
            logger.info(f"Retrieved session object in finally block. Type: {type(completed_session)}")
            if completed_session:
                logger.info(f"Attributes via dir(): {dir(completed_session)}")
                try:
                    # Try dumping if it's a Pydantic model
                    logger.info(f"Session content via model_dump(): {completed_session.model_dump()}")
                except AttributeError:
                    logger.info("Session object does not have model_dump().")
                except Exception as dump_err:
                    logger.info(f"Error during model_dump(): {dump_err}")
            else:
                logger.info("completed_session object is None.")
            # --- END DETAILED LOGGING ---

            # logger.debug(f"Retrieved session object content: {completed_session}") # Keep debug for full object
            if completed_session and isinstance(memory_service, JsonFileMemoryService):  # Check type before accessing private members
                logger.info(f"Explicitly updating session {session_id} in JsonFileMemoryService.")
                # Directly update the internal dict
                # Use try-except around potentially failing attribute access
                try:
                    key = memory_service._get_session_key(completed_session)
                    memory_service._sessions[key] = completed_session
                    logger.info(f"Forcing save to JSON file: {memory_service.filepath}")
                    memory_service._save_to_json()  # Force save
                except AttributeError as ae:
                    logger.error(f"AttributeError accessing session attributes needed for saving: {ae}")
                except Exception as save_err:
                    logger.error(f"Unexpected error updating/saving session in memory service: {save_err}")
            elif completed_session:
                logger.warning(f"Memory service is not JsonFileMemoryService ({type(memory_service)}), cannot force save.")
            else:
                logger.warning(f"Could not retrieve session {session_id} from session service in finally block.")
        except Exception as e:
            logger.error(f"Error during final session saving for {session_id}: {e}", exc_info=True)
        # ------------------------------------------
    logger.info("Agent run finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ADK Agent E2E Test Script")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level (default: INFO)")
    args = parser.parse_args()

    # Read ENV VARS before calling main()
    memory_service_type_env = os.getenv("ADK_E2E_MEMORY_SERVICE", "in_memory").lower()
    gcp_project_env = os.getenv("ADK_E2E_GCP_PROJECT")
    gcp_location_env = os.getenv("ADK_E2E_GCP_LOCATION")

    # Ensure GOOGLE_GENAI_USE_VERTEXAI is set if using Vertex AI models/services
    if memory_service_type_env == "vertex_ai_rag":
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
        if "GOOGLE_CLOUD_PROJECT" not in os.environ and gcp_project_env:
            os.environ["GOOGLE_CLOUD_PROJECT"] = gcp_project_env
        if "GOOGLE_CLOUD_LOCATION" not in os.environ and gcp_location_env:
            os.environ["GOOGLE_CLOUD_LOCATION"] = gcp_location_env

    # Run the main async function
    try:
        # Pass parsed log level to main
        asyncio.run(main(log_level_arg=args.log_level))
    except Exception as e:
        logger.critical(f"Unhandled exception during script execution: {e}", exc_info=True)
        sys.exit(1)
