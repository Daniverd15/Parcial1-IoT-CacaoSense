#!/usr/bin/env python3
"""Emisor con el SDK oficial azure-iot-device (DPS + MQTT/TLS) para los nodos 03, 04, 05 y 07.

  python sdk_device.py cacao-03-lote3-python      # Lote 3: suelo, comando setIrrigation, property writable
  python sdk_device.py cacao-04-aire-api          # puente API publica Open-Meteo Air Quality (CAMS)
  python sdk_device.py cacao-05-meteo-atlas       # feed meteorologico Open-Meteo (equivalente Atlas Weather)
  python sdk_device.py cacao-07-campo-replay      # replay del CSV historico de la estacion de campo

Opciones: --count N (termina tras N mensajes), --interval S (sobrescribe el intervalo del catalogo).
Credenciales: senders/.env (IOTC_ID_SCOPE y <DEVICE>_DEVICE_KEY). Nunca se imprimen.
"""
from __future__ import annotations

import argparse
import csv
import json
import signal
import sys
import threading
import time
from datetime import datetime, timezone

from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse, ProvisioningDeviceClient

import farm
import feeds
from common import DEVICES, ROOT, DeviceConfig, load_env, utc_now

VERSION = "sdk_device.py v1.2.0"


class State:
    def __init__(self, interval: int):
        self.interval = interval
        self.irrigation = False
        self.seq = 0
        self.replay = None
        self.stop = threading.Event()


def log(dev: str, msg: str) -> None:
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [{dev}] {msg}", flush=True)


def load_replay() -> list[dict]:
    with (ROOT / "fixtures" / "estacion_campo_historico.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sample(dev: str, st: State) -> dict:
    now = datetime.now(timezone.utc)
    if dev == "cacao-03-lote3-python":
        d = farm.soil(now, 3, st.irrigation)
        return {k: d[k] for k in ("soilMoisture", "soilTemperature", "soilEC", "illuminance")}
    if dev == "cacao-04-aire-api":
        return feeds.current("air")
    if dev == "cacao-05-meteo-atlas":
        return feeds.current("weather")
    if dev == "cacao-07-campo-replay":
        row = st.replay[st.seq % len(st.replay)]
        return {"rainfall": float(row["rainfall"]), "leafWetness": float(row["leafWetness"]),
                "humidity": float(row["humidity"]), "sourceKind": "historical_replay",
                "sourceTimestamp": row["sourceTimestamp"]}
    raise SystemExit("Dispositivo no soportado por este emisor: " + dev)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("device")
    ap.add_argument("--count", type=int, default=0)
    ap.add_argument("--interval", type=int, default=0)
    args = ap.parse_args()
    dev = args.device
    meta = DEVICES[dev]
    load_env()
    cfg = DeviceConfig.from_env(dev)
    st = State(args.interval or meta["intervalSec"])
    if dev == "cacao-07-campo-replay":
        st.replay = load_replay()

    log(dev, f"{VERSION} | origen: {meta['source']} | intervalo {st.interval}s")
    log(dev, "[DPS] Registrando en global.azure-devices-provisioning.net (MQTT/TLS 8883)...")
    prov = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host="global.azure-devices-provisioning.net", registration_id=dev,
        id_scope=cfg.id_scope, symmetric_key=cfg.device_key)
    reg = prov.register()
    if reg.status != "assigned":
        raise SystemExit(f"DPS no asigno el dispositivo: {reg.status}")
    hub = reg.registration_state.assigned_hub
    log(dev, f"[DPS] assigned -> hub={hub}")

    client = IoTHubDeviceClient.create_from_symmetric_key(symmetric_key=cfg.device_key, hostname=hub, device_id=dev)
    client.on_connection_state_change = lambda: log(dev, f"[HUB] estado de conexion: {'CONNECTED' if client.connected else 'DISCONNECTED'}")

    def on_method(req):
        enabled = bool(req.payload) if not isinstance(req.payload, dict) else bool(req.payload.get("enabled"))
        if req.name == "setIrrigation":
            st.irrigation = enabled
            client.patch_twin_reported_properties({"irrigationEnabled": enabled})
            result = f"Riego lote 3 {'HABILITADO' if enabled else 'DESHABILITADO'}"
        else:
            result = f"Comando {req.name} no soportado"
        log(dev, f"[CMD] {req.name}({req.payload}) -> {result}")
        client.send_method_response(MethodResponse.create_from_method_request(req, 200, result))

    def on_patch(patch):
        if "samplingIntervalSec" in patch:
            value = int(patch["samplingIntervalSec"])
            st.interval = max(5, min(value, 3600))
            client.patch_twin_reported_properties({"samplingIntervalSec": {
                "value": st.interval, "ac": 200, "av": patch.get("$version", 1), "ad": "aplicado"}})
            log(dev, f"[PROP] samplingIntervalSec -> {st.interval}s (writable property sincronizada)")

    client.on_method_request_received = on_method
    client.on_twin_desired_properties_patch_received = on_patch
    client.connect()
    log(dev, f"[HUB] CONNECTED a {hub}:8883 como '{dev}'")
    client.patch_twin_reported_properties({"firmwareVersion": VERSION, "zone": meta["zone"], "originId": meta["source"],
                                           "samplingIntervalSec": {"value": st.interval, "ac": 200, "av": 0, "ad": "inicial"}})

    signal.signal(signal.SIGTERM, lambda *a: st.stop.set())
    try:
        while not st.stop.is_set():
            try:
                data = sample(dev, st)
            except Exception as exc:          # feed caido: se registra el hueco, no se inventa el dato
                log(dev, f"[FUENTE] sin dato ({type(exc).__name__}); se reintenta en el proximo ciclo")
                st.stop.wait(st.interval)
                continue
            msg = Message(json.dumps(data, separators=(",", ":")), content_encoding="utf-8", content_type="application/json")
            client.send_message(msg)
            st.seq += 1
            log(dev, f"[TX #{st.seq}] {msg.data}")
            if args.count and st.seq >= args.count:
                break
            st.stop.wait(st.interval)
    except KeyboardInterrupt:
        pass
    finally:
        log(dev, "[FIN] desconexion controlada")
        client.shutdown()


if __name__ == "__main__":
    sys.exit(main())
