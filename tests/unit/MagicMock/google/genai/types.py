"""
Mock implementations of types from google.genai.types.
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class GenerationConfig:
    """Mock GenerationConfig class."""

    def __init__(self, temperature: float = 0.7, top_p: float = 0.95, top_k: int = 40, max_output_tokens: int = 1024):
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.max_output_tokens = max_output_tokens


class HarmCategory(Enum):
    """Mock HarmCategory enum."""

    HARM_CATEGORY_HATE_SPEECH = "harm_category_hate_speech"
    HARM_CATEGORY_SEXUALLY_EXPLICIT = "harm_category_sexually_explicit"
    HARM_CATEGORY_HARASSMENT = "harm_category_harassment"
    HARM_CATEGORY_DANGEROUS_CONTENT = "harm_category_dangerous_content"


class HarmBlockThreshold(Enum):
    """Mock HarmBlockThreshold enum."""

    BLOCK_NONE = "block_none"
    BLOCK_LOW_AND_ABOVE = "block_low_and_above"
    BLOCK_MEDIUM_AND_ABOVE = "block_medium_and_above"
    BLOCK_ONLY_HIGH = "block_only_high"


class FunctionCall:
    """Mock FunctionCall class."""

    def __init__(self, name: str, args: Dict[str, Any]):
        self.name = name
        self.args = args


class Content:
    """Mock Content class."""

    def __init__(self, parts: List[Any] | None = None):
        self.parts = parts or []


class Part:
    """Mock Part class."""

    def __init__(self, text: Optional[str] = None, function_call: Optional[FunctionCall] = None):
        self.text = text
        self.function_call = function_call
