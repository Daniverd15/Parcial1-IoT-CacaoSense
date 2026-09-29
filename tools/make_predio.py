"""Ilustracion del predio CacaoSense con los 10 nodos ubicados en su zona (tile de imagen del panel).

  python tools/make_predio.py      -> assets/predio_nodos.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import (Circle, Ellipse, FancyBboxPatch, PathPatch, Polygon, Rectangle, Arc)
from matplotlib.path import Path as MPath

OUT = Path(__file__).resolve().parents[1] / "assets" / "predio_nodos.png"
rng = np.random.default_rng(7)
W, H = 16, 9
# colores por plantilla DTDL
C_SUELO, C_CLIMA, C_POS, C_RIEGO = "#8D5524", "#1E88E5", "#F57C00", "#00ACC1"
CREAM, DARK = "#FFF8EE", "#1B120B"

fig = plt.figure(figsize=(W, H), dpi=110)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")


def grad_rect(x0, y0, x1, y1, c0, c1, n=90, vertical=True, z=0):
    a, b = np.array(matplotlib.colors.to_rgb(c0)), np.array(matplotlib.colors.to_rgb(c1))
    for i in range(n):
        t = i / (n - 1)
        if vertical:
            ax.add_patch(Rectangle((x0, y0 + (y1 - y0) * i / n), x1 - x0, (y1 - y0) / n + 0.01,
                                   color=(1 - t) * a + t * b, lw=0, zorder=z))
        else:
            ax.add_patch(Rectangle((x0 + (x1 - x0) * i / n, y0), (x1 - x0) / n + 0.01, y1 - y0,
                                   color=(1 - t) * a + t * b, lw=0, zorder=z))


# cielo y montanas (Santander)
grad_rect(0, 7.2, W, H, "#F6C77B", "#7FB3D5", z=0)
ax.add_patch(Circle((13.6, 8.25), 0.42, color="#FFE8A3", zorder=1))
for pts, col in [([(0, 7.2), (1.8, 8.3), (3.6, 7.6), (5.8, 8.6), (8.2, 7.7), (10.5, 8.5), (12.7, 7.6), (14.8, 8.2), (16, 7.7), (16, 7.2)], "#5D7F5A"),
                 ([(0, 7.2), (2.6, 7.9), (4.8, 7.35), (7.2, 8.0), (9.6, 7.3), (12.0, 7.95), (16, 7.3), (16, 7.2)], "#44683F")]:
    ax.add_patch(Polygon(pts, closed=True, color=col, zorder=2))
# terreno
grad_rect(0, 0, W, 7.25, "#6FAF4F", "#8CC265", z=3)
for _ in range(900):  # textura de pasto
    x, y = rng.uniform(0, W), rng.uniform(0, 7.2)
    ax.add_patch(Circle((x, y), rng.uniform(0.01, 0.03), color="#5E9C43", alpha=0.5, lw=0, zorder=4))

# camino de tierra (entrada abajo -> poscosecha -> bodega)
road = MPath([(8.3, -0.2), (8.4, 1.2), (7.6, 2.4), (8.6, 3.6), (10.2, 3.9), (12.0, 3.4), (13.4, 2.4)],
             [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4])
ax.add_patch(PathPatch(road, fill=False, lw=26, color="#C9A26B", capstyle="round", zorder=5))
ax.add_patch(PathPatch(road, fill=False, lw=2, color="#E4C898", ls=(0, (4, 6)), zorder=6))


def cacao_plot(x0, y0, w, h, label):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0,rounding_size=0.15",
                                fc="#7A5230", ec="#5A3A1E", lw=2, zorder=7))
    for r in np.arange(y0 + 0.25, y0 + h - 0.1, 0.42):
        for c in np.arange(x0 + 0.25, x0 + w - 0.1, 0.42):
            ax.add_patch(Circle((c, r), 0.17, color="#2E6B2F", zorder=8))
            ax.add_patch(Circle((c - 0.05, r + 0.05), 0.08, color="#3F8A3A", zorder=9))
            if rng.random() < 0.45:
                ax.add_patch(Ellipse((c + 0.09, r - 0.07), 0.07, 0.11, color="#E08A2B", zorder=10))
    ax.text(x0 + w / 2, y0 + h + 0.12, label, ha="center", va="bottom", fontsize=11, color=CREAM,
            fontweight="bold", zorder=11, bbox=dict(boxstyle="round,pad=0.25", fc="#3B2412", ec="none", alpha=0.85))


cacao_plot(0.6, 3.9, 2.4, 2.4, "Lote 1")
cacao_plot(3.4, 3.9, 2.4, 2.4, "Lote 2")
cacao_plot(0.6, 0.6, 2.4, 2.6, "Lote 3")

# dosel / sombra: arboles grandes
for (x, y, r) in [(4.4, 1.2, 0.55), (5.3, 2.1, 0.62), (6.1, 1.0, 0.5), (4.3, 2.7, 0.45), (6.4, 2.6, 0.5)]:
    ax.add_patch(Circle((x + 0.08, y - 0.08), r, color="#24521F", alpha=0.5, zorder=7))
    ax.add_patch(Circle((x, y), r, color="#2F6E2A", zorder=8))
    ax.add_patch(Circle((x - r * 0.3, y + r * 0.3), r * 0.45, color="#48913F", zorder=9))
ax.text(5.3, 0.25, "Dosel / sombra", ha="center", fontsize=11, color=CREAM, fontweight="bold", zorder=11,
        bbox=dict(boxstyle="round,pad=0.25", fc="#1F3E1B", ec="none", alpha=0.85))

# reservorio
ax.add_patch(Ellipse((12.9, 5.6), 3.0, 1.6, color="#2B7BB9", zorder=7))
ax.add_patch(Ellipse((12.8, 5.7), 2.5, 1.2, color="#4FA3E0", zorder=8))
for dx in (-0.6, 0.1, 0.7):
    ax.add_patch(Arc((12.8 + dx, 5.7 + dx * 0.1), 0.5, 0.12, theta1=0, theta2=180, color="#BFE3FA", lw=1.5, zorder=9))
ax.add_patch(Rectangle((11.1, 5.05), 0.35, 0.3, color="#607D8B", zorder=9))  # bomba
ax.plot([11.1, 6.0, 6.0], [5.2, 5.2, 6.3], color="#90A4AE", lw=3, zorder=6)  # tuberia de riego
ax.text(12.9, 4.55, "Reservorio / riego", ha="center", fontsize=11, color=CREAM, fontweight="bold", zorder=11,
        bbox=dict(boxstyle="round,pad=0.25", fc="#0D4A73", ec="none", alpha=0.85))

# secado / fermentacion
ax.add_patch(Rectangle((8.9, 4.4), 2.2, 1.3, color="#8D6E63", zorder=7))
ax.add_patch(Polygon([(8.75, 5.7), (10.0, 6.35), (11.25, 5.7)], color="#A1422A", zorder=8))
for i in range(3):
    ax.add_patch(Rectangle((9.1 + i * 0.65, 4.55), 0.5, 0.45, color="#5D4037", ec="#3E2723", lw=1.5, zorder=9))
for i in range(2):  # camas de secado
    ax.add_patch(Rectangle((8.9 + i * 1.15, 3.95), 1.0, 0.32, color="#6D4C41", zorder=7))
    for k in range(10):
        ax.add_patch(Circle((8.97 + i * 1.15 + k * 0.095, 4.11), 0.035, color="#C07A3A", zorder=8))
ax.text(10.0, 6.45, "Secado / fermentación", ha="center", fontsize=11, color=CREAM, fontweight="bold", zorder=11,
        bbox=dict(boxstyle="round,pad=0.25", fc="#5A2A17", ec="none", alpha=0.85))

# bodega + porton de entrada
ax.add_patch(Rectangle((13.2, 1.3), 1.9, 1.2, color="#BCAAA4", zorder=7))
ax.add_patch(Polygon([(13.05, 2.5), (14.15, 3.05), (15.25, 2.5)], color="#6D4C41", zorder=8))
ax.add_patch(Rectangle((13.95, 1.3), 0.45, 0.65, color="#4E342E", zorder=9))
ax.plot([6.8, 16], [0.08, 0.08], color="#795548", lw=3, zorder=6)  # cerca
for x in np.arange(6.8, 16, 0.5):
    ax.plot([x, x], [0.0, 0.3], color="#795548", lw=2, zorder=6)
ax.text(14.15, 0.75, "Perímetro / bodega", ha="center", fontsize=11, color=CREAM, fontweight="bold", zorder=11,
        bbox=dict(boxstyle="round,pad=0.25", fc="#3E2723", ec="none", alpha=0.85))

# estacion meteorologica (colina), sensor de aire (camino), estacion de campo
ax.plot([7.2, 7.2], [6.4, 7.7], color="#ECEFF1", lw=3, zorder=9)
ax.add_patch(Rectangle((6.95, 6.7), 0.5, 0.35, color="#263238", zorder=10))  # panel solar
for a in (0, 120, 240):
    t = np.radians(a)
    ax.plot([7.2, 7.2 + 0.3 * np.cos(t)], [7.7, 7.7 + 0.12 * np.sin(t)], color="#ECEFF1", lw=2, zorder=10)
ax.text(7.2, 6.05, "Meteo del predio", ha="center", fontsize=10, color=CREAM, fontweight="bold", zorder=11,
        bbox=dict(boxstyle="round,pad=0.2", fc="#0D3C61", ec="none", alpha=0.85))
ax.plot([9.9, 9.9], [2.2, 3.1], color="#CFD8DC", lw=3, zorder=9)
ax.add_patch(Rectangle((9.72, 2.95), 0.36, 0.3, color="#37474F", zorder=10))
ax.text(9.9, 1.8, "Aire rural", ha="center", fontsize=10, color=CREAM, fontweight="bold", zorder=11,
        bbox=dict(boxstyle="round,pad=0.2", fc="#0D3C61", ec="none", alpha=0.85))
ax.add_patch(Rectangle((6.5, 4.5), 0.7, 0.45, color="#ECEFF1", zorder=9))
ax.add_patch(Rectangle((7.5, 4.5), 0.18, 0.5, color="#B0BEC5", zorder=9))  # pluviometro
ax.text(7.1, 4.05, "Estación de campo", ha="center", fontsize=10, color=CREAM, fontweight="bold", zorder=11,
        bbox=dict(boxstyle="round,pad=0.2", fc="#0D3C61", ec="none", alpha=0.85))

# nube Azure IoT Central
cx, cy = 3.9, 8.3
for (dx, dy, r) in [(0, 0, 0.42), (0.45, 0.12, 0.5), (0.95, 0, 0.4), (0.45, -0.18, 0.38)]:
    ax.add_patch(Circle((cx + dx, cy + dy), r, color="white", zorder=20))
ax.text(cx + 0.47, cy - 0.02, "Azure IoT Central", ha="center", va="center", fontsize=11, color="#0B5CAD",
        fontweight="bold", zorder=21)

# nodos
NODES = [
    ("01", 1.8, 5.1, C_SUELO, "Digital Twin"),
    ("02", 4.6, 5.1, C_SUELO, "Wokwi ESP32 #1"),
    ("03", 1.8, 1.9, C_SUELO, "Python SDK"),
    ("04", 9.9, 3.25, C_CLIMA, "API CAMS"),
    ("05", 7.2, 7.1, C_CLIMA, "Feed Open-Meteo"),
    ("06", 10.0, 5.05, C_POS, "MQTT paho"),
    ("07", 6.85, 4.72, C_CLIMA, "Replay ERA5"),
    ("08", 5.3, 2.1, C_POS, "HTTPS REST"),
    ("09", 11.3, 5.2, C_RIEGO, "Wokwi ESP32 #2"),
    ("10", 14.2, 1.95, C_RIEGO, "Node MQTT.js"),
]
for num, x, y, col, src in NODES:
    ax.plot([x, cx + 0.47], [y, cy - 0.3], color="white", lw=1, alpha=0.35, ls=(0, (2, 3)), zorder=15)
for num, x, y, col, src in NODES:
    for r, a in ((0.55, 0.18), (0.42, 0.28)):
        ax.add_patch(Circle((x, y), r, color=col, alpha=a, lw=0, zorder=16))
    ax.add_patch(Circle((x, y), 0.3, fc=col, ec="white", lw=2.5, zorder=17))
    ax.text(x, y, num, ha="center", va="center", fontsize=12, color="white", fontweight="bold", zorder=18)
    ax.text(x + 0.38, y - 0.02, src, ha="left", va="center", fontsize=9, color="white", zorder=18,
            bbox=dict(boxstyle="round,pad=0.2", fc=DARK, ec=col, lw=1.2, alpha=0.88))

# leyenda
ax.add_patch(FancyBboxPatch((11.7, 7.35), 4.05, 1.45, boxstyle="round,pad=0,rounding_size=0.15",
                            fc=DARK, ec="#D9A441", lw=1.5, alpha=0.9, zorder=19))
ax.text(11.9, 8.55, "Predio CacaoSense · Rionegro (Santander)", fontsize=10.5, color=CREAM, fontweight="bold",
        va="center", zorder=20)
for i, (lab, col) in enumerate([("Suelo", C_SUELO), ("Clima y aire", C_CLIMA), ("Poscosecha y dosel", C_POS),
                                ("Riego y perímetro", C_RIEGO)]):
    x, y = 11.95 + (i % 2) * 1.9, 8.1 - (i // 2) * 0.42
    ax.add_patch(Circle((x, y), 0.11, fc=col, ec="white", lw=1.2, zorder=20))
    ax.text(x + 0.2, y, lab, fontsize=9.5, color=CREAM, va="center", zorder=20)

fig.savefig(OUT, facecolor=DARK)
print("ilustracion en", OUT)
