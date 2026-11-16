"""Phase 3a - Thompson's construction: AST -> epsilon-NFA."""
from collections import deque
from dataclasses import dataclass, field

from .parser import Node


@dataclass
class NFA:
    n: int
    start: int
    accept: int
    trans: list                       # (src, dst, symbol-or-None); None = epsilon
    alphabet: list
    eps: list = field(init=False)     # eps[q]      -> [targets]
    mv: list = field(init=False)      # mv[q][sym]  -> [targets]
    accepting: list = field(init=False)

    def __post_init__(self):
        self.eps = [[] for _ in range(self.n)]
        self.mv = [{} for _ in range(self.n)]
        for a, b, s in self.trans:
            if s is None:
                self.eps[a].append(b)
            else:
                self.mv[a].setdefault(s, []).append(b)
        self.accepting = [i == self.accept for i in range(self.n)]

    def closure(self, states) -> tuple:
        """Epsilon-closure of a set of states (sorted tuple)."""
        stack, seen = list(states), set(states)
        while stack:
            x = stack.pop()
            for y in self.eps[x]:
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        return tuple(sorted(seen))

    def step(self, states, sym) -> tuple:
        """States reachable from `states` on `sym`, then epsilon-closed."""
        tgt = set()
        for x in states:
            tgt.update(self.mv[x].get(sym, ()))
        return self.closure(tgt)


def bfs_renumber(n: int, start: int, trans) -> list:
    """Return old->new numbering in BFS order from `start` (nicer labels)."""
    out = [[] for _ in range(n)]
    for a, b, _ in trans:
        out[a].append(b)
    mapping = [-1] * n
    mapping[start] = 0
    count, q = 1, deque([start])
    while q:
        x = q.popleft()
        for y in out[x]:
            if mapping[y] < 0:
                mapping[y] = count
                count += 1
                q.append(y)
    for i in range(n):
        if mapping[i] < 0:
            mapping[i] = count
            count += 1
    return mapping


def thompson(ast: Node) -> NFA:
    count = 0
    trans = []

    def new():
        nonlocal count
        count += 1
        return count - 1

    def add(a, b, s=None):
        trans.append((a, b, s))

    def build(node):
        k = node.kind
        if k == "eps":
            s, e = new(), new(); add(s, e); return s, e
        if k == "chr":
            s, e = new(), new(); add(s, e, node.value); return s, e
        if k == "cat":
            fs, fe = build(node.kids[0])
            for kid in node.kids[1:]:
                gs, ge = build(kid)
                add(fe, gs)
                fe = ge
            return fs, fe
        if k == "alt":
            s = new()
            frags = [build(kid) for kid in node.kids]
            e = new()
            for fs, fe in frags:
                add(s, fs); add(fe, e)
            return s, e
        # unary operators
        s = new()
        fs, fe = build(node.kids[0])
        e = new()
        add(s, fs)
        if k in ("star", "opt"):
            add(s, e)
        if k in ("star", "plus"):
            add(fe, fs)
        add(fe, e)
        return s, e

    s0, e0 = build(node=ast)
    m = bfs_renumber(count, s0, trans)
    T = [(m[a], m[b], s) for a, b, s in trans]
    alphabet = sorted({s for _, _, s in T if s is not None})
    return NFA(count, m[s0], m[e0], T, alphabet)
