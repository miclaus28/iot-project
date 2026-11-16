# air-quality-collector

Polls the [Open-Meteo air quality API](https://open-meteo.com/en/docs/air-quality-api)
on a fixed interval and keeps two files up to date in a Docker volume:

| File               | Content                                                    |
|--------------------|------------------------------------------------------------|
| `air_quality.json` | The whole raw API response, byte for byte                  |
| `air_quality.xml`  | Only `european_aqi`, `pm2_5` and `pm10`, built from the JSON |

Both files are overwritten on every poll (atomically, so readers never see a partial file).

```xml
<?xml version='1.0' encoding='utf-8'?>
<air_quality time="2026-11-16T16:00">
  <european_aqi unit="EAQI">35</european_aqi>
  <pm2_5 unit="μg/m³">12.3</pm2_5>
  <pm10 unit="μg/m³">16.8</pm10>
</air_quality>
```

`time` is the hour the values belong to, as reported by the API (GMT).

## Run with Docker Compose

Run from the repository root, where `docker-compose.yml` and `.env` live:

```sh
cp .env.example .env        # already done if .env exists
docker compose up -d --build
docker compose logs -f air-quality-collector
docker compose exec air-quality-collector cat /data/air_quality.xml
```

The files live in the named volume `air_quality_data`. Another service in the
stack reads them by mounting the same volume:

```yaml
    volumes:
      - air_quality_data:/data:ro
```

## Configuration (`.env`)

| Variable                  | Default                                                  | Meaning                         |
|---------------------------|----------------------------------------------------------|---------------------------------|
| `POLL_INTERVAL_SECONDS`   | `60`                                                     | Seconds between collections     |
| `LATITUDE` / `LONGITUDE`  | `46.7712` / `23.6236`                                    | Location to monitor             |
| `OPEN_METEO_API_URL`      | `https://air-quality-api.open-meteo.com/v1/air-quality`  | API endpoint                    |
| `REQUEST_TIMEOUT_SECONDS` | `10`                                                     | Per-request timeout             |
| `JSON_FILENAME`           | `air_quality.json`                                       | Raw response file name          |
| `XML_FILENAME`            | `air_quality.xml`                                        | Reduced file name               |
| `LOG_LEVEL`               | `INFO`                                                   | `DEBUG`/`INFO`/`WARNING`/`ERROR` |

Changes take effect after `docker compose up -d` (the container is recreated).
`DATA_DIR` is set to `/data` by `docker-compose.yml`; it defaults to `./data` outside Docker.

## Behaviour

- A failed poll (network error, HTTP error, malformed payload) is logged and the
  previous files are left untouched; the next poll runs on schedule.
- The container is reported `healthy` while the XML file is fresher than
  `max(3 × POLL_INTERVAL_SECONDS, 120 s)`.
- `SIGTERM` stops the loop immediately, so `docker compose down` is fast.

## Local development (uv)

`uv.lock` is not committed: the image build resolves dependencies itself, and a
local `uv sync` creates a git-ignored one.

```sh
cd data-collector
uv sync
uv run air-quality-collector
uv run pytest
uv run ruff check
```

## Layout

```
├── docker-compose.yml          service, env_file, volume, healthcheck
├── .env / .env.example         runtime settings
└── data-collector/
    ├── pyproject.toml          project metadata, entry points, dev tools
    ├── Dockerfile              multi-stage build with uv, non-root runtime
    ├── src/air_quality_collector/
    │   ├── config.py           settings from environment variables
    │   ├── client.py           HTTP request to Open-Meteo
    │   ├── storage.py          raw JSON file, JSON -> XML conversion
    │   ├── main.py             polling loop and signal handling
    │   └── healthcheck.py      container healthcheck
    └── tests/
```
