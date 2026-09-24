#!/usr/bin/env python3
"""Puente HTTP/REST - nodo 08 Dosel/sombra. Sin SDK y sin MQTT.

  1) DPS por HTTPS: PUT https://global.azure-devices-provisioning.net/{scope}/registrations/{id}/register
  2) Telemetria: POST https://{hub}/devices/{id}/messages/events?api-version=2021-04-12  -> HTTP 204
Toma el clima exterior del feed Open-Meteo y aplica el efecto de sombra del dosel (farm.canopy).
  python https_bridge.py [--count N] [--interval S]
"""
from __future__ import annotations

import argparse
import json
import signal
import threading
import time
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import Request, urlopen

import farm
import feeds
from common import DEVICES, DeviceConfig, load_env, provision_https, sas_token

DEV = "cacao-08-dosel-rest"
VERSION = "https_bridge.py v1.0.0"


def log(msg):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [{DEV}] {msg}", flush=True)


def post_event(hub, cfg, data, created=None):
    url = f"https://{hub}/devices/{quote(DEV)}/messages/events?api-version=2021-04-12"
    headers = {"Authorization": sas_token(f"{hub}/devices/{DEV}", cfg.device_key),
               "Content-Type": "application/json", "iothub-contenttype": "application/json",
               "iothub-contentencoding": "utf-8"}
    if created:
        headers["iothub-app-iothub-creation-time-utc"] = created
    body = json.dumps(data, separators=(",", ":")).encode()
    with urlopen(Request(url, data=body, headers=headers, method="POST"), timeout=30) as r:
        return r.status, len(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=0)
    ap.add_argument("--interval", type=int, default=0)
    args = ap.parse_args()
    load_env()
    cfg = DeviceConfig.from_env(DEV)
    interval = args.interval or DEVICES[DEV]["intervalSec"]
    log(f"{VERSION} | origen: {DEVICES[DEV]['source']} | intervalo {interval}s")
    log("[DPS] PUT .../registrations/{id}/register (HTTPS 443)")
    hub, _ = provision_https(cfg)
    log(f"[DPS] assigned -> {hub}")
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *a: stop.set())
    weather, n = None, 0
    while not stop.is_set():
        try:
            if n % 5 == 0:
                weather = feeds.current("weather")
        except Exception:
            log("[FUENTE] feed meteo no disponible; se usa modelo local de sombra")
        data = farm.canopy(datetime.now(timezone.utc), weather)
        t0 = time.time()
        try:
            status, size = post_event(hub, cfg, data)
            n += 1
            log(f"[POST #{n}] HTTP {status} en {1000 * (time.time() - t0):.0f} ms bytes={size} {json.dumps(data)}")
        except Exception as exc:
            log(f"[POST] fallo ({type(exc).__name__}); se reintenta en el proximo ciclo")
        if args.count and n >= args.count:
            break
        stop.wait(interval)


if __name__ == "__main__":
    main()
