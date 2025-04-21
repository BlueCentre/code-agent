# Diagram Validation Feature

## Validation Procedure

After making changes to Mermaid diagrams in the documentation, follow these steps to validate that they render correctly on GitHub:

1. Commit and push your changes to the repository.
2. Wait a few minutes for GitHub to process the changes.
3. Visit the documentation page on GitHub.
4. Check that each diagram renders properly instead of showing "Loading" text.
5. If any diagrams are not rendering:
   - Confirm the diagram uses syntax compatible with GitHub's Mermaid implementation.
   - Simplify complex diagrams that may exceed GitHub's rendering capabilities.
   - Remove special styling, if present.
   - Ensure proper indentation and avoid special characters.
   - **Check for extraneous characters:** Ensure lines don't have unintended trailing characters, especially after semicolons.
   - **Quote complex labels:** Enclose node labels in double quotes (`""`) if they contain HTML (like `<br>`), markdown, punctuation (like `()`, `,`, `/`), or other non-alphanumeric characters (excluding underscores). When in doubt, quote the label. (e.g., `NodeId["Label line 1<br>Label line 2"]`, `AnotherId["My Label (New)"]`).
   - **Use specific types:** Prefer explicitly listed types (like `flowchart TD`) over more general ones (`graph TD`) if encountering issues.

## Mermaid Version Check

You can check GitHub's current Mermaid version with this code:

```mermaid
info
```

## Common Diagram Types Supported

The following diagram types are well-supported by GitHub's Mermaid implementation:

1. **Flowchart** (using `flowchart TD` or `flowchart LR`)
2. **Sequence Diagram** (using `sequenceDiagram`)
3. **Class Diagram** (using `classDiagram`)
4. **State Diagram** (using `stateDiagram-v2`)
5. **Entity Relationship Diagram** (using `erDiagram`)
6. **User Journey** (using `journey`)
7. **Gantt** (using `gantt`)
8. **Pie Chart** (using `pie`)
9. **Requirement Diagram** (using `requirementDiagram`)

## Testing Diagram

Here's a simple test diagram that should always render correctly:

```mermaid
flowchart TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E
```

## Sequence Diagram

The following sequence diagram illustrates how the diagram validation feature works:

```mermaid
sequenceDiagram
    participant User
    participant CLI as CLI Application (main.py)
    participant Agent as CodeAgent (agent.py)
    participant LLM as LLM Client
    participant FileTool as File Tools Module
    participant CmdTool as Command Tools Module

    User->>CLI: Request to validate diagrams or create documentation with diagrams
    CLI->>Agent: run_turn(prompt)

    Agent->>LLM: Request completion with history
    LLM->>Agent: Return completion with file read/edit call

    alt Creating/Editing a file with Mermaid diagrams
        Agent->>FileTool: apply_edit(target_file, code_edit)

        FileTool->>FileTool: Extract Mermaid diagram code blocks

        alt Diagrams found in edit
            FileTool->>CmdTool: run_native_command("npx @mermaid-js/mermaid-cli validate")
            CmdTool->>CmdTool: Create temporary file with diagram
            CmdTool->>Shell: Execute validation command
            Shell->>CmdTool: Return validation result

            alt Validation successful
                CmdTool->>FileTool: Return success
                FileTool->>FileTool: Proceed with edit
            else Validation fails
                CmdTool->>FileTool: Return validation error
                FileTool->>Agent: Return validation error
                Agent->>LLM: Request correction with error details
                LLM->>Agent: Return updated diagram
                Agent->>FileTool: apply_edit with corrected diagram
            end
        else No diagrams found
            FileTool->>FileTool: Proceed with normal edit
        end
    else Validating existing diagrams
        Agent->>FileTool: read_file(path)
        FileTool->>Agent: Return file contents

        Agent->>Agent: Extract Mermaid diagram code blocks

        Agent->>CmdTool: run_native_command("npx @mermaid-js/mermaid-cli validate")
        CmdTool->>CmdTool: Create temporary file with diagram
        CmdTool->>Shell: Execute validation command
        Shell->>CmdTool: Return validation result

        CmdTool->>Agent: Return validation result

        alt Validation successful
            Agent->>CLI: Return success message
        else Validation fails
            Agent->>LLM: Request correction with error details
            LLM->>Agent: Return corrected diagram
            Agent->>FileTool: apply_edit with corrected diagram
        end
    end

    Agent->>CLI: Return final response
    CLI->>User: Display response
```

This diagram illustrates:
1. How Mermaid diagrams are validated during document creation/editing
2. The process for validating existing diagrams in documentation files
3. How validation errors are handled and corrected
4. The interaction between file tools and command tools during validation
5. The role of external Mermaid CLI tools in the validation process
