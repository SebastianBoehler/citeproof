"""Static HTML audit dashboard rendering."""

from __future__ import annotations

import json
from collections import Counter
from html import escape
from typing import Any

from citeproof.models import VerificationResult


def results_to_html(results: list[VerificationResult]) -> str:
    """Render claim verification results as a self-contained HTML dashboard."""

    return claim_results_to_html(
        [result.to_dict() for result in results],
        title="CiteProof Audit Dashboard",
    )


def paper_report_to_html(report: Any) -> str:
    """Render a whole-paper verification report as a self-contained HTML dashboard."""

    bibliography = report.bibliography
    summary = {
        "Loaded sources": report.loaded_source_count,
        "Mapped sources": report.mapped_source_count,
        "Bib errors": bibliography["error_count"],
        "Bib warnings": bibliography["warning_count"],
    }
    return claim_results_to_html(
        report.claim_results,
        title="CiteProof Paper Audit",
        summary=summary,
    )


def claim_results_to_html(
    claim_results: list[dict[str, Any]],
    title: str,
    summary: dict[str, int] | None = None,
) -> str:
    """Render serialized claim results as an inspectable local dashboard."""

    counts = Counter(result["label"] for result in claim_results)
    payload = {
        "title": title,
        "summary": summary or {},
        "counts": dict(counts),
        "results": claim_results,
    }
    data = json.dumps(payload, sort_keys=True).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
