"""Crea grupos de dispositivos y el dashboard de organizacion 'Cuarto de control CacaoSense' por REST.

  python tools/build_dashboard.py
"""
import json
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
from iotc_admin import call  # noqa: E402

T = "dtmi:unab:cacaosense:tpl_"
GROUPS = {
    "grp-suelo": ("Suelo - lotes 1 a 3", f"SELECT * FROM devices WHERE $template = \"{T}suelo;1\""),
    "grp-clima": ("Clima y aire", f"SELECT * FROM devices WHERE $template = \"{T}clima;1\""),
    "grp-poscosecha": ("Poscosecha y dosel", f"SELECT * FROM devices WHERE $template = \"{T}poscosecha;1\""),
    "grp-riego": ("Riego y perimetro", f"SELECT * FROM devices WHERE $template = \"{T}riego;1\""),
}


def groups():
    ids = {}
    for gid, (name, q) in GROUPS.items():
        st, res = call("PUT", f"/deviceGroups/{gid}", {"displayName": name, "filter": q})
        print("grupo", gid, st, res.get("error", {}).get("message", "ok"))
        ids[gid] = gid
    return ids


def line(title, group, devices, caps, x, y, w=4, h=3, duration="P1D", res="PT30M"):
    return {"displayName": title, "x": x, "y": y, "width": w, "height": h,
            "configuration": {"type": "lineChart", "group": group, "devices": devices,
                              "capabilities": [{"capability": c, "aggregateFunction": "avg"} for c in caps],
                              "format": {"xAxisEnabled": True, "yAxisEnabled": True, "legendEnabled": True},
                              "queryRange": {"type": "time", "duration": duration, "resolution": res}}}


def lkv(title, group, devices, caps, x, y, w=2, h=2):
    return {"displayName": title, "x": x, "y": y, "width": w, "height": h,
            "configuration": {"type": "lkv", "group": group, "devices": devices,
                              "capabilities": [{"capability": c, "aggregateFunction": "avg"} for c in caps],
                              "showTrend": True, "format": {"abbreviateValue": False, "wordWrap": True, "textSize": 14}}}


def kpi(title, group, devices, cap, fn, x, y, duration="P1D", w=2, h=1):
    return {"displayName": title, "x": x, "y": y, "width": w, "height": h,
            "configuration": {"type": "kpi", "group": group, "devices": devices,
                              "capabilities": [{"capability": cap, "aggregateFunction": fn}],
                              "queryRange": {"type": "time", "duration": duration},
                              "format": {"abbreviateValue": False, "wordWrap": False, "textSize": 14}}}


def md(title, text, x, y, w, h, href="/devices"):
    return {"displayName": title, "x": x, "y": y, "width": w, "height": h,
            "configuration": {"type": "markdown", "description": text, "href": href}}


def img(title, key, x, y, w, h, bg="#2B1A10"):
    """Tile de imagen. La subida del archivo solo existe en la UI (Editar -> tile -> Imagen); el id resultante
    se guarda en IMAGES para que este script conserve la imagen al regenerar el panel."""
    return {"displayName": title, "x": x, "y": y, "width": w, "height": h,
            "configuration": {"type": "image", "image": IMAGES.get(key, ""),
                              "format": {"backgroundColor": bg, "fitImage": True, "showTitle": False,
                                         "textColor": "#FFFFFF", "textSize": 0, "textSizeUnit": "px"}}}


# ids de las imagenes subidas en IoT Central (assets/cacaosense_banner.png, assets/predio_nodos.png,
# analisis/arquitectura_cacaosense.png)
IMAGES = {"banner": "02a94315-24ac-4e96-a2e9-16fde30db9b6", "arquitectura": "b985c114-c965-4322-a949-4ac720f6cb4b",
          "predio": "6e276ae2-3ba4-41b9-a4bc-2009e8a50781"}

ZONE_MAP = """| Zona | Nodo | Origen |
|---|---|---|
| 🌱 Lote 1 | 01 | Digital Twin |
| 🌱 Lote 2 | 02 | Wokwi ESP32 #1 |
| 🌱 Lote 3 | 03 | Python SDK |
| 💨 Aire rural | 04 | API Open-Meteo AQ |
| ⛅ Meteo predio | 05 | Feed Atlas equiv. |
| 🔥 Fermentación | 06 | MQTT paho |
| 📡 Estación campo | 07 | Replay CSV ERA5 |
| 🌳 Dosel | 08 | HTTPS REST |
| 💧 Reservorio | 09 | Wokwi ESP32 #2 |
| 🏠 Bodega | 10 | Node MQTT.js |"""

