## CLI Typer Interface Improvements

### Run & Create

-   **Enhance Help Text with Default Values:** Explicitly mention default values in the help strings for options (e.g., `--session-id`, boolean flags) for improved clarity.
-   **Clarify Interactive Mode Activation:** Add a note in the documentation or help text about using `instruction="-"` as a shortcut to start interactive mode directly for the `run` command.
-   **Provide Choices for `--log-level`:** If using a fixed set of logging levels, consider using Typer's `show_choices=True` or listing valid options in the help text for the `--log-level` option in the `run` command.
-   **Consider Grouping Options (Conceptual):** While not a Typer feature for help text, conceptually group related options (e.g., LLM configuration) in code definition and external documentation for better organization across commands.
-   **Refine Help Text for `--agent-path`:** Ensure the help text clearly explains that it can be a directory or file and the behavior when no path is provided and no default is in config for the `run` command.
-   **Leverage Rich Console for More Structured Output:** Continue utilizing `rich` for clear visual separation of different types of output (agent messages, system info, errors) across all commands.
-   **Ensure Consistency Across Commands:** Maintain consistent option naming, help text style, and Typer feature usage across all CLI commands for a cohesive user experience.    
-   **Explicitly State Interactive Prompting:** In the help text for options that trigger interactive prompts if not provided (like in the `create` command), mention this behavior.
-   **Improve Help Text for Parameter Options:** For options that pre-fill interactive prompts (like `--model`, `--api-key` in `create`), clarify that they skip the corresponding prompt.
-   **Add Examples to Option Help:** For key options like `--template` in `create`, consider adding a few common examples directly in the help text.                 
-   **Consider a `--non-interactive` Flag:** Add an optional flag (`--non-interactive`) to commands that use interactive prompts to disable them and force failure if information is missing, useful for scripting.
-   **Refine Error Messages for Missing Arguments:** For required arguments like `APP_NAME` in `create`, slightly expand the error message to briefly explain what the argument represents.

### Config
-   **Standardize Provider Command Output:** Ensure consistency in the structure and type of information presented across all `config <provider>` commands (status, setup, config options, models, examples).
-   **Add a `config list-providers` Command:** Implement a command to simply list the names of all supported providers for easy discovery.                          
-   **Improve `config verbosity` Help/Usage:** Explicitly list valid string names (QUIET, NORMAL, VERBOSE, DEBUG) in the help text and show examples of both numeric and string inputs.
-   **Refine `config set-agent-path` Input Validation Feedback:** Add a note in the help text that the path should point to a valid agent entry point (e.g., `agent.py` file or a directory containing it).
-   **Add Confirmation for `config reset`:** Implement a confirmation prompt before executing the `config reset` command to prevent accidental configuration loss.              
-   **Enhance `config show` Output:** Consider adding a more human-readable, formatted output option for the configuration details, potentially using `rich` features, in addition to or as an alternative to the raw JSON.


