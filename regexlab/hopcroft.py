"""Phase 3c - Hopcroft's partition-refinement DFA minimisation.

Uses Hopcroft's smaller-half rule. Pre-images are found by scanning all states
(O(|S|·n²) worst case) for readability; inverse-transition lists would give the
optimal O(|S|·n log n).
"""
from .subset import DFA


def hopcroft(dfa: DFA) -> DFA:
    A = dfa.alphabet
    dead = dfa.n                       # hidden dead state makes the DFA total
    N = dfa.n + 1
    delta = [dict(d) for d in dfa.delta] + [{}]
    for q in range(N):
        for c in A:
            delta[q].setdefault(c, dead)

    accepting = frozenset(q for q in range(dfa.n) if dfa.accepting[q])
    non_accepting = frozenset(range(N)) - accepting
    P = [b for b in (accepting, non_accepting) if b]   # partition
    W = list(P)                                        # worklist of splitters

    while W:
        S = W.pop()
        for c in A:
            X = {q for q in range(N) if delta[q][c] in S}    # pre-image of S on c
            if not X:
                continue
            next_P = []
            for Y in P:
                inter, diff = Y & X, Y - X
                if inter and diff:
                    next_P += [inter, diff]
                    if Y in W:
                        W.remove(Y)
                        W += [inter, diff]
                    else:                                    # smaller half suffices
                        W.append(inter if len(inter) <= len(diff) else diff)
                else:
                    next_P.append(Y)
            P = next_P

    block = {q: i for i, Y in enumerate(P) for q in Y}
    dead_block = block[dead]
    rep = [min(Y) for Y in P]
    btrans = [{c: block[delta[rep[i]][c]] for c in A if block[delta[rep[i]][c]] != dead_block}
              for i in range(len(P))]

    # renumber blocks breadth-first from the start block, dropping the dead block
    ident = {block[dfa.start]: 0}
    order = [block[dfa.start]]
    for b in order:
        for c in A:
            t = btrans[b].get(c)
            if t is not None and t not in ident:
                ident[t] = len(order)
                order.append(t)

    trans, new_delta = [], []
    for new, b in enumerate(order):
        row = {}
        for c in A:
            t = btrans[b].get(c)
            if t is not None:
                row[c] = ident[t]
                trans.append((new, ident[t], c))
        new_delta.append(row)
    return DFA(
        n=len(order), start=0,
        accepting=[rep[b] < dfa.n and dfa.accepting[rep[b]] for b in order],
        trans=trans, alphabet=A, delta=new_delta,
        members=[sorted(q for q in P[b] if q != dead) for b in order],
    )
