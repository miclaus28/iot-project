"""Air quality collector: Open-Meteo -> raw JSON file -> reduced XML file."""

PARAMETERS: tuple[str, ...] = ("european_aqi", "pm2_5", "pm10")

__all__ = ["PARAMETERS"]
