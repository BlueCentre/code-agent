# Memory Management in Code Agent

This document explains the implementation of long-term knowledge (memory) in the Code Agent, which follows the Google ADK Memory pattern.

## Overview

Code Agent now supports long-term knowledge through the `MemoryService` abstraction, allowing conversations and data to be stored, retrieved, and searched across multiple sessions. The memory system is designed to work in tandem with the session management system.

## Memory Architecture

The memory implementation consists of several key components:

### 1. Memory Types

Our implementation supports several distinct memory types:

- **Short-Term Memory**: Stores recent user interactions and queries
- **Long-Term Memory**: Persists important information across multiple sessions
- **Working Memory**: Tracks active tool executions and their results
- **Semantic Memory**: Stores conceptual knowledge (associations, categories, etc.)
- **Episodic Memory**: Records sequences of events and their temporal relationships

### 2. Memory Service Implementation

#### `BaseMemoryService`

An abstract base class that defines the interface for memory services:

```python
class BaseMemoryService:
    """Base class for memory services that store and retrieve long-term knowledge."""
    
    def add_session_to_memory(self, session: Session) -> None:
        """Add session information to long-term memory."""
        raise NotImplementedError("Subclasses must implement add_session_to_memory")
    
    def search_memory(self, app_name: str, user_id: str, query: str) -> List[Dict[str, Any]]:
        """Search memory for information relevant to the query."""
        raise NotImplementedError("Subclasses must implement search_memory")
```

#### `InMemoryMemoryService`

A concrete implementation that stores memory in-memory:

```python
class InMemoryMemoryService(BaseMemoryService):
    """Memory service that stores session information in memory and performs basic keyword matching for searches."""
    
    def __init__(self):
        """Initialize the in-memory memory service."""
        self._memories: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
```

This implementation:
- Stores memories in a nested dictionary structure by app name and user ID
- Extracts text content from session events
- Performs basic keyword matching for memory searches
- Scores results by relevance based on term matches

### 3. Memory Tool

The `load_memory` tool allows agents to query the memory service:

```python
async def load_memory(query: str, app_name: str = "code_agent", user_id: str = "default_user") -> str:
    """Load relevant information from long-term memory based on a search query."""
    # Get the memory service
    memory_service = get_memory_service()
    
    # Search memory for relevant information
    search_response = memory_service.search_memory(app_name, user_id, query)
```

## Integration with Agent

The memory system is integrated into the Code Agent in several places:

1. **Session Completion**: When a conversation turn completes successfully, the session is automatically saved to memory:

```python
# Save the completed session to memory for future reference
if response_text and loop_ended_naturally:
    session = await self.session_manager.get_session(self.session_id)
    get_memory_service().add_session_to_memory(session)
    verbosity_controller.show_debug("Session added to long-term memory")
```

2. **Tool Definition**: The `load_memory` tool is made available to the agent:

```python
{
    "name": "load_memory",
    "description": "Retrieves information from long-term memory based on a search query",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "The search query to find relevant information",
            },
        },
        "required": ["query"],
    },
}
```

## Usage Example

Here's how the memory system works in practice:

1. **Session Interaction**: A user interacts with the Code Agent across multiple sessions.

2. **Automatic Memory Storage**: As conversations occur, they're automatically stored in memory.

3. **Memory Querying**: In a later session, if the user asks about something discussed previously, the agent can use the `load_memory` tool to retrieve relevant information:

```
User: "What did we discuss about Python yesterday?"

Agent: (thinking) This requires information from past sessions. Let me search memory.
Agent: (using load_memory tool with query "Python discussion")

Memory Results: 
User: I'm working on a Python project.
Assistant: Great, let me know how I can help with your Python project.

Agent: "Yesterday, we discussed your Python project. You mentioned you were working on it, and I offered to help."
```

## Technical Notes

- The current implementation uses in-memory storage, which means memories are lost when the application restarts.
- The search functionality uses basic keyword matching rather than semantic similarity.
- Future enhancements could include persistent storage and vector-based semantic search. 