:root {{
  color-scheme: light;
  --bg: #f7f8fb;
  --panel: #ffffff;
  --text: #1f2937;
  --muted: #687385;
  --border: #d9dee8;
  --supported: #16724a;
  --partial: #93610b;
  --bad: #b42318;
  --unknown: #46556b;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--text); }}
header {{
  padding: 24px clamp(18px, 4vw, 44px);
  border-bottom: 1px solid var(--border);
  background: var(--panel);
}}
h1 {{ margin: 0 0 8px; font-size: 28px; line-height: 1.2; font-weight: 700; }}
.subtitle {{ margin: 0; color: var(--muted); font-size: 14px; }}
.stats {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }}
.stat {{ border: 1px solid var(--border); border-radius: 6px; padding: 7px 10px; font-size: 13px; }}
main {{ display: grid; grid-template-columns: minmax(320px, 43%) minmax(0, 1fr); min-height: calc(100vh - 142px); }}
.list {{ border-right: 1px solid var(--border); padding: 18px; overflow: auto; }}
.toolbar {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }}
.filter {{
  border: 1px solid var(--border);
  background: var(--panel);
  border-radius: 6px;
  color: var(--text);
  cursor: pointer;
  font-size: 13px;
  padding: 7px 10px;
}}
.filter[aria-pressed="true"] {{ border-color: #1d4ed8; color: #1d4ed8; }}
.claim {{
  width: 100%;
  text-align: left;
  border: 1px solid var(--border);
  background: var(--panel);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
  cursor: pointer;
}}
.claim.active {{ border-color: #1d4ed8; box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.12); }}
.claim-text {{ margin: 8px 0 10px; font-size: 14px; line-height: 1.45; }}
.meta {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }}
.badge, .citation {{
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  line-height: 1;
  min-height: 24px;
  padding: 5px 8px;
}}
.badge {{ color: #ffffff; font-weight: 650; }}
.supported {{ background: var(--supported); }}
.partially_supported {{ background: var(--partial); }}
.contradicted {{ background: var(--bad); }}
.unsupported, .uncertain {{ background: var(--unknown); }}
.citation {{ background: #edf2ff; color: #21439a; border: 0; cursor: pointer; }}
.detail {{ padding: 22px clamp(18px, 4vw, 36px); overflow: auto; }}
.panel {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 14px; }}
h2 {{ margin: 0 0 12px; font-size: 20px; line-height: 1.25; }}
h3 {{ margin: 0 0 10px; font-size: 14px; line-height: 1.35; color: var(--muted); text-transform: uppercase; }}
.reason {{ margin: 8px 0 0; line-height: 1.55; }}
.evidence {{ border-top: 1px solid var(--border); padding-top: 12px; margin-top: 12px; }}
.source {{ color: var(--muted); font-size: 12px; margin-bottom: 6px; }}
blockquote {{ margin: 0; padding-left: 12px; border-left: 3px solid var(--border); line-height: 1.55; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ border-bottom: 1px solid var(--border); padding: 8px; text-align: left; vertical-align: top; }}
@media (max-width: 820px) {{
  main {{ grid-template-columns: 1fr; }}
  .list {{ border-right: 0; border-bottom: 1px solid var(--border); max-height: 48vh; }}
}}
</style>
</head>
<body>
<header>
  <h1>{escape(title)}</h1>
  <p class="subtitle">Click a claim or citation chip to inspect evidence, contradictions, and repair guidance.</p>
  <div class="stats" id="stats"></div>
</header>
<main>
  <section class="list">
    <div class="toolbar" id="filters"></div>
    <div id="claims"></div>
  </section>
  <section class="detail" id="detail"></section>
</main>
<script id="citeproof-data" type="application/json">{data}</script>
<script>
const payload = JSON.parse(document.getElementById("citeproof-data").textContent);
let active = 0;
let filter = "all";
const labels = ["all", "supported", "partially_supported", "contradicted", "unsupported", "uncertain"];
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({{
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}}[char]));
const labelClass = (label) => ["supported", "partially_supported", "contradicted", "unsupported", "uncertain"].includes(label)
  ? label : "uncertain";

function renderStats() {{
  const parts = Object.entries(payload.summary).map(([key, value]) => `${{esc(key)}}: ${{esc(value)}}`);
  Object.entries(payload.counts).forEach(([key, value]) => parts.push(`${{esc(key)}}: ${{esc(value)}}`));
  document.getElementById("stats").innerHTML = parts.map((item) => `<span class="stat">${{item}}</span>`).join("");
}}

function renderFilters() {{
  document.getElementById("filters").innerHTML = labels.map((label) =>
    `<button class="filter" aria-pressed="${{filter === label}}" data-filter="${{label}}">${{label}}</button>`
  ).join("");
  document.querySelectorAll(".filter").forEach((button) => button.addEventListener("click", () => {{
    filter = button.dataset.filter;
    const first = visibleResults()[0];
    active = first ? first.index : 0;
    render();
  }}));
}}

function visibleResults() {{
  return payload.results
    .map((result, index) => ({{ result, index }}))
    .filter((item) => filter === "all" || item.result.label === filter);
}}

function renderClaims() {{
  const items = visibleResults();
  document.getElementById("claims").innerHTML = items.map(({{ result, index }}) => {{
    const citations = (result.citations || []).map((key) =>
      `<button class="citation" data-index="${{index}}" title="Inspect citation ${{esc(key)}}">${{esc(key)}}</button>`
    ).join("");
    return `<button class="claim ${{active === index ? "active" : ""}}" data-index="${{index}}">
      <div class="meta"><span class="badge ${{labelClass(result.label)}}">${{esc(result.label)}}</span>
      <span class="stat">confidence ${{Number(result.confidence || 0).toFixed(3)}}</span></div>
      <p class="claim-text">${{esc(result.claim)}}</p>
      <div class="meta">${{citations || '<span class="stat">no citations</span>'}}</div>
    </button>`;
  }}).join("") || '<div class="panel">No claims match this filter.</div>';
  document.querySelectorAll(".claim, .citation").forEach((node) => node.addEventListener("click", (event) => {{
    event.stopPropagation();
    active = Number(node.dataset.index);
    render();
  }}));
}}

function renderDetail() {{
  const result = payload.results[active] || payload.results[0];
  if (!result) {{
    document.getElementById("detail").innerHTML = '<div class="panel">No citation-bearing claims found.</div>';
    return;
  }}
  const trace = result.trace || {{}};
  const evidence = (result.evidence || []).map((item, index) => `
    <div class="evidence">
      <div class="source">Evidence ${{index + 1}} - ${{esc(item.source_id)}}${{item.page ? `, page ${{item.page}}` : ""}} - score ${{Number(item.score || 0).toFixed(4)}}</div>
      <blockquote>${{esc(item.text)}}</blockquote>
    </div>`).join("");
  const atoms = ((trace.atom_verifications || [])).map((atom) => `
    <tr><td>${{esc(atom.label)}}</td><td>${{esc(atom.text)}}</td><td>${{esc(atom.failure_mode || "none")}}</td><td>${{esc(atom.reason)}}</td></tr>`
  ).join("");
  document.getElementById("detail").innerHTML = `
    <div class="panel">
      <h2>${{esc(result.claim)}}</h2>
      <div class="meta"><span class="badge ${{labelClass(result.label)}}">${{esc(result.label)}}</span>
      <span class="stat">failure: ${{esc(result.failure_mode || "none")}}</span>
      <span class="stat">review: ${{esc(trace.review_action || "none")}}</span></div>
      <p class="reason">${{esc(result.reason)}}</p>
    </div>
    <div class="panel"><h3>Cited Evidence</h3>${{evidence || "<p>No evidence spans were selected.</p>"}}</div>
    <div class="panel"><h3>Atomic Checks</h3><table><thead><tr><th>Label</th><th>Atom</th><th>Failure</th><th>Reason</th></tr></thead><tbody>${{atoms || '<tr><td colspan="4">No atom trace available.</td></tr>'}}</tbody></table></div>`;
}}

function render() {{
  renderStats();
  renderFilters();
  renderClaims();
  renderDetail();
}}
render();
</script>
</body>
</html>
"""
