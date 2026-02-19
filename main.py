"""
Status page monitor: poll configured targets, detect new events, print to console.
"""
import asyncio
import aiohttp
from config import load_config
from pipeline.detector import ChangeDetector
from pipeline.formatter import format_event
from providers.atlassian import AtlassianAdapter


async def run_once(
    session: aiohttp.ClientSession,
    target: dict,
    adapter: AtlassianAdapter,
    detector: ChangeDetector,
) -> None:
    """Scrape one target, filter to new events, print formatted."""
    events = await adapter.fetch_events(session, target)
    new = detector.filter_new(events)
    for e in new:
        print(format_event(e))


async def main() -> None:
    cfg = load_config()
    target = cfg["targets"][0]
    interval = target.get("scrape_interval") or cfg.get("scrape_interval", 30)
    adapter = AtlassianAdapter()
    detector = ChangeDetector()

    async with aiohttp.ClientSession() as session:
        for _ in range(2):
            await run_once(session, target, adapter, detector)
            await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
