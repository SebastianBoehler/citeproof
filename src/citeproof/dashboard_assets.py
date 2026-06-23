"""Static assets for the local audit dashboard."""

DASHBOARD_STYLE = """
:root {
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
}
* { box-sizing: border-box; }
body { margin: 0; color: var(--ink); background: var(--bg); }
header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  padding: 20px clamp(18px, 3vw, 36px);
  border-bottom: 1px solid var(--border);
  background: var(--paper);
}
h1 { margin: 0 0 6px; font-size: 25px; line-height: 1.2; }
.subtitle { margin: 0; color: var(--muted); font-size: 14px; }
.stats { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; max-width: 520px; }
.stat, .badge, .cite {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  border-radius: 999px;
  padding: 5px 8px;
  font-size: 12px;
  line-height: 1;
}
.stat { border: 1px solid var(--border); background: #f8fafc; color: #475467; }
.badge { color: #fff; font-weight: 700; }
.supported { background: var(--supported); }
.partially_supported { background: var(--partial); }
.contradicted { background: var(--bad); }
.unsupported, .uncertain { background: var(--unknown); }
.cite { border: 0; background: #eaf1ff; color: #1e40af; cursor: pointer; }
.shell { display: grid; grid-template-columns: minmax(0, 1fr) 420px; min-height: calc(100vh - 86px); }
.document { padding: 22px clamp(16px, 4vw, 46px); overflow: auto; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 auto 16px; max-width: 860px; }
.filter {
  border: 1px solid var(--border);
  background: var(--paper);
  border-radius: 6px;
  color: var(--ink);
  cursor: pointer;
  font-size: 13px;
  padding: 7px 10px;
}
.filter[aria-pressed="true"] { border-color: var(--blue); color: var(--blue); }
.paper {
  max-width: 860px;
  min-height: 760px;
  margin: 0 auto;
  padding: clamp(26px, 5vw, 56px);
  background: var(--paper);
  border: 1px solid var(--border);
  box-shadow: 0 18px 48px rgba(16, 24, 40, 0.08);
}
.paper-title { margin: 0 0 22px; font-size: 15px; color: var(--muted); text-transform: uppercase; }
.doc-heading { margin: 28px 0 12px; font-size: 24px; line-height: 1.25; }
.doc-paragraph {
  margin: 0 0 18px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 18px;
  line-height: 1.72;
}
.annotated {
  position: relative;
  padding: 12px 12px 12px 16px;
  border: 1px solid transparent;
  border-left-width: 4px;
  border-radius: 7px;
  background: #fbfcff;
  cursor: pointer;
}
.annotated.active { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(29, 78, 216, 0.12); }
.cite.active, .mini-badge.active { outline: 2px solid rgba(29, 78, 216, 0.45); outline-offset: 2px; }
.status-supported { border-left-color: var(--supported); background: #f3fbf7; }
.status-partially_supported { border-left-color: var(--partial); background: #fff8eb; }
.status-contradicted { border-left-color: var(--bad); background: #fff5f4; }
.status-unsupported, .status-uncertain { border-left-color: var(--unknown); background: #f8fafc; }
.claim-top, .claim-bottom { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
.line { color: var(--muted); font-size: 12px; }
.inline-cite { transform: translateY(-1px); }
.annotation-badges { display: inline-flex; gap: 4px; margin: 0 6px; vertical-align: middle; }
.mini-badge { border: 0; cursor: pointer; min-height: 21px; padding: 4px 7px; }
.inspector {
  position: sticky;
  top: 0;
  height: calc(100vh - 86px);
  overflow: auto;
  padding: 20px;
  border-left: 1px solid var(--border);
  background: #fbfcff;
}
.panel { background: var(--paper); border: 1px solid var(--border); border-radius: 8px; padding: 15px; margin-bottom: 14px; }
h2 { margin: 0 0 12px; font-size: 19px; line-height: 1.28; }
h3 { margin: 0 0 10px; font-size: 13px; color: var(--muted); text-transform: uppercase; }
.reason, blockquote { font-size: 14px; line-height: 1.55; }
.reason { margin: 9px 0 0; }
.why-label {
  margin-top: 14px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: #f8fafc;
  overflow: hidden;
}
.why-title {
  margin: 0;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
  font-weight: 800;
  color: var(--muted);
  text-transform: uppercase;
}
.why-row {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
  line-height: 1.45;
}
.why-row:last-child { border-bottom: 0; }
.why-key { color: var(--muted); font-weight: 700; }
.failure-mode-value { font-weight: 800; color: var(--ink); }
.source { color: var(--muted); font-size: 12px; margin-bottom: 6px; }
.evidence { border-top: 1px solid var(--border); padding-top: 12px; margin-top: 12px; }
blockquote { margin: 0; padding-left: 12px; border-left: 3px solid var(--border); }
mark { background: #fff0a6; color: inherit; padding: 0 1px; border-radius: 2px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
td, th { border-bottom: 1px solid var(--border); padding: 8px 6px; text-align: left; vertical-align: top; }
@media (max-width: 980px) {
  header { display: block; }
  .stats { justify-content: flex-start; margin-top: 14px; }
  .shell { grid-template-columns: 1fr; }
  .inspector { position: static; height: auto; border-left: 0; border-top: 1px solid var(--border); }
}
""".strip()
