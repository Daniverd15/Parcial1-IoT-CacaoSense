"""Modelos de senal del predio de cacao (CacaoSense).

Cada funcion recibe un instante UTC y devuelve las variables de un nodo. Los modelos son
deterministas (misma hora -> mismo valor base) + ruido pequeno, de modo que el envio en vivo
y la carga historica (store-and-forward) usan exactamente la misma logica.
Las variables meteorologicas y de aire NO se inventan: vienen de Open-Meteo (ver feeds.py).
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

COL = timezone(timedelta(hours=-5))          # hora local Colombia
BATCH_START = datetime(2026, 9, 17, 8, 0, tzinfo=COL)   # inicio lote de fermentacion
BATCH_DAYS = 7                                # ciclo fermentacion (6 d) + secado de muestra


def _local_hour(t: datetime) -> float:
    lt = t.astimezone(COL)
    return lt.hour + lt.minute / 60 + lt.second / 3600


def daylight(t: datetime) -> float:
    """0 de noche, 1 a mediodia solar (06:00-18:00 local)."""
    h = _local_hour(t)
    return max(0.0, math.sin(math.pi * (h - 6) / 12)) if 6 <= h <= 18 else 0.0


def _noise(scale: float) -> float:
    return random.gauss(0, scale)


def soil(t: datetime, lote: int, irrigation: bool = False) -> dict:
    """Humedad volumetrica (% VWC), temperatura de suelo y CE aparente de un lote.
    Cada lote tiene retencion distinta; el suelo se seca en el dia y recupera de noche."""
    day_idx = (t.astimezone(COL).date() - BATCH_START.date()).days
    base = {1: 34.0, 2: 29.0, 3: 24.0}[lote] - 1.2 * (day_idx % 5)   # secado entre lluvias
    h = _local_hour(t)
    dry = 5.0 * (1 - math.cos(math.pi * max(0, min(h - 7, 11)) / 11)) / 2   # 0..5 % en la tarde
    sm = base - dry + (6.0 if irrigation else 0.0) + _noise(0.3)
    st = 23.0 + 3.2 * math.sin(math.pi * (h - 9) / 12) * (1 if 9 <= h <= 21 else 0) + _noise(0.1)
    ec = 0.45 + 0.012 * sm + _noise(0.01)
    lux = 42000 * daylight(t) * (0.55 + 0.1 * lote) * random.uniform(0.85, 1.0)   # bajo sombrio
    return {"soilMoisture": round(sm, 1), "soilTemperature": round(st, 2), "soilEC": round(ec, 3),
            "illuminance": round(lux), "temperature": round(st + 2.5 + _noise(0.2), 1)}


def fermentation(t: datetime) -> dict:
    """Caja de fermentacion: 28 C -> ~45 C a las 48 h -> ~50 C a las 96 h y descenso (ICCO/AGROSAVIA)."""
    hours = ((t - BATCH_START).total_seconds() / 3600) % (BATCH_DAYS * 24)
    if hours <= 48:
        temp = 28 + 17 * hours / 48
    elif hours <= 96:
        temp = 45 + 5 * (hours - 48) / 48
    elif hours <= 144:
        temp = 50 - 12 * (hours - 96) / 48
    else:
        temp = 38 - 8 * (hours - 144) / 24
    turn = 1.5 * math.sin(2 * math.pi * hours / 24)          # volteo diario
    mass = 50.0 - 0.09 * hours                              # perdida de exudado y agua
    return {"boxTemperature": round(temp + turn + _noise(0.2), 2),
            "humidity": round(78 - 0.08 * hours + _noise(0.8), 1), "mass": round(mass + _noise(0.05), 2)}


def canopy(t: datetime, weather: dict | None) -> dict:
    """Dosel/sombra: toma el clima exterior (si esta disponible) y aplica efecto de sombra."""
    d = daylight(t)
    t_out = weather.get("temperature") if weather else 24 + 6 * d
    rh_out = weather.get("humidity") if weather else 85 - 20 * d
    return {"temperature": round(t_out - 1.8 * d + _noise(0.15), 1),
            "humidity": round(min(99.0, rh_out + 7 + _noise(0.8)), 1),
            "illuminance": round(18000 * d * random.uniform(0.8, 1.0))}


def warehouse(t: datetime, seq: int) -> dict:
    """Bodega/perimetro: puerta y movimiento en horario de trabajo (07-17 h)."""
    h = _local_hour(t)
    work = 7 <= h <= 17
    door = work and (seq % 9 in (0, 1))
    motion = door or (work and random.random() < 0.25) or (not work and random.random() < 0.02)
    return {"doorOpen": door, "motion": motion, "temperature": round(25 + 4 * daylight(t) + _noise(0.2), 1)}


def leaf_wetness(rain_mm: float, humidity: float) -> float:
    """% del intervalo con hoja mojada (analogo a PHYTOS 31 umbralizado)."""
    if rain_mm > 0.1:
        return 100.0
    return round(max(0.0, min(100.0, (humidity - 85) * 6.5)), 1)
