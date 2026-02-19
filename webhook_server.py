"""
Webhook receiver: accept Statuspage POSTs, parse via adapter, run through pipeline and print.
"""
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from pipeline.detector import ChangeDetector
from pipeline.formatter import format_event
from providers.atlassian import AtlassianAdapter

app = FastAPI()
detector = ChangeDetector()
atlassian = AtlassianAdapter()


@app.post("/webhook", response_class=PlainTextResponse)
async def webhook(request: Request) -> str:
    """Accept Statuspage webhook POST; parse with Atlassian adapter, detect new, format and print."""
    body = await request.body()
    headers = {k: v for k, v in request.headers.items()}
    events = atlassian.parse_webhook(body, headers)
    new = detector.filter_new(events)
    for e in new:
        print(format_event(e))
    return "OK"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
