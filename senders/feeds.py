"""Puentes a fuentes publicas: Open-Meteo Air Quality (CAMS) y Open-Meteo Forecast (feed meteo).

Se conserva siempre la marca de tiempo de la fuente (sourceTimestamp) separada de la de ingestion.
Atribucion: datos de Open-Meteo.com (CC BY 4.0) y Copernicus Atmosphere Monitoring Service.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LAT = float(os.getenv("CACAO_LATITUDE", "7.2647"))
LON = float(os.getenv("CACAO_LONGITUDE", "-73.1497"))

WEATHER = {"temperature_2m": "temperature", "relative_humidity_2m": "humidity", "rain": "rainfall",
           "wind_speed_10m": "windSpeed", "shortwave_radiation": "radiation"}
AIR = {"pm2_5": "pm25", "pm10": "pm10", "us_aqi": "aqi"}
URLS = {"weather": "https://api.open-meteo.com/v1/forecast",
        "air": "https://air-quality-api.open-meteo.com/v1/air-quality"}


def _get(url: str) -> dict:
    with urlopen(Request(url, headers={"User-Agent": "CacaoSense-UNAB/1.0"}), timeout=30) as r:
        return json.loads(r.read())


def _iso(value: str) -> str:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def current(kind: str) -> dict:
    """Observacion/modelo 'current' de la fuente. Lanza excepcion si falta un campo (sin inventar)."""
    fields = WEATHER if kind == "weather" else AIR
    extra = ",relative_humidity_2m" if kind == "air" else ""
    q = {"latitude": LAT, "longitude": LON, "current": ",".join(fields) + extra, "timezone": "UTC"}
    if kind == "weather":
        q["wind_speed_unit"] = "kmh"
    data = _get(URLS[kind] + "?" + urlencode(q))
    cur = data["current"]
    out = {dst: float(cur[src]) for src, dst in fields.items()}
    if kind == "air":
        w = current("weather")          # AQ API no trae HR: se toma del feed meteo del mismo punto
        out["humidity"] = w["humidity"]
    out.update(sourceKind="public_api_model", sourceTimestamp=_iso(cur["time"]))
    return out


def hourly(kind: str, start: str, end: str) -> dict[str, dict]:
    """Serie horaria real de la fuente para fechas pasadas -> {ISO hora UTC: valores}."""
    fields = WEATHER if kind == "weather" else AIR
    q = {"latitude": LAT, "longitude": LON, "hourly": ",".join(fields), "start_date": start,
         "end_date": end, "timezone": "UTC"}
    if kind == "weather":
        q["wind_speed_unit"] = "kmh"
    data = _get(URLS[kind] + "?" + urlencode(q))["hourly"]
    series = {}
    for i, t in enumerate(data["time"]):
        row = {dst: data[src][i] for src, dst in fields.items()}
        if all(v is not None for v in row.values()):
            series[_iso(t)] = {k: float(v) for k, v in row.items()}
    return series
