"""Banner del cuarto de control (tile de imagen en IoT Central, tema oscuro): mazorca + ondas + lema."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, Ellipse, Rectangle

OUT = Path(__file__).resolve().parents[1] / "assets"
BROWN, DARK, GOLD, GREEN, CREAM, LEAF = "#6B3A1E", "#2B1A10", "#D9A441", "#3E7C3A", "#FFF8EE", "#8BC34A"

fig = plt.figure(figsize=(12, 5), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 12)
ax.set_ylim(0, 5)
ax.axis("off")
# fondo en degradado cafe (franjas verticales)
for i in range(120):
    t = i / 119
    c = tuple((1 - t) * a + t * b for a, b in zip(matplotlib.colors.to_rgb(BROWN), matplotlib.colors.to_rgb(DARK)))
    ax.add_patch(Rectangle((i * 0.1, 0), 0.1, 5, color=c, lw=0))
# hojas de fondo
for (x, y, w, h, a) in [(10.6, 4.3, 2.4, 0.8, 35), (11.3, 0.6, 2.2, 0.7, -30), (0.4, 0.3, 1.8, 0.6, 20)]:
    ax.add_patch(Ellipse((x, y), w, h, angle=a, color=GREEN, alpha=0.35, lw=0))
# mazorca
ax.add_patch(Ellipse((1.9, 2.4), 1.7, 3.3, angle=-25, color="#8A4B25"))
for dx in (-0.38, 0, 0.38):
    ax.add_patch(Arc((1.9 + dx * 0.9, 2.4 + dx * 0.4), 0.55, 3.0, angle=-25, color=GOLD, lw=2.6))
ax.add_patch(Ellipse((2.75, 4.15), 1.0, 0.4, angle=30, color=LEAF))
for r in (0.7, 1.15, 1.6):
    ax.add_patch(Arc((3.1, 3.5), r, r, theta1=-10, theta2=80, color=LEAF, lw=3.5))
# texto
ax.text(4.2, 3.35, "CacaoSense", fontsize=58, fontweight="bold", color=CREAM, va="center")
ax.text(4.25, 2.3, "Cuarto de control  ·  Granja y cultivo de cacao", fontsize=21, color=GOLD, va="center")
ax.text(4.25, 1.6, "Rionegro, Santander  ·  UNAB 2026-II", fontsize=16, color=CREAM, alpha=0.85, va="center")
# chips de la flota
chips = ["10 nodos", "10 orígenes", "4 plantillas DTDL", "Azure IoT Central"]
x = 4.25
for label in chips:
    w = 0.085 * len(label) + 0.4
    ax.add_patch(matplotlib.patches.FancyBboxPatch((x, 0.55), w, 0.5, boxstyle="round,pad=0,rounding_size=0.22",
                                                   color=GREEN, lw=0))
    ax.text(x + w / 2, 0.8, label, fontsize=13, color=CREAM, ha="center", va="center", fontweight="bold")
    x += w + 0.15
ax.add_patch(Circle((11.55, 4.55), 0.12, color=LEAF))
ax.text(11.35, 4.55, "EN VIVO", fontsize=11, color=LEAF, ha="right", va="center", fontweight="bold")
fig.savefig(OUT / "cacaosense_banner.png", facecolor=DARK)
print("banner en", OUT / "cacaosense_banner.png")

