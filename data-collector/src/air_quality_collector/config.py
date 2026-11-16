"""Runtime configuration, read from environment variables.

Docker Compose injects these from the `.env` file; see `.env.example`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    """An environment variable holds an unusable value."""


def _number(env: Mapping[str, str], name: str, default: float, *, minimum: float | None = None,
            maximum: float | None = None) -> float:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from None
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}, got {value}")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} must be <= {maximum}, got {value}")
    return value


def _text(env: Mapping[str, str], name: str, default: str) -> str:
    return env.get(name, "").strip() or default


@dataclass(frozen=True, slots=True)
class Settings:
    poll_interval_seconds: float = 60.0
    latitude: float = 46.7712
    longitude: float = 23.6236
    api_url: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    request_timeout_seconds: float = 10.0
    data_dir: Path = Path("data")
    json_filename: str = "air_quality.json"
    xml_filename: str = "air_quality.xml"
    log_level: str = "INFO"

    @property
    def json_path(self) -> Path:
        return self.data_dir / self.json_filename

    @property
    def xml_path(self) -> Path:
        return self.data_dir / self.xml_filename

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        d = cls()
        return cls(
            poll_interval_seconds=_number(
                env, "POLL_INTERVAL_SECONDS", d.poll_interval_seconds, minimum=1
            ),
            latitude=_number(env, "LATITUDE", d.latitude, minimum=-90, maximum=90),
            longitude=_number(env, "LONGITUDE", d.longitude, minimum=-180, maximum=180),
            api_url=_text(env, "OPEN_METEO_API_URL", d.api_url),
            request_timeout_seconds=_number(
                env, "REQUEST_TIMEOUT_SECONDS", d.request_timeout_seconds, minimum=0.1
            ),
            data_dir=Path(_text(env, "DATA_DIR", str(d.data_dir))),
            json_filename=_text(env, "JSON_FILENAME", d.json_filename),
            xml_filename=_text(env, "XML_FILENAME", d.xml_filename),
            log_level=_text(env, "LOG_LEVEL", d.log_level).upper(),
        )
