#!/usr/bin/env python3
"""Cliente MQTT EXPLICITO (paho-mqtt, sin azure-iot-device) - nodo 06 Secado/Fermentacion.

Todo el protocolo a la vista (continuacion del Lab 3):
  1) SAS generado a mano (HMAC-SHA256 de la clave del dispositivo).
  2) Registro DPS por MQTT: $dps/registrations/PUT/iotdps-register/?$rid=1
  3) CONNECT al IoT Hub asignado (8883, TLS, username {hub}/{id}/?api-version=2021-04-12)
  4) PUBLISH QoS 1 a devices/{id}/messages/events/  (+ property bag opcional)
  5) Metodos directos: $iothub/methods/POST/#  (setAlertLed)

  python mqtt_explicit.py cacao-06-ferm-paho [--count N] [--interval S]
El modulo tambien expone connect() y publish() que usa backfill.py (store-and-forward).
"""
from __future__ import annotations

import argparse
import json
import signal
import ssl
import threading
import time
from datetime import datetime, timezone
from urllib.parse import quote

import paho.mqtt.client as mqtt

import farm
from common import DEVICES, DeviceConfig, load_env, sas_token

VERSION = "mqtt_explicit.py v1.1.0"
DPS_HOST = "global.azure-devices-provisioning.net"


def log(dev, msg):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [{dev}] {msg}", flush=True)


def _client(client_id):
    c = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    ctx = ssl.create_default_context()
    c.tls_set_context(ctx)
    return c


def dps_register(cfg: DeviceConfig) -> str:
    dev = cfg.device_id
    done, out = threading.Event(), {}
    c = _client(dev)
    c.username_pw_set(f"{cfg.id_scope}/registrations/{dev}/api-version=2019-03-31",
                      sas_token(f"{cfg.id_scope}/registrations/{dev}", cfg.device_key, policy="registration"))

    def on_connect(cl, u, f, rc):
        log(dev, f"[DPS] CONNACK rc={rc}; PUBLISH $dps/registrations/PUT/iotdps-register/?$rid=1")
        cl.subscribe("$dps/registrations/res/#", qos=1)
        cl.publish("$dps/registrations/PUT/iotdps-register/?$rid=1", json.dumps({"registrationId": dev}), qos=1)

    def on_message(cl, u, m):
        body = json.loads(m.payload or b"{}")
        if "/res/202" in m.topic:
            time.sleep(2)
            cl.publish(f"$dps/registrations/GET/iotdps-get-operationstatus/?$rid=2&operationId={body['operationId']}", "", qos=1)
        elif "/res/200" in m.topic:
            out["hub"] = body["registrationState"]["assignedHub"]
            done.set()
        else:
            out["err"] = m.topic
            done.set()

    c.on_connect, c.on_message = on_connect, on_message
    c.connect(DPS_HOST, 8883, 60)
    c.loop_start()
    done.wait(40)
    c.loop_stop()
    c.disconnect()
    if "hub" not in out:
        raise RuntimeError(f"DPS no asigno hub ({out.get('err', 'timeout')})")
    log(dev, f"[DPS] 200 assigned -> {out['hub']}")
    return out["hub"]


def connect(cfg: DeviceConfig, on_method=None):
    dev = cfg.device_id
    hub = dps_register(cfg)
    state = {"connected": threading.Event()}
    c = _client(dev)
    c.username_pw_set(f"{hub}/{dev}/?api-version=2021-04-12",
                      sas_token(f"{hub}/devices/{dev}", cfg.device_key, expires=int(time.time()) + 24 * 3600))
    c.reconnect_delay_set(1, 30)

    def on_connect(cl, u, f, rc):
        log(dev, f"[HUB] CONNACK rc={rc} ({'CONNECTED' if rc == 0 else 'RECHAZADO'}) {hub}:8883")
        if rc == 0:
            state["connected"].set()
            cl.subscribe("$iothub/methods/POST/#", qos=0)

    def on_disconnect(cl, u, rc):
        state["connected"].clear()
        log(dev, f"[HUB] DISCONNECTED rc={rc}; paho reintenta con backoff")

    def on_message(cl, u, m):
        name = m.topic.split("/POST/")[1].split("/")[0]
        rid = m.topic.split("$rid=")[1]
        payload = json.loads(m.payload or b"null")
        result = on_method(name, payload) if on_method else "sin manejador"
        log(dev, f"[CMD] {name}({payload}) -> {result}")
        cl.publish(f"$iothub/methods/res/200/?$rid={rid}", json.dumps(result), qos=0)

    c.on_connect, c.on_disconnect, c.on_message = on_connect, on_disconnect, on_message
    c.connect(hub, 8883, keepalive=120)
    c.loop_start()
    state["connected"].wait(20)
    return c


def publish(c, dev: str, data: dict, created: str | None = None, qos: int = 1):
    """PUBLISH al topic de eventos. Con 'created' se agrega iothub-creation-time-utc al property bag
    (IoT Central lo usa como marca de tiempo del mensaje: patron store-and-forward)."""
    topic = f"devices/{dev}/messages/events/"
    if created:
        topic += "iothub-creation-time-utc=" + quote(created, safe="")
    body = json.dumps(data, separators=(",", ":"))
    return c.publish(topic, body, qos=qos), topic, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("device", nargs="?", default="cacao-06-ferm-paho")
    ap.add_argument("--count", type=int, default=0)
    ap.add_argument("--interval", type=int, default=0)
    args = ap.parse_args()
    dev = args.device
    load_env()
    cfg = DeviceConfig.from_env(dev)
    interval = args.interval or DEVICES[dev]["intervalSec"]
    led = {"on": False}

    def on_method(name, payload):
        if name == "setAlertLed":
            led["on"] = bool(payload)
            return f"LED de alerta de fermentacion {'ON' if led['on'] else 'OFF'}"
        return f"comando {name} no soportado"

    log(dev, f"{VERSION} | origen: {DEVICES[dev]['source']} | intervalo {interval}s | QoS 1")
    c = connect(cfg, on_method)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *a: stop.set())
    n = 0
    try:
        while not stop.is_set():
            data = farm.fermentation(datetime.now(timezone.utc))
            t0 = time.time()
            info, topic, body = publish(c, dev, data)
            info.wait_for_publish(10)
            n += 1
            log(dev, f"[TX #{n}] topic={topic} qos=1 bytes={len(body)} PUBACK={1000 * (time.time() - t0):.0f}ms {body}")
            if args.count and n >= args.count:
                break
            stop.wait(interval)
    except KeyboardInterrupt:
        pass
    finally:
        log(dev, "[FIN] DISCONNECT controlado")
        c.loop_stop()
        c.disconnect()


if __name__ == "__main__":
    main()
