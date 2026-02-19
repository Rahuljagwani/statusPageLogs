"""
Webhook receiver: accept provider webhook POSTs, detect provider from payload, dispatch to adapter, print.
GET /api/events returns last events from log; GET / serves a simple HTML dashboard.
"""
import json
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse
from models import UnifiedEvent
from pipeline.detector import ChangeDetector
from pipeline.formatter import format_event
from providers.atlassian import AtlassianAdapter
from providers.base import BaseAdapter
from event_log import append_events as log_append_events, read_last_events

app = FastAPI()
detector = ChangeDetector()
_adapters: dict[str, BaseAdapter] = {"atlassian": AtlassianAdapter()}


def _detect_webhook_provider(body: bytes) -> str | None:
    """Infer provider from webhook payload shape. Returns 'atlassian', 'status_io', or None."""
    try:
        data = json.loads(body.decode("utf-8") if isinstance(body, bytes) else body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    # Atlassian Statuspage: has "page" and ("incident" or "component_update")
    if "page" in data and ("incident" in data or "component_update" in data):
        return "atlassian"
    # Status.io (placeholder for future): different shape
    # if "result" in data or "status_overall" in data:
    #     return "status_io"
    return None


@app.post("/webhook", response_class=PlainTextResponse)
async def webhook(request: Request) -> str:
    """Accept webhook POST; detect provider, parse via adapter, detect new, format and print."""
    body = await request.body()
    headers = {k: v for k, v in request.headers.items()}
    provider = _detect_webhook_provider(body)
    events: list[UnifiedEvent] = []
    if provider and provider in _adapters:
        events = _adapters[provider].parse_webhook(body, headers)
    new = detector.filter_new(events)
    for e in new:
        print(format_event(e))
    if new:
        log_append_events(new)
    return "OK"


@app.get("/api/events")
async def get_events(limit: int = 200) -> JSONResponse:
    """Return the last `limit` logged events (newest first)."""
    events = read_last_events(limit=limit)
    return JSONResponse(content={"events": events, "count": len(events)})


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Simple HTML page that fetches and displays last events."""
    html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Status page events</title>
<style>
  body { font-family: system-ui; max-width: 900px; margin: 1rem auto; padding: 0 1rem; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #eee; }
  th { background: #f5f5f5; }
  .ts { white-space: nowrap; }
  .msg { max-width: 400px; }
</style>
</head>
<body>
  <h1>Status page events (last 24h / 100KB)</h1>
  <p><a href="/api/events">JSON</a></p>
  <table>
    <thead><tr><th class="ts">Time</th><th>Source</th><th>Product</th><th>Status</th><th class="msg">Message</th></tr></thead>
    <tbody id="tbody"></tbody>
  </table>
  <script>
    fetch('/api/events?limit=200')
      .then(r => r.json())
      .then(d => {
        const tbody = document.getElementById('tbody');
        d.events.forEach(e => {
          const tr = document.createElement('tr');
          tr.innerHTML = '<td class="ts">' + (e.timestamp || '') + '</td><td>' + (e.source_id || '') + '</td><td>' + (e.product_name || '') + '</td><td>' + (e.status || '') + '</td><td class="msg">' + (e.message || '').replace(/</g, '&lt;') + '</td>';
          tbody.appendChild(tr);
        });
        if (d.events.length === 0) tbody.innerHTML = '<tr><td colspan="5">No events yet.</td></tr>';
      })
      .catch(e => { document.getElementById('tbody').innerHTML = '<tr><td colspan="5">Error loading events.</td></tr>'; });
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
