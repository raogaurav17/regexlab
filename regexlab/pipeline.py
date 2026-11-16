"""The full compiler pipeline: regex -> tokens -> AST -> NFA -> DFA -> minimal DFA."""
from dataclasses import dataclass

from .hopcroft import hopcroft
from .lexer import ParseError, tokenize
from .parser import Node, parse
from .subset import DFA, StateLimitError, subset_construction
from .thompson import NFA, thompson

MAX_REGEX_LENGTH = 200


@dataclass
class Model:
    src: str
    tokens: list
    ast: Node
    nfa: NFA
    dfa: DFA
    min: DFA


def build(src: str, max_states: int = 2000) -> Model:
    if not src:
        raise ParseError("Enter a regular expression.", 0)
    if len(src) > MAX_REGEX_LENGTH:
        raise ParseError(f"Expression too long (max {MAX_REGEX_LENGTH} characters).", MAX_REGEX_LENGTH)
    tokens = tokenize(src)
    ast = parse(src, tokens)
    nfa = thompson(ast)
    dfa = subset_construction(nfa, max_states)
    return Model(src, tokens, ast, nfa, dfa, hopcroft(dfa))


__all__ = ["Model", "build", "ParseError", "StateLimitError"]
