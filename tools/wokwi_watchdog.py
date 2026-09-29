"""Vigilante de los simuladores Wokwi (nodos 02 y 09) en Wokwi for VS Code.

Lee fleet.json (lo escribe fleet_monitor.py cada minuto) y, si un nodo Wokwi aparece Disconnected, reinicia su
simulador en la ventana de VS Code (tools/vscode_cmd.ps1 -> "Wokwi: Restart Simulator"). Espera 8 min entre
reinicios del mismo nodo para dar tiempo a WiFi -> NTP -> DPS -> MQTT.
  python tools/wokwi_watchdog.py        # logs en senders/logs/local_wokwi_watchdog.log
"""
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLEET = ROOT / "fleet.json"
LOG = ROOT / "senders" / "logs" / "local_wokwi_watchdog.log"
WINDOWS = {"cacao-02-lote2-wokwi": "lote2 - Visual Studio Code", "cacao-09-riego-wokwi": "riego - Visual Studio Code"}
COOLDOWN = 8 * 60


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    last = {d: time.time() for d in WINDOWS}  # no reiniciar al arrancar: el simulador puede estar conectando
    log("vigilante Wokwi iniciado")
    while True:
        try:
            snap = json.loads(FLEET.read_text(encoding="utf-8"))
            fresh = (datetime.now(timezone.utc) - datetime.fromisoformat(snap["at"])).total_seconds() < 180
            for dev, title in WINDOWS.items():
                if fresh and snap["devices"].get(dev) == "Disconnected" and time.time() - last[dev] > COOLDOWN:
                    out = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File",
                                          str(ROOT / "tools" / "vscode_cmd.ps1"), title, "Wokwi: Restart Simulator"],
                                         capture_output=True, text=True, timeout=60).stdout.strip()
                    last[dev] = time.time()
                    log(f"{dev} Disconnected -> Restart Simulator ({out})")
        except Exception as exc:
            log(f"error {type(exc).__name__}: {exc}")
        time.sleep(60)


if __name__ == "__main__":
    main()
