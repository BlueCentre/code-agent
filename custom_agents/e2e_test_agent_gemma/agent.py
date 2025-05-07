"""
Your local Ollama agent.
"""

from google.adk.agents import Agent

from code_agent.agents.ollama.adk_integration import OllamaLlm

# Create custom Ollama LLM for ADK
ollama_llm = OllamaLlm(
    model="gemma3:latest",  # Use your preferred Ollama model
    base_url="http://localhost:11434",  # Adjust if your Ollama server is on a different address
)

# Initialize agent with the custom LLM
root_agent = Agent(
    model=ollama_llm,  # Use the OllamaLlm instance instead of model name string
    name="root_agent",
    description="A helpful assistant powered by a local Ollama model.",
    instruction="Answer user questions to the best of your knowledge.",
    # Note: To use Ollama, ensure your configuration is set up with:
    # default_provider: "ollama" in ~/.config/code-agent/config.yaml
    # or use --provider ollama when running commands
)


# If you encounter ADK integration issues, you can use the direct provider:
"""
from code_agent.agents.ollama import OllamaDirectProvider

# Initialize with your model and Ollama server URL
ollama_provider = OllamaDirectProvider(
    model="gemma3:latest",
    base_url="http://localhost:11434"
)

# Example usage:
# response = ollama_provider.generate("What is your name?")
# print(response)
"""
