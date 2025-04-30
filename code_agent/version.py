"""Code Agent CLI Version"""

try:
    from importlib.metadata import version

    __version__ = version("cli-code-agent")
except ImportError:
    __version__ = "0.2.1"  # Fallback version
