"""Command-line interface:  python -m regexlab --help"""
import argparse
import sys
from pathlib import Path

from .lexer import ParseError
from .parser import ast_lines
from .pipeline import build
from .render import draw_svg, to_dot
from .report import build_report
from .simulate import run_all
from .subset import StateLimitError
from .tables import LABELS, automaton_tables, text_table


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="regexlab",
        description="Visualise regex -> NFA -> DFA -> minimal DFA.",
        epilog='example: python -m regexlab "(a|b)*abb" -t babb -t abab -o out/')
    p.add_argument("regex", nargs="?", help="regular expression (| * + ? and parentheses; \\ escapes)")
    p.add_argument("-t", "--test", action="append", default=[], metavar="STRING",
                   help="test string to run through all automata (repeatable)")
    p.add_argument("-o", "--out", metavar="DIR",
                   help="write nfa/dfa/min .svg + .dot files and report.html into DIR")
    p.add_argument("-q", "--quiet", action="store_true", help="don't print tables")
    p.add_argument("--serve", action="store_true", help="start the interactive web demo")
    p.add_argument("--port", type=int, default=8000, help="port for --serve (default 8000)")
    p.add_argument("--no-browser", action="store_true", help="with --serve: don't open a browser tab")
    return p


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.serve:
        from .server import serve
        serve(args.port, open_browser=not args.no_browser)
        return 0
    if args.regex is None:
        _parser().error("give a regex, or use --serve")

    try:
        model = build(args.regex)
    except (ParseError, StateLimitError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    print(f"regex : {args.regex}")
    print("tokens: " + " ".join(f"{t.type}({t.value})" for t in model.tokens))
    print("\nsyntax tree:\n" + "\n".join("  " + l for l in ast_lines(model.ast)))
    print(f"\nε-NFA {model.nfa.n} states  →  DFA {model.dfa.n} states  →  minimal DFA {model.min.n} states")

    if not args.quiet:
        for title, head, rows in automaton_tables(model):
            print(f"\n{title}\n{text_table(head, rows)}")
        print("\n→ start   * accepting   — no transition")

    for s in args.test:
        r = run_all(model, s)
        o = "" if r["oracle"] is None else ("  (matches Python re)" if r["oracle"] == r["accepted"] else "  (DIFFERS from Python re!)")
        print(f"\ntest {s!r}: {'ACCEPT' if r['accepted'] else 'REJECT'}{o}")
        fmt = lambda xs, p: "{" + ", ".join(f"{p}{x}" for x in xs) + "}" if xs else "∅"
        nfa_w = max(len(fmt(x, "q")) for x in r["steps"]["nfa"])
        dfa_w = max(len(fmt(x, "D")) for x in r["steps"]["dfa"])
        for i in range(len(s) + 1):
            print(f"  {i}  {s[i - 1] if i else '·'}  NFA {fmt(r['steps']['nfa'][i], 'q'):<{nfa_w}}  "
                  f"DFA {fmt(r['steps']['dfa'][i], 'D'):<{dfa_w}}  MIN {fmt(r['steps']['min'][i], 'M')}")

    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        for key in ("nfa", "dfa", "min"):
            g = getattr(model, key)
            (out / f"{key}.svg").write_text(draw_svg(g, key, LABELS[key], background=True), encoding="utf-8")
            (out / f"{key}.dot").write_text(to_dot(g, key.upper(), LABELS[key]), encoding="utf-8")
        (out / "report.html").write_text(build_report(model, args.test), encoding="utf-8")
        print(f"\nwrote nfa/dfa/min .svg + .dot and report.html to {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
