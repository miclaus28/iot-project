"""HTTP client for the Open-Meteo air quality endpoint."""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request

from air_quality_collector import PARAMETERS
from air_quality_collector.config import Settings


class FetchError(RuntimeError):
    """The API could not be reached or answered with an error."""


def build_url(settings: Settings) -> str:
    query = urllib.parse.urlencode(
        {
            "latitude": settings.latitude,
            "longitude": settings.longitude,
            "current": ",".join(PARAMETERS),
        },
        safe=",",
    )
    return f"{settings.api_url}?{query}"


def fetch_raw(settings: Settings) -> bytes:
    """Return the response body exactly as the API sent it."""
    request = urllib.request.Request(
        build_url(settings),
        headers={"Accept": "application/json", "User-Agent": "air-quality-collector/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        # Open-Meteo explains bad requests in the body: {"error": true, "reason": "..."}
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise FetchError(f"HTTP {exc.code} from API: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FetchError(f"request failed: {exc}") from exc
