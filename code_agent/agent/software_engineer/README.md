# Software Engineer Agent

This sample demonstrates the use of Agent Development Kit to create an AI-powered software engineering assistant. The Software Engineer Agent helps developers with various tasks including code reviews, design pattern recommendations, test generation, debugging assistance, and documentation.

## Overview

The Software Engineer Agent consists of multiple specialized sub-agents, each responsible for a specific aspect of software development:

1. **Code Review Agent**: Reviews code, identifies issues, and suggests improvements
2. **Design Pattern Agent**: Recommends design patterns for specific problems
3. **Testing Agent**: Helps generate test cases and testing strategies
4. **Debugging Agent**: Assists with debugging issues
5. **Documentation Agent**: Helps create documentation
6. **DevOps Agent**: Provides guidance on CI/CD, deployment

## Agent Details

| Feature | Description |
| --- | --- |
| **Interaction Type:** | Conversational |
| **Complexity:**  | Advanced |
| **Agent Type:**  | Multi Agent |
| **Components:**  | Tools, AgentTools, Memory |
| **Vertical:**  | Software Development |

### Agent Architecture

The Software Engineer Agent uses a hierarchical architecture with a root agent orchestrating specialized sub-agents:

```
root_agent
├── code_review_agent
├── design_pattern_agent
├── testing_agent
├── debugging_agent
├── documentation_agent
└── devops_agent
```

### Component Details

* **Agents:**
  * `code_review_agent` - Reviews code, identifies issues, and suggests improvements
  * `design_pattern_agent` - Recommends design patterns for specific problems
  * `testing_agent` - Helps generate test cases and testing strategies
  * `debugging_agent` - Assists with debugging issues
  * `documentation_agent` - Helps create documentation
  * `devops_agent` - Provides guidance on CI/CD, deployment
* **Tools:**
  * `code_analysis_tool` - Analyzes code for patterns, complexity, and potential issues
  * `memory_tool` - Stores and retrieves information about the project context
* **AgentTools:**
  * `pattern_recommendation_tool` - Recommends design patterns for specific problems
  * `test_generation_tool` - Generates test cases based on code
  * `documentation_generation_tool` - Generates documentation for code
  * `debugging_assistance_tool` - Assists with debugging issues
  * `deployment_assistance_tool` - Provides guidance on deployment

## Setup and Installation

### Folder Structure
```
.
├── README.md
├── pyproject.toml
├── software_engineer/
│   ├── shared_libraries/
│   ├── tools/
│   └── sub_agents/
│       ├── code_review/
│       ├── design_pattern/
│       ├── testing/
│       ├── debugging/
│       ├── documentation/
│       └── devops/
├── tests/
│   └── unit/
├── eval/
│   └── data/
└── deployment/
```

### Prerequisites

- Python 3.11+
- Google Cloud Project (for Vertex AI integration)
- Google Agent Development Kit 1.0+
- Poetry: Install Poetry by following the instructions on the official Poetry [website](https://python-poetry.org/docs/)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/software_engineer.git
   cd software_engineer
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Set the required environment variables

4. Authenticate your GCloud account:
   ```bash
   gcloud auth application-default login
   ```

5. Activate the virtual environment:
   ```bash
   poetry shell
   ```

## Running the Agent

### Configuring File Edit Approvals

By default, for safety, the agent requires user confirmation before creating or modifying any file. When the agent needs to edit a file, it will first show you the proposed path and content and ask for your approval.

You can change this behavior for your current session:

*   **To disable approvals (allow direct edits):** Tell the agent: `"Disable file edit approvals for this session."` (The agent should use the `configure_edit_approval` tool with `require_approval=False`).
*   **To re-enable approvals:** Tell the agent: `"Enable file edit approvals for this session."` (The agent should use the `configure_edit_approval` tool with `require_approval=True`).

### Using `adk`

Start the agent locally:

```bash
adk run software_engineer
```

Or use the web interface:

```bash
adk web
```

### Sample Agent Interaction

Example usage:
- "Can you review my code for potential issues?"
- "I need help implementing a factory pattern in Python"
- "Generate unit tests for this function"
- "Help me debug this error"
- "Create documentation for this module"
- "Recommend a CI/CD pipeline for my project"

## Running Tests

```bash
poetry install --with dev
pytest
``` 