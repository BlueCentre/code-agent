# End-to-End Testing

This directory contains end-to-end tests for the code-agent CLI.

## Ollama Integration Tests

The Ollama integration tests demonstrate how to interact with local Ollama models.

### Files

- `test_ollama_integration.py` - Main test script that:
  1. Tests direct Ollama API connectivity using the `code_agent.agents.ollama` package
  2. Creates a simple agent that demonstrates Ollama works while using Gemini as a fallback

### Running Tests

```bash
# Run the Ollama integration test
python -m tests.e2e.test_ollama_integration
```

### Integration Challenges

See the detailed documentation in `docs/testing_adk_cli_e2e.md` for an explanation of the challenges encountered when trying to integrate Ollama with the Google ADK. 