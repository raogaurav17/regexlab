"""Phase 3b - subset construction: epsilon-NFA -> DFA."""
from dataclasses import dataclass, field

from .thompson import NFA


class StateLimitError(Exception):
    """The DFA would exceed the configured number of states."""


@dataclass
class DFA:
    n: int
    start: int
    accepting: list                 # bool per state
    trans: list                     # (src, dst, symbol)
    alphabet: list
    delta: list = field(default_factory=list)    # delta[q][sym] -> q' (missing = dead)
    sets: list = None               # subset DFA: NFA-state tuple per DFA state
    members: list = None            # minimal DFA: merged DFA states per block


def subset_construction(nfa: NFA, max_states: int = 2000) -> DFA:
    start = nfa.closure([nfa.start])
    sets, index, trans = [start], {start: 0}, []
    q = 0
    while q < len(sets):
        for c in nfa.alphabet:
            target = nfa.step(sets[q], c)
            if not target:
                continue
            if target not in index:
                if len(sets) >= max_states:
                    raise StateLimitError(
                        f"DFA would exceed {max_states} states - try a smaller expression.")
                index[target] = len(sets)
                sets.append(target)
            trans.append((q, index[target], c))
        q += 1
    delta = [{} for _ in sets]
    for a, b, c in trans:
        delta[a][c] = b
    return DFA(
        n=len(sets), start=0,
        accepting=[nfa.accept in s for s in sets],
        trans=trans, alphabet=nfa.alphabet, delta=delta, sets=sets,
    )
