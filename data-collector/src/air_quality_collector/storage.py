"""Persistence: the raw JSON response and the reduced XML document.

Both files are replaced atomically (write to a temp file, then rename), so a
reader in another container never sees a half-written file.
"""

from __future__ import annotations

import json
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from air_quality_collector import PARAMETERS


class PayloadError(ValueError):
    """The API response does not have the expected shape."""


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(data)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.chmod(tmp_name, 0o644)  # mkstemp defaults to 0600; other services must read it
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def save_raw_json(raw: bytes, path: Path) -> None:
    """Overwrite `path` with the untouched API response, after checking it is JSON."""
    try:
        json.loads(raw)
    except ValueError as exc:
        raise PayloadError(f"response is not valid JSON: {exc}") from exc
    _atomic_write(path, raw)


def build_xml(payload: dict[str, Any]) -> bytes:
    """Reduce an Open-Meteo payload to the three tracked parameters.

    <air_quality time="2026-11-04T20:00">
      <european_aqi>34</european_aqi>
      <pm2_5 unit="μg/m³">8.4</pm2_5>
      <pm10 unit="μg/m³">18.2</pm10>
    </air_quality>
    """
    current = payload.get("current")
    if not isinstance(current, dict):
        reason = payload.get("reason")
        raise PayloadError(f"no 'current' object in response{f' ({reason})' if reason else ''}")

    units = payload.get("current_units") or {}
    root = ET.Element("air_quality")
    if current.get("time"):
        root.set("time", str(current["time"]))

    for name in PARAMETERS:
        value = current.get(name)
        if value is None:
            raise PayloadError(f"'{name}' is missing or null in 'current'")
        element = ET.SubElement(root, name)
        element.text = str(value)
        if units.get(name):
            element.set("unit", str(units[name]))

    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def convert_json_to_xml(json_path: Path, xml_path: Path) -> dict[str, Any]:
    """Read the saved JSON file and overwrite the XML file. Returns the values written."""
    payload = json.loads(json_path.read_bytes())
    if not isinstance(payload, dict):
        raise PayloadError("response is not a JSON object")
    _atomic_write(xml_path, build_xml(payload))
    current = payload["current"]
    return {"time": current.get("time"), **{name: current[name] for name in PARAMETERS}}
