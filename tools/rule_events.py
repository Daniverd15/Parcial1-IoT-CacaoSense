"""Reconstruye los disparos de las Rules de IoT Central en la ventana de 4 dias.

IoT Central no expone por API el historial de disparos; se reevalua cada regla sobre la telemetria
descargada (analisis/datos_4dias.csv) con la misma condicion y ventana de agregacion configuradas.
Un "evento" es una racha continua de ventanas que cumplen la condicion (la regla dispara al entrar y
se rearma al salir). R7 se evalua con la misma regla del puesto de mando: un nodo sin mensajes por
mas de max(3 x intervalo, 5 min) cuenta como Disconnected.
  python tools/rule_events.py      -> analisis/alertas_4dias.csv
"""
import json
from datetime import timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AN = ROOT / "analisis"
COL = timezone(timedelta(hours=-5))
CAT = json.loads((ROOT / "senders" / "catalog.json").read_text(encoding="utf-8-sig"))["devices"]

# (regla, variable, operador, umbral, agregacion, ventana)
RULES = [
    ("R1 Suelo seco", "soilMoisture", "<", 20, "mean", "15min"),
    ("R2 Fermentacion alta", "boxTemperature", ">", 52, "mean", "5min"),
    ("R3 Reservorio bajo", "waterLevel", "<", 20, "mean", "5min"),
    ("R4 Calidad de aire", "aqi", ">", 100, "max", "5min"),
]


def episodes(flags, win):
    """Agrupa ventanas consecutivas que cumplen la condicion en (inicio, fin); un hueco rompe la racha."""
    t = flags[flags].index.to_series()
    if t.empty:
        return []
    run = (t.diff() != pd.Timedelta(win)).cumsum()
    return [(g.iloc[0], g.iloc[-1]) for _, g in t.groupby(run)]


def events(df):
    rows = []
    for name, var, op, thr, agg, win in RULES:
        if var not in df:
            continue
        for dev, sub in df[df[var].notna()].groupby("device"):
            s = pd.to_numeric(sub.set_index("ts")[var], errors="coerce").dropna().sort_index()
            a = getattr(s.resample(win), agg)().dropna()
            flags = a < thr if op == "<" else a > thr
            for t0, t1 in episodes(flags, win):
                seg = a[t0:t1]
                peak = seg.min() if op == "<" else seg.max()
                rows.append([name, dev, t0, t1 + pd.Timedelta(win), f"{var} {op} {thr}", round(float(peak), 1)])
    for d in CAT:
        lim = timedelta(seconds=max(3 * d["intervalSec"], 300))
        for day, sub in df[df.device == d["id"]].groupby("day"):
            s = sub.ts.sort_values()
            for a, b in zip(s[:-1], s[1:]):
                if b - a > lim:
                    rows.append(["R7 Nodo sin reporte", d["id"], a + lim, b, "fleetDisconnected > 0",
                                 round((b - a).total_seconds() / 60)])
    ev = pd.DataFrame(rows, columns=["regla", "nodo", "inicio", "fin", "condicion", "pico"])
    ev = ev.sort_values(["regla", "inicio"]).reset_index(drop=True)
    ev["dia"] = ev.inicio.dt.tz_convert(COL).dt.strftime("%Y-%m-%d")
    return ev


def main():
    df = pd.read_csv(AN / "datos_4dias.csv", low_memory=False)
    df["ts"] = pd.to_datetime(df.ts, utc=True, format="ISO8601")
    ev = events(df)
    ev.to_csv(AN / "alertas_4dias.csv", index=False)
    print(ev.groupby(["regla", "dia"]).size().unstack(fill_value=0))
    return ev


if __name__ == "__main__":
    main()
