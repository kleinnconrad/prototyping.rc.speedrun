"""Generate a top view drawing (PNG) of a chassis plate.

The drawing shows the plate in the style of photos/cad_chassis_drawing.png:
filled outline, cutouts, through holes, dashed countersinks and hole labels.
The outline of a reference plate can be added as a dashed line.

Usage (from the root directory of the repository):
    python scripts/cad/generate_drawing.py

Without arguments, the script draws the speedrun chassis plate (wide) with the
outline of the chassis plate and writes
photos/cad_chassis_speedrun_wide_drawing.png.

Requires the packages matplotlib and numpy.
"""
import argparse
import json

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
from matplotlib.patches import Polygon as MPoly

CAD = "cad/chassis"
FILL, EDGE, CSK, LABEL = "#3c4046", "#1b1b1b", "#c77dff", "#ff8c00"


def contour_points(prims, n=40):
    """Polygon points of a contour (arcs with n segments)."""
    pts = []
    for p in prims:
        if p["type"] == "line":
            pts.append(p["start"])
            continue
        c, r = np.array(p["center"]), p["r"]
        ang = lambda q: np.arctan2(q[1] - c[1], q[0] - c[0])
        a0, am, a1 = ang(p["start"]), ang(p["mid"]), ang(p["end"])
        for s in (1, -1):
            m = (am - a0) * s % (2 * np.pi)
            e = (a1 - a0) * s % (2 * np.pi)
            if m < e:
                break
        t = a0 + s * np.linspace(0, e, n, endpoint=False)
        pts += list(np.c_[c[0] + r * np.cos(t), c[1] + r * np.sin(t)])
    return np.array(pts)


def main():
    parser = argparse.ArgumentParser(description="Generate a top view drawing of a chassis plate.")
    parser.add_argument("--geometry", default=f"{CAD}/chassis_plate_speedrun_wide/chassis_plate_speedrun_wide_geometry.json")
    parser.add_argument("--reference", default=f"{CAD}/chassis_plate/chassis_plate_geometry.json",
                        help="geometry JSON of the reference outline, empty string for none")
    parser.add_argument("--reference-label", default="Outline of the chassis plate")
    parser.add_argument("--title", default="Speedrun chassis plate (wide) - top view")
    parser.add_argument("--output", default="photos/cad_chassis_speedrun_wide_drawing.png")
    args = parser.parse_args()

    with open(args.geometry, encoding="utf-8") as f:
        g = json.load(f)
    outline = contour_points(g["outline"])
    dense = contour_points(g["outline"], n=2000)          # for the dimensions
    xmin, xmax = dense[:, 0].min(), dense[:, 0].max()
    ymin, ymax = dense[:, 1].min(), dense[:, 1].max()

    fig, ax = plt.subplots(figsize=(10, 13))
    ax.add_patch(MPoly(outline, closed=True, fc=FILL, ec=EDGE, lw=1.0, zorder=2))
    for contour in g["cutouts"].values():
        ax.add_patch(MPoly(contour_points(contour), closed=True, fc="white", ec=EDGE, lw=0.8, zorder=3))
    if args.reference:
        with open(args.reference, encoding="utf-8") as f:
            ref = contour_points(json.load(f)["outline"])
        ref = np.vstack([ref, ref[:1]])
        ax.plot(ref[:, 0], ref[:, 1], color="#bebebe", lw=0.9, ls=(0, (5, 4)), zorder=4)
    for h in g["holes"]:
        ax.add_patch(Circle((h["x"], h["y"]), g["hole_d"] / 2, fc="white", ec=EDGE, lw=0.5, zorder=5))
        ax.add_patch(Circle((h["x"], h["y"]), g["csk_d"] / 2, fill=False, ec=CSK, lw=0.9, ls=(0, (3, 2)), zorder=5))
        ax.annotate(h["id"], (h["x"], h["y"]), xytext=(5, 5), textcoords="offset points",
                    fontsize=6.5, color=LABEL, zorder=6)
    ax.set_aspect("equal")
    ax.set_xlim(-112, 112)
    ax.set_ylim(-34, 340)
    ax.grid(True, color="#ededed", lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")
    ax.set_title(args.title)
    # dimensions
    x_dim = round(xmax) + 6
    ax.annotate("", (round(xmin, 2), -10), (round(xmax, 2), -10), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text(0, -14, f"{xmax - xmin:.2f} (wide section)", ha="center", va="top", fontsize=9)
    ax.annotate("", (x_dim, round(ymin, 3)), (x_dim, round(ymax, 3)), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text(x_dim + 2, round((ymin + ymax) / 2, 1), f"{ymax - ymin:.2f}", rotation=90, va="center", fontsize=9)
    ax.text(0, -26, f"Countersinks (dashed, Ø{g['csk_d']:g} × {g['csk_angle']:g}°) on BOTTOM face "
                    f"· through Ø{g['hole_d']:g} · t = {g['thickness']:.1f}",
            ha="center", va="top", fontsize=8.5)
    if args.reference:
        ax.legend(handles=[Line2D([], [], color="#bebebe", lw=0.9, ls=(0, (5, 4)), label=args.reference_label)],
                  loc="upper right", fontsize=8, framealpha=0.95)
    fig.tight_layout()
    fig.savefig(args.output, dpi=150)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
