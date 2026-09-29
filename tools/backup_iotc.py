"""Respaldo completo de la app IoT Central (configuracion + toda la telemetria) por si la app deja de estar disponible.

  python tools/backup_iotc.py [--desde 2026-09-24]   -> backups/<fecha-hora>/
    config/*.json           dispositivos, plantillas, paneles, grupos, reglas (sin credenciales)
    telemetria_<id>.csv     todas las variables de la plantilla del dispositivo, desde --desde hasta ahora
    resumen.json            filas por dispositivo y rango de fechas
"""
import argparse
import csv
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iotc_admin import call  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
COL = timezone(timedelta(hours=-5))
PREVIEW = "2022-10-31-preview"


def get(path, api="2022-07-31"):
    st, res = call("GET", path, api=api)
    if st != 200:
        print("GET", path, st, str(res)[:200])
    return res


def telemetry_names(template):
    names = []
    for comp in template.get("capabilityModel", {}).get("contents", []):
        if "Telemetry" in comp.get("@type", []) or comp.get("@type") == "Telemetry":
            names.append(comp["name"])
    return names


def query(q):
    body, rows = {"query": q}, []
    while True:
        for attempt in range(8):  # la Query API limita la tasa (429)
            st, res = call("POST", "/query", body, api=PREVIEW)
            if st != 429:
                break
            time.sleep(3 + 2 * attempt)
        if st != 200:
            print("query error", st, res.get("error", {}).get("message", "")[:160])
            return rows
        rows += res.get("results", [])
        if not res.get("continuationToken"):
            return rows
        body = {"query": q, "continuationToken": res["continuationToken"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="2026-09-24")
    args = ap.parse_args()
    out = ROOT / "backups" / datetime.now().strftime("%Y%m%d-%H%M")
    (out / "config").mkdir(parents=True, exist_ok=True)

    devices = get("/devices").get("value", [])
    templates = get("/deviceTemplates").get("value", [])
    for name, path, api in [("devices", "/devices", "2022-07-31"), ("deviceTemplates", "/deviceTemplates", "2022-07-31"),
                            ("deviceGroups", "/deviceGroups", "2022-07-31"), ("dashboards", "/dashboards", PREVIEW),
                            ("jobs", "/jobs", "2022-07-31"), ("users", "/users", "2022-07-31")]:
        (out / "config" / f"{name}.json").write_text(json.dumps(get(path, api), indent=2, ensure_ascii=False), encoding="utf-8")
    st, rules = call("GET", "/rules", api=PREVIEW)
    (out / "config" / "rules.json").write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")

    tpl_by_id = {t["@id"]: t for t in templates}
    start = datetime.fromisoformat(args.desde).replace(tzinfo=COL).astimezone(timezone.utc)
    end = datetime.now(timezone.utc)
    resumen = {}
    for d in devices:
        tpl = d.get("template")
        if not tpl:
            continue
        names = telemetry_names(tpl_by_id.get(tpl, {}))
        cols = ", ".join(names)
        rows, t0 = [], start
        while t0 < end:  # bloques de 6 h para no superar el limite de filas por consulta
            t1 = t0 + timedelta(hours=6)
            rows += query(f"SELECT $id, $ts, {cols} FROM {tpl} WHERE $id = '{d['id']}' AND "
                          f"$ts >= '{t0:%Y-%m-%dT%H:%M:%SZ}' AND $ts < '{t1:%Y-%m-%dT%H:%M:%SZ}'")
            time.sleep(0.3)
            t0 = t1
        rows.sort(key=lambda r: r["$ts"])
        with open(out / f"telemetria_{d['id']}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["$id", "$ts"] + names, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        resumen[d["id"]] = {"filas": len(rows), "primera": rows[0]["$ts"] if rows else None,
                            "ultima": rows[-1]["$ts"] if rows else None}
        print(f"{d['id']:<24} {len(rows):>6} filas", flush=True)
    (out / "resumen.json").write_text(json.dumps({"hasta": end.isoformat(), "dispositivos": resumen}, indent=2),
                                      encoding="utf-8")
    print("respaldo en", out)


if __name__ == "__main__":
    main()
