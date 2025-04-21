# Command Execution Feature

This document explains the command execution capabilities in Code Agent, including security features, configuration options, and best practices.

## Overview

Code Agent can execute native terminal commands using the `run_native_command` tool. This powerful feature lets the agent interact with your local environment but requires careful security controls to prevent unwanted actions.

## Basic Usage

The agent can suggest and execute commands like:

```
You: List all Python files in the current directory
Agent: I'll find all Python files in the current directory.

Command requested: find . -type f -name "*.py" | sort

Do you want to run this command? [y/N]: y

Running command...
./code_agent/__init__.py
./code_agent/agent/agent.py
...
```

## Security Features

### Command Validation

Commands go through multiple validation steps:

1. **Path Validation**: Checks for suspicious path patterns
2. **Command Pattern Validation**: Checks against allowed/disallowed patterns
3. **Risk Assessment**: Flags potentially dangerous commands

### Command Allowlist

The allowlist controls which commands can be executed:

```yaml
# In ~/.config/code-agent/config.yaml
native_command_allowlist:
  - "ls"
  - "find"
  - "grep"
  - "cat"
  # Additional allowlisted commands
```

**How Allowlisting Works:**
- If the allowlist is empty, all commands require confirmation
- If the allowlist contains items, commands starting with those prefixes will be executed with less scrutiny
- Commands must match from the beginning (e.g., "ls" matches "ls -la" but not "als")

### Dangerous Command Detection

Certain commands are flagged as dangerous, including:

- `rm -rf` and variants - Can delete files recursively
- `sudo` commands - Escalated privileges
- Disk formatting commands - Can erase data
- System modification commands - Can alter system state

These commands always require explicit confirmation, regardless of allowlist settings.

### Auto-Approval Setting

Auto-approval can be configured for commands:

```yaml
# In ~/.config/code-agent/config.yaml
auto_approve_native_commands: false  # Default and recommended
```

**WARNING**: Setting `auto_approve_native_commands` to `true` is extremely risky and not recommended. Even with this setting, dangerous commands will still require confirmation.

## Command Execution Process

1. **Command Request**: The agent requests to run a specific command
2. **Security Validation**: The command is checked against security rules
3. **User Confirmation**: User is prompted to approve (unless auto-approved)
4. **Execution**: Command is executed in a controlled environment
5. **Result Capture**: Output is captured and returned to the agent

## Configuration Options

### Command Line Flags

```bash
# Enable auto-approval for this session only (use with extreme caution)
code-agent --auto-approve-native-commands run "Your prompt here"
```

### Configuration File

```yaml
# ~/.config/code-agent/config.yaml

# Security settings - strongly recommended to keep as default
auto_approve_native_commands: false

# Commands that can be run without triggering warnings
native_command_allowlist:
  - "ls -la"
  - "cat"
  - "grep"
  - "find"
  # Additional safe commands

# Security section contains additional controls
security:
  # Enable command validation to prevent execution of dangerous commands (true/false)
  command_validation: true
```

### Environment Variables

```bash
# Set auto-approval (not recommended)
export CODE_AGENT_AUTO_APPROVE_NATIVE_COMMANDS=false

# Set command validation
export CODE_AGENT_SECURITY_COMMAND_VALIDATION=true
```

## Best Practices

1. **Keep Auto-Approval Disabled**:
   - Never enable auto-approval in shared or production environments
   - Review all commands before execution

2. **Use Specific Allowlist**:
   - Add only necessary commands to the allowlist
   - Use specific command patterns rather than broad ones

3. **Review Commands Carefully**:
   - Understand what the command will do before approving
   - Be especially careful with file deletion or modification commands

4. **Run in Limited Environment**:
   - Run the agent with least privilege user account
   - Consider using in a container or sandbox for extra security

5. **Be Cautious with System Commands**:
   - Be extra careful with commands that:
     - Install software
     - Modify system configuration
     - Access sensitive directories
     - Use elevated privileges

## Advanced Command Patterns

For more precise control, you can use specific patterns in your allowlist:

```yaml
native_command_allowlist:
  - "ls -la"       # Allow ls with these specific flags
  - "find . -type" # Allow find with specific starting arguments
  - "grep -r"      # Allow recursive grep
```

## Troubleshooting

- **Command fails with security error**: The command violates security rules and cannot be executed
- **Command always requires confirmation**: The command isn't in allowlist or matches dangerous patterns
- **Command produces unexpected results**: Check the full command to ensure it does what you expect

## Security Recommendations

- Regularly review `native_command_allowlist` for unnecessary or overly broad patterns
- Consider using `git` command with specific subcommands in allowlist (e.g., `git status`)
- Avoid allowing commands that can modify system state without specific need
- Use `auto_approve_native_commands: false` (the default) for maximum security
