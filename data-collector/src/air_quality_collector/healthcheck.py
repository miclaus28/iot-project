"""Container healthcheck: healthy while the XML file keeps being refreshed."""

from __future__ import annotations

import sys
import time

from air_quality_collector.config import ConfigError, Settings


def main() -> int:
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 1

    max_age = max(3 * settings.poll_interval_seconds, 120.0)
    try:
        age = time.time() - settings.xml_path.stat().st_mtime
    except FileNotFoundError:
        print(f"{settings.xml_path} does not exist yet", file=sys.stderr)
        return 1
    if age > max_age:
        print(f"{settings.xml_path} is stale ({age:.0f}s > {max_age:.0f}s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
