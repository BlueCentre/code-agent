try:
    from importlib.metadata import version

    __version__ = version("cli-code-agent")
except ImportError:
    __version__ = "0.1.0"  # Fallback version
