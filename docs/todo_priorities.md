# Consolidated Priority Task List

This document consolidates all tasks, improvements, and future enhancements for the Code Agent project into a single prioritized reference.

## Critical Priority

- **Test Suite Completion**
  - ✅ Add tests for 'chat' command (more complex due to interaction) [from todo_priorities]
  - ✅ Improve test coverage, especially for edge cases in tools [from implementation.md] (Current: 80% coverage)
  - ✅ Complete test LLM interaction with mocked responses/tool calls [from implementation.md]

- **Error Handling Refinement**
  - ✅ Refine error handling and user feedback for API errors, tool failures, configuration issues, and LLM runtime errors [from implementation.md]
  - ✅ Implement more informative error messages for file operation failures [from future_improvements.md]
  - ✅ Update test assertions to match new error message format [in response to error message improvements]

## High Priority

- **Tool Enhancement**
  - ✅ Add support for tools/function calling in LLM integration [from todo_priorities]
  - 🔜 Enhance security checks for `apply_edit` and `run_native_command` (e.g., stricter path validation) [from implementation.md]
  - 🔄 Add size limits and pagination to `read_file` [from implementation.md]
  - 🔄 Add timeout and working directory options to native tools [from todo_priorities]

- **Configuration Improvements**
  - ✅ Fully implement the CLI > Env > File hierarchy for all configuration options [from implementation.md]
  - ✅ Use pydantic-settings for more robust env var handling [from todo_priorities]
  - ✅ Implement dynamic configuration validation with clear error messages [from future_improvements.md]

- **User Experience Improvements**
  - 🔄 Enhance confirmation prompts with more context and better diff highlighting [from future_improvements.md]
  - 🔄 Implement "thinking indicator" and step-by-step output for complex operations [from future_improvements.md]

## Medium Priority

- **Provider Support Enhancement**
  - 🔄 Test integration with local models (Ollama) [from implementation.md]
  - 🔄 Improve provider-specific configuration options [from implementation.md]

- **History Management**
  - 🔄 Add option to load specific history files [from implementation.md]
  - 🔄 Implement improved command history and recall in CLI [from future_improvements.md]
  - 🔄 Enhance session management (save/restore agent sessions) [from future_improvements.md]

- **Code Quality**
  - 🔄 Fix linting issues (line length, trailing whitespace, etc.) [from implementation.md]
  - 🔄 Ensure consistent code style across the codebase [from implementation.md]
  - 🔄 Set up CI/CD pipeline for automated testing and linting [from implementation.md]
  - 🔄 Implement hermetic build system to ensure consistency between local and CI environments [from hermetic_builds.md]

## Low Priority

- **Security Enhancements**
  - 🔄 Implement stricter command allowlist with more specific patterns [from future_improvements.md]
  - 🔄 Add input sanitization to prevent command injection vulnerabilities [from future_improvements.md]

- **Testing Improvements**
  - 🔄 Add checks for warning print messages in tests (requires capsys) [from todo_priorities]
  - 🔄 Add contribution guidelines with code style requirements [from implementation.md]

- **Packaging & Distribution**
  - 🔄 Finalize packaging for distribution (e.g., PyPI) [from implementation.md]
  - 🔄 Implement changelog tracking [from implementation.md]

## Future Enhancements

- **Asynchronous Operations**
  - 🔄 Implement background execution for long-running operations [from future_improvements.md]
  - 🔄 Use asyncio or threading to prevent CLI freezing during processing [from future_improvements.md]

- **Advanced Memory Management**
  - 🔄 Implement long-term conversation memory using vector databases [from PLAN.md]
  - 🔄 Add knowledge extraction and summarization for extended conversations [from PLAN.md]
  - 🔄 Develop context windowing techniques for managing token limits [from PLAN.md]

- **Extended Tool Capabilities**
  - 🔄 Create a dynamic tool discovery and registration system [from PLAN.md]
  - 🔄 Add Git-specific tooling for repository management [from PLAN.md]
  - 🔄 Develop project analysis tools for codebase understanding [from PLAN.md]
  - 🔄 Integrate with code quality tools and test runners [from PLAN.md]

- **Enhanced Collaboration**
  - 🔄 Implement session sharing between team members [from PLAN.md]
  - 🔄 Add history export and import features [from PLAN.md]
  - 🔄 Develop collaborative editing capabilities [from PLAN.md]

- **User Interface Improvements**
  - 🔄 Create optional TUI (Text User Interface) with interactive components [from PLAN.md]
  - 🔄 Add terminal-based code editor integration [from PLAN.md]
  - 🔄 Implement syntax-highlighted diffs with interactive application [from PLAN.md]

- **Integration Possibilities**
  - 🔄 Develop integration with IDEs via plugins/extensions [from PLAN.md]
  - 🔄 Enhance integration with version control systems [from PLAN.md]
  - 🔄 Create CI/CD pipeline integration [from PLAN.md]

- **Customization**
  - 🔄 Design plugin architecture for community contributions [from PLAN.md]
  - 🔄 Develop custom tool development framework [from PLAN.md]
  - 🔄 Create template system for common tasks [from PLAN.md]

---

*Note: This list consolidates items from multiple sources including the original `todo_priorities.md`, `future_improvements.md`, `PLAN.md`, and `implementation.md`. The prioritization has been updated to reflect current project status.*

**Legend:**
- ✅ Completed
- 🔜 Next item to work on
- 🔄 In progress or pending
