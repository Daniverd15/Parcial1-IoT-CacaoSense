"""Descarga la telemetria de los 4 dias no continuos desde IoT Central (Query API) y genera:
  - analisis/datos_4dias.csv           filas crudas ($id, $ts, variables)
  - analisis/estadisticas_4dias.csv    max / min / promedio / recuento / suma por dia, nodo y variable
  - analisis/*.png                     graficos (serie de 4 dias, asincronia/huecos, comparativa)
  python tools/analyze.py
"""
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iotc_admin import call  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analisis"
OUT.mkdir(exist_ok=True)
DAYS = ["2026-09-24", "2026-09-25", "2026-09-26", "2026-09-27"]   # 4 fechas con datos reales en vivo
COL = timezone(timedelta(hours=-5))
CAT = json.loads((ROOT / "senders" / "catalog.json").read_text(encoding="utf-8-sig"))["devices"]
SUM_VARS = {"rainfall"}                  # variables donde la sumatoria tiene sentido fisico
BROWN, GOLD, GREEN = "#6B3A1E", "#D9A441", "#3E7C3A"
PALETTE = ["#6B3A1E", "#3E7C3A", "#D9A441", "#2F6DB5", "#B5462F", "#7A5BA6", "#2A9D8F", "#8C8C8C", "#E07A1F", "#1B4332"]


DIAS_ES = {"2026-09-24": "Jue 24-sep", "2026-09-25": "Vie 25-sep", "2026-09-26": "Sab 26-sep", "2026-09-27": "Dom 27-sep"}


def dia_es(day):
    return DIAS_ES[day]


def fetch():
    rows = []
    for d in CAT:
        tpl = d["template"]
        cols = ", ".join(d["telemetry"])
        for day in DAYS:
            start = datetime.fromisoformat(day).replace(tzinfo=COL).astimezone(timezone.utc)
            t0 = start
            while t0 < start + timedelta(days=1):          # bloques de 6 h para no superar 10k filas
                t1 = t0 + timedelta(hours=6)
                q = (f"SELECT $id, $ts, {cols} FROM {tpl} WHERE $id = '{d['id']}' AND "
                     f"$ts >= '{t0:%Y-%m-%dT%H:%M:%SZ}' AND $ts < '{t1:%Y-%m-%dT%H:%M:%SZ}'")
                body = {"query": q}
                while True:
                    for attempt in range(6):                  # la Query API limita la tasa (429)
                        st, res = call("POST", "/query", body, api="2022-10-31-preview")
                        if st != 429:
                            break
                        time.sleep(3 + 2 * attempt)
                    if st != 200:
                        print("query error", d["id"], day, res.get("error", {}).get("message", "")[:120])
                    for r in res.get("results", []):
                        rows.append({"device": r["$id"], "ts": r["$ts"], "day": day,
                                     **{k: r.get(k) for k in d["telemetry"]}})
                    if not res.get("continuationToken"):
                        break
                    body = {"query": q, "continuationToken": res["continuationToken"]}
                time.sleep(0.4)
                t0 = t1
        print(d["id"], sum(1 for r in rows if r["device"] == d["id"]), "filas")
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, format="ISO8601")
    # El simulador nativo genero valores aleatorios sin rango hasta publicar minValue/maxValue en la
    # plantilla v1 (24-sep 19:52 UTC); esas muestras de puesta a punto se excluyen del analisis.
    twin_tuning = (df.device == "cacao-01-lote1-twin") & (df.ts < pd.Timestamp("2026-09-24T19:53:00Z"))
    df = df[~twin_tuning]
    df.to_csv(OUT / "datos_4dias.csv", index=False)
    return df


def stats(df):
    out = []
    for d in CAT:
        sub = df[df.device == d["id"]]
        for var in d["telemetry"]:
            if var not in sub:
                continue
            for day in DAYS:
                s = pd.to_numeric(sub[sub.day == day][var].map(lambda v: float(v) if v is not None else None), errors="coerce").dropna()
                if s.empty:
                    out.append({"nodo": d["id"], "variable": var, "dia": day, "recuento": 0})
                    continue
                out.append({"nodo": d["id"], "variable": var, "dia": day, "max": round(s.max(), 2), "min": round(s.min(), 2),
                            "promedio": round(s.mean(), 2), "recuento": int(s.count()),
                            "suma": round(s.sum(), 2) if var in SUM_VARS or sub[var].dtype == bool else ""})
    st = pd.DataFrame(out)
    st.to_csv(OUT / "estadisticas_4dias.csv", index=False)
    return st


