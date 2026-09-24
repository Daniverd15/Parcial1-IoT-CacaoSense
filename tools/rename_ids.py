"""Migra los 7 nodos con datos de prueba a IDs nuevos (IoT Central conserva el historial por ID).
Reemplaza los IDs en el codigo, elimina los dispositivos viejos y crea los nuevos."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
MAP = {
    "cacao-03-lote3-python": "cacao-03-lote3-sdk",
    "cacao-04-aire-api": "cacao-04-aire-cams",
    "cacao-05-meteo-atlas": "cacao-05-meteo-feed",
    "cacao-06-fermenta-mqtt": "cacao-06-ferm-paho",
    "cacao-07-campo-replay": "cacao-07-campo-era5",
    "cacao-08-dosel-https": "cacao-08-dosel-rest",
    "cacao-10-bodega-node": "cacao-10-bodega-mqttjs",
}
FILES = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix in {".py", ".js", ".json", ".sh", ".md", ".txt", ".example"}
         and not any(x in p.parts for x in ("node_modules", ".git", "analisis", "evidencias", "models"))
         and p.name not in {"rename_ids.py", "purge_backfill.py", "package-lock.json", "package.json"}]
if __name__ == "__main__":
    for p in FILES:
        s = p.read_text(encoding="utf-8-sig")
        n = s
        for old, new in MAP.items():
            n = n.replace(old, new).replace(old.upper().replace("-", "_"), new.upper().replace("-", "_"))
        if n != s:
            p.write_text(n, encoding="utf-8")
            print("actualizado", p.relative_to(ROOT))
    from iotc_admin import call, catalog
    for d in catalog()["devices"]:
        if d["id"] in MAP.values():
            old = next(k for k, v in MAP.items() if v == d["id"])
            print(old, "delete", call("DELETE", f"/devices/{old}")[0],
                  "->", d["id"], "create", call("PUT", f"/devices/{d['id']}", {"displayName": d["displayName"], "template": d["template"],
                                                                              "simulated": False, "enabled": True})[0])
