"""Descarga el historico horario ERA5 (Open-Meteo Archive) del predio y arma el CSV del replay (nodo 07).

leafWetness se deriva con farm.leaf_wetness (lluvia o HR > 85 %). Ejecutar: python tools/make_replay_csv.py
"""
import csv
import json
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "senders"))
import farm  # noqa: E402
import feeds  # noqa: E402

q = {"latitude": feeds.LAT, "longitude": feeds.LON, "start_date": "2026-08-01", "end_date": "2026-09-15",
     "hourly": "rain,relative_humidity_2m", "timezone": "UTC"}
data = json.loads(urlopen("https://archive-api.open-meteo.com/v1/archive?" + urlencode(q), timeout=60).read())["hourly"]
out = ROOT / "senders" / "fixtures" / "estacion_campo_historico.csv"
rows = 0
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["sourceTimestamp", "rainfall", "humidity", "leafWetness", "source"])
    for t, rain, rh in zip(data["time"], data["rain"], data["relative_humidity_2m"]):
        if rain is None or rh is None:
            continue
        w.writerow([t + ":00Z", rain, rh, farm.leaf_wetness(rain, rh), "Open-Meteo Archive ERA5"])
        rows += 1
print(out, rows, "filas")
