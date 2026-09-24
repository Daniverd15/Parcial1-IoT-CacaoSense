#!/usr/bin/env python3
"""Carga historica store-and-forward de la ventana de 4 dias no continuos.

Un nodo rural sin enlace guarda las lecturas con su hora y las sube cuando vuelve el 4G/LTE.
Cada mensaje se publica con la identidad (SAS) del propio dispositivo y el property bag
`iothub-creation-time-utc`, que IoT Central usa como marca de tiempo en graficos y Data Explorer.

  - 04 aire y 05 meteo: series horarias REALES de Open-Meteo (Air Quality CAMS / Forecast) de esas fechas.
  - 07 estacion de campo: lluvia y HR horarias reales del mismo punto -> humectacion foliar derivada.
  - 03 suelo, 06 fermentacion, 08 dosel, 10 bodega: mismos modelos de farm.py que usa el envio en vivo.
Cada dispositivo tiene ventanas y huecos distintos (asincronia + desconexiones documentadas).
  python backfill.py            # dias 2026-09-18, 2026-09-20, 2026-09-22
"""
from __future__ import annotations

import json
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import farm
import feeds
import mqtt_explicit as mx
from common import ROOT, DeviceConfig, load_env

DAYS = ["2026-09-18", "2026-09-20", "2026-09-22"]
COL = farm.COL
# dispositivo: (paso en minutos, {dia: [(hora_ini, hora_fin), ...] en hora local})
PLAN = {
    "cacao-03-lote3-sdk":  (10, {"2026-09-18": [(0, 13), (15.5, 24)], "2026-09-20": [(6, 24)], "2026-09-22": [(0, 24)]}),
    "cacao-04-aire-cams":      (60, {d: [(0, 24)] for d in DAYS}),
    "cacao-05-meteo-feed":   (60, {d: [(0, 24)] for d in DAYS}),
    "cacao-06-ferm-paho": (15, {"2026-09-18": [(0, 24)], "2026-09-20": [(0, 9), (11, 24)], "2026-09-22": [(0, 24)]}),
    "cacao-07-campo-era5":  (60, {"2026-09-18": [(0, 24)], "2026-09-20": [(0, 24)], "2026-09-22": [(0, 5), (8, 24)]}),
    "cacao-08-dosel-rest":   (20, {"2026-09-18": [(5, 19)], "2026-09-20": [(5, 19)], "2026-09-22": [(5, 19)]}),
    "cacao-10-bodega-mqttjs":   (10, {"2026-09-18": [(6, 20)], "2026-09-20": [(7, 13)], "2026-09-22": [(6, 20)]}),
}


def iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    load_env()
    random.seed(20260924)
    start, end = (datetime.fromisoformat(DAYS[0]) - timedelta(days=1)).date().isoformat(), DAYS[-1]
    weather = feeds.hourly("weather", start, end)
    air = feeds.hourly("air", start, end)
    logdir = ROOT / "logs"
    logdir.mkdir(exist_ok=True)
    report = []
    for dev, (step, windows) in PLAN.items():
        cfg = DeviceConfig.from_env(dev)
        client = mx.connect(cfg)
        sent = 0
        for day, spans in windows.items():
            base = datetime.fromisoformat(day).replace(tzinfo=COL)
            for h0, h1 in spans:
                t = base + timedelta(hours=h0)
                while t < base + timedelta(hours=h1):
                    hour_key = iso(t.replace(minute=0, second=0))
                    w, a = weather.get(hour_key), air.get(hour_key)
                    if dev == "cacao-03-lote3-sdk":
                        s = farm.soil(t, 3)
                        data = {k: s[k] for k in ("soilMoisture", "soilTemperature", "soilEC", "illuminance")}
                    elif dev == "cacao-04-aire-cams" and a and w:
                        data = {**a, "humidity": w["humidity"], "sourceKind": "public_api_model", "sourceTimestamp": hour_key}
                    elif dev == "cacao-05-meteo-feed" and w:
                        data = {**w, "sourceKind": "public_api_model", "sourceTimestamp": hour_key}
                    elif dev == "cacao-06-ferm-paho":
                        data = farm.fermentation(t)
                    elif dev == "cacao-07-campo-era5" and w:
                        data = {"rainfall": w["rainfall"], "humidity": w["humidity"],
                                "leafWetness": farm.leaf_wetness(w["rainfall"], w["humidity"]),
                                "sourceKind": "historical_replay", "sourceTimestamp": hour_key}
                    elif dev == "cacao-08-dosel-rest":
                        data = farm.canopy(t, w)
                    elif dev == "cacao-10-bodega-mqttjs":
                        data = farm.warehouse(t, sent)
                    else:
                        data = None
                    if data:
                        info, _, _ = mx.publish(client, dev, data, created=iso(t))
                        info.wait_for_publish(10)
                        sent += 1
                        if sent % 25 == 0:
                            time.sleep(0.5)
                    t += timedelta(minutes=step)
        client.disconnect()
        client.loop_stop()
        line = f"{dev}: {sent} mensajes historicos (paso {step} min) en {', '.join(windows)}"
        print(line, flush=True)
        report.append({"device": dev, "messages": sent, "stepMin": step,
                       "windows": {d: s for d, s in windows.items()}})
    (logdir / "backfill_resumen.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
