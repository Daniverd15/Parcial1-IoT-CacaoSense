"""Diagrama de arquitectura de referencia CacaoSense (4 capas con telecomunicaciones explicitas)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "analisis"
OUT.mkdir(exist_ok=True)
BROWN, GOLD, GREEN, BLUE, GREY, CREAM = "#6B3A1E", "#D9A441", "#3E7C3A", "#2F6DB5", "#5A5A5A", "#FFF8EE"

fig, ax = plt.subplots(figsize=(17, 10.5))
ax.set_xlim(0, 170)
ax.set_ylim(0, 105)
ax.axis("off")
fig.patch.set_facecolor("white")


def box(x, y, w, h, text, fc, ec, fs=8.5, color="black", bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec=ec, lw=1.3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=color,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(x1, y1, x2, y2, color=GREY, text=None, fs=7, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=11, color=color, lw=1.2, ls=ls))
    if text:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.2, text, fontsize=fs, color=color, ha="center")


# Carriles de capas
lanes = [(0, "1. CAPA DE DISPOSITIVO\n(predio de cacao, 10 nodos)", "#F7EFE6"),
         (44, "2. CAPA DE RED /\nTELECOMUNICACIONES", "#EAF2FB"),
         (88, "3. CAPA DE PLATAFORMA\n(Azure)", "#EEF6EC"),
         (130, "4. CAPA DE OPERACION", "#FBF6E8")]
for x, t, c in lanes:
    ax.add_patch(FancyBboxPatch((x + 1, 1), 39 if x < 130 else 38, 98, boxstyle="round,pad=0,rounding_size=2", fc=c, ec="#DDDDDD"))
    ax.text(x + 21, 96, t, ha="center", va="top", fontsize=10.5, fontweight="bold", color=BROWN)

nodes = [
    ("01 Lote 1 suelo - Digital Twin (simulador nativo)", GREY, "interno"),
    ("02 Lote 2 suelo - Wokwi ESP32 #1 (PubSubClient)", GREEN, "Wi-Fi"),
    ("03 Lote 3 suelo - Python azure-iot-device", BLUE, "LAN/VM"),
    ("04 Aire rural - puente API Open-Meteo AQ (CAMS)", BLUE, "HTTPS"),
    ("05 Meteo predio - feed Open-Meteo (equiv. Atlas)", BLUE, "HTTPS"),
    ("06 Fermentacion - MQTT explicito paho", BLUE, "LAN/VM"),
    ("07 Estacion de campo - replay CSV ERA5", BLUE, "LAN/VM"),
    ("08 Dosel - puente HTTPS REST", BLUE, "LAN/VM"),
    ("09 Reservorio/riego - Wokwi ESP32 #2", GREEN, "Wi-Fi"),
    ("10 Bodega - Node.js MQTT.js + puesto mando", BLUE, "LAN/VM"),
]
ys = [86 - i * 8.4 for i in range(10)]
for (label, col, _), y in zip(nodes, ys):
    box(3, y - 3, 35, 6, label, "white", col, fs=7.6)

# Capa de red
box(47, 76, 35, 12, "Wokwi-GUEST (Wi-Fi 2.4 GHz)\n-> gateway publico Wokwi\n(nodos 02 y 09)", "white", GREEN, fs=8)
box(47, 52, 35, 19, "VM Azure vm-parcial1-cacao\n(Ubuntu 22.04, mexicocentral)\nsystemd: cacao-03..10 + fleet\nsimula el gateway de borde del predio", "white", BLUE, fs=8)
box(47, 30, 35, 17, "Enlace rural propuesto:\nRouter 4G/LTE Cat4 (Teltonika RUT241)\n+ respaldo Starlink\ncola local store-and-forward\n(iothub-creation-time-utc)", "white", BROWN, fs=8)
box(47, 8, 35, 17, "Seguridad de transporte\nMQTT/TLS 1.2 puerto 8883\nHTTPS 443 (nodo 08 y APIs)\nSAS HMAC-SHA256 por dispositivo\nQoS 0/1 (IoT Hub no admite QoS 2)", "white", GREY, fs=8)
for y in ys:
    arrow(38.5, y, 46.5, 82 if y in (ys[1], ys[8]) else 61, color="#9A9A9A", style="-")

# Capa de plataforma
box(91, 76, 36, 11, "Azure DPS\nglobal.azure-devices-provisioning.net\nID Scope + registro por dispositivo", "white", GREEN, fs=8)
box(91, 58, 36, 13, "IoT Hub gestionado (iotc-...azure-devices.net)\ndevices/{id}/messages/events/\n$iothub/methods (comandos) - twin (props)", "white", GREEN, fs=8)
box(91, 30, 36, 23, "Azure IoT Central\ncacaosense-unab2026\n\nDigital Twin (4 plantillas DTDL v2):\nSuelo | Clima y Aire |\nPoscosecha y Dosel | Riego y Perimetro\nproperties, writable, comandos", CREAM, BROWN, fs=8.2, bold=False)
box(91, 8, 36, 17, "Fuentes publicas externas\nOpen-Meteo Forecast / Air Quality / Archive\n(CAMS, ERA5) - HTTPS GET\nsourceTimestamp conservado", "white", BLUE, fs=8)
arrow(82.5, 82, 90.5, 82, GREEN, "1 DPS")
arrow(82.5, 62, 90.5, 80, BLUE, "1 DPS")
arrow(82.5, 60, 90.5, 64, BLUE, "2 telemetria")
arrow(82.5, 80, 90.5, 66, GREEN, "2 telemetria")
arrow(109, 58, 109, 53.5, BROWN)
arrow(90.5, 16, 82.5, 56, BLUE, "API ->", style="-|>")
arrow(109, 76, 109, 71.5, GREEN)

# Capa de operacion
box(133, 70, 35, 17, "Dashboard 'Cuarto de control'\nlogo, estado de flota,\nKPI min/max, 7 graficos,\nmapa de zonas, alertas", "white", BROWN, fs=8.2)
box(133, 50, 35, 15, "Views por dispositivo\n(Overview / About / comandos /\nproperties / raw data)", "white", GREEN, fs=8.2)
box(133, 30, 35, 15, "Rules + acciones\nR1 suelo seco, R2 fermentacion,\nR3 reservorio, R4 AQI, R5 bodega,\nR7 nodo sin reporte -> correo", "white", "#B5462F", fs=8.2)
box(133, 8, 35, 17, "Data Explorer / Query API\nventana 4 dias no continuos\n18, 20, 22 y 24-sep-2026\nmax / min / prom / recuento / suma", "white", BLUE, fs=8.2)
for y in (78, 57, 37, 16):
    arrow(127.5, 41, 132.5, y, BROWN)
arrow(132.5, 35, 127.5, 64, "#B5462F", "comando", ls="--")
ax.text(85, 0.3, "CacaoSense - Arquitectura de referencia (Parcial 1 IoT UNAB 2026-II). Flechas: 1 = aprovisionamiento DPS, 2 = telemetria MQTT/HTTPS; discontinua = comandos C2D.",
        ha="center", fontsize=8, color=GREY)
fig.savefig(OUT / "arquitectura_cacaosense.png", dpi=150, bbox_inches="tight")
print("ok")

