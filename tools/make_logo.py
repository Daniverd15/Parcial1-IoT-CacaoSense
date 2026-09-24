"""Dibuja el logo de CacaoSense (mazorca de cacao + ondas de senal) en PNG."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Ellipse, FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "assets"
OUT.mkdir(exist_ok=True)
BROWN, GOLD, GREEN, CREAM = "#6B3A1E", "#D9A441", "#3E7C3A", "#FFF8EE"


def draw(ax, with_text=True):
    ax.set_xlim(0, 10 if with_text else 4)
    ax.set_ylim(0, 4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Ellipse((1.7, 1.9), 1.5, 2.9, angle=-25, color=BROWN))
    for dx in (-0.35, 0, 0.35):
        ax.add_patch(Arc((1.7 + dx * 0.9, 1.9 + dx * 0.4), 0.5, 2.6, angle=-25, color=GOLD, lw=2.2))
    ax.add_patch(Ellipse((2.45, 3.45), 0.9, 0.35, angle=30, color=GREEN))
    for r in (0.6, 1.0, 1.4):
        ax.add_patch(Arc((2.75, 2.9), r, r, theta1=-10, theta2=80, color=GREEN, lw=3))
    if with_text:
        ax.text(4.0, 2.25, "CacaoSense", fontsize=40, fontweight="bold", color=BROWN, va="center", family="DejaVu Sans")
        ax.text(4.05, 1.15, "Granja y cultivo de cacao  |  IoT UNAB", fontsize=15, color=GREEN, va="center")


fig = plt.figure(figsize=(10, 4), dpi=120)
ax = fig.add_axes([0, 0, 1, 1])
fig.patch.set_facecolor(CREAM)
ax.add_patch(FancyBboxPatch((0.1, 0.1), 9.8, 3.8, boxstyle="round,pad=0,rounding_size=0.4", color=CREAM))
draw(ax)
fig.savefig(OUT / "cacaosense_logo.png", facecolor=CREAM)

fig = plt.figure(figsize=(4, 4), dpi=64)
ax = fig.add_axes([0, 0, 1, 1])
fig.patch.set_facecolor(CREAM)
draw(ax, with_text=False)
fig.savefig(OUT / "cacaosense_icon.png", facecolor=CREAM)
print("logos en", OUT)
