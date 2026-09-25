# CacaoSense — Parcial 1 IoT + Cloud + Sistemas Distribuidos (UNAB 2026-II)

**Escenario 5.3 · Granja y cultivo de cacao.** Flota heterogénea de **10 dispositivos con 10 orígenes de envío distintos**
hacia Azure IoT Central, con Digital Twin (DTDL), reglas, dashboard tipo cuarto de control y análisis de 4 días reales.

Autores: Daniel Villamizar · Tomás Urieles
App: `https://cacaosense-unab2026.azureiotcentral.com` · VM: `vm-parcial1-cacao` (Ubuntu 22.04, mexicocentral)

## Catálogo (un solo inventario, 10 orígenes)

| # | ID en Central | Zona | Origen de envío | Protocolo | Intervalo |
|---|---|---|---|---|---|
| 01 | cacao-01-lote1-twin | Lote 1 | Digital Twin / simulador nativo | interno IoT Central | ~75 s |
| 02 | cacao-02-lote2-wokwi | Lote 2 | Wokwi ESP32 #1 (PubSubClient) | MQTT/TLS 8883 | 15 s |
| 03 | cacao-03-lote3-sdk | Lote 3 | Python `azure-iot-device` | MQTT/TLS (SDK) | 15 s (writable) |
| 04 | cacao-04-aire-cams | Aire rural | API pública Open-Meteo Air Quality (CAMS) | HTTPS → MQTT | 300 s |
| 05 | cacao-05-meteo-feed | Meteorología | Feed Open-Meteo (equivalente Atlas Weather) | HTTPS → MQTT | 300 s |
| 06 | cacao-06-ferm-paho | Fermentación | MQTT explícito `paho-mqtt` | MQTT/TLS QoS 1 | 60 s |
| 07 | cacao-07-campo-era5 | Estación de campo | Replay CSV histórico (ERA5) | MQTT/TLS (SDK) | 30 s |
| 08 | cacao-08-dosel-rest | Dosel | Puente HTTP/REST | HTTPS 443 | 60 s |
| 09 | cacao-09-riego-wokwi | Reservorio | Wokwi ESP32 #2 (firmware riego) | MQTT/TLS 8883 | 30 s |
| 10 | cacao-10-bodega-mqttjs | Bodega | Node.js `mqtt` (MQTT.js) + puesto de mando | MQTT/TLS 8883 | 20 s |

## Estructura

```
models/        DTDL v2 de las 4 plantillas (generadas por tools/build_models.py)
senders/       emisores: sdk_device.py, mqtt_explicit.py, https_bridge.py, node/bodega.js, fleet_monitor.py
               farm.py (modelos de señal), feeds.py (Open-Meteo), common.py (SAS, DPS HTTPS), catalog.json
               fixtures/estacion_campo_historico.csv (replay ERA5)   .env.example (plantilla SIN claves)
wokwi/         lote2_suelo/ y riego/: sketch.ino + diagram.json + libraries.txt (clave = PEGAR_PRIMARY_KEY)
deploy/        install_services.sh (systemd) y cacao-cron (desconexiones controladas diarias)
tools/         iotc_admin.py (REST: plantillas, dispositivos, credenciales, query), build_dashboard.py,
               analyze.py (4 días: estadísticas + gráficos), build_report.py (Word/PDF), make_diagram.py, snap.ps1
analisis/      datos_4dias.csv, estadisticas_4dias.csv, gráficos y diagrama de arquitectura
evidencias/    capturas de IoT Central / Wokwi y logs de la VM
Informe_Parcial1_CacaoSense.docx / .pdf    documento profesional (expediente del cliente)
```

## Decisiones técnicas

- **4 plantillas por dominio** (Suelo, Clima y Aire, Poscosecha y Dosel, Riego y Perímetro) en lugar de una gigante: views limpias
  y reglas por dominio. El simulador nativo respeta `minValue/maxValue` declarados en el DTDL.
- **Aprovisionamiento por DPS con clave simétrica de dispositivo**; nunca se usa la clave de grupo.
- **Estado de flota por heartbeat**: la API pública de IoT Central no expone Connected/Disconnected. `fleet_monitor.py` consulta la
  Query API (Connected si hay mensaje en `max(3×intervalo, 5 min)`) y el nodo 10 lo publica (`fleetConnected/Disconnected/Unassociated`).
- **Desconexiones documentadas**: `deploy/cacao-cron` detiene nodos a horas fijas (06: 02:00–02:30, 10: 03:00–03:10, 08: 12:00–12:20,
  03: 16:00–16:15, hora Colombia). También renueva el SAS de 24 h de los clientes MQTT explícitos.
- **Fuentes públicas sin inventar datos**: si la API no responde, se registra el hueco y no se envía un valor de relleno.

## Cómo generar el SAS (sin secretos en claro)

`sr = urlencode("{hub}/devices/{id}")`, `firma = base64(HMAC-SHA256(base64decode(clave), sr + "\n" + expiry))`,
`SAS = "SharedAccessSignature sr=…&sig=urlencode(firma)&se=expiry"`. Para DPS el recurso es `{idScope}/registrations/{id}`
con `&skn=registration`. Implementado en `senders/common.py` (Python), `node/bodega.js` (crypto) y los sketches (mbedTLS).

## Ejecutar

```bash
cd senders && cp .env.example .env         # completar ID Scope y claves de dispositivo
python -m pip install -r requirements.txt   # azure-iot-device, paho-mqtt<2
python sdk_device.py cacao-03-lote3-sdk  # nodo 03 (uno de los dos códigos de la sustentación)
python mqtt_explicit.py                     # nodo 06
python https_bridge.py                      # nodo 08
cd node && npm ci && node bodega.js         # nodo 10
```
En la VM: `bash deploy/install_services.sh` y `sudo install -m644 deploy/cacao-cron /etc/cron.d/`.
Wokwi: pegar `sketch.ino`, `diagram.json` y librerías en wokwi.com, reemplazar `PEGAR_PRIMARY_KEY` y pulsar Play.
Alternativa sin la cola de compilación de wokwi.com (usada desde el 25/09): `python tools/make_vscode_wokwi.py` genera
`wokwi/vscode/{lote2,riego}` (PlatformIO + `wokwi.toml`; la clave va en `src/secrets.h`, ignorado por git), `pio run` y
en VS Code `F1 → Wokwi: Start Simulator` (una ventana por nodo).

Informe: `python tools/build_report.py --refresh` (consulta IoT Central, rehace estadísticas/gráficos y genera DOCX + PDF).

## Seguridad

`.env`, `PRIVADO_*`, `logs/` y `node_modules/` están en `.gitignore`. Si una clave se expone, regenerarla en
IoT Central → dispositivo → Conectar.

## Nota de transparencia

El 24/09/2026 se probó la carga diferida (store-and-forward con `iothub-creation-time-utc`, `senders/backfill.py`) con fechas
18, 20 y 22/09. Para que la app conserve solo datos recibidos en vivo, los 7 dispositivos de esa prueba se eliminaron y la flota
se re-aprovisionó con IDs nuevos (`tools/rename_ids.py`). El análisis y el informe usan **solo los 4 días recibidos en vivo**
(24, 25, 26 y 27/09/2026). Los datos de los nodos 01 (Digital Twin) y los modelos de señal de `farm.py` son simulados, como permite
el enunciado; los de los nodos 04, 05 y 07 provienen de fuentes públicas reales (Open-Meteo/CAMS/ERA5).
