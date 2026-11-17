/* Front end only: all automata logic and SVG drawing live in Python (regexlab/). */
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const TABS = [
    { id: "ast", label: (c) => `1 · Tokens &amp; tree <small>${c.ast} nodes</small>` },
    { id: "nfa", label: (c) => `2 · NFA <small>${c.nfa} states</small>` },
    { id: "dfa", label: (c) => `3 · DFA <small>${c.dfa} states</small>` },
    { id: "min", label: (c) => `4 · Minimal DFA <small>${c.min} states</small>` },
    { id: "tables", label: () => "Tables" },
  ];
  const CAPS = {
    nfa: "Thompson's construction — ε-edges glue the fragments for each operator.",
    dfa: "Subset construction — every DFA state is the ε-closure of a set of NFA states (see Tables).",
    min: "Hopcroft partition refinement — equivalent DFA states are merged; the dead state is omitted.",
  };
  const EXAMPLES = [["(a|b)*abb", "babb"], ["a(b|c)*d", "abcbd"], ["(0|1)*01", "1101"],
                    ["a+b?c*", "aabcc"], ["(ab|a)(c|bc)", "abc"], ["(a*b*)*", "abba"]];

  let info = null, run = null, tab = "nfa", pos = 0, timer = null, buildSeq = 0, runSeq = 0, debounce = null;

  const api = async (path, params) => (await fetch(path + "?" + new URLSearchParams(params))).json();

  async function rebuild() {
    const seq = ++buildSeq;
    const data = await api("/api/build", { re: $("#re").value });
    if (seq !== buildSeq) return;
    if (!data.ok) { $("#err").textContent = data.error; return; }
    $("#err").textContent = "";
    info = data;
    renderPanels();
    await rerun();
  }

  async function rerun() {
    const seq = ++runSeq;
    const data = await api("/api/run", { re: $("#re").value, s: $("#str").value });
    if (seq !== runSeq || !data.ok) return;
    run = data;
    pos = Math.min(pos, data.chars.length);
    renderRun();
  }

  function setTab(id) {
    tab = id;
    document.querySelectorAll(".tab").forEach((b) => b.setAttribute("aria-selected", b.dataset.id === id));
    document.querySelectorAll(".panel").forEach((p) => (p.hidden = p.dataset.id !== id));
  }

  function renderPanels() {
    $("#tabs").innerHTML = TABS.map((t) =>
      `<button class="tab" role="tab" data-id="${t.id}" aria-selected="${t.id === tab}" aria-controls="panel-${t.id}">${t.label(info.counts)}</button>`).join("");
    $("#tabs").querySelectorAll(".tab").forEach((b) => (b.onclick = () => setTab(b.dataset.id)));
    const toks = info.tokens.map((t) => `<span class="tok"><b>${t.type}</b>${esc(t.value)}</span>`).join("");
    let html = `<div class="panel" id="panel-ast" role="tabpanel" data-id="ast"><p class="cap">Lexer output, then the parse tree (recursive descent).</p>
      <div class="toks">${toks}</div><pre class="tree">${esc(info.tree)}</pre></div>`;
    for (const id of ["nfa", "dfa", "min"]) {
      html += `<div class="panel" id="panel-${id}" role="tabpanel" data-id="${id}"><p class="cap">${CAPS[id]}</p><div class="graph">${info.svg[id]}</div>
        <div class="legend"><span>→ start · ◎ accepting · highlighted = active during the test run</span>
        <button data-exp="${id}">Download SVG</button></div></div>`;
    }
    html += `<div class="panel" id="panel-tables" role="tabpanel" data-id="tables">${info.tables}</div>`;
    $("#panels").innerHTML = html;
    $("#panels").querySelectorAll("[data-exp]").forEach((b) => (b.onclick = () => exportSvg(b.dataset.exp)));
    setTab(tab);
  }

  function exportSvg(id) {
    const svg = document.querySelector(`.panel[data-id="${id}"] svg`).cloneNode(true);
    const vb = svg.getAttribute("viewBox").split(" ");
    svg.setAttribute("style", "--bg:#fff;--panel:#fff;--ink:#111;--edge:#333;--hl:#ffe08a;--accent:#2f5bea;--ok:#1a7f4b");
    svg.querySelectorAll(".active").forEach((n) => n.classList.remove("active"));
    const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    ["x", "y", "width", "height"].forEach((a, i) => bg.setAttribute(a, vb[i]));
    bg.setAttribute("fill", "#fff");
    svg.insertBefore(bg, svg.firstChild.nextSibling);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(svg)], { type: "image/svg+xml" }));
    a.download = `${id}-automaton.svg`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  function renderRun() {
    if (!run || !info) return;
    const chars = run.chars;
    $("#tape").innerHTML = chars.length
      ? chars.map((c, i) => `<span class="c ${i < pos ? "done" : i === pos ? "next" : ""}">${esc(c)}</span>`).join("")
      : '<span class="empty">(empty string)</span>';
    const fmt = (arr, p) => (arr.length ? "{" + arr.map((i) => p + i).join(", ") + "}" : "∅ (dead)");
    for (const id of ["nfa", "dfa", "min"]) {
      const active = new Set(run.steps[id][pos]);
      document.querySelectorAll(`[id^="${id}-n"]`).forEach((g, i) => g.classList.toggle("active", active.has(i)));
    }
    $("#status").innerHTML =
      `<div><b>NFA active states</b><span class="mono">${esc(fmt(run.steps.nfa[pos], "q"))}</span></div>` +
      `<div><b>DFA state</b><span class="mono">${esc(fmt(run.steps.dfa[pos], "D"))}</span></div>` +
      `<div><b>Minimal DFA state</b><span class="mono">${esc(fmt(run.steps.min[pos], "M"))}</span></div>`;
    const v = $("#verdict");
    if (pos === chars.length) {
      v.className = "verdict " + (run.accepted ? "ok" : "bad");
      v.innerHTML = (run.accepted ? "✓ ACCEPTED" : "✗ REJECTED") + "<small>" +
        (run.agree ? "NFA, DFA and minimal DFA agree" : "AUTOMATA DISAGREE — bug!") +
        (run.oracle === null ? "" : run.oracle === run.accepted ? " · matches Python re ✓" : " · differs from Python re ✗") + "</small>";
    } else { v.className = "verdict"; v.textContent = ""; }
  }

  const stop = () => { if (timer) { clearInterval(timer); timer = null; $("#bPlay").textContent = "Play"; } };
  const len = () => (run ? run.chars.length : 0);

  $("#re").addEventListener("input", () => { stop(); clearTimeout(debounce); debounce = setTimeout(rebuild, 120); });
  $("#str").addEventListener("input", () => { stop(); pos = 0; rerun(); });
  $("#bReset").onclick = () => { stop(); pos = 0; renderRun(); };
  $("#bBack").onclick = () => { stop(); pos = Math.max(0, pos - 1); renderRun(); };
  $("#bNext").onclick = () => { stop(); pos = Math.min(len(), pos + 1); renderRun(); };
  $("#bEnd").onclick = () => { stop(); pos = len(); renderRun(); };
  $("#bPlay").onclick = () => {
    if (timer) return stop();
    if (pos >= len()) pos = 0;
    renderRun();
    $("#bPlay").textContent = "Pause";
    timer = setInterval(() => {
      if (pos >= len()) return stop();
      pos++; renderRun();
      if (pos >= len()) stop();
    }, 800);
  };
  EXAMPLES.forEach(([re, s]) => {
    const b = document.createElement("button");
    b.className = "chip"; b.textContent = re;
    b.onclick = () => { stop(); $("#re").value = re; $("#str").value = s; pos = 0; rebuild(); };
    $("#examples").appendChild(b);
  });
  rebuild();
})();