### Session
-   **Enhance `sessions` List Output:** For the `sessions` command, consider adding more details to the list of available sessions, such as creation/modification timestamps or a brief summary, if this information can be easily retrieved from the saved session files.
-   **Add Filtering/Sorting Options for `sessions`:** Implement options for the `sessions` command to filter the list (e.g., by age, by name pattern) or sort it (e.g., by date).
-   **Add Machine-Readable Output for `sessions`:** Include an option (e.g., `--json`) to output the list of sessions in a machine-readable format like JSON, useful for scripting.
-   **Plan for `history` Command Enhancement (Post-Persistence):** When a persistent session service is implemented, enhance the `history` command to actually display the conversation history. Consider options for filtering (e.g., by author, keywords) and output formats (e.g., plain text, JSON
-   **Consider `session delete` Command:** Add a command to delete one or more saved session files. This command should include a confirmation prompt to prevent accidental data loss.
-   **Consider `session view` Command:** Add a command to display the raw content of a saved session file, which could be useful for debugging or inspecting session state.
-   **Clarify Session ID Origin in Help Text:** Ensure help text for arguments/options requiring a session ID clearly indicates where valid session IDs can be obtained (e.g., from the `sessions` command or when saving a session with `run --save-session`).


### Eval
-   **Refine `agent_module_file_path` Argument:** Clarify the help text and potentially adjust `file_okay`/`dir_okay` parameters for the `agent_module_file_path` argument in the `eval` command to consistently indicate whether it expects a directory containing `agent.py` or the `agent.py` file itself, aligning with the `run` command's `agent_path`.
-   **Remove Redundant "Optional." from Option Help:** Remove the word "Optional." from the beginning of help texts for options like `--config-file-path`, `--print-detailed-results`, etc., as Typer already indicates optional parameters.
-   **Use Enum for `log_level` Option:** Define and use an `Enum` for valid logging levels (e.g., DEBUG, INFO, WARNING) for the `log_level` option in the `eval` command to improve validation and provide clearer help text showing allowed values.
-   **Add More Examples for `eval` Command:** Include additional examples in the `eval` command's docstring or help text demonstrating how to use options like `--config-file-path`, `--result-file-path`, `--log-level`, and `--log-to-tmp`.
-   **Clarify Output Formats:** Briefly mention the format of the detailed results printed to the console and the format of the saved results file in the help text for `--print-detailed-results` and `--result-file-path`.


### Web
-   **Explicitly State Default for `agents_dir`:** In the help text for the `agents_dir` argument in the `web` command, explicitly mention that the default is the current working directory (`.`).
-   **Refine Multi-line Help Text Formatting:** Ensure consistent and clear formatting for multi-line help texts, such as the one for the `session_db_url` option in the `web` command.    
-   **Use Enum for `log_level` Option in `web`:** Define and use an `Enum` for valid logging levels (e.g., DEBUG, INFO, WARNING) for the `log_level` option in the `web` command to improve validation and provide clearer help text showing allowed values, consistent with other commands.
-   **Add More Examples for `web` Command:** Include additional examples in the `web` command's docstring or help text demonstrating how to use options like `--port`, `--session-db-url`, and `--allow-origins`.
-   **Clarify `agents_dir` Structure:** Reiterate in the help text for `agents_dir` that it should be a directory where each sub-directory represents a single agent.


### Provider
-   **Add `providers set-default` Command:** Implement a command within the `providers` sub-app to set the default LLM provider and model, offering a more intuitive way to configure defaults than just editing the config file or using a separate `config` command.
-   **Add `providers list-models <provider>` Command:** Implement a command to list available models for a specific configured provider. This could potentially query the provider's API or a local cache to show models relevant to the user's setup.
-   **Enhance Provider Availability Check:** For providers like Ollama, consider adding a more robust check (e.g., attempting to connect to the configured URL) to the `providers list` command or a separate `providers check <provider>` command to give users clearer feedback on whether the provider service is actually reachable.
-   **Centralize Provider Information:** Consider moving the `providers_info` dictionary to a shared configuration or data structure that can be accessed by both the `config` and `providers` commands to ensure consistency and avoid duplication.


### Deploy
-   **Clarify "Required" vs. "Optional" in Deployment Help Text:** For options like `--project` and `--region` in `deploy cloud_run`, reconcile the help text stating they are "Required" with their definition as `Optional[str]`. Explain that they are required *unless* a default can be inferred interactive prompting is used.
-   **Improve Default Value Communication in Deployment:** For options with dynamic or implicit defaults (like `--app-name` or `--temp-folder` in `deploy cloud_run`), explicitly state the default *behavior* or *location* in the help text.
-   **Provide Examples for Key Options:** Add examples for important options like `--project`, `--region`, `--service-name`, and `--session-db-url` within the command's docstring or help text to show common usage patterns.
-   **Use Enums for `--verbosity`:** Define an `Enum` for valid verbosity levels (QUIET, NORMAL, VERBOSE, DEBUG) and use it for the `--verbosity` option to provide better validation and clearer help text showing the allowed values, similar to the `config verbosity` command.
-   **Structure Multi-line Help Text:** Ensure the multi-line help text for options like `--session-db_url` is consistently formatted for readability in the `--help` output.
-   **Add More Deployment Examples:** Include additional examples in the main command docstring demonstrating how to use various options, such as specifying project/region, setting a custom service name, or deploying with the UI.
-   **Mention External Dependencies:** Add a note in the `deploy cloud_run` help text or documentation about the dependency on the Google Cloud SDK (`gcloud`) being installed and authenticated for Cloud Run deployments.