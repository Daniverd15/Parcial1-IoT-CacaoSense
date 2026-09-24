"""Administracion de la app IoT Central por REST (plantillas, dispositivos, credenciales, consultas).

Autentica con el token AAD de Azure CLI (az login); no guarda secretos en el repo.
Uso:
  python tools/iotc_admin.py templates      # publica las 4 plantillas DTDL
  python tools/iotc_admin.py devices        # crea los 10 dispositivos del catalogo
  python tools/iotc_admin.py creds          # escribe senders/.env (ignorado por git)
  python tools/iotc_admin.py status         # estado de la flota
  python tools/iotc_admin.py query "SELECT ..."
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = os.getenv("IOTC_APP", "cacaosense-unab2026")
BASE = f"https://{APP}.azureiotcentral.com/api"
API = "2022-07-31"
AZ = os.getenv("AZ_CLI", str(ROOT.parent / ".tools" / "azurecli" / "Scripts" / "az.bat"))
_token = None


def token():
    global _token
    if not _token:
        out = subprocess.run([AZ, "account", "get-access-token", "--resource", "https://apps.azureiotcentral.com",
                              "--query", "accessToken", "-o", "tsv"], capture_output=True, text=True, shell=False)
        _token = out.stdout.strip()
        if not _token:
            raise SystemExit("No se obtuvo token AAD: " + out.stderr[-300:])
    return _token


def call(method, path, body=None, api=API):
    url = f"{BASE}{path}{'&' if '?' in path else '?'}api-version={api}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def catalog():
    return json.loads((ROOT / "senders" / "catalog.json").read_text(encoding="utf-8"))


def templates():
    for f in sorted((ROOT / "models").glob("cacaosense-*-v1.json")):
        model = json.loads(f.read_text(encoding="utf-8"))
        tid = model["@id"].replace("cacaosense:", "cacaosense:tpl_")
        body = {"@type": ["ModelDefinition", "DeviceModel"], "displayName": model["displayName"]["en"],
                "capabilityModel": model}
        st, res = call("PUT", f"/deviceTemplates/{tid}", body)
        print(f.name, st, res.get("error", {}).get("message", "ok"))


def devices():
    cat = catalog()
    for d in cat["devices"]:
        body = {"displayName": d["displayName"], "template": d["template"], "simulated": d.get("simulated", False),
                "enabled": True}
        st, res = call("PUT", f"/devices/{d['id']}", body)
        print(d["id"], st, res.get("error", {}).get("message", "ok"))


def creds():
    cat = catalog()
    lines = ["# Generado por tools/iotc_admin.py creds. NO SUBIR A GIT."]
    scope = None
    for d in cat["devices"]:
        if d.get("simulated"):
            continue
        st, res = call("GET", f"/devices/{d['id']}/credentials")
        scope = res.get("idScope", scope)
        key = res.get("symmetricKey", {}).get("primaryKey", "")
        lines.append(f"{d['id'].upper().replace('-', '_')}_DEVICE_KEY={key}")
    lines.insert(1, f"IOTC_ID_SCOPE={scope}")
    env = ROOT / "senders" / ".env"
    if env.exists():   # conservar variables que no son claves de dispositivo (token de API, coordenadas)
        lines += [l for l in env.read_text(encoding="utf-8-sig").splitlines()
                  if "=" in l and not l.startswith("#") and not l.startswith("IOTC_ID_SCOPE") and "_DEVICE_KEY=" not in l]
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("senders/.env escrito para", len(lines) - 2, "dispositivos (valores no mostrados)")


def status():
    st, res = call("GET", "/devices")
    for d in res.get("value", []):
        print(f"{d['id']:26} provisioned={d.get('provisioned')} simulated={d.get('simulated')} template={d.get('template')}")


def query(q):
    st, res = call("POST", "/query", {"query": q}, api="2022-10-31-preview")
    print(json.dumps(res, indent=1, ensure_ascii=False)[:20000])
    return res


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "query":
        query(sys.argv[2])
    else:
        globals()[action]()

