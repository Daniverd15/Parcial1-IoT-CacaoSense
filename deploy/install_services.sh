#!/usr/bin/env bash
# Instala los emisores de CacaoSense como servicios systemd en la VM (vm-parcial1-cacao).
# Cada servicio reinicia solo si cae (Restart=always) y registra en journalctl.
#   bash install_services.sh            # instala y arranca
#   sudo systemctl stop cacao-06        # desconexion controlada (hueco documentado)
set -euo pipefail
BASE=/home/azureuser/cacao/senders
PY=/home/azureuser/cacao/.venv/bin/python
declare -A CMD=(
  [cacao-03]="$PY -u $BASE/sdk_device.py cacao-03-lote3-python"
  [cacao-04]="$PY -u $BASE/sdk_device.py cacao-04-aire-api"
  [cacao-05]="$PY -u $BASE/sdk_device.py cacao-05-meteo-atlas"
  [cacao-06]="$PY -u $BASE/mqtt_explicit.py cacao-06-fermenta-mqtt"
  [cacao-07]="$PY -u $BASE/sdk_device.py cacao-07-campo-replay"
  [cacao-08]="$PY -u $BASE/https_bridge.py"
  [cacao-10]="/usr/local/bin/node $BASE/node/bodega.js"
)
for name in "${!CMD[@]}"; do
  sudo tee /etc/systemd/system/$name.service >/dev/null <<EOF
[Unit]
Description=CacaoSense emisor $name -> Azure IoT Central
After=network-online.target
Wants=network-online.target

[Service]
User=azureuser
WorkingDirectory=$BASE
ExecStart=${CMD[$name]}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
done
sudo systemctl daemon-reload
sudo systemctl enable --now ${START:-cacao-03 cacao-04 cacao-05 cacao-06 cacao-07 cacao-08 cacao-10}
systemctl --no-pager --type=service | grep cacao
