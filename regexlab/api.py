"""JSON payloads shared by the web server and the tests."""
from .lexer import ParseError
from .parser import ast_lines, ast_size
from .pipeline import build
from .render import draw_svg
from .simulate import run_all
from .subset import StateLimitError
from .tables import LABELS, tables_html

_ERRORS = (ParseError, StateLimitError)


def build_payload(src: str) -> dict:
    try:
        m = build(src)
    except _ERRORS as e:
        return {"ok": False, "error": str(e)}
    return {
        "ok": True,
        "tokens": [{"type": t.type, "value": t.value, "pos": t.pos} for t in m.tokens],
        "tree": "\n".join(ast_lines(m.ast)),
        "counts": {"ast": ast_size(m.ast), "nfa": m.nfa.n, "dfa": m.dfa.n, "min": m.min.n},
        "svg": {k: draw_svg(getattr(m, k), k, LABELS[k]) for k in ("nfa", "dfa", "min")},
        "tables": tables_html(m),
    }


def run_payload(src: str, s: str) -> dict:
    try:
        m = build(src)
    except _ERRORS as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "chars": list(s), **run_all(m, s)}
