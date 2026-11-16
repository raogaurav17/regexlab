"""Transition tables for the three automata, as data, plain text or HTML."""
from html import escape

LABELS = {"nfa": lambda i: f"q{i}", "dfa": lambda i: f"D{i}", "min": lambda i: f"M{i}"}


def _set(items, f) -> str:
    return "{" + ", ".join(f(x) for x in items) + "}" if items else "—"


def _mark(is_start: bool, is_acc: bool) -> str:
    return ("→" if is_start else "") + ("*" if is_acc else "")


def automaton_tables(model) -> list:
    """Return [(title, header, rows), ...] for NFA, DFA and minimal DFA."""
    nfa, dfa, mn = model.nfa, model.dfa, model.min
    A = nfa.alphabet
    q, D, M = LABELS["nfa"], LABELS["dfa"], LABELS["min"]
    nrows = [[_mark(i == nfa.start, nfa.accepting[i]) + q(i), _set(nfa.eps[i], q)]
             + [_set(nfa.mv[i].get(c, []), q) for c in A] for i in range(nfa.n)]
    drows = [[_mark(i == 0, dfa.accepting[i]) + D(i), _set(dfa.sets[i], q)]
             + [D(dfa.delta[i][c]) if c in dfa.delta[i] else "—" for c in A] for i in range(dfa.n)]
    mrows = [[_mark(i == 0, mn.accepting[i]) + M(i), _set(mn.members[i], D)]
             + [M(mn.delta[i][c]) if c in mn.delta[i] else "—" for c in A] for i in range(mn.n)]
    return [
        ("ε-NFA transition table", ["State", "ε", *A], nrows),
        ("DFA (subset construction)", ["State", "NFA states", *A], drows),
        ("Minimal DFA (Hopcroft)", ["State", "Merged DFA states", *A], mrows),
    ]


def text_table(header, rows) -> str:
    widths = [max(len(str(r[i])) for r in [header, *rows]) for i in range(len(header))]
    line = lambda r: "│ " + " │ ".join(str(c).ljust(w) for c, w in zip(r, widths)) + " │"
    bar = lambda l, m, r: l + m.join("─" * (w + 2) for w in widths) + r
    return "\n".join([bar("┌", "┬", "┐"), line(header), bar("├", "┼", "┤"),
                      *[line(r) for r in rows], bar("└", "┴", "┘")])


def html_table(header, rows) -> str:
    head = "".join(f"<th>{escape(str(h))}</th>" for h in header)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def tables_html(model) -> str:
    parts = [f"<h3>{escape(t)}</h3>{html_table(h, r)}" for t, h, r in automaton_tables(model)]
    parts.append('<p class="cap">→ start state &nbsp; * accepting state &nbsp; — no transition (implicit dead state)</p>')
    return "".join(parts)
