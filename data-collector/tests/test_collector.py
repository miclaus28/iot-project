import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import pytest

from air_quality_collector import main as main_module
from air_quality_collector.client import FetchError, build_url
from air_quality_collector.config import ConfigError, Settings
from air_quality_collector.storage import (
    PayloadError,
    build_xml,
    convert_json_to_xml,
    save_raw_json,
)

SAMPLE = {
    "latitude": 46.7712,
    "longitude": 23.6236,
    "current_units": {"european_aqi": "", "pm2_5": "μg/m³", "pm10": "μg/m³"},
    "current": {
        "time": "2026-11-04T20:00",
        "interval": 3600,
        "european_aqi": 34,
        "pm2_5": 8.4,
        "pm10": 18.2,
    },
}
RAW = json.dumps(SAMPLE, ensure_ascii=False).encode()


def test_settings_defaults_and_overrides():
    assert Settings.from_env({}).poll_interval_seconds == 60
    settings = Settings.from_env({"POLL_INTERVAL_SECONDS": "15", "DATA_DIR": "/data"})
    assert settings.poll_interval_seconds == 15
    assert settings.xml_path == Path("/data/air_quality.xml")


@pytest.mark.parametrize(
    "env",
    [{"POLL_INTERVAL_SECONDS": "abc"}, {"POLL_INTERVAL_SECONDS": "0"}, {"LATITUDE": "91"}],
)
def test_settings_reject_bad_values(env):
    with pytest.raises(ConfigError):
        Settings.from_env(env)


def test_build_url_matches_spec():
    assert build_url(Settings()) == (
        "https://air-quality-api.open-meteo.com/v1/air-quality"
        "?latitude=46.7712&longitude=23.6236&current=european_aqi,pm2_5,pm10"
    )


def test_xml_contains_only_the_three_parameters():
    root = ET.fromstring(build_xml(SAMPLE))
    assert root.tag == "air_quality"
    assert root.attrib == {"time": "2026-11-04T20:00"}
    assert [(child.tag, child.text) for child in root] == [
        ("european_aqi", "34"),
        ("pm2_5", "8.4"),
        ("pm10", "18.2"),
    ]
    assert root.find("pm2_5").get("unit") == "μg/m³"


@pytest.mark.parametrize(
    "payload",
    [
        {"error": True, "reason": "bad latitude"},
        {"current": {"european_aqi": 1, "pm2_5": 2}},
        {"current": {"european_aqi": 1, "pm2_5": None, "pm10": 3}},
    ],
)
def test_xml_rejects_incomplete_payload(payload):
    with pytest.raises(PayloadError):
        build_xml(payload)


def test_json_is_saved_verbatim_and_overwritten(tmp_path):
    path = tmp_path / "nested" / "aq.json"
    save_raw_json(b'{"old": 1}', path)
    save_raw_json(RAW, path)
    assert path.read_bytes() == RAW
    assert list(path.parent.iterdir()) == [path]  # no temp files left behind


def test_invalid_json_does_not_overwrite(tmp_path):
    path = tmp_path / "aq.json"
    save_raw_json(RAW, path)
    with pytest.raises(PayloadError):
        save_raw_json(b"<html>502</html>", path)
    assert path.read_bytes() == RAW


def test_convert_reads_json_file(tmp_path):
    json_path, xml_path = tmp_path / "aq.json", tmp_path / "aq.xml"
    save_raw_json(RAW, json_path)
    values = convert_json_to_xml(json_path, xml_path)
    assert values == {"time": "2026-11-04T20:00", "european_aqi": 34, "pm2_5": 8.4, "pm10": 18.2}
    assert ET.parse(xml_path).getroot().find("pm10").text == "18.2"


def test_collect_once_success_and_failure(tmp_path):
    settings = Settings(data_dir=tmp_path)
    with mock.patch.object(main_module, "fetch_raw", return_value=RAW):
        assert main_module.collect_once(settings) is True
    before = settings.xml_path.read_bytes()

    with mock.patch.object(main_module, "fetch_raw", side_effect=FetchError("down")):
        assert main_module.collect_once(settings) is False
    assert settings.xml_path.read_bytes() == before