def four_day_panels(df, device, var, title, unit, fname, color=BROWN):
    sub = df[(df.device == device)].dropna(subset=[var]).copy()
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.6), sharey=True)
    for ax, day in zip(axes, DAYS):
        s = sub[sub.day == day].sort_values("ts")
        t = s.ts.dt.tz_convert(COL)
        ax.plot(t, s[var].astype(float), color=color, lw=1.4)
        if len(s):
            ax.axhline(s[var].astype(float).mean(), color=GOLD, ls="--", lw=1)
        ax.set_title(dia_es(day), fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=COL))
        ax.tick_params(axis="x", labelsize=8, rotation=30)
        ax.grid(alpha=.25)
    axes[0].set_ylabel(unit)
    fig.suptitle(f"{title} - 4 dias no continuos (IoT Central, hora local)", fontsize=12, color=BROWN, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=130)
    plt.close(fig)


def soil_all(df):
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.6), sharey=True)
    for ax, day in zip(axes, DAYS):
        for i, dev in enumerate(["cacao-01-lote1-twin", "cacao-02-lote2-wokwi", "cacao-03-lote3-sdk"]):
            s = df[(df.device == dev) & (df.day == day)].dropna(subset=["soilMoisture"]).sort_values("ts")
            if len(s):
                ax.plot(s.ts.dt.tz_convert(COL), s.soilMoisture.astype(float), lw=1.3, color=PALETTE[i], label=f"Lote {i + 1}")
        ax.axhline(20, color="#B5462F", ls=":", lw=1.2, label="Umbral R1 (20 %)")
        ax.set_title(dia_es(day), fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=COL))
        ax.tick_params(axis="x", labelsize=8, rotation=30)
        ax.grid(alpha=.25)
    axes[0].set_ylabel("% VWC")
    axes[-1].legend(fontsize=8, loc="upper right")
    fig.suptitle("Humedad de suelo por lote (variable indispensable) - 4 dias no continuos", fontsize=12, color=BROWN, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "g1_humedad_suelo_4dias.png", dpi=130)
    plt.close(fig)


def asynchrony(df):
    """Linea de tiempo de mensajes por nodo: intervalos distintos y huecos (desconexiones)."""
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.6), sharey=True)
    ids = [d["id"] for d in CAT]
    for ax, day in zip(axes, DAYS):
        for i, dev in enumerate(ids):
            s = df[(df.device == dev) & (df.day == day)]
            ax.scatter(s.ts.dt.tz_convert(COL), [i] * len(s), s=3, color=PALETTE[i], marker="|")
        ax.set_title(dia_es(day), fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H", tz=COL))
        ax.set_xlim(datetime.fromisoformat(day).replace(tzinfo=COL), datetime.fromisoformat(day).replace(tzinfo=COL) + timedelta(days=1))
        ax.grid(alpha=.2)
    axes[0].set_yticks(range(len(ids)))
    axes[0].set_yticklabels([f"{d['id'][6:8]} {d['zone'][:16]} ({d['intervalSec']} s)" for d in CAT], fontsize=8)
    fig.suptitle("Asincronia y desconexion: cada marca es un mensaje recibido por IoT Central (huecos = nodo desconectado)",
                 fontsize=11, color=BROWN, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "g6_asincronia_huecos.png", dpi=130)
    plt.close(fig)


def comparison(st):
    sel = st[(st.nodo == "cacao-05-meteo-feed") & (st.variable.isin(["temperature", "humidity"]))].dropna(subset=["max"])
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.6))
    for ax, var, unit in zip(axes, ["temperature", "humidity"], ["°C", "% HR"]):
        s = sel[sel.variable == var]
        x = range(len(s))
        ax.bar([i - .25 for i in x], s["min"], .25, color=GREEN, label="min")
        ax.bar(x, s["promedio"], .25, color=GOLD, label="promedio")
        ax.bar([i + .25 for i in x], s["max"], .25, color=BROWN, label="max")
        ax.set_xticks(list(x))
        ax.set_xticklabels(s["dia"])
        ax.set_ylabel(unit)
        ax.set_title(f"Meteorologia del predio - {var}")
        ax.grid(axis="y", alpha=.25)
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "g7_comparativa_meteo.png", dpi=130)
    plt.close(fig)


def main():
    df = fetch()
    st = stats(df)
    soil_all(df)
    four_day_panels(df, "cacao-05-meteo-feed", "temperature", "Temperatura del aire (feed meteo)", "°C", "g2_temperatura_4dias.png", "#B5462F")
    four_day_panels(df, "cacao-05-meteo-feed", "rainfall", "Lluvia horaria (feed meteo)", "mm", "g3_lluvia_4dias.png", "#2F6DB5")
    four_day_panels(df, "cacao-06-ferm-paho", "boxTemperature", "Temperatura de masa en fermentacion", "°C", "g4_fermentacion_4dias.png")
    four_day_panels(df, "cacao-04-aire-cams", "pm25", "PM2.5 aire rural (API CAMS)", "µg/m³", "g5_pm25_4dias.png", "#7A5BA6")
    asynchrony(df)
    comparison(st)
    print(st.to_string()[:6000])


if __name__ == "__main__":
    main()
