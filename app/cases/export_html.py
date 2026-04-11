from __future__ import annotations

from jinja2 import BaseLoader, Environment, select_autoescape

from app.cases.models import CaseDetail, IOCAggregate

_ENV = Environment(
    loader=BaseLoader(),
    autoescape=select_autoescape(["html", "xml"]),
)
_CASE_PACK_TEMPLATE = _ENV.from_string(
    """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{{ detail.title }} — Investigation case pack</title>
  <style>
    :root {
      --bg: #0f1419;
      --panel: #1a2332;
      --text: #e7ecf3;
      --muted: #8b9bb4;
      --accent: #3d8bfd;
      --border: #2d3a4d;
    }
    * { box-sizing: border-box; }
    body {
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      line-height: 1.5;
    }
    header {
      padding: 1.5rem 2rem;
      border-bottom: 1px solid var(--border);
      background: linear-gradient(180deg, #152028 0%, var(--bg) 100%);
    }
    h1 { font-size: 1.35rem; margin: 0 0 0.35rem; font-weight: 600; }
    .meta { color: var(--muted); font-size: 0.875rem; }
    .wrap { max-width: 960px; margin: 0 auto; padding: 1.5rem 2rem 3rem; }
    section { margin-bottom: 2rem; }
    h2 {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin: 0 0 0.75rem;
      font-weight: 600;
    }
    .pill {
      display: inline-block;
      padding: 0.15rem 0.55rem;
      border-radius: 999px;
      font-size: 0.75rem;
      background: var(--panel);
      border: 1px solid var(--border);
      margin-right: 0.35rem;
      margin-bottom: 0.35rem;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem 1.1rem;
    }
    .timeline-item {
      border-left: 3px solid var(--accent);
      padding-left: 1rem;
      margin-bottom: 1.25rem;
    }
    .timeline-item.kind-note { border-left-color: #6c757d; }
    .timeline-item.kind-triage_snapshot { border-left-color: #20c997; }
    .timeline-item.kind-search_snapshot { border-left-color: #6610f2; }
    .timeline-item.kind-ioc_signal { border-left-color: #fd7e14; }
    .timeline-item.kind-status_change { border-left-color: #ffc107; }
    .t-head { font-weight: 600; font-size: 0.95rem; margin-bottom: 0.25rem; }
    .t-time { font-size: 0.8rem; color: var(--muted); margin-bottom: 0.5rem; }
    .json {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.78rem;
      background: #0b0f14;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.65rem 0.75rem;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .summary { white-space: pre-wrap; }
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    th, td { text-align: left; padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--border); }
    th { color: var(--muted); font-weight: 500; }
  </style>
</head>
<body>
  <header>
    <h1>{{ detail.title }}</h1>
    <div class="meta">
      Case ID: <code>{{ detail.id }}</code>
      · Status: <strong>{{ detail.status.value }}</strong>
      {% if detail.severity %}
      · Severity: <strong>{{ detail.severity.value }}</strong>
      {% endif %}
      {% if detail.owner %}· Owner: {{ detail.owner }}{% endif %}
    </div>
    <div class="meta" style="margin-top:0.5rem;">
      Created {{ detail.created_at }} · Updated {{ detail.updated_at }}
    </div>
  </header>
  <div class="wrap">
    {% if detail.tags %}
    <section>
      <h2>Tags</h2>
      <div>{% for t in detail.tags %}<span class="pill">{{ t }}</span>{% endfor %}</div>
    </section>
    {% endif %}

    {% if detail.external_refs %}
    <section>
      <h2>External references</h2>
      <div class="panel">
        <table>
          <thead><tr><th>Key</th><th>Value</th></tr></thead>
          <tbody>
            {% for k, v in detail.external_refs.items() %}
            <tr><td>{{ k }}</td><td>{{ v }}</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </section>
    {% endif %}

    {% if detail.summary %}
    <section>
      <h2>Summary</h2>
      <div class="panel summary">{{ detail.summary }}</div>
    </section>
    {% endif %}

    <section>
      <h2>IOC rollup</h2>
      <div class="panel">
        {% if ioc.ipv4 or ioc.sha256 or ioc.domains %}
        <table>
          <thead><tr><th>Type</th><th>Values</th></tr></thead>
          <tbody>
            {% if ioc.ipv4 %}
            <tr><td>IPv4</td><td>{{ ioc.ipv4 | join(', ') }}</td></tr>
            {% endif %}
            {% if ioc.domains %}
            <tr><td>Domains</td><td>{{ ioc.domains | join(', ') }}</td></tr>
            {% endif %}
            {% if ioc.sha256 %}
            <tr><td>SHA256</td><td>{{ ioc.sha256 | join(', ') }}</td></tr>
            {% endif %}
          </tbody>
        </table>
        {% else %}
        <span style="color:var(--muted)">No IOC-shaped tokens detected in case text or timeline.</span>
        {% endif %}
      </div>
    </section>

    <section>
      <h2>Timeline ({{ detail.timeline | length }} entries)</h2>
      {% for e in detail.timeline %}
      <div class="timeline-item kind-{{ e.kind.value }}">
        <div class="t-head">{{ e.kind.value }} · {% if e.title %}{{ e.title }}{% else %}<em>Untitled</em>{% endif %}</div>
        <div class="t-time">#{{ e.id }} · {{ e.created_at }}</div>
        {% if e.body %}
        <div class="panel" style="margin-bottom:0.5rem;">{{ e.body }}</div>
        {% endif %}
        {% if e.payload %}
        <div class="json">{{ e.payload | tojson(indent=2) }}</div>
        {% endif %}
      </div>
      {% endfor %}
    </section>
  </div>
</body>
</html>
""".strip()
)


def render_case_pack_html(detail: CaseDetail, ioc: IOCAggregate) -> str:
    """Produce a self-contained HTML document for sharing or archiving."""

    return _CASE_PACK_TEMPLATE.render(detail=detail, ioc=ioc)
