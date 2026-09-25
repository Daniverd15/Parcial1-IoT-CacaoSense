"""Genera los proyectos PlatformIO + Wokwi for VS Code de los nodos 02 y 09 (wokwi/vscode/).

El firmware se compila en local (PlatformIO) y se simula con la extension Wokwi de VS Code,
sin depender de la cola de compilacion de wokwi.com. La clave de dispositivo va SOLO en
src/secrets.h, generado desde senders/.env e ignorado por git.
  python tools/make_vscode_wokwi.py
"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODES = {"lote2": ("lote2_suelo", "cacao-02-lote2-wokwi"), "riego": ("riego", "cacao-09-riego-wokwi")}

PIO = """; CacaoSense - {dev} (ESP32 simulado con Wokwi for VS Code)
[env:esp32dev]
platform = espressif32@7.1.2
board = esp32dev
framework = arduino
monitor_speed = 115200
lib_deps =
  knolleary/PubSubClient@^2.8
  bblanchon/ArduinoJson@^6.21.5
  adafruit/DHT sensor library@^1.4.6
  adafruit/Adafruit Unified Sensor@^1.1.14
"""
TOML = """[wokwi]
version = 1
firmware = '.pio/build/esp32dev/firmware.bin'
elf = '.pio/build/esp32dev/firmware.elf'
"""


def env():
    out = {}
    for line in (ROOT / "senders" / ".env").read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def main():
    e = env()
    for name, (src, dev) in NODES.items():
        d = ROOT / "wokwi" / "vscode" / name
        (d / "src").mkdir(parents=True, exist_ok=True)
        sketch = (ROOT / "wokwi" / src / "sketch.ino").read_text(encoding="utf-8")
        sketch = re.sub(r'#define ID_SCOPE +"[^"]*"\n', '#include "secrets.h"   // ID_SCOPE y DEVICE_KEY (no se sube a git)\n', sketch)
        sketch = re.sub(r'#define DEVICE_KEY +"[^"]*"\n', "", sketch)
        (d / "src" / "main.ino").write_text(sketch, encoding="utf-8", newline="\n")
        key = e[dev.upper().replace("-", "_") + "_DEVICE_KEY"]
        (d / "src" / "secrets.h").write_text(
            f'#pragma once\n#define ID_SCOPE   "{e["IOTC_ID_SCOPE"]}"\n#define DEVICE_KEY "{key}"\n', encoding="utf-8")
        shutil.copy(ROOT / "wokwi" / src / "diagram.json", d / "diagram.json")
        (d / "platformio.ini").write_text(PIO.format(dev=dev), encoding="utf-8")
        (d / "wokwi.toml").write_text(TOML, encoding="utf-8")
        print(name, "->", d.relative_to(ROOT), "(secrets.h escrito, valor no mostrado)")


if __name__ == "__main__":
    main()
