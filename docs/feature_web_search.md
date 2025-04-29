# Web Search Feature

This document describes the web search capability provided by the Code Agent.

## Overview

Code Agent leverages the Google Agent Development Kit (ADK) which includes a built-in `google_search` tool. This allows the agent to access and retrieve up-to-date information from the web when its internal knowledge is insufficient or outdated.

## Functionality

When the agent determines that external information is needed to answer a query or fulfill a request, it can utilize the `google_search` tool.

Key capabilities include:
- **Finding Current Information:** Accessing real-time data like news, events, or recent technical documentation.
- **Answering Knowledge Gaps:** Retrieving information not present in the agent's training data.
- **Research:** Gathering external context for analysis or problem-solving.

## Usage

Users typically don't need to explicitly invoke the web search. The agent intelligently decides when to use the `google_search` tool based on the prompt.

Examples where web search might be used:

```bash
# Query about current events
code-agent run "What were the major technology announcements last week?"

# Query about recent software releases
code-agent run "What are the key features in the latest Python release?"

# Query requiring external knowledge
code-agent run "Summarize the main points of the Model Context Protocol (MCP)."
```

You can also explicitly ask the agent to perform a search:
```bash
code-agent run "Search the web for reviews of the latest Gemini models."
```

## Configuration

The `google_search` tool is part of the standard ADK toolset. There are no specific configuration options within Code Agent (`config.yaml`) to enable or disable this tool separately.

## Security and Limitations

- Search results are processed by the agent and are subject to the LLM's interpretation.
- The quality and relevance of search results depend on the underlying search engine used by the ADK tool.
- The agent's ability to effectively use search depends on the prompt and the LLM's reasoning capabilities. 