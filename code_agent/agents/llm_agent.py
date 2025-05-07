"""
LLM Agent stub module to avoid missing module errors.
"""

# Re-export from actual implementation
try:
    from google.adk.agents import Agent as LlmAgent
except ImportError:

    class LlmAgent:
        """Stub LlmAgent class to prevent import errors."""

        pass
