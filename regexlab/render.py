"""Draw an automaton as a standalone SVG (pure Python) or export it as Graphviz DOT.

Works on any object with: n, start, accepting (list[bool]), trans [(src, dst, sym|None)].
"""
import math
from collections import deque
from html import escape

R, GX, GY = 20, 108, 78           # node radius, column spacing, row spacing

# Colours fall back to a light theme when the SVG is opened on its own;
# inside the web page the page's CSS variables take over (dark mode etc.).
SVG_CSS = """
.ed path{fill:none;stroke:var(--edge,#4a4a45);stroke-width:1.6}
.ed text{font:600 13px ui-monospace,Menlo,Consolas,monospace;fill:var(--ink,#1d1d1b);text-anchor:middle;dominant-baseline:central;paint-order:stroke;stroke:var(--bg,#fff);stroke-width:5px;stroke-linejoin:round}
.nd circle{fill:var(--panel,#fff);stroke:var(--edge,#4a4a45);stroke-width:1.8}
.nd circle.inner{fill:none}
.nd text{font:600 12px ui-monospace,Menlo,Consolas,monospace;fill:var(--ink,#1d1d1b);text-anchor:middle;dominant-baseline:central}
.nd.active circle.main{fill:var(--hl,#ffe08a);stroke:var(--accent,#2f5bea);stroke-width:2.6}
.nd.active.acc circle.main{stroke:var(--ok,#1a7f4b)}
.mk{fill:var(--edge,#4a4a45)}
.st{fill:none;stroke:var(--edge,#4a4a45);stroke-width:1.6}
"""


def _edge_label(syms) -> str:
    names = sorted(s for s in syms if s is not None)
    return ",".join(names + (["ε"] if None in syms else []))


