# Software Engineer LLaMa LiteLLM Agent

This agent is meant to use LLaMa models via LiteLLM for the Software Engineer agent.

## Model Compatibility

This agent is compatible with both Gemini and LLaMA models, with adaptations to handle different argument formats:

- **Gemini models**: Pass arguments to tool functions as actual Python dictionaries
- **LLaMA models**: Pass arguments to tool functions as string representations of dictionaries (e.g., `"{'action': 'list'}"`)

The tool functions maintain type annotations of `args: dict` for ADK's automatic function calling, while internally using a parsing utility to handle both dictionary and string representations:

```python
def parse_args(args):
    """Utility function to parse arguments for tool functions.
    
    Handles both dictionary and string arguments for compatibility with 
    different LLM models (Gemini uses dict, LLaMA uses str).
    """
    if isinstance(args, dict):
        return args
    elif isinstance(args, str):
        try:
            # Try parsing as JSON first
            try:
                return json.loads(args)
            except json.JSONDecodeError:
                # If not valid JSON, try parsing as a Python literal
                return ast.literal_eval(args)
        except (ValueError, SyntaxError, AttributeError) as e:
            raise ValueError(f"Failed to parse arguments: {e}")
    else:
        raise ValueError(f"Unsupported args type: {type(args)}")
```

This approach keeps the function signatures simple and compatible with ADK's parameter parsing requirements, while still supporting the different argument formats that various models might provide.

### Implementation in Tool Functions

Tool functions are defined with standard type annotations for ADK compatibility:

```python
def configure_shell_whitelist(args: dict, tool_context: ToolContext) -> ConfigureShellWhitelistOutput:
    """Manages the whitelist of shell commands that bypass approval.

    Args:
        args (dict): A dictionary containing:
            action (Literal["add", "remove", "list", "clear"]): The action.
            command (Optional[str]): The command for add/remove.
            Also handles string representation of arguments for LLaMA models.
        tool_context (ToolContext): The context for accessing session state.
    """
    try:
        args_dict = parse_args(args)
        action = args_dict.get("action")
        command = args_dict.get("command")
    except ValueError as e:
        return ConfigureShellWhitelistOutput(status=str(e))
    
    # Function implementation continues...
```

## Agent Setup Instructions

This sample demonstrates the use of Agent Development Kit to create an AI-powered software engineering assistant. The Software Engineer Agent helps developers with various tasks including code reviews, design pattern recommendations, test generation, debugging assistance, and documentation.

## Overview

The Software Engineer Agent consists of multiple specialized sub-agents, each responsible for a specific aspect of software development:

1. **Code Review Agent**: Reviews code, identifies issues, and suggests improvements
2. **Code Quality Agent**: Performs static analysis and provides detailed code quality improvements
3. **Design Pattern Agent**: Recommends design patterns for specific problems
4. **Testing Agent**: Helps generate test cases and testing strategies
5. **Debugging Agent**: Assists with debugging issues
6. **Documentation Agent**: Helps create documentation
7. **DevOps Agent**: Provides guidance on CI/CD, deployment

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
├── code_quality_agent
├── design_pattern_agent
├── testing_agent
├── debugging_agent
├── documentation_agent
└── devops_agent
```

### Component Details

* **Agents:**
  * `code_review_agent` - Reviews code, identifies issues, and suggests improvements
  * `code_quality_agent` - Performs static analysis and provides detailed code quality metrics and improvements
  * `design_pattern_agent` - Recommends design patterns for specific problems
  * `testing_agent` - Helps generate test cases and testing strategies
  * `debugging_agent` - Assists with debugging issues
  * `documentation_agent` - Helps create documentation
  * `devops_agent` - Provides guidance on CI/CD, deployment
* **Tools:**
  * `analyze_code_tool` - Analyzes code for patterns, complexity, and potential issues using multiple static analysis engines
  * `get_analysis_issues_by_severity_tool` - Filters code issues by severity level
  * `suggest_code_fixes_tool` - Suggests specific fixes for identified code issues
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

3. Install code analysis tool dependencies:
   ```bash
   pip install -r code_analysis_requirements.txt
   ```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Set the required environment variables

5. Authenticate your GCloud account:
   ```bash
   gcloud auth application-default login
   ```

6. Activate the virtual environment:
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
- "Analyze the code quality in this file"
- "Check this file for security vulnerabilities"
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