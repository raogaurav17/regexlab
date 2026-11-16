"""Run input strings through the automata, recording every step."""
import re


def run_nfa(nfa, s: str) -> list:
    cur = nfa.closure([nfa.start])
    steps = [cur]
    for ch in s:
        cur = nfa.step(cur, ch)
        steps.append(cur)
    return steps


def run_dfa(dfa, s: str) -> list:
    cur = dfa.start
    steps = [(cur,)]
    for ch in s:
        if cur is not None:
            cur = dfa.delta[cur].get(ch)       # None = fell into the dead state
        steps.append(() if cur is None else (cur,))
    return steps


def nfa_accepts(nfa, steps) -> bool:
    return nfa.accept in steps[-1]


def dfa_accepts(dfa, steps) -> bool:
    return bool(steps[-1]) and dfa.accepting[steps[-1][0]]


def oracle(tokens, s: str):
    """Ask Python's own `re` engine; used as an independent correctness check.

    The pattern is rebuilt from our tokens so escapes mean the same thing in both.
    """
    pattern = "".join(re.escape(t.value) if t.type == "CHAR" else t.value for t in tokens)
    try:
        return re.fullmatch(pattern, s) is not None
    except re.error:
        return None


def run_all(model, s: str) -> dict:
    sn, sd, sm = run_nfa(model.nfa, s), run_dfa(model.dfa, s), run_dfa(model.min, s)
    a, b, c = nfa_accepts(model.nfa, sn), dfa_accepts(model.dfa, sd), dfa_accepts(model.min, sm)
    o = oracle(model.tokens, s)
    return {
        "steps": {"nfa": [list(x) for x in sn], "dfa": [list(x) for x in sd], "min": [list(x) for x in sm]},
        "accepted": a,
        "agree": a == b == c,
        "oracle": o,
    }