ALERTS = """- 🟤 **R1 Suelo seco**: soilMoisture < 20 % VWC (lotes 1-3)
- 🔥 **R2 Fermentación alta**: boxTemperature > 52 °C
- 💧 **R3 Reservorio bajo**: waterLevel < 20 %
- 💨 **R4 Aire**: aqi > 100 (US AQI)
- 🔌 **R7 Nodo sin reporte**: fleetDisconnected > 0

Ver *Rules* para el historial de disparos."""


def TILES(soil):
    """Cuadricula de 6 columnas (unidad ~ 1/6 del ancho visible en IoT Central)."""
    riego, bodega = ["cacao-09-riego-wokwi"], ["cacao-10-bodega-mqttjs"]
    meteo, aire, ferm = ["cacao-05-meteo-feed"], ["cacao-04-aire-cams"], ["cacao-06-ferm-paho"]
    return [
        img("CacaoSense | Cuarto de control", "banner", 0, 0, 2, 1),
        lkv("📶 Estado de la flota", "grp-riego", bodega, ["fleetConnected", "fleetDisconnected", "fleetUnassociated"], 2, 0, 1, 2),
        lkv("⛅ Clima actual del predio", "grp-clima", meteo, ["temperature", "humidity", "rainfall", "windSpeed"], 3, 0, 1, 2),
        lkv("💨 Aire rural (API CAMS)", "grp-clima", aire, ["pm25", "pm10", "aqi"], 4, 0, 1, 2),
        lkv("💧 Riego y accesos", "grp-riego", riego + bodega, ["waterLevel", "pumpOn", "doorOpen", "motion"], 5, 0, 1, 2),
        kpi("🌱 Suelo MIN hoy (% VWC)", "grp-suelo", soil, "soilMoisture", "min", 0, 1, w=1),
        kpi("🌱 Suelo MAX hoy (% VWC)", "grp-suelo", soil, "soilMoisture", "max", 1, 1, w=1),
        kpi("🌡️ Temp. aire MAX hoy", "grp-clima", meteo, "temperature", "max", 0, 2, w=1),
        kpi("🌡️ Temp. aire MIN hoy", "grp-clima", meteo, "temperature", "min", 1, 2, w=1),
        kpi("🌧️ Lluvia acumulada hoy (mm)", "grp-clima", meteo, "rainfall", "sum", 0, 3, w=1),
        kpi("🔥 Fermentación MAX hoy (°C)", "grp-poscosecha", ferm, "boxTemperature", "max", 1, 3, w=1),
        line("🌱 Humedad de suelo por lote (% VWC)", "grp-suelo", soil, ["soilMoisture"], 2, 2, w=4, h=2, duration="PT12H", res="PT10M"),
        line("⛅ Meteorología: temperatura y humedad", "grp-clima", meteo, ["temperature", "humidity"], 0, 4, w=3, h=2, duration="PT12H", res="PT10M"),
        line("🔥 Fermentación: temperatura de masa (°C)", "grp-poscosecha", ferm, ["boxTemperature"], 3, 4, w=3, h=2, duration="PT12H", res="PT10M"),
        line("💨 Calidad de aire PM2.5 / PM10", "grp-clima", aire, ["pm25", "pm10"], 0, 6, w=3, h=2, duration="PT12H", res="PT10M"),
        line("🌧️ Lluvia y humectación foliar", "grp-clima", meteo + ["cacao-07-campo-era5"], ["rainfall", "leafWetness"], 3, 6, w=3, h=2, duration="PT12H", res="PT10M"),
        line("💧 Reservorio (%) y caudal (L/min)", "grp-riego", riego, ["waterLevel", "flowRate"], 0, 8, w=3, h=2, duration="PT12H", res="PT10M"),
        line("🌳 Dosel: temperatura y HR bajo sombra", "grp-poscosecha", ["cacao-08-dosel-rest"], ["temperature", "humidity"], 3, 8, w=3, h=2, duration="PT12H", res="PT10M"),
        img("🗺️ Predio CacaoSense: 10 nodos distribuidos", "predio", 0, 10, 4, 3),
        md("🗺️ Mapa de zonas del predio", ZONE_MAP, 4, 10, 2, 3),
        md("🚨 Alertas y reglas activas", ALERTS, 0, 13, 2, 3, href="/rules"),
        img("🧭 Arquitectura de la solución", "arquitectura", 2, 13, 4, 3, bg="#FFFFFF"),
    ]


def dashboard():
    soil = ["cacao-01-lote1-twin", "cacao-02-lote2-wokwi", "cacao-03-lote3-sdk"]
    tiles = TILES(soil)
    body = {"displayName": "Cuarto de control CacaoSense", "tiles": tiles, "favorite": True}
    st, res = call("PUT", "/dashboards/dtmi:cacaosense:controlroom", body, api="2022-10-31-preview")
    print("dashboard", st, json.dumps(res.get("error", "ok"))[:800])


if __name__ == "__main__":
    groups()
    dashboard()
