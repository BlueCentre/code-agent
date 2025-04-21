# Consolidated Priority Task List

This document consolidates all tasks, improvements, and future enhancements for the Code Agent project into a single prioritized reference.

## Critical Priority

- **Test Suite Completion**
  - ✅ Add tests for 'chat' command (more complex due to interaction) [from planning_priorities]
  - ✅ Improve test coverage, especially for edge cases in tools [from getting_started_implementation.md] (Current: 80% coverage)
  - ✅ Complete test LLM interaction with mocked responses/tool calls [from getting_started_implementation.md]

- **Error Handling Refinement**
  - ✅ Refine error handling and user feedback for API errors, tool failures, configuration issues, and LLM runtime errors [from getting_started_implementation.md]
  - ✅ Implement more informative error messages for file operation failures [from planning_improvements.md]
  - ✅ Update test assertions to match new error message format [in response to error message improvements]

## High Priority

- **Tool Enhancement**
  - ✅ Add support for tools/function calling in LLM integration [from planning_priorities]
  - ✅ Enhance security checks for `apply_edit` and `run_native_command` (e.g., stricter path validation) [from getting_started_implementation.md]
  - 🔜 Add size limits and pagination to `read_file` [from getting_started_implementation.md]
  - 🔄 Add timeout and working directory options to native tools [from planning_priorities]

- **Configuration Improvements**
  - ✅ Fully implement the CLI > Env > File hierarchy for all configuration options [from getting_started_implementation.md]
  - ✅ Use pydantic-settings for more robust env var handling [from planning_priorities]
  - ✅ Implement dynamic configuration validation with clear error messages [from planning_improvements.md]

- **User Experience Improvements**
  - 🔄 Enhance confirmation prompts with more context and better diff highlighting [from planning_improvements.md]
  - 🔄 Implement "thinking indicator" and step-by-step output for complex operations [from planning_improvements.md]

## Medium Priority

- **Provider Support Enhancement**
  - 🔄 Test integration with local models (Ollama) [from getting_started_implementation.md]
  - 🔄 Improve provider-specific configuration options [from getting_started_implementation.md]

- **History Management**
  - 🔄 Add option to load specific history files [from getting_started_implementation.md]
  - 🔄 Implement improved command history and recall in CLI [from planning_improvements.md]
  - 🔄 Enhance session management (save/restore agent sessions) [from planning_improvements.md]

- **Code Quality**
  - 🔄 Fix linting issues (line length, trailing whitespace, etc.) [from getting_started_implementation.md]
  - 🔄 Ensure consistent code style across the codebase [from getting_started_implementation.md]
  - 🔄 Set up CI/CD pipeline for automated testing and linting [from getting_started_implementation.md]
  - 🔄 Implement hermetic build system to ensure consistency between local and CI environments [from development_hermetic_builds.md]

## Low Priority

- **Security Enhancements**
  - 🔄 Implement stricter command allowlist with more specific patterns [from planning_improvements.md]
  - 🔄 Add input sanitization to prevent command injection vulnerabilities [from planning_improvements.md]

- **Testing Improvements**
  - 🔄 Add checks for warning print messages in tests (requires capsys) [from planning_priorities]
  - 🔄 Add contribution guidelines with code style requirements [from getting_started_implementation.md]

- **Packaging & Distribution**
  - 🔄 Finalize packaging for distribution (e.g., PyPI) [from getting_started_implementation.md]
  - 🔄 Implement changelog tracking [from getting_started_implementation.md]

## Future Enhancements

- **Asynchronous Operations**
  - 🔄 Implement background execution for long-running operations [from planning_improvements.md]
  - 🔄 Use asyncio or threading to prevent CLI freezing during processing [from planning_improvements.md]

- **Advanced Memory Management**
  - 🔄 Implement long-term conversation memory using vector databases [from planning_mcp.md]
  - 🔄 Add knowledge extraction and summarization for extended conversations [from planning_mcp.md]
  - 🔄 Develop context windowing techniques for managing token limits [from planning_mcp.md]

- **Extended Tool Capabilities**
  - 🔄 Create a dynamic tool discovery and registration system [from planning_mcp.md]
  - 🔄 Add Git-specific tooling for repository management [from planning_mcp.md]
  - 🔄 Develop project analysis tools for codebase understanding [from planning_mcp.md]
  - 🔄 Integrate with code quality tools and test runners [from planning_mcp.md]

- **Enhanced Collaboration**
  - 🔄 Implement session sharing between team members [from planning_mcp.md]
  - 🔄 Add history export and import features [from planning_mcp.md]
  - 🔄 Develop collaborative editing capabilities [from planning_mcp.md]

- **User Interface Improvements**
  - 🔄 Create optional TUI (Text User Interface) with interactive components [from planning_mcp.md]
  - 🔄 Add terminal-based code editor integration [from planning_mcp.md]
  - 🔄 Implement syntax-highlighted diffs with interactive application [from planning_mcp.md]

- **Integration Possibilities**
  - 🔄 Develop integration with IDEs via plugins/extensions [from planning_mcp.md]
  - 🔄 Enhance integration with version control systems [from planning_mcp.md]
  - 🔄 Create CI/CD pipeline integration [from planning_mcp.md]

- **Customization**
  - 🔄 Design plugin architecture for community contributions [from planning_mcp.md]
  - 🔄 Develop custom tool development framework [from planning_mcp.md]
  - 🔄 Create template system for common tasks [from planning_mcp.md]

---

*Note: This list consolidates items from multiple sources including the original `planning_priorities.md`, `planning_improvements.md`, `planning_mcp.md`, and `getting_started_implementation.md`. The prioritization has been updated to reflect current project status.*

**Legend:**
- ✅ Completed
- 🔜 Next item to work on
- 🔄 In progress or pending
