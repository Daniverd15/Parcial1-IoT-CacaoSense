#!/usr/bin/env python3
"""Puesto de mando: estado agregado de la flota para el cuarto de control.

IoT Central no expone el estado Connected/Disconnected por su API REST publica, asi que se usa un
criterio de heartbeat documentado sobre la Query API:
  Connected     -> el nodo tiene mensaje en los ultimos max(3 x intervalo, 5 min)
  Disconnected  -> nodo aprovisionado y con plantilla, pero sin mensajes recientes
  Unassociated  -> dispositivo sin plantilla asociada o nunca aprovisionado
Escribe ../fleet.json; el nodo 10 (bodega.js) lo publica como fleetConnected / fleetDisconnected / fleetUnassociated.
Autenticacion: IOTC_API_TOKEN (token de API de IoT Central con rol Operador) en .env.
"""
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from common import CATALOG, ROOT, load_env

APP = "https://cacaosense-unab2026.azureiotcentral.com/api"
OUT = ROOT.parent / "fleet.json"


def api(method, path, body=None, version="2022-07-31"):
    req = Request(f"{APP}{path}?api-version={version}", method=method,
                  data=None if body is None else json.dumps(body).encode(),
                  headers={"Authorization": os.environ["IOTC_API_TOKEN"], "Content-Type": "application/json"})
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"{}")


def snapshot():
    now = datetime.now(timezone.utc)
    devices = {d["id"]: d for d in api("GET", "/devices").get("value", [])}
    state = {}
    for d in CATALOG["devices"]:
        dev = devices.get(d["id"], {})
        if not dev.get("template") or not dev.get("provisioned"):
            state[d["id"]] = "Unassociated"
            continue
        window = max(3 * d["intervalSec"], 300)
        since = (now - timedelta(seconds=window)).strftime("%Y-%m-%dT%H:%M:%SZ")
        q = f"SELECT TOP 1 $id, $ts FROM {d['template']} WHERE $id = '{d['id']}' AND $ts >= '{since}'"
        rows = api("POST", "/query", {"query": q}, "2022-10-31-preview").get("results", [])
        state[d["id"]] = "Connected" if rows else "Disconnected"
    counts = {k: sum(v == k for v in state.values()) for k in ("Connected", "Disconnected", "Unassociated")}
    return {"at": now.isoformat(), "counts": counts, "devices": state}


def main():
    load_env()
    while True:
        try:
            snap = snapshot()
            OUT.write_text(json.dumps(snap), encoding="utf-8")
            print(time.strftime("%Y-%m-%d %H:%M:%S"), "[FLOTA]", snap["counts"], flush=True)
        except Exception as exc:
            print(time.strftime("%Y-%m-%d %H:%M:%S"), "[FLOTA] error", type(exc).__name__, flush=True)
        time.sleep(60)


if __name__ == "__main__":
    main()
