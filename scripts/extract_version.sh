#!/bin/bash
# extract_version.sh - Extracts version from project files without requiring package installation

# Try reading from pyproject.toml first (most reliable for Poetry projects)
if [ -f pyproject.toml ]; then
    # More robust extraction using awk
    VERSION=$(awk -F'"' '/^version = / {print $2}' pyproject.toml)
    if [ ! -z "$VERSION" ]; then
        echo $VERSION
        exit 0
    fi
fi

# Try reading from setup.py
if [ -f setup.py ]; then
    VERSION=$(grep -E "version\s*=\s*[\"']([^\"']+)[\"']" setup.py | head -1 | sed -E "s/.*version\s*=\s*[\"']([^\"']+)[\"'].*/\1/")
    if [ ! -z "$VERSION" ]; then
        echo $VERSION
        exit 0
    fi
fi

# Try reading from package __init__.py
for init_file in $(find . -name "__init__.py" -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/__pycache__/*"); do
    VERSION=$(grep -E "__version__\s*=\s*[\"']([^\"']+)[\"']" "$init_file" | head -1 | sed -E "s/.*__version__\s*=\s*[\"']([^\"']+)[\"'].*/\1/")
    if [ ! -z "$VERSION" ]; then
        echo $VERSION
        exit 0
    fi
done

# Try reading package name from pyproject.toml (for fallback if version not found)
if [ -f pyproject.toml ]; then
    PACKAGE_NAME=$(awk -F'"' '/^name = / {print $2}' pyproject.toml)
    echo "0.1.0-$PACKAGE_NAME" # Fallback with package name as suffix
    exit 0
fi

# Ultimate fallback
echo "0.1.0" 