"""Static HTML audit dashboard rendering."""

from __future__ import annotations

import json
from collections import Counter
from html import escape
from typing import Any

from citeproof.dashboard_assets import DASHBOARD_STYLE
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
{DASHBOARD_STYLE}
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
  document.querySelectorAll("#paper .annotated, #paper .cite, #paper .mini-badge").forEach((node) => node.addEventListener("click", (event) => {{
    event.stopPropagation();
    select(Number(node.dataset.claim ?? node.dataset.index));
  }}));
  document.querySelectorAll("#paper .annotated").forEach((node) => {{
    const index = Number(node.dataset.claim);
    node.hidden = filter !== "all" && payload.results[index]?.label !== filter;
    node.classList.toggle("active", index === active);
  }});
  document.querySelectorAll("#paper .cite, #paper .mini-badge").forEach((node) => {{
    const index = Number(node.dataset.index);
    if (Number.isFinite(index)) node.hidden = filter !== "all" && payload.results[index]?.label !== filter;
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
      <div class="source">Evidence ${{index + 1}} - ${{esc(item.title || item.source_id)}}${{item.citation_key ? ` - ${{esc(item.citation_key)}}` : ""}}${{item.page ? `, page ${{esc(item.page)}}` : ""}} - score ${{Number(item.score || 0).toFixed(4)}}</div>
      <blockquote>${{highlight(item.text, result.claim)}}</blockquote>
    </div>`).join("");
  const atoms = (trace.atom_verifications || []).map((atom) =>
    `<tr><td>${{esc(atom.label)}}</td><td>${{esc(atom.text)}}</td><td>${{esc(atom.failure_mode || "none")}}</td><td>${{esc(atom.candidate_count ?? 0)}}</td><td>${{esc(atom.best_support_rank ?? "none")}}</td><td>${{esc(atom.best_contradiction_rank ?? "none")}}</td></tr>`
  ).join("");
  document.getElementById("inspector").innerHTML = `
    <div class="panel">
      <h2>${{esc(result.claim)}}</h2>
      <div class="claim-bottom"><span class="badge ${{labelClass(result.label)}}">${{esc(result.label)}}</span></div>
      <div class="why-label">
        <p class="why-title">Why this label?</p>
        <div class="why-row"><span class="why-key">Failure mode</span><span class="failure-mode-value">${{esc(result.failure_mode || "none")}}</span></div>
        <div class="why-row"><span class="why-key">Confidence</span><span>${{Number(result.confidence || 0).toFixed(2)}}</span></div>
        <div class="why-row"><span class="why-key">Source gate</span><span>${{esc(trace.source_gate_status || "unknown")}}</span></div>
        <div class="why-row"><span class="why-key">Reason</span><span>${{esc(result.reason || "No reason reported.")}}</span></div>
        <div class="why-row"><span class="why-key">Review action</span><span>${{esc(trace.review_action || "none")}}</span></div>
      </div>
    </div>
    <div class="panel"><h3>Citation Keys</h3><div class="claim-bottom">${{(result.citations || []).map((key) => `<span class="cite">${{esc(key)}}</span>`).join("") || "none"}}</div></div>
    <div class="panel"><h3>Evidence Snippets</h3>${{evidence || "<p>No evidence spans were selected.</p>"}}</div>
    <div class="panel"><h3>Atomic Evidence Trace</h3><table><thead><tr><th>Label</th><th>Atom</th><th>Failure</th><th>Candidates</th><th>Best support</th><th>Best contradiction</th></tr></thead><tbody>${{atoms || '<tr><td colspan="6">No atom trace available.</td></tr>'}}</tbody></table></div>`;
}}
function render() {{ renderStats(); renderFilters(); renderPaper(); renderInspector(); }}
render();
</script>
</body>
</html>
"""
