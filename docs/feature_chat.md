# Chat Feature

This document describes the interactive chat functionality in Code Agent, including conversation management, special commands, and history persistence.

## Starting a Chat Session

To start an interactive chat session with Code Agent:

```bash
# Start a chat with default provider and model
code-agent chat

# Start a chat with a specific provider
code-agent --provider openai chat

# Start a chat with a specific model
code-agent --provider anthropic --model claude-3-opus chat
```

The chat session will start in your terminal with a welcome message and prompt for input.

## Special Commands

Chat mode supports several special commands that begin with a forward slash `/`:

| Command | Description |
|---------|-------------|
| `/help` | Display a list of available commands |
| `/clear` | Clear the current conversation history |
| `/exit` or `/quit` | Exit the chat session |

Example usage:

```
You: /help
Agent: Available commands:
  /help - Show this help message
  /clear - Clear conversation history
  /exit or /quit - Exit the chat session
```

## Conversation History

### Persistence

Chat history is automatically saved between sessions:

- History files are stored in `~/.config/code-agent/history/`
- Files are named with timestamps: `chat_YYYYMMDD_HHMMSS.json`
- The most recent history is automatically loaded when starting a new chat

### Saving Behavior

History is saved in these scenarios:
- When you exit the chat normally with `/exit` or `/quit`
- When you press `Ctrl+C` to interrupt the chat
- If an unexpected error occurs (to preserve conversation)

### Clearing History

To clear the current conversation history:

```
You: /clear
Agent: History cleared.
```

This clears the current session history but doesn't delete saved history files.

## Multi-turn Conversations

Chat mode maintains context across multiple messages, allowing for more natural interactions:

```
You: Write a function to calculate the factorial of a number.
Agent: [Provides factorial function]

You: Can you modify it to use recursion?
Agent: [Provides recursive factorial function, referencing the previous implementation]

You: Add error handling for negative numbers.
Agent: [Adds error handling to the recursive function]
```

Benefits of multi-turn conversations:
- The agent remembers previous context
- Follow-up questions work naturally
- Complex tasks can be broken down into steps
- Refinements and iterations are more efficient

## Tool Usage in Chat Mode

All of Code Agent's tools are available in chat mode:

- **Reading files**: Ask to read files from your system
- **Editing files**: The agent can propose changes with confirmation
- **Running commands**: The agent can execute shell commands with confirmation

Example usage:

```
You: Show me the content of README.md
Agent: [Shows file content using read_file tool]

You: Create a new file called example.py with a simple hello world function
Agent: [Proposes file creation with apply_edit tool]

You: List all Python files in the current directory
Agent: [Executes command using run_native_command tool]
```

## Best Practices for Chat Mode

1. **Use chat mode for iterative tasks**:
   - Multi-step processes that need context
   - Code refinement and improvement
   - Debugging sessions

2. **Break complex requests into smaller steps**:
   - Ask for one thing at a time for best results
   - Build on previous responses

3. **Manage history for best performance**:
   - Use `/clear` when starting a new, unrelated task
   - Start a fresh session if the context window gets too full

4. **Provide feedback**:
   - Tell the agent when its response is helpful or not
   - Clarify your requirements when needed

5. **Exit properly**:
   - Use `/exit` or `/quit` to ensure history is saved
   - Avoid abruptly closing the terminal

## Troubleshooting

- **Agent doesn't remember context**: The conversation may have exceeded the context window. Use `/clear` and start the specific task again.
- **History not loading**: Check if the history files exist in `~/.config/code-agent/history/`
- **Agent seems confused**: Try clearing history with `/clear` to start fresh
- **Chat session crashes**: Look for error messages. In most cases, history should be saved automatically.

## Sequence Diagram

The following sequence diagram illustrates the chat interaction flow from when a user submits a query to when they receive a response:

```mermaid
sequenceDiagram
    participant User
    participant CLI as CLI Application (cli/main.py)
    participant Agent as CodeAgent (agent/)
    participant LiteLLM as LLM Interface
    participant Provider as LLM Provider
    participant Tools as Tool Modules (tools/)

    User->>CLI: Submit query
    CLI->>Agent: run_turn(prompt)

    Agent->>Agent: add_user_message(prompt)
    Agent->>Agent: Create system message
    Agent->>Agent: add_system_message(instructions)

    Agent->>LiteLLM: Request completion with history
    LiteLLM->>Provider: Make API request
    Provider->>LiteLLM: Return response
    LiteLLM->>Agent: Return completion

    alt Response contains tool calls
        Agent->>Tools: Execute tool call
        Tools->>Agent: Return tool result
        Agent->>LiteLLM: Request follow-up completion with tool result
        LiteLLM->>Provider: Make API request
        Provider->>LiteLLM: Return response
        LiteLLM->>Agent: Return follow-up completion
    end

    Agent->>Agent: add_assistant_message(response)
    Agent->>CLI: Return final response
    CLI->>User: Display response
```

This diagram shows:
1. The user submitting a query to the CLI
2. The CLI passing the query to the CodeAgent
3. The agent preparing the conversation history and instructions
4. The agent requesting a completion from the LLM provider
5. The handling of tool calls if present in the response
6. The final response being returned to the user
