"""Genera los modelos DTDL v2 (Digital Twin) de CacaoSense, uno por dominio del predio.

Version de las plantillas: 1.0.0 (dtmi ...;1). Ejecutar: python tools/build_models.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTX = ["dtmi:iotcentral:context;2", "dtmi:dtdl:context;2"]

# name: (displayName, schema, displayUnit, sensor de referencia)
VARS = {
    "soilMoisture":    ("Humedad volumetrica del suelo", "double", "% VWC", "METER TEROS 12"),
    "soilTemperature": ("Temperatura del suelo", "double", "°C", "METER TEROS 12"),
    "soilEC":          ("Conductividad electrica aparente", "double", "dS/m", "METER TEROS 12"),
    "temperature":     ("Temperatura del aire", "double", "°C", "AM2302/DHT22 o Vaisala WXT530"),
    "humidity":        ("Humedad relativa", "double", "% HR", "AM2302/DHT22 o Vaisala WXT530"),
    "illuminance":     ("Iluminancia", "double", "lx", "ROHM BH1750FVI"),
    "rainfall":        ("Lluvia del intervalo", "double", "mm", "Vaisala WXT530"),
    "windSpeed":       ("Velocidad del viento", "double", "km/h", "Vaisala WXT530"),
    "radiation":       ("Radiacion solar global", "double", "W/m²", "Apogee SP-110-SS"),
    "pm25":            ("PM2.5", "double", "µg/m³", "Sensirion SPS30"),
    "pm10":            ("PM10", "double", "µg/m³", "Sensirion SPS30"),
    "aqi":             ("Indice US AQI", "double", "indice", "Calculado (EPA US AQI)"),
    "leafWetness":     ("Humectacion foliar", "double", "% tiempo mojado", "METER PHYTOS 31"),
    "mass":            ("Masa del lote en fermentacion", "double", "kg", "Celda de carga + HX711"),
    "boxTemperature":  ("Temperatura de la masa (caja)", "double", "°C", "Maxim DS18B20"),
    "waterLevel":      ("Nivel del reservorio", "double", "%", "MaxBotix MB7389"),
    "flowRate":        ("Caudal de riego", "double", "L/min", "DFRobot SEN0217"),
    "pumpOn":          ("Bomba encendida", "boolean", "", "Rele / contactor"),
    "doorOpen":        ("Puerta de bodega abierta", "boolean", "", "Littelfuse 59025 (reed)"),
    "motion":          ("Movimiento en perimetro", "boolean", "", "Panasonic EKMB1101112 (PIR)"),
    "fleetConnected":    ("Connected", "integer", "nodos", "Puesto de mando (heartbeat)"),
    "fleetDisconnected": ("Disconnected", "integer", "nodos", "Puesto de mando (heartbeat)"),
    "fleetUnassociated": ("Unassociated", "integer", "nodos", "Puesto de mando (heartbeat)"),
    "sourceKind":      ("Naturaleza del dato", "string", "", "metadato"),
    "sourceTimestamp": ("Marca de tiempo de la fuente", "dateTime", "UTC", "metadato"),
}


# Rango operativo del escenario (lo usa el simulador nativo de IoT Central): (min, max, decimales)
RANGES = {"soilMoisture": (15, 45, 1), "soilTemperature": (20, 30, 2), "soilEC": (0.3, 1.5, 3),
          "illuminance": (0, 45000, 0), "temperature": (17, 34, 1)}


def tel(name):
    title, schema, unit, sensor = VARS[name]
    item = {"@type": "Telemetry", "name": name, "displayName": {"en": title}, "schema": schema,
            "description": {"en": f"Sensor de referencia: {sensor}." + (f" Unidad: {unit}." if unit else "")}}
    if unit and schema in ("double", "integer"):
        item["displayUnit"] = {"en": unit}
    if name in RANGES:
        lo, hi, dec = RANGES[name]
        item.update({"@type": ["Telemetry", "NumberValue"], "minValue": lo, "maxValue": hi, "decimalPlaces": dec})
    return item


def prop(name, title, schema, writable=False):
    return {"@type": "Property", "name": name, "displayName": {"en": title}, "schema": schema, "writable": writable}


def cmd(name, title):
    return {"@type": "Command", "name": name, "displayName": {"en": title},
            "request": {"@type": "CommandPayload", "name": "enabled", "displayName": {"en": "Activar"}, "schema": "boolean"},
            "response": {"@type": "CommandPayload", "name": "result", "displayName": {"en": "Resultado"}, "schema": "string"}}


COMMON_PROPS = [prop("samplingIntervalSec", "Intervalo de envio (s)", "integer", writable=True),
                prop("firmwareVersion", "Version del codigo", "string"),
                prop("zone", "Zona del predio", "string"),
                prop("originId", "Origen de envio", "string")]

MODELS = {
    "suelo": ("CacaoSense Nodo de Suelo",
              ["soilMoisture", "soilTemperature", "soilEC", "illuminance", "temperature"],
              [cmd("setIrrigation", "Habilitar riego del lote"), cmd("setAlertLed", "LED de alerta")],
              [prop("irrigationEnabled", "Riego habilitado", "boolean")]),
    "clima": ("CacaoSense Clima y Aire",
              ["temperature", "humidity", "rainfall", "windSpeed", "radiation", "pm25", "pm10", "aqi",
               "leafWetness", "sourceKind", "sourceTimestamp"], [], []),
    "poscosecha": ("CacaoSense Poscosecha y Dosel",
                   ["boxTemperature", "temperature", "humidity", "mass", "illuminance"],
                   [cmd("setAlertLed", "LED de alerta")], []),
    "riego": ("CacaoSense Riego y Perimetro",
              ["waterLevel", "flowRate", "pumpOn", "doorOpen", "motion", "temperature",
               "fleetConnected", "fleetDisconnected", "fleetUnassociated"],
              [cmd("setPump", "Encender/apagar bomba"), cmd("setAlertLed", "Sirena/LED de perimetro")], []),
}


def build():
    out = {}
    for key, (title, tels, cmds, extra) in MODELS.items():
        out[key] = {"@id": f"dtmi:unab:cacaosense:{key};1", "@type": "Interface", "@context": CTX,
                    "displayName": {"en": title},
                    "description": {"en": "Parcial 1 IoT UNAB 2026-II - Granja y cultivo de cacao. Plantilla v1.0.0"},
                    "contents": [tel(t) for t in tels] + COMMON_PROPS + extra + cmds}
    return out


def main():
    dest = ROOT / "models"
    dest.mkdir(exist_ok=True)
    for old in dest.glob("*.json"):
        old.unlink()
    for key, model in build().items():
        (dest / f"cacaosense-{key}-v1.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(MODELS)} modelos DTDL escritos en {dest}")


if __name__ == "__main__":
    main()
