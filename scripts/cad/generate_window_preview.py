"""Generate a preview image (PNG) that compares the old and the longer motor window.

Left: top view of the whole plate with hole labels. Right: detail of the window
with the dimensions. The old window is drawn as a red dashed line, the longer
window as a solid line.

Usage (from the root directory of the repository):
    python scripts/cad/generate_window_preview.py

Without arguments, the script compares the speedrun chassis plate (wide) with
the variant with the longer motor window and writes
photos/cad_chassis_speedrun_wide_motor10_preview.png.

Requires the packages matplotlib and numpy.
"""
import argparse
import json

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

CAD = "cad/chassis_v2"


def contour_points(prims, n=48):
    """Closed polyline of a contour (arcs with n points)."""
    pts = []
    for p in prims:
        if p["type"] == "line":
            pts += [p["start"], p["end"]]
            continue
        c, r = np.array(p["center"]), p["r"]
        ang = lambda q: np.arctan2(q[1] - c[1], q[0] - c[0])
        a0, am, a1 = ang(p["start"]), ang(p["mid"]), ang(p["end"])
        for s in (1, -1):
            m = (am - a0) * s % (2 * np.pi)
            e = (a1 - a0) * s % (2 * np.pi)
            if m < e:
                break
        t = a0 + s * np.linspace(0, e, n)
        pts += list(np.c_[c[0] + r * np.cos(t), c[1] + r * np.sin(t)])
    pts = np.array(pts)
    return np.vstack([pts, pts[:1]])


def window_bounds(geometry):
    pts = [p[k] for p in geometry["cutouts"]["window"] for k in ("start", "end")]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    radius = [p["r"] for p in geometry["cutouts"]["window"] if p["type"] == "arc"][0]
    return min(xs), max(xs), min(ys), max(ys), radius


def main():
    parser = argparse.ArgumentParser(description="Compare the old and the longer motor window.")
    parser.add_argument("--old", default=f"{CAD}/chassis_plate_speedrun_wide/chassis_plate_speedrun_wide_geometry.json")
    parser.add_argument("--new", default=f"{CAD}/chassis_plate_speedrun_wide_motor10/chassis_plate_speedrun_wide_motor10_geometry.json")
    parser.add_argument("--output", default="photos/cad_chassis_speedrun_wide_motor10_preview.png")
    args = parser.parse_args()

    with open(args.old, encoding="utf-8") as f:
        g_old = json.load(f)
    with open(args.new, encoding="utf-8") as f:
        g_new = json.load(f)
    x0, x1, y0, y1o, _ = window_bounds(g_old)
    _, _, _, y1n, radius = window_bounds(g_new)
    width, ext = x1 - x0, y1n - y1o
    dense = contour_points(g_new["outline"], n=2000)
    size = (f"{dense[:, 0].max() - dense[:, 0].min():.2f} x {dense[:, 1].max() - dense[:, 1].min():.2f} "
            f"x {g_new['thickness']:.1f} mm")

    def draw(ax, zoom):
        o = contour_points(g_new["outline"])
        ax.plot(o[:, 0], o[:, 1], "k-", lw=1.2, label="outline")
        s = contour_points(g_new["cutouts"]["slot"])
        ax.plot(s[:, 0], s[:, 1], color="0.35", lw=1.0, label="slot (unchanged)")
        w0 = contour_points(g_old["cutouts"]["window"])
        w1 = contour_points(g_new["cutouts"]["window"])
        ax.plot(w1[:, 0], w1[:, 1], color="#1f4e9c", lw=1.8, label=f"new window {width:.3f} x {y1n - y0:.3f}")
        ax.plot(w0[:, 0], w0[:, 1], color="#d62728", lw=1.4, ls="--", label=f"old window {width:.3f} x {y1o - y0:.3f}")
        for h in g_new["holes"]:
            ax.add_patch(Circle((h["x"], h["y"]), g_new["hole_d"] / 2, fill=False, lw=0.8, color="k"))
            ax.add_patch(Circle((h["x"], h["y"]), g_new["csk_d"] / 2, fill=False, lw=0.6, ls=":", color="0.4"))
            ax.annotate(h["id"], (h["x"], h["y"]), xytext=(4, 3), textcoords="offset points",
                        fontsize=7 if zoom else 6, color="#333333")
        ax.set_aspect("equal")
        ax.grid(True, lw=0.3, color="0.85")
        ax.set_xlabel("x [mm]")
        ax.set_ylabel("y [mm]")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 12), gridspec_kw={"width_ratios": [1.05, 1]})
    draw(a1, False)
    a1.set_title(f"Speedrun chassis plate (wide), motor window +{ext:g} mm toward End A\n"
                 f"top view (side without countersinks), {size}", fontsize=10)
    a1.annotate("End A (H34-H36), +y", (0, 330), ha="center", fontsize=8)
    a1.annotate("End B (H01-H04), y = 0", (0, -9), ha="center", fontsize=8)
    a1.set_ylim(-14, 338)
    a1.legend(loc="lower left", fontsize=8, framealpha=0.95)

    draw(a2, True)
    a2.set_xlim(-30, 75)
    a2.set_ylim(40, 160)
    for y, dy, txt, c in ((y0, 3.0, f"y min {y0:.3f} (fixed)", "k"),
                          (y1o, 0, f"old y max {y1o:.3f}", "#d62728"),
                          (y1n, 0, f"new y max {y1n:.3f}", "#1f4e9c")):
        a2.annotate(txt, (x1 + 1.5, y + dy), va="center", fontsize=8, color=c)
    a2.annotate("", (x0 + 4, y1n), (x0 + 4, y1o), arrowprops=dict(arrowstyle="<->", color="#1f4e9c", lw=1))
    a2.annotate(f"+{ext:.3f}", (x0 + 5, (y1o + y1n) / 2), va="center", fontsize=8, color="#1f4e9c")
    a2.annotate("", (x0, round(y0 - 4.1, 1)), (x1, round(y0 - 4.1, 1)),
                arrowprops=dict(arrowstyle="<->", color="k", lw=0.8))
    a2.annotate(f"{width:.3f} (unchanged)", ((x0 + x1) / 2, round(y0 - 6.1, 1)), ha="center", va="top", fontsize=8)
    a2.annotate(f"{y1n - y0:.3f}", (x0 + 11.7, round((y0 + y1n) / 2 - 2.3)), ha="center", fontsize=9,
                color="#1f4e9c", rotation=90, va="center")
    a2.annotate(f"R {radius:.1f} (all four corners)", (x0 + 1, y1n + 3), fontsize=8, color="#1f4e9c")
    a2.set_title("Detail: window. Solid = new, red dashed = old.\n"
                 f"Through holes Ø{g_new['hole_d']:g} (solid), countersink Ø{g_new['csk_d']:g} on bottom face (dotted)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(args.output, dpi=130)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
