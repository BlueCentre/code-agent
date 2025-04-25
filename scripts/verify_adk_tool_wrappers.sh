#!/bin/bash
# Script to verify the ADK tool wrappers implementation status

echo "========================================================="
echo "Google ADK Tool Wrappers Verification - Milestone 2"
echo "========================================================="

# Check if we're in the right directory
if [ ! -d "code_agent" ] || [ ! -d "tests" ]; then
  echo "Error: This script must be run from the project root directory."
  exit 1
fi

# Check if in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
  echo "Warning: Virtual environment not detected. Activating .venv if it exists..."
  if [ -d ".venv" ]; then
    source .venv/bin/activate
  else
    echo "Error: .venv directory not found. Please activate your virtual environment."
    exit 1
  fi
fi

echo -e "\n📋 Checking for tool wrapper implementations..."
echo "------------------------------------------------"

# Check for file existence
echo -n "Checking for ADK tools module... "
if [ -f "code_agent/adk/tools.py" ]; then
  echo "✅ Found"
else
  echo "❌ Not found"
  echo "Error: code_agent/adk/tools.py is missing. Ensure you're on the correct branch."
  exit 1
fi

echo -n "Checking for ADK tools tests... "
if [ -f "tests/unit/test_adk_tools.py" ]; then
  echo "✅ Found"
else
  echo "❌ Not found"
  echo "Error: tests/unit/test_adk_tools.py is missing. Ensure you're on the correct branch."
  exit 1
fi

echo -e "\n🧪 Running ADK tool wrapper tests..."
echo "------------------------------------------------"
python -m pytest tests/unit/test_adk_tools.py -v

TEST_RESULT=$?
if [ $TEST_RESULT -ne 0 ]; then
  echo -e "\n❌ Tests failed. Please fix the issues before proceeding."
  exit 1
fi

echo -e "\n✅ All tests passed successfully!"

echo -e "\n📊 Tool Wrapper Implementation Status:"
echo "------------------------------------------------"
echo "✅ Implemented:"
echo "  - read_file"
echo "  - delete_file"
echo "  - apply_edit"
echo "  - list_dir"
echo "  - run_terminal_cmd"
echo
echo "❌ Not implemented:"
echo "  - file_search"
echo "  - codebase_search"
echo "  - grep_search"
echo "  - web_search"

echo -e "\n⚠️ Important Note:"
echo "------------------------------------------------"
echo "These tool wrappers exist but are NOT yet connected to a functioning ADK agent."
echo "The CLI will NOT use these wrappers until the ADK agent implementation is complete."
echo "To verify the current state, only use the unit tests, not the CLI commands."

echo -e "\n🔜 Next Steps:"
echo "------------------------------------------------"
echo "1. Create the ADK Agent implementation (code_agent/adk/agent.py)"
echo "2. Connect the ADK tools to the ADK Agent"
echo "3. Update the CLI to use the ADK Agent"
echo "4. Implement remaining tool wrappers"

echo -e "\n========================================================="
echo "Verification complete!"
echo "========================================================="\n 