- In this prompt, I want you to:
  - use uv command for all commands in this repository, example 'uv tool run pytest', 'uv python ...', 'uv tool ruff ...', 'uv pip ...', etc
  - watch the terminal interaction outputs for interactive commands and fix issues
  - don't run it in the backaground since you cannot monitor the terminal
  - if you encounter any issues related to authentication, the run 'source .env' to load the environment variables and use sandbox/ tests to verify functionality
  - verify .env exist by running 'ls -la' and 'cat .env'
  - only address my request, don't add any other text or comments
  - always use the official google adk docs for all code implementation
  - always use the official google adk docs if you encounter any issues
  - clean up old code when replacing it with new code
  - update relevant files and documentation


  ---

1. When you respond, can you tell me which agent is handling the answer to your response?
2. Can you read through the files in the current dir and tell me what it is doing?
3. Read through the docs and all the Python files in the current directory
4. Can you draw me a sequence diagram of how this all works?
5. Can you use mermaid and then render it in ascii?
6. If I wanted to expand the filesystem tool that we have, for you to be able to write and modify files, how would you do that here?
7. Can you read these files that you plan to create or modify and if they exist, can you show me the diff of where you would add or change code?

1. When you respond, can you tell me which agent is handling the answer to your response?
2. Can you read through the files in the current dir and tell me what it is doing?
3. Read through the docs and all the Python files in the current directory
4. If I wanted to expand the filesystem tool that we have, for you to be able to write and modify files, how would you do that here?
5. Can you read these files that you plan to create or modify and if they exist, can you show me the diff of where you would add or change code?

1. When you respond, can you tell me which agent is handling the answer to your response?
2. Read through the docs and ALL the Python files in the current directory.
3. Can you analyze the code and tell me what it is doing?
4. While analyzing the code, if you haven't read the code, please read it.
5. After you analyze the code, compare it to official google adk best practices.
6. What are the areas that you think are not following best practices?
