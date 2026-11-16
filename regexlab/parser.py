"""Phase 2 - syntax analysis: recursive-descent parser building an AST.

Grammar (precedence: repetition > concatenation > union):

    regex  -> term ( '|' term )*
    term   -> factor*                 (empty term = epsilon)
    factor -> atom ( '*' | '+' | '?' )*
    atom   -> CHAR | '(' regex ')'
"""
from dataclasses import dataclass

from .lexer import ParseError, tokenize


@dataclass(frozen=True)
class Node:
    kind: str            # eps, chr, cat, alt, star, plus, opt
    value: str = ""      # the literal for 'chr'
    kids: tuple = ()


_REPEAT = {"STAR": "star", "PLUS": "plus", "QMARK": "opt"}


def parse(src: str, tokens=None) -> Node:
    toks = tokenize(src) if tokens is None else tokens
    i = 0

    def is_(t):
        return i < len(toks) and toks[i].type == t

    def regex():
        nonlocal i
        alts = [term()]
        while is_("UNION"):
            i += 1
            alts.append(term())
        return alts[0] if len(alts) == 1 else Node("alt", kids=tuple(alts))

    def term():
        items = []
        while i < len(toks) and not is_("UNION") and not is_("RPAREN"):
            items.append(factor())
        if not items:
            return Node("eps")
        return items[0] if len(items) == 1 else Node("cat", kids=tuple(items))

    def factor():
        nonlocal i
        a = atom()
        while i < len(toks) and toks[i].type in _REPEAT:
            a = Node(_REPEAT[toks[i].type], kids=(a,))
            i += 1
        return a

    def atom():
        nonlocal i
        t = toks[i]
        if t.type == "LPAREN":
            i += 1
            r = regex()
            if not is_("RPAREN"):
                raise ParseError(f'Missing ")" for "(" at position {t.pos}', t.pos)
            i += 1
            return r
        if t.type == "CHAR":
            i += 1
            return Node("chr", value=t.value)
        raise ParseError(f'Nothing to repeat before "{t.value}" at position {t.pos}', t.pos)

    ast = regex()
    if i < len(toks):
        raise ParseError(f'Unmatched ")" at position {toks[i].pos}', toks[i].pos)
    return ast


_LABEL = {"alt": "|  union", "cat": "·  concat", "star": "*  star",
          "plus": "+  plus", "opt": "?  optional", "eps": "ε  empty"}


def ast_lines(node: Node) -> list:
    """Pretty-print the AST as an indented tree (box-drawing characters)."""
    out = []

    def label(n):
        return f"'{n.value}'" if n.kind == "chr" else _LABEL[n.kind]

    def walk(n, prefix, last, root):
        out.append(label(n) if root else prefix + ("└─ " if last else "├─ ") + label(n))
        child_prefix = "" if root else prefix + ("   " if last else "│  ")
        for k, kid in enumerate(n.kids):
            walk(kid, child_prefix, k == len(n.kids) - 1, False)

    walk(node, "", True, True)
    return out


def ast_size(node: Node) -> int:
    return 1 + sum(ast_size(k) for k in node.kids)
