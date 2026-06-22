"""Static HTML audit dashboard rendering."""

from __future__ import annotations

import json
from collections import Counter
from html import escape
from typing import Any

from citeproof.document_render import render_audit_document
from citeproof.models import VerificationResult


def results_to_html(
    results: list[VerificationResult],
    source_text: str | None = None,
) -> str:
    """Render claim verification results as a self-contained HTML dashboard."""

    return claim_results_to_html(
        [result.to_dict() for result in results],
        title="CiteProof Audit Dashboard",
        source_text=source_text,
    )


def paper_report_to_html(report: Any, source_text: str | None = None) -> str:
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
        source_text=source_text,
    )


def claim_results_to_html(
    claim_results: list[dict[str, Any]],
    title: str,
    summary: dict[str, int] | None = None,
    source_text: str | None = None,
) -> str:
    """Render serialized claim results as an inspectable local dashboard."""

    counts = Counter(result["label"] for result in claim_results)
    payload = {
        "title": title,
        "summary": summary or {},
        "counts": dict(counts),
        "results": claim_results,
        "documentHtml": render_audit_document(source_text, claim_results),
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
  --bg: #f4f6fa;
  --paper: #ffffff;
  --ink: #1d2430;
  --muted: #667085;
  --border: #d9dee8;
  --blue: #1d4ed8;
  --supported: #14724f;
  --partial: #9a6208;
  --bad: #b42318;
  --unknown: #475467;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: var(--ink); background: var(--bg); }}
header {{
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  padding: 20px clamp(18px, 3vw, 36px);
  border-bottom: 1px solid var(--border);
  background: var(--paper);
}}
h1 {{ margin: 0 0 6px; font-size: 25px; line-height: 1.2; }}
.subtitle {{ margin: 0; color: var(--muted); font-size: 14px; }}
.stats {{ display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; max-width: 520px; }}
.stat, .badge, .cite {{
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  border-radius: 999px;
  padding: 5px 8px;
  font-size: 12px;
  line-height: 1;
}}
.stat {{ border: 1px solid var(--border); background: #f8fafc; color: #475467; }}
.badge {{ color: #fff; font-weight: 700; }}
.supported {{ background: var(--supported); }}
.partially_supported {{ background: var(--partial); }}
.contradicted {{ background: var(--bad); }}
.unsupported, .uncertain {{ background: var(--unknown); }}
.cite {{ border: 0; background: #eaf1ff; color: #1e40af; cursor: pointer; }}
.shell {{ display: grid; grid-template-columns: minmax(0, 1fr) 420px; min-height: calc(100vh - 86px); }}
.document {{ padding: 22px clamp(16px, 4vw, 46px); overflow: auto; }}
.toolbar {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 0 auto 16px; max-width: 860px; }}
.filter {{
  border: 1px solid var(--border);
  background: var(--paper);
  border-radius: 6px;
  color: var(--ink);
  cursor: pointer;
  font-size: 13px;
  padding: 7px 10px;
}}
.filter[aria-pressed="true"] {{ border-color: var(--blue); color: var(--blue); }}
.paper {{
  max-width: 860px;
  min-height: 760px;
  margin: 0 auto;
  padding: clamp(26px, 5vw, 56px);
  background: var(--paper);
  border: 1px solid var(--border);
  box-shadow: 0 18px 48px rgba(16, 24, 40, 0.08);
}}
.paper-title {{ margin: 0 0 22px; font-size: 15px; color: var(--muted); text-transform: uppercase; }}
.doc-heading {{ margin: 28px 0 12px; font-size: 24px; line-height: 1.25; }}
.doc-paragraph {{
  margin: 0 0 18px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 18px;
  line-height: 1.72;
}}
.annotated {{
  position: relative;
  padding: 12px 12px 12px 16px;
  border: 1px solid transparent;
  border-left-width: 4px;
  border-radius: 7px;
  background: #fbfcff;
  cursor: pointer;
}}
.annotated.active {{ border-color: var(--blue); box-shadow: 0 0 0 3px rgba(29, 78, 216, 0.12); }}
.claim-span.annotated {{ display: inline; position: static; border: 0; border-radius: 5px; padding: 2px 4px; -webkit-box-decoration-break: clone; box-decoration-break: clone; }}
.status-supported {{ border-left-color: var(--supported); background: #f3fbf7; }}
.status-partially_supported {{ border-left-color: var(--partial); background: #fff8eb; }}
.status-contradicted {{ border-left-color: var(--bad); background: #fff5f4; }}
.status-unsupported, .status-uncertain {{ border-left-color: var(--unknown); background: #f8fafc; }}
.claim-top, .claim-bottom {{ display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }}
.line {{ color: var(--muted); font-size: 12px; }}
.inline-cite {{ transform: translateY(-1px); }}
.annotation-badges {{ display: inline-flex; gap: 4px; margin-left: 6px; vertical-align: middle; }}
.mini-badge {{ border: 0; cursor: pointer; min-height: 21px; padding: 4px 7px; }}
.inspector {{
  position: sticky;
  top: 0;
  height: calc(100vh - 86px);
  overflow: auto;
  padding: 20px;
  border-left: 1px solid var(--border);
  background: #fbfcff;
}}
.panel {{ background: var(--paper); border: 1px solid var(--border); border-radius: 8px; padding: 15px; margin-bottom: 14px; }}
h2 {{ margin: 0 0 12px; font-size: 19px; line-height: 1.28; }}
h3 {{ margin: 0 0 10px; font-size: 13px; color: var(--muted); text-transform: uppercase; }}
.reason, blockquote {{ font-size: 14px; line-height: 1.55; }}
.reason {{ margin: 9px 0 0; }}
.source {{ color: var(--muted); font-size: 12px; margin-bottom: 6px; }}
.evidence {{ border-top: 1px solid var(--border); padding-top: 12px; margin-top: 12px; }}
blockquote {{ margin: 0; padding-left: 12px; border-left: 3px solid var(--border); }}
mark {{ background: #fff0a6; color: inherit; padding: 0 1px; border-radius: 2px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
td, th {{ border-bottom: 1px solid var(--border); padding: 8px 6px; text-align: left; vertical-align: top; }}
@media (max-width: 980px) {{
  header {{ display: block; }}
  .stats {{ justify-content: flex-start; margin-top: 14px; }}
  .shell {{ grid-template-columns: 1fr; }}
  .inspector {{ position: static; height: auto; border-left: 0; border-top: 1px solid var(--border); }}
}}
</style>
</head>
<body>
<header>
  <div>
    <h1>{escape(title)}</h1>
    <p class="subtitle">Paper text overlay with citation-level verification and an evidence inspector.</p>
  </div>
  <div class="stats" id="stats"></div>
</header>
<main class="shell">
  <section class="document">
    <div class="toolbar" id="filters"></div>
    <div class="paper">
      <p class="paper-title">Paper Text Overlay</p>
      <div id="paper"></div>
    </div>
  </section>
  <aside class="inspector" id="inspector"></aside>
</main>
<script id="citeproof-data" type="application/json">{data}</script>
<script>
const payload = JSON.parse(document.getElementById("citeproof-data").textContent);
let active = 0;
let filter = "all";
const labels = ["all", "supported", "partially_supported", "contradicted", "unsupported", "uncertain"];
const known = labels.slice(1);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({{
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}}[char]));
const labelClass = (label) => known.includes(label) ? label : "uncertain";
const terms = (text) => [...new Set(String(text ?? "").toLowerCase().match(/[a-z0-9][a-z0-9-]{{3,}}/g) || [])].slice(0, 12);
function highlight(text, claim) {{
  let html = esc(text);
  for (const term of terms(claim)) {{
    html = html.replace(new RegExp(`\\\\b(${{term.replace(/[.*+?^${{}}()|[\\]\\\\]/g, "\\\\$&")}})\\\\b`, "gi"), "<mark>$1</mark>");
  }}
  return html;
}}
function visibleItems() {{
  return payload.results.map((result, index) => ({{ result, index }}))
    .filter((item) => filter === "all" || item.result.label === filter);
}}
function select(index) {{
  active = index;
  render();
  document.querySelector(`[data-claim="${{index}}"]`)?.scrollIntoView({{ block: "nearest", behavior: "smooth" }});
}}
function renderStats() {{
  const items = Object.entries(payload.summary || {{}}).map(([key, value]) => `${{esc(key)}}: ${{esc(value)}}`);
  Object.entries(payload.counts || {{}}).forEach(([key, value]) => items.push(`${{esc(key)}}: ${{esc(value)}}`));
  document.getElementById("stats").innerHTML = items.map((item) => `<span class="stat">${{item}}</span>`).join("");
}}
function renderFilters() {{
  document.getElementById("filters").innerHTML = labels.map((label) =>
    `<button class="filter" aria-pressed="${{filter === label}}" data-filter="${{label}}">${{esc(label)}}</button>`
  ).join("");
  document.querySelectorAll(".filter").forEach((button) => button.addEventListener("click", () => {{
    filter = button.dataset.filter;
    active = visibleItems()[0]?.index ?? 0;
    render();
  }}));
}}
function renderPaper() {{
  document.getElementById("paper").innerHTML = payload.documentHtml || '<p>No paper text available.</p>';
  document.querySelectorAll(".annotated, .cite, .mini-badge").forEach((node) => node.addEventListener("click", (event) => {{
    event.stopPropagation();
    select(Number(node.dataset.claim ?? node.dataset.index));
  }}));
  document.querySelectorAll(".annotated").forEach((node) => {{
    const index = Number(node.dataset.claim);
    node.hidden = filter !== "all" && payload.results[index]?.label !== filter;
    node.classList.toggle("active", index === active);
  }});
}}
function renderInspector() {{
  const result = payload.results[active] || payload.results[0];
  if (!result) {{
    document.getElementById("inspector").innerHTML = '<div class="panel">No citation-bearing claims found.</div>';
    return;
  }}
  const trace = result.trace || {{}};
  const evidence = (result.evidence || []).map((item, index) => `
    <div class="evidence">
      <div class="source">Evidence ${{index + 1}} - ${{esc(item.source_id)}}${{item.page ? `, page ${{esc(item.page)}}` : ""}} - score ${{Number(item.score || 0).toFixed(4)}}</div>
      <blockquote>${{highlight(item.text, result.claim)}}</blockquote>
    </div>`).join("");
  const atoms = (trace.atom_verifications || []).map((atom) =>
    `<tr><td>${{esc(atom.label)}}</td><td>${{esc(atom.text)}}</td><td>${{esc(atom.failure_mode || "none")}}</td></tr>`
  ).join("");
  document.getElementById("inspector").innerHTML = `
    <div class="panel">
      <h2>${{esc(result.claim)}}</h2>
      <div class="claim-bottom"><span class="badge ${{labelClass(result.label)}}">${{esc(result.label)}}</span><span class="stat">failure: ${{esc(result.failure_mode || "none")}}</span></div>
      <p class="reason">${{esc(result.reason)}}</p>
      <p class="reason"><strong>Review action:</strong> ${{esc(trace.review_action || "none")}}</p>
    </div>
    <div class="panel"><h3>Citation Keys</h3><div class="claim-bottom">${{(result.citations || []).map((key) => `<span class="cite">${{esc(key)}}</span>`).join("") || "none"}}</div></div>
    <div class="panel"><h3>Evidence Snippets</h3>${{evidence || "<p>No evidence spans were selected.</p>"}}</div>
    <div class="panel"><h3>Atomic Checks</h3><table><thead><tr><th>Label</th><th>Atom</th><th>Failure</th></tr></thead><tbody>${{atoms || '<tr><td colspan="3">No atom trace available.</td></tr>'}}</tbody></table></div>`;
}}
function render() {{
  renderStats();
  renderFilters();
  renderPaper();
  renderInspector();
}}
render();
</script>
</body>
</html>
"""
