"""Entry point: poll the API on a fixed interval until asked to stop."""

from __future__ import annotations

import logging
import signal
import sys
import threading
import time

from air_quality_collector.client import FetchError, build_url, fetch_raw
from air_quality_collector.config import ConfigError, Settings
from air_quality_collector.storage import PayloadError, convert_json_to_xml, save_raw_json

log = logging.getLogger("air_quality_collector")


def collect_once(settings: Settings) -> bool:
    """Run one fetch -> JSON -> XML cycle. Returns True on success.

    A failed cycle leaves the previous files in place.
    """
    try:
        raw = fetch_raw(settings)
        save_raw_json(raw, settings.json_path)
        values = convert_json_to_xml(settings.json_path, settings.xml_path)
    except (FetchError, PayloadError) as exc:
        log.error("collection failed: %s", exc)
        return False
    except OSError as exc:
        log.error("could not write output files: %s", exc)
        return False
    log.info("collected %s", " ".join(f"{k}={v}" for k, v in values.items()))
    return True


def run(settings: Settings, stop: threading.Event) -> None:
    interval = settings.poll_interval_seconds
    next_run = time.monotonic()
    while not stop.is_set():
        collect_once(settings)
        # Fixed-rate schedule: a slow request does not push later polls back.
        next_run += interval
        delay = next_run - time.monotonic()
        if delay < 0:  # overran one or more slots; restart the schedule from now
            next_run = time.monotonic()
            delay = 0
        stop.wait(delay)


def main() -> int:
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    stop = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())

    log.info(
        "starting: every %gs, %s -> %s, %s",
        settings.poll_interval_seconds,
        build_url(settings),
        settings.json_path,
        settings.xml_path,
    )
    run(settings, stop)
    log.info("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
