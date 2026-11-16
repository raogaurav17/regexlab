"""regexlab - regex -> NFA -> DFA -> minimal DFA, with visualisation."""
from .pipeline import Model, build
from .lexer import ParseError
from .subset import StateLimitError

__version__ = "1.0.0"
__all__ = ["build", "Model", "ParseError", "StateLimitError"]
