# Testing Strategies for Code Agent

This document outlines the approaches used for testing the Code Agent project.

## Unit Tests

-   **Location:** `tests/unit/`
-   **Purpose:** Verify the correctness of individual functions, classes, and modules in isolation.
-   **Framework:** `pytest`
-   **Execution:** `uv run pytest tests/unit/`

## Integration Tests

-   **Location:** `tests/integration/`
-   **Purpose:** Test the interaction between different components of the agent, including agent logic, tools, and potentially external services (mocked where appropriate).
-   **Framework:** `pytest`
-   **Execution:** `uv run pytest tests/integration/`

### Memory Integration Testing (`tests/integration/test_memory_integration.py`)

Testing the agent's memory capabilities requires understanding the distinction between different execution runtimes and memory service types:

*   **Execution Runtimes:**
    *   **`pytest` Environment:** When running tests programmatically using `pytest` (like in `test_memory_integration.py`), we manually instantiate the `Runner`, `SessionService`, and `MemoryService`. This gives fine-grained control but might not perfectly replicate the environment set up by the `adk run` CLI.
    *   **`adk run` CLI Environment:** When running the agent via the command line (`uv run adk run ...`), the ADK framework manages the setup of services, potentially using default configurations.

*   **`InMemoryMemoryService` Limitations:**
    *   The default `google.adk.memory.InMemoryMemoryService` stores information only within the current running process.
    *   When using `adk run` in scripts like `run_e2e_tests.sh`, each agent invocation is typically a separate process. Therefore, `InMemoryMemoryService` **cannot** be used to test *cross-session* memory recall in this E2E script because the memory is lost when each `adk run` process exits.
    *   The `Runner`, when configured with `InMemoryMemoryService` programmatically (in `pytest`), is expected to handle adding session information to the memory implicitly. However, current integration tests (`test_agent_load_memory_e2e`) show that the agent is failing to utilize the `load_memory` tool effectively in this setup, possibly due to LLM reasoning or subtle framework interactions. Debugging this specific test setup is ongoing.

*   **Current Status:**
    *   `test_memory_integration` (the original test function): Verifies lower-level memory service interactions (using a custom `get_memory_service()` potentially returning a custom wrapper or the standard service, interacting via non-standard `.add()`/`.search()`).
    *   `test_agent_load_memory_e2e`: Attempts to test the agent's use of the standard `load_memory` tool with `InMemoryMemoryService` in a programmatic `pytest` context. This test is currently **failing** because the agent does not call `load_memory` as expected.
    *   `run_e2e_tests.sh`: **Cannot** currently test cross-session memory recall due to the limitations of `InMemoryMemoryService` with the `adk run` process isolation.

*   **Future E2E Memory Testing:** To properly test cross-session memory recall in the `run_e2e_tests.sh` script, we need to investigate configuring `adk run` to use a **persistent `MemoryService`** (e.g., `VertexAiRagMemoryService`).

## End-to-End (E2E) Tests

-   **Location:** `scripts/run_e2e_tests.sh`
-   **Purpose:** Simulate user interactions with the agent via the `adk run` command-line interface, testing the complete flow from user input to agent response and side effects (like file creation or command execution).
-   **Framework:** Shell script invoking `adk run`.
-   **Execution:** `bash scripts/run_e2e_tests.sh`
-   **Limitations:** As noted above, currently cannot test cross-session memory recall using the default `InMemoryMemoryService`. 