def draw_svg(g, prefix: str, label, background: bool = False) -> str:
    n = g.n
    merged = {}
    for a, b, s in g.trans:
        merged.setdefault((a, b), set()).add(s)

    out_adj = [[] for _ in range(n)]
    in_adj = [[] for _ in range(n)]
    for (a, b) in merged:
        out_adj[a].append(b)
        in_adj[b].append(a)

    # layer nodes by BFS depth from the start state
    depth = [-1] * n
    depth[g.start] = 0
    q = deque([g.start])
    while q:
        x = q.popleft()
        for y in out_adj[x]:
            if depth[y] < 0:
                depth[y] = depth[x] + 1
                q.append(y)
    max_d = max(depth)
    for i in range(n):
        if depth[i] < 0:
            max_d += 1
            depth[i] = max_d
    layers = [[] for _ in range(max_d + 1)]
    for i in range(n):
        layers[depth[i]].append(i)
    max_count = max(len(L) for L in layers)

    # order each layer by the barycentre of its predecessors to cut crossings
    yi = [0.0] * n
    for d, L in enumerate(layers):
        if d > 0:
            def key(i):
                preds = [j for j in in_adj[i] if depth[j] < d]
                return sum(yi[j] for j in preds) / len(preds) if preds else i
            L.sort(key=lambda i: (key(i), i))
        for k, v in enumerate(L):
            yi[v] = k + (max_count - len(L)) / 2

    def pos(i):
        return 70 + depth[i] * GX, 60 + yi[i] * GY

    box = [1e9, 1e9, -1e9, -1e9]

    def bb(x, y, r=0):
        box[0] = min(box[0], x - r); box[1] = min(box[1], y - r)
        box[2] = max(box[2], x + r); box[3] = max(box[3], y + r)

    def unit(x, y):
        l = math.hypot(x, y) or 1
        return x / l, y / l

    arrow = f"url(#arr-{prefix})"
    edges, nodes = [], []

    for (a, b), syms in merged.items():
        text = _edge_label(syms)
        px, py = pos(a)
        qx, qy = pos(b)
        if a == b:
            d = (f"M{px - R*.55:.1f},{py - R*.83:.1f} C{px - R*1.5:.1f},{py - R - 40:.1f} "
                 f"{px + R*1.5:.1f},{py - R - 40:.1f} {px + R*.55:.1f},{py - R*.83:.1f}")
            lx, ly = px, py - R - 36
            bb(px, py - R - 44, 14)
        else:
            dx, dy = qx - px, qy - py
            length = math.hypot(dx, dy) or 1
            nx, ny = -dy / length, dx / length
            dl = depth[b] - depth[a]
            if (b, a) in merged:
                off = 26
            elif dl <= 0 or dl >= 2:
                off = 22 + 12 * min(abs(dl), 5)
            else:
                off = 0
            mx, my = (px + qx) / 2, (py + qy) / 2
            cx, cy = mx + nx * off * 2, my + ny * off * 2
            sx, sy = unit(cx - px, cy - py)
            tx, ty = unit(cx - qx, cy - qy)
            d = (f"M{px + sx*R:.1f},{py + sy*R:.1f} Q{cx:.1f},{cy:.1f} "
                 f"{qx + tx*(R+3):.1f},{qy + ty*(R+3):.1f}")
            if off:
                lx, ly = mx + nx * (off + 12), my + ny * (off + 12)
            else:
                m = 1 if ny <= 0 else -1
                lx, ly = mx + nx * m * 12, my + ny * m * 12
            bb(mx + nx * off, my + ny * off, 4)
            bb(lx, ly, 14)
        edges.append(f'<g><path d="{d}" marker-end="{arrow}"/>'
                     f'<text x="{lx:.1f}" y="{ly:.1f}">{escape(text)}</text></g>')

    for i in range(n):
        x, y = pos(i)
        bb(x, y, R + 2)
        cls = "nd acc" if g.accepting[i] else "nd"
        inner = f'<circle class="inner" cx="{x:.1f}" cy="{y:.1f}" r="{R - 4.5}"/>' if g.accepting[i] else ""
        nodes.append(f'<g class="{cls}" id="{prefix}-n{i}"><circle class="main" cx="{x:.1f}" cy="{y:.1f}" r="{R}"/>'
                     f'{inner}<text x="{x:.1f}" y="{y:.1f}">{escape(label(i))}</text></g>')
        if i == g.start:
            edges.append(f'<path class="st" d="M{x - R - 36:.1f},{y:.1f} L{x - R - 2:.1f},{y:.1f}" marker-end="{arrow}"/>')
            bb(x - R - 38, y)

    pad = 22
    vx, vy = box[0] - pad, box[1] - pad
    w, h = box[2] - box[0] + 2 * pad, box[3] - box[1] + 2 * pad
    bg = f'<rect x="{vx:.1f}" y="{vy:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#fff"/>' if background else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx:.1f} {vy:.1f} {w:.1f} {h:.1f}" '
        f'width="{math.ceil(w)}" height="{math.ceil(h)}"><style>{SVG_CSS}</style>{bg}'
        f'<defs><marker id="arr-{prefix}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
        f'markerHeight="8" orient="auto"><path class="mk" d="M0,0 L10,5 L0,10 z"/></marker></defs>'
        f'<g class="ed">{"".join(edges)}</g><g>{"".join(nodes)}</g></svg>'
    )


def to_dot(g, name: str, label) -> str:
    """Graphviz DOT source, e.g. `dot -Tpng nfa.dot -o nfa.png`."""
    q = lambda s: '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    lines = [f"digraph {name} {{", "  rankdir=LR;", "  node [shape=circle, fontname=monospace];",
             '  __start [shape=point, label=""];', f"  __start -> {q(label(g.start))};"]
    for i in range(g.n):
        if g.accepting[i]:
            lines.append(f"  {q(label(i))} [shape=doublecircle];")
    merged = {}
    for a, b, s in g.trans:
        merged.setdefault((a, b), set()).add(s)
    for (a, b), syms in merged.items():
        lines.append(f"  {q(label(a))} -> {q(label(b))} [label={q(_edge_label(syms))}];")
    lines.append("}")
    return "\n".join(lines) + "\n"
