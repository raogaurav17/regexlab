"""Correctness tests for Thompson, subset construction and Hopcroft."""
import itertools
import random
import re
import unittest

from regexlab.hopcroft import hopcroft
from regexlab.pipeline import build
from regexlab.simulate import dfa_accepts, nfa_accepts, oracle, run_dfa, run_nfa
from regexlab.subset import StateLimitError, subset_construction
from regexlab.thompson import thompson
from regexlab.parser import parse


def all_strings(alphabet, max_len):
    yield ""
    for n in range(1, max_len + 1):
        for t in itertools.product(alphabet, repeat=n):
            yield "".join(t)


def random_regex(rng, depth):
    r = rng.randrange(2 if depth <= 0 else 9)
    if r < 2:
        return rng.choice("ab")
    sub = lambda: random_regex(rng, depth - 1)
    if r < 4:
        return sub() + sub()
    if r == 4:
        return f"({sub()}|{sub()})"
    if r == 5:
        return f"({sub()})*"
    if r == 6:
        return f"({sub()})+"
    if r == 7:
        return f"({sub()})?"
    return sub() + sub() + sub()


def myhill_nerode_classes(dfa):
    """Independent oracle: table-filling algorithm on the completed DFA (+ dead state).

    Returns the number of equivalence classes, including the dead state's class.
    """
    n, dead = dfa.n, dfa.n
    delta = [{c: dfa.delta[q].get(c, dead) for c in dfa.alphabet} for q in range(n)]
    delta.append({c: dead for c in dfa.alphabet})
    acc = [dfa.accepting[q] for q in range(n)] + [False]
    N = n + 1
    marked = {(p, q) for p in range(N) for q in range(p + 1, N) if acc[p] != acc[q]}
    changed = True
    while changed:
        changed = False
        for p in range(N):
            for q in range(p + 1, N):
                if (p, q) in marked:
                    continue
                for c in dfa.alphabet:
                    a, b = sorted((delta[p][c], delta[q][c]))
                    if a != b and (a, b) in marked:
                        marked.add((p, q))
                        changed = True
                        break
    parent = list(range(N))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for p in range(N):
        for q in range(p + 1, N):
            if (p, q) not in marked:
                parent[find(p)] = find(q)
    return len({find(x) for x in range(N)})


class KnownResultTests(unittest.TestCase):
    def test_dragon_book_example(self):
        # The classic (a|b)*abb example (Aho et al., Compilers): 5-state subset DFA, 4 states minimised
        m = build("(a|b)*abb")
        self.assertEqual((m.dfa.n, m.min.n), (5, 4))

    def test_small_cases(self):
        # (regex, DFA states, minimal states). Hand-checked: for `a|b` the subsets {3,5} and
        # {4,5} are distinct DFA states that Hopcroft merges; likewise {0,1,2} and {1,2,3} for `a*`.
        for src, dfa_n, min_n in [("a", 2, 2), ("a|b", 3, 2), ("a*", 2, 1), ("ab", 3, 3), ("a+", 2, 2)]:
            with self.subTest(src=src):
                m = build(src)
                self.assertEqual((m.dfa.n, m.min.n), (dfa_n, min_n))

    def test_thompson_single_accept_no_outgoing(self):
        nfa = thompson(parse("(a|b)*abb"))
        self.assertEqual(sum(nfa.accepting), 1)
        self.assertFalse(nfa.eps[nfa.accept] or nfa.mv[nfa.accept])
        self.assertEqual(nfa.start, 0)

    def test_state_limit(self):
        # (a|b)*a(a|b){n} needs ~2^n DFA states
        nfa = build("(a|b)*a(a|b)(a|b)(a|b)").nfa
        with self.assertRaises(StateLimitError):
            subset_construction(nfa, max_states=5)

    def test_escapes(self):
        m = build(r"a\*b")
        self.assertTrue(dfa_accepts(m.min, run_dfa(m.min, "a*b")))
        self.assertFalse(dfa_accepts(m.min, run_dfa(m.min, "aab")))

    def test_empty_alternative_accepts_empty_string(self):
        m = build("a|")
        for s, expect in [("", True), ("a", True), ("aa", False)]:
            self.assertEqual(dfa_accepts(m.min, run_dfa(m.min, s)), expect)


class EquivalenceTests(unittest.TestCase):
    def check(self, src, strings):
        m = build(src)
        for s in strings:
            expected = re.fullmatch(src, s) is not None
            got = (nfa_accepts(m.nfa, run_nfa(m.nfa, s)),
                   dfa_accepts(m.dfa, run_dfa(m.dfa, s)),
                   dfa_accepts(m.min, run_dfa(m.min, s)))
            self.assertEqual(got, (expected,) * 3, f"{src!r} on {s!r}")

    def test_fixed_examples(self):
        strings = list(all_strings("abc", 5))
        for src in ["(a|b)*abb", "a(b|c)*", "a+b?c*", "(ab|a)(c|bc)", "(a*b*)*", "((a|b)(a|b))*", "a?a?a?aaa"]:
            with self.subTest(src=src):
                self.check(src, strings)

    def test_random_regexes_nfa_dfa_min_agree_with_python_re(self):
        rng = random.Random(2026)
        strings = list(all_strings("ab", 6))
        for _ in range(250):
            self.check(random_regex(rng, 4), strings)

    def test_oracle_uses_literal_escapes(self):
        m = build(r"\d")                       # our lexer: literal 'd', not a digit class
        self.assertTrue(oracle(m.tokens, "d"))
        self.assertFalse(oracle(m.tokens, "5"))


class MinimalityTests(unittest.TestCase):
    def test_hopcroft_matches_myhill_nerode_on_random_regexes(self):
        rng = random.Random(7)
        for _ in range(200):
            src = random_regex(rng, 4)
            m = build(src)
            # classes of the completed DFA, minus the dead state's own class
            self.assertEqual(m.min.n, myhill_nerode_classes(m.dfa) - 1, src)

    def test_never_larger_than_dfa(self):
        rng = random.Random(11)
        for _ in range(100):
            m = build(random_regex(rng, 4))
            self.assertLessEqual(m.min.n, m.dfa.n)

    def test_idempotent(self):
        rng = random.Random(13)
        for _ in range(100):
            m = build(random_regex(rng, 4))
            self.assertEqual(hopcroft(m.min).n, m.min.n)

    def test_minimal_dfa_has_no_dead_state(self):
        m = build("(ab)*c")
        for q in range(m.min.n):
            # every state must be able to reach an accepting state
            seen, stack = {q}, [q]
            while stack:
                x = stack.pop()
                for y in m.min.delta[x].values():
                    if y not in seen:
                        seen.add(y)
                        stack.append(y)
            self.assertTrue(any(m.min.accepting[s] for s in seen))


if __name__ == "__main__":
    unittest.main()
