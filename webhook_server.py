"""
Webhook receiver: accept provider webhook POSTs, detect provider from payload, dispatch to adapter, print.
"""
import json
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from models import UnifiedEvent
from pipeline.detector import ChangeDetector
from pipeline.formatter import format_event
from providers.atlassian import AtlassianAdapter
from providers.base import BaseAdapter

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
    return "OK"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
