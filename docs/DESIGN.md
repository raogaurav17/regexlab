# Design notes

## 1. Pipeline

```
regex string
   │  lexer.py      tokenize()               scanner
   ▼
tokens ──────────────────────────────────────────────────────────────
   │  parser.py     parse()                  recursive descent → AST
   ▼
AST
   │  thompson.py   thompson()               Thompson's construction
   ▼
ε-NFA
   │  subset.py     subset_construction()    Rabin–Scott powerset
   ▼
DFA
   │  hopcroft.py   hopcroft()               partition refinement
   ▼
minimal DFA
```

`pipeline.build()` runs all stages and returns a `Model`. Everything downstream
(rendering, tables, simulation, report, web API) only reads the `Model`.

| Module | Role |
|---|---|
| `lexer.py`, `parser.py` | front end: tokens, grammar, AST, error positions |
| `thompson.py`, `subset.py`, `hopcroft.py` | the three automata algorithms |
| `simulate.py` | step-by-step execution + independent oracle (Python `re`) |
| `render.py` | automaton → SVG (own layered layout) or Graphviz DOT |
| `tables.py`, `report.py` | transition tables, static HTML report |
| `api.py`, `server.py`, `web/` | local interactive demo (stdlib `http.server` + vanilla JS) |
| `cli.py` | `python -m regexlab ...` |

## 2. Grammar

```
regex  → term ( '|' term )*
term   → factor*                 (empty term = ε)
factor → atom ( '*' | '+' | '?' )*
atom   → CHAR | '(' regex ')'
```

Precedence from tightest to loosest: repetition, concatenation, union. `\` turns
the next character into a literal. The grammar is LL(1) after the empty-term rule,
so plain recursive descent works with one token of lookahead.

## 3. Algorithms

**Thompson's construction.** Each AST node yields a fragment with one entry and
one exit state. Every node creates at most 2 new states (concatenation creates
none), so |Q| ≤ 2 · |AST|. The exit state of the whole NFA is the only accepting
state and has no outgoing edges. Concatenation is joined with an ε-edge rather
than by merging states: slightly larger drawings, simpler and obviously correct.
States are renumbered in BFS order from the start so labels read left to right.

**Subset construction.** A DFA state is an ε-closed set of NFA states. Start from
`closure({start})`; for each unseen set and symbol compute `closure(move(S, a))`.
Worst case 2ⁿ states, so `max_states` (default 2000) raises `StateLimitError`
instead of hanging; the demo shows that as a normal error message.

**Hopcroft minimisation.** Partition {accepting, non-accepting}; keep a worklist
of splitters; for splitter `S` and symbol `c`, split every block `Y` into
`Y ∩ pre(S,c)` and `Y \ pre(S,c)`. When `Y` is already queued both halves replace
it, otherwise only the smaller half is queued (Hopcroft's key idea). A hidden dead
state makes the DFA total so every pre-image is well defined; the dead block is
dropped from the output.

*Complexity honesty:* the textbook bound O(|Σ| · n log n) needs inverse-transition
lists so each pre-image costs O(|pre|). This implementation scans all states for
every (splitter, symbol) pair, so its worst case is O(|Σ| · n²). The smaller-half
rule and the output are Hopcroft's; only the data structure is simplified. For the
automaton sizes a visualiser can draw (tens of states) this is irrelevant.

## 4. Rendering

`render.draw_svg` takes any automaton with `n, start, accepting, trans`.

1. Layer states by BFS depth from the start state (columns).
2. Order each column by the barycentre of its predecessors' rows (cuts crossings).
3. Draw each edge as a quadratic Bézier. Adjacent-layer edges are straight;
   back edges, same-layer edges and edges skipping layers bulge out; opposite
   edges between the same pair bow in opposite directions. Parallel edges merge
   into one label (`a,b`).

No third-party layout engine is needed. `to_dot` exports the same graphs for
Graphviz (`dot -Tpng min.dot -o min.png`) when a "textbook" layout is preferred.

## 5. Testing strategy (`python -m unittest`)

| Layer | What is checked |
|---|---|
| Lexer / parser | token types, escapes, precedence, ε-terms, error messages and positions |
| Known results | `(a|b)*abb` → 5-state DFA → 4-state minimal DFA; hand-checked small cases |
| Equivalence | NFA, DFA and minimal DFA accept exactly what Python's `re.fullmatch` accepts, on ~250 seeded random regexes × all strings of length ≤ 6 |
| Minimality | minimal state count equals the number of Myhill–Nerode classes computed by an **independent** table-filling implementation; minimising twice changes nothing; no dead state remains |
| Output | SVGs parse as XML and contain every node; DOT export; CLI exit codes and files; HTTP API; path-traversal attempts return 404 |

The oracle rebuilds the Python pattern from *tokens* (escaping literals) so an
escape such as `\d` means the literal `d` in both engines rather than "digit".

## 6. Limitations / extensions

- Only literals, `| * + ?`, grouping and `\` escapes. No classes (`[a-z]`), `.`,
  counted repetition `{m,n}`, anchors or back-references (the last cannot be
  represented by a finite automaton at all).
- Matching is whole-string (`fullmatch`), not substring search.
- Possible extensions: character classes (expand to unions), a lexer generator that
  emits code from the minimal DFA, Thompson with merged states to match Aho's
  figures exactly, Hopcroft with inverse lists, DFA equivalence / product construction.

## 7. References

- K. Thompson, "Regular expression search algorithm", *CACM* 11(6), 1968, 419–422.
- M. O. Rabin and D. Scott, "Finite automata and their decision problems", *IBM J. Res. Dev.* 3(2), 1959, 114–125.
- J. E. Hopcroft, "An n log n algorithm for minimizing states in a finite automaton", in *Theory of Machines and Computations*, Academic Press, 1971, 189–196.
- A. V. Aho, M. S. Lam, R. Sethi, J. D. Ullman, *Compilers: Principles, Techniques, and Tools*, 2nd ed., Addison-Wesley, 2006, Chapter 3.
