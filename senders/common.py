"""Configuration, device-scoped SAS and append-only evidence; never print credentials."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
CATALOG = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8-sig"))
DEVICES = {d["id"]: d for d in CATALOG["devices"]}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def load_env(path: Path = ROOT / ".env") -> None:
    """Read a simple dotenv file without executing shell syntax; existing env wins."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", key.strip()):
            raise ValueError("Invalid dotenv entry; expected NAME=value")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


def env_prefix(device_id: str) -> str:
    return device_id.upper().replace("-", "_")


@dataclass(repr=False)
class DeviceConfig:
    device_id: str
    id_scope: str
    device_key: str = field(repr=False)
    model_id: str = ""

    @classmethod
    def from_env(cls, device_id: str) -> "DeviceConfig":
        prefix = env_prefix(device_id)
        scope = os.getenv("IOTC_ID_SCOPE", "").strip()
        key = os.getenv(prefix + "_DEVICE_KEY", "").strip()
        if not scope or not key:
            raise ValueError(f"Configure IOTC_ID_SCOPE and {prefix}_DEVICE_KEY in .env")
        try:
            decoded = base64.b64decode(key, validate=True)
        except Exception:
            raise ValueError(f"{prefix}_DEVICE_KEY must be a base64 device key") from None
        if len(decoded) < 16:
            raise ValueError(f"{prefix}_DEVICE_KEY is too short")
        return cls(device_id, scope, key, os.getenv(prefix + "_MODEL_ID") or DEVICES[device_id].get("modelId", ""))


def sas_token(resource: str, key: str, *, policy: str | None = None,
              expires: int | None = None) -> str:
    expiry = int(time.time()) + 3600 if expires is None else expires
    uri = quote(resource, safe="")
    signature = base64.b64encode(hmac.new(base64.b64decode(key, validate=True),
                                          f"{uri}\n{expiry}".encode(), hashlib.sha256).digest()).decode()
    token = f"SharedAccessSignature sr={uri}&sig={quote(signature, safe='')}&se={expiry}"
    return token + (f"&skn={quote(policy, safe='')}" if policy else "")


def request_json(url: str, *, method: str = "GET", body: dict | None = None,
                 headers: dict | None = None, timeout: int = 30) -> tuple[int, dict, dict]:
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    data = None if body is None else json.dumps(body, allow_nan=False).encode("utf-8")
    try:
        with urlopen(Request(url, data=data, headers=request_headers, method=method), timeout=timeout) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}, dict(response.headers.items())
    except HTTPError as exc:
        # Do not expose request headers, credentials, or raw server response bodies.
        raise RuntimeError(f"HTTPS request failed, status={exc.code}") from None
    except (URLError, TimeoutError):
        raise RuntimeError("HTTPS request failed: network/TLS/timeout") from None


def provision_https(config: DeviceConfig) -> tuple[str, str]:
    base = ("https://global.azure-devices-provisioning.net/" + quote(config.id_scope, safe="")
            + "/registrations/" + quote(config.device_id, safe=""))
    headers = {"Authorization": sas_token(f"{config.id_scope}/registrations/{config.device_id}",
                                          config.device_key, policy="registration")}
    body = {"registrationId": config.device_id}
    if config.model_id:
        body["payload"] = {"modelId": config.model_id}
    status, result, response_headers = request_json(base + "/register?api-version=2019-03-31",
                                                   method="PUT", body=body, headers=headers)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        state = result.get("registrationState", {})
        outcome = state.get("status", result.get("status"))
        if outcome == "assigned":
            hub, device = state.get("assignedHub", ""), state.get("deviceId", "")
            if not re.fullmatch(r"[A-Za-z0-9.-]+\.azure-devices\.net", hub) or device != config.device_id:
                raise RuntimeError("DPS returned an unexpected hub/device identity")
            return hub, device
        if outcome in {"failed", "disabled"} or status not in {200, 202}:
            raise RuntimeError(f"DPS provisioning rejected, status={outcome or status}")
        operation = result.get("operationId")
        if not operation:
            raise RuntimeError("DPS response omitted operationId")
        retry = next((v for k, v in response_headers.items() if k.lower() == "retry-after"), "3")
        time.sleep(min(max(float(retry), 1), 15))
        status, result, response_headers = request_json(
            base + "/operations/" + quote(operation, safe="") + "?api-version=2019-03-31", headers=headers)
    raise RuntimeError("DPS assignment timeout after 120 seconds")


class EvidenceLog:
    def __init__(self, device_id: str, *, dry_run: bool, directory: Path | None = None):
        self.device_id, self.dry_run = device_id, dry_run
        self.directory = directory or ROOT / "logs" / ("dry-run" if dry_run else "live")
        self.directory.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, **fields) -> None:
        # Restrict callers to evidence, never to a transport/config object.
        forbidden = {"password", "key", "device_key", "token", "authorization", "connection_string"}
        if any(k.lower() in forbidden for k in fields):
            raise ValueError("Secret fields cannot be logged")
        row = {"observedAt": utc_now(), "deviceId": self.device_id,
               "mode": "dry-run" if self.dry_run else "live", "event": event, **fields}
        encoded = json.dumps(row, ensure_ascii=False, allow_nan=False)
        if "SharedAccessSignature " in encoded:
            raise ValueError("SAS tokens cannot be logged")
        date = row["observedAt"][:10]
        with (self.directory / f"{date}_{self.device_id}.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(encoded + "\n")
        print(encoded, flush=True)
