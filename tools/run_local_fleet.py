"""Supervisor local de los emisores de la VM (03-08, 10) cuando la VM no esta disponible.

Replica deploy/install_services.sh (reinicio automatico, RestartSec=10) y deploy/cacao-cron
(desconexiones controladas diarias en hora local Colombia; el reinicio renueva el SAS de 24 h).
Mantiene el equipo despierto mientras corre (SetThreadExecutionState, sin cambiar el plan de energia).
  python tools/run_local_fleet.py                    # logs en senders/logs/local_<nodo>.log
  python tools/run_local_fleet.py --sin cacao-03     # sustentacion: el nodo 03 corre en otro equipo
"""
import argparse
import ctypes
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SENDERS = ROOT / "senders"
LOGS = SENDERS / "logs"
PY = sys.executable
CMD = {
    "cacao-03": [PY, "-u", "sdk_device.py", "cacao-03-lote3-sdk"],
    "cacao-04": [PY, "-u", "sdk_device.py", "cacao-04-aire-cams"],
    "cacao-05": [PY, "-u", "sdk_device.py", "cacao-05-meteo-feed"],
    "cacao-06": [PY, "-u", "mqtt_explicit.py", "cacao-06-ferm-paho"],
    "cacao-07": [PY, "-u", "sdk_device.py", "cacao-07-campo-era5"],
    "cacao-08": [PY, "-u", "https_bridge.py"],
    "cacao-10": ["node", "node/bodega.js"],
    "fleet": [PY, "-u", "fleet_monitor.py"],  # estado de flota que publica el nodo 10
}
# Ventanas de desconexion controlada (hora local), igual que deploy/cacao-cron.
GAPS = {
    "cacao-06": ((2, 0), (2, 30)),
    "cacao-10": ((3, 0), (3, 10)),
    "cacao-08": ((12, 0), (12, 20)),
    "cacao-03": ((16, 0), (16, 15)),
}
# Pantalla encendida tambien: con la sesion bloqueada Chromium frena los simuladores Wokwi de VS Code.
ES_CONTINUOUS, ES_SYSTEM_REQUIRED, ES_DISPLAY_REQUIRED = 0x80000000, 0x00000001, 0x00000002


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    with open(LOGS / "local_supervisor.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def in_gap(name, now):
    if name not in GAPS:
        return False
    (h1, m1), (h2, m2) = GAPS[name]
    return (h1, m1) <= (now.hour, now.minute) < (h2, m2)


def start(name):
    out = open(LOGS / f"local_{name}.log", "a", encoding="utf-8")
    p = subprocess.Popen(CMD[name], cwd=SENDERS, stdout=out, stderr=subprocess.STDOUT,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    log(f"START {name} pid={p.pid}")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin", nargs="*", default=[], choices=sorted(CMD), help="nodos que corren en otro equipo")
    args = ap.parse_args()
    for name in args.sin:
        CMD.pop(name)
    LOGS.mkdir(exist_ok=True)
    # Instancia unica: dos supervisores duplicarian los clientes y el hub los expulsaria entre si (rc=7).
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\CacaoSenseLocalFleet")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        log("ya hay un supervisor corriendo; salgo")
        return
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
    procs, next_try = {}, {}
    log("supervisor local iniciado" + (f" (sin {', '.join(args.sin)})" if args.sin else ""))
    try:
        while True:
            now = datetime.now()
            for name in CMD:
                p = procs.get(name)
                if in_gap(name, now):
                    if p and p.poll() is None:
                        p.terminate()
                        log(f"STOP {name} (desconexion controlada)")
                    procs.pop(name, None)
                    continue
                if p and p.poll() is None:
                    continue
                if p:
                    log(f"{name} termino con codigo {p.returncode}; reinicio en 10 s")
                    procs.pop(name)
                    next_try[name] = time.time() + 10
                if time.time() >= next_try.get(name, 0):
                    procs[name] = start(name)
            time.sleep(5)
    finally:
        for name, p in procs.items():
            if p.poll() is None:
                p.terminate()
        log("supervisor detenido")


if __name__ == "__main__":
    main()
