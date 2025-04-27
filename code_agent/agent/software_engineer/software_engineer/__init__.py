"""
Software Engineer Agent.

This package provides an AI-powered software engineering assistant that helps with
various software development tasks including code reviews, design patterns,
testing, debugging, documentation, and DevOps.
"""

# Importing root_agent here causes circular dependency when structure is refactored for adk run
# from ..agent import root_agent

# __all__ = ["root_agent"]

# NOTE: SWITCH TO ADK WEB or COMMENT OUT FOR ADK RUN
from . import agent
