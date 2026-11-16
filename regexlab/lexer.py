"""Phase 1 - lexical analysis: regex source text -> token stream."""
from dataclasses import dataclass


class ParseError(Exception):
    """Raised for any syntax error in the regular expression."""

    def __init__(self, message: str, pos: int):
        super().__init__(message)
        self.pos = pos


@dataclass(frozen=True)
class Token:
    type: str   # CHAR, UNION, STAR, PLUS, QMARK, LPAREN, RPAREN
    value: str
    pos: int


_SPECIAL = {
    "|": "UNION", "*": "STAR", "+": "PLUS", "?": "QMARK",
    "(": "LPAREN", ")": "RPAREN",
}


def tokenize(src: str) -> list:
    """Split `src` into tokens. A backslash makes the next character a literal."""
    tokens, i = [], 0
    while i < len(src):
        c = src[i]
        if c == "\\":
            if i + 1 >= len(src):
                raise ParseError('Dangling "\\" at end of expression', i)
            tokens.append(Token("CHAR", src[i + 1], i))
            i += 2
            continue
        tokens.append(Token(_SPECIAL.get(c, "CHAR"), c, i))
        i += 1
    return tokens
