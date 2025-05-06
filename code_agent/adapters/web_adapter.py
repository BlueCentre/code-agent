"""
Web Server Adapter - Provides compatibility with Google ADK CLI web server functionality.

This module adapts our Typer-based CLI to work with ADK CLI web server patterns and components.
It handles agent loading, session management, and FastAPI configuration for web and API server commands.
"""

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.types import Lifespan

from code_agent.adapters.adk_adapter import ADK_AVAILABLE, adk_adapter

logger = logging.getLogger(__name__)


# Define request/response models for API
class ChatRequest(BaseModel):
    """Chat request model."""

    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""

    message: str
    session_id: str


def get_static_dir() -> Path:
    """
    Get the directory containing static assets for the web UI.

    Returns:
        Path to the static directory
    """
    return Path(__file__).parent.parent / "static"


def create_web_app(
    agents_dir: str,
    session_db_url: str = "",
    allow_origins: Optional[List[str]] = None,
    lifespan: Optional[Lifespan[FastAPI]] = None,
    trace_to_cloud: bool = False,
    with_ui: bool = True,
) -> FastAPI:
    """
    Create a FastAPI application for the web UI and API.

    Args:
        agents_dir: Directory containing agent definitions
        session_db_url: Database URL for session storage
        allow_origins: Additional origins to allow for CORS
        lifespan: Optional lifespan context manager
        trace_to_cloud: Whether to enable cloud tracing
        with_ui: Whether to include the web UI

    Returns:
        FastAPI application
    """
    # Create lifespan context manager if not provided
    if not lifespan:

        @asynccontextmanager
        async def default_lifespan(app: FastAPI):
            # Setup code
            logger.info(f"Starting server with agents directory: {agents_dir}")
            yield
            # Cleanup code
            logger.info("Server shutting down")

        lifespan = default_lifespan

    # Create the FastAPI app
    app = FastAPI(lifespan=lifespan)

    # Add CORS middleware
    origins = [
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
    ]

    if allow_origins:
        origins.extend(allow_origins)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files if UI is enabled
    if with_ui:
        static_dir = get_static_dir()
        if static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")
        else:
            logger.warning(f"Static directory not found at {static_dir}. Web UI will not be available.")

    # Root endpoint - redirect to web UI if enabled
    if with_ui:

        @app.get("/", response_class=HTMLResponse)
        async def root():
            """Redirect to the web UI."""
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Code Agent Web Interface</title>
                <meta http-equiv="refresh" content="0;url=/static/index.html">
            </head>
            <body>
                <p>Redirecting to <a href="/static/index.html">Web UI</a>...</p>
            </body>
            </html>
            """
    else:

        @app.get("/")
        async def root():
            """API root endpoint."""
            return {"message": "Code Agent API Server"}

    # Health check endpoint
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}

    # Configuration endpoint
    @app.get("/api/config")
    async def get_config_endpoint():
        """Get server configuration."""
        return {
            "agents_dir": agents_dir,
            "session_db_url": session_db_url or "memory://",
        }

    # List available agents
    @app.get("/api/agents")
    async def list_agents():
        """List available agents."""
        agents_path = Path(agents_dir)
        if not agents_path.exists() or not agents_path.is_dir():
            raise HTTPException(status_code=404, detail=f"Agents directory not found: {agents_dir}")

        agents = []
        for item in agents_path.iterdir():
            agent_file = item / "agent.py"
            if item.is_dir() and agent_file.exists():
                try:
                    # Check if it's a valid agent
                    agent_name = item.name

                    with open(agent_file, "r") as f:
                        content = f.read()
                        # Look for Agent class or known patterns
                        if "Agent(" in content or "class" in content:
                            agents.append({"id": agent_name, "name": agent_name, "path": str(item), "file": str(agent_file)})
                except Exception as e:
                    logger.warning(f"Error reading agent file {agent_file}: {e}")

        return {"agents": agents}

    # Chat with an agent
    @app.post("/api/chat/{agent_id}", response_model=ChatResponse)
    async def chat_with_agent(
        agent_id: str,
        request: ChatRequest = Body(...),
    ):
        """Chat with an agent."""
        agent_path = Path(agents_dir) / agent_id
        agent_file = agent_path / "agent.py"

        if not agent_file.exists():
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

        try:
            # Load the agent
            agent = adk_adapter.load_agent(agent_path)
            if not agent:
                raise HTTPException(status_code=500, detail="Failed to load agent")

            # Generate a session ID if not provided
            session_id = request.session_id or str(uuid.uuid4())

            # Create user ID (fixed for now)
            user_id = "web_user"

            # Create or get session
            session = None
            if ADK_AVAILABLE and adk_adapter.session_service:
                if request.session_id:
                    try:
                        session = adk_adapter.session_service.get_session(app_name=agent_id, user_id=user_id, session_id=session_id)
                    except Exception:
                        # If session doesn't exist, create a new one
                        session = None

                if not session:
                    session = adk_adapter.create_session(app_name=agent_id, user_id=user_id)
                    session_id = session.id

            # Create content
            content = adk_adapter.create_content(request.message)

            # Get runner
            runner = adk_adapter.get_runner(agent, agent_id)

            if runner:
                # Use ADK runner
                response_text = ""
                async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                    if event.content and event.content.parts:
                        if text := "".join(part.text or "" for part in event.content.parts):
                            if event.author != "user":  # Skip echoing user message
                                response_text += text
            else:
                # Fallback to direct agent call if runner not available
                if hasattr(agent, "generate_content"):
                    response = agent.generate_content(request.message)
                    response_text = response.text
                else:
                    # Try calling the agent directly
                    try:
                        response_text = str(agent(request.message))
                    except Exception as e:
                        logger.exception(f"Error calling agent: {e}")
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to generate response: {e!s}",
                        )

            return ChatResponse(
                message=response_text,
                session_id=session_id,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error in chat endpoint: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process chat request: {e!s}",
            )

    # Streaming chat with an agent
    @app.post("/api/chat/{agent_id}/stream")
    async def stream_chat_with_agent(
        agent_id: str,
        request: ChatRequest = Body(...),
    ):
        """Chat with an agent with streaming response."""
        agent_path = Path(agents_dir) / agent_id
        agent_file = agent_path / "agent.py"

        if not agent_file.exists():
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

        try:
            # Load the agent
            agent = adk_adapter.load_agent(agent_path)
            if not agent:
                raise HTTPException(status_code=500, detail="Failed to load agent")

            # Generate a session ID if not provided
            session_id = request.session_id or str(uuid.uuid4())

            # Create user ID (fixed for now)
            user_id = "web_user"

            # Create or get session
            session = None
            if ADK_AVAILABLE and adk_adapter.session_service:
                if request.session_id:
                    try:
                        session = adk_adapter.session_service.get_session(app_name=agent_id, user_id=user_id, session_id=session_id)
                    except Exception:
                        # If session doesn't exist, create a new one
                        session = None

                if not session:
                    session = adk_adapter.create_session(app_name=agent_id, user_id=user_id)
                    session_id = session.id

            # Create content
            content = adk_adapter.create_content(request.message)

            # Get runner
            runner = adk_adapter.get_runner(agent, agent_id)

            if not runner:
                raise HTTPException(status_code=501, detail="Streaming not supported without ADK Runner")

            # Define async generator for streaming
            async def event_generator():
                try:
                    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                        if event.content and event.content.parts:
                            if text := "".join(part.text or "" for part in event.content.parts):
                                if event.author != "user":  # Skip echoing user message
                                    # Format as server-sent event
                                    yield f"data: {text}\n\n"

                    # End with session ID
                    yield f"data: [SESSION_ID]{session_id}[/SESSION_ID]\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logger.exception(f"Error in streaming: {e}")
                    yield f"data: [ERROR]{e!s}[/ERROR]\n\n"
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error in streaming chat endpoint: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process streaming chat request: {e!s}",
            )

    # Error handler
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions."""
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {exc!s}"},
        )

    return app


# Utility function to run a FastAPI app with Uvicorn
def run_web_server(
    app: FastAPI,
    host: str = "0.0.0.0",
    port: int = 8000,
    log_level: str = "info",
    reload: bool = False,
):
    """
    Run a FastAPI app with Uvicorn.

    Args:
        app: FastAPI application
        host: Host to listen on
        port: Port to listen on
        log_level: Logging level
        reload: Whether to enable auto-reload
    """
    import uvicorn

    # Configure and run the server
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level=log_level.lower(),
        reload=reload,
    )
    server = uvicorn.Server(config)

    try:
        # Run the server (blocking call)
        server.run()
    except Exception as e:
        logger.exception(f"Error running web server: {e}")
        raise
