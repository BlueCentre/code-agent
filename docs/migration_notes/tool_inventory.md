# Tool Inventory for Google ADK Migration

## Overview

This document catalogs all existing tools in the codebase that need to be migrated to the Google ADK framework. Each tool is categorized based on complexity and migration difficulty to help with planning.

## Tool Categories

- **Category 1**: Simple tools with minimal dependencies, easiest to migrate
- **Category 2**: Moderately complex tools with some dependencies
- **Category 3**: Complex tools with many dependencies or external integrations

## Tool Inventory

### File Operations

| Tool Function | Description | Category | Dependencies | Notes |
|---------------|-------------|----------|--------------|-------|
| `read_file` | Reads contents of a file | 1 | `os`, `pathlib` | Simple file I/O |
| `edit_file` | Modifies contents of a file | 2 | `os`, `pathlib` | Handles file paths and content manipulation |
| `list_dir` | Lists directory contents | 1 | `os`, `pathlib` | Simple directory listing |
| `file_search` | Searches for files with pattern matching | 2 | `glob`, `pathlib` | Fuzzy file matching |
| `delete_file` | Deletes a file | 1 | `os`, `pathlib` | Simple file removal |

### Code Analysis

| Tool Function | Description | Category | Dependencies | Notes |
|---------------|-------------|----------|--------------|-------|
| `codebase_search` | Semantic search of codebase | 3 | External search index | Requires semantic search capabilities |
| `grep_search` | Pattern-based code search | 2 | `re`, subprocess | Calls external grep-like utilities |

### Terminal & Execution

| Tool Function | Description | Category | Dependencies | Notes |
|---------------|-------------|----------|--------------|-------|
| `run_terminal_cmd` | Executes terminal commands | 3 | `subprocess`, security handlers | Requires careful security handling |

### Web & External Services

| Tool Function | Description | Category | Dependencies | Notes |
|---------------|-------------|----------|--------------|-------|
| `web_search` | Performs web searches | 3 | External API, rate limiting | External service integration |
| `mcp_puppeteer` tools | Web browser automation | 3 | External browser control | Complex external integration |
| `mcp_sonarqube` tools | SonarQube integration | 3 | External API | Complex external integration |

### Memory & Knowledge Graph

| Tool Function | Description | Category | Dependencies | Notes |
|---------------|-------------|----------|--------------|-------|
| `mcp_memory_*` tools | Knowledge graph operations | 3 | Graph database, state management | Complex state management |

## Migration Approach

### Strategy by Category

1. **Category 1 Tools**:
   - Direct 1:1 mapping to ADK FunctionTool
   - Minimal refactoring needed
   - Ideal for initial migration phase

2. **Category 2 Tools**:
   - Require some refactoring to match ADK patterns
   - Will need more thorough testing
   - Should be migrated after Category 1

3. **Category 3 Tools**:
   - Will require significant refactoring
   - May need architectural changes
   - Should be migrated last with careful integration testing

## Next Steps

1. Begin with Category 1 tools to establish patterns
2. Create unit tests for all tools before migration
3. Document any ADK-specific considerations for each tool
4. Track migration progress in this document

## Migration Progress Tracking

| Tool Function | Original Location | ADK Implementation | Status | Notes |
|---------------|-------------------|-------------------|--------|-------|
| `read_file` | `code_agent/tools/file_operations.py` | Not started | 🔴 Not started | |
| `edit_file` | `code_agent/tools/file_operations.py` | Not started | 🔴 Not started | |
| `list_dir` | `code_agent/tools/file_operations.py` | Not started | 🔴 Not started | |
| (Add more as inventory progresses) | | | | | 