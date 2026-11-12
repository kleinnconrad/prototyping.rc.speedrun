"""Generate the drawing and the 1:1 print templates of the chassis plate and the top brace.

Outputs (from the geometry data in cad/chassis):
* photos/cad_chassis_drawing.png: top view of the chassis plate and the top brace with
  hole labels and main dimensions
* cad/chassis/chassis_plate/chassis_plate_T410R_1to1_A3.pdf: 1:1 template of the chassis
  plate on one A3 page (portrait)
* cad/chassis/chassis_plate/chassis_plate_T410R_1to1_A4x2.pdf: 1:1 template of the chassis
  plate on two A4 pages (portrait) with a 20 mm overlap zone
* cad/chassis/top_brace/top_brace_T410R_1to1_A4.pdf: 1:1 template of the top brace on one
  A4 page (portrait)

The templates are drawn for printing at 100 % ("actual size"). For a PDF viewer that prints
at another fixed scale, the option --print-scale (for example 0.97) enlarges the content by
1/print_scale; then use --suffix to keep the 100 % files.

Usage (from the root directory of the repository):
    python scripts/cad/generate_chassis_templates.py [--print-scale 1.0] [--suffix ""]

Requires the packages matplotlib, numpy and reportlab.
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402
from matplotlib.patches import Polygon as MPoly  # noqa: E402
from reportlab.lib.pagesizes import A3, A4  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_drawing import contour_points, FILL, EDGE, CSK as CSK_PNG, LABEL  # noqa: E402
from generate_print_template import contour_path, text, bar, RED, CSK, BLUE  # noqa: E402

CAD = "cad/chassis"
PLATE_JSON = f"{CAD}/chassis_plate/chassis_plate_geometry.json"
BRACE_JSON = f"{CAD}/top_brace/top_brace_geometry.json"
ZONE = (150.0, 170.0)            # overlap zone of the A4x2 template (plate y), no holes inside
DARK = (0.3, 0.3, 0.3)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extent(g):
    p = contour_points(g["outline"], n=2000)
    return p[:, 0].min(), p[:, 0].max(), p[:, 1].min(), p[:, 1].max()


def width_at(g, y):
    """Width of the outline at the height y (outer intersections of the contour)."""
    p = contour_points(g["outline"], n=2000)
    q = np.roll(p, -1, axis=0)
    xs = []
    for (x0, y0), (x1, y1) in zip(p, q):
        if (y0 - y) * (y1 - y) <= 0 and y0 != y1:
            xs.append(x0 + (y - y0) / (y1 - y0) * (x1 - x0))
    return max(xs) - min(xs)


def hole_distance(g, a, b):
    h = {k["id"]: k for k in g["holes"]}
    return math.hypot(h[a]["x"] - h[b]["x"], h[a]["y"] - h[b]["y"])


# ---------------------------------------------------------------- PDF templates
def draw_part(c, g):
    """Outline, cutouts, holes with centre cross, countersinks and labels (1 unit = 1 mm)."""
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.25)
    c.setDash()
    c.drawPath(contour_path(c, g["outline"]), stroke=1, fill=0)
    for cut in g["cutouts"].values():
        c.drawPath(contour_path(c, cut), stroke=1, fill=0)
    for h in g["holes"]:
        x, y = h["x"], h["y"]
        if g.get("csk_d", 0) > g["hole_d"]:
            c.setDash([0.6, 0.5])
            c.setLineWidth(0.15)
            c.setStrokeColorRGB(*CSK)
            c.circle(x, y, g["csk_d"] / 2, stroke=1, fill=0)
        c.setDash()
        c.setLineWidth(0.2)
        c.setStrokeColorRGB(*RED)
        c.circle(x, y, g["hole_d"] / 2, stroke=1, fill=0)
        c.setLineWidth(0.1)
        c.setStrokeColorRGB(0, 0, 0)
        c.line(x - 2.6, y, x + 2.6, y)
        c.line(x, y - 2.6, x, y + 2.6)
        text(c, x + 2.4, y + 2.4, h["id"], 1.9, (0.2, 0.2, 0.2))


def write_notes(c, x, y, lines):
    for s, size, bold, col in lines:
        text(c, x, y, s, size, col, bold)
        y -= max(size * 1.45, 1.2)


def print_lines(print_scale):
    pct = f"{print_scale * 100:g}"
    if print_scale == 1.0:
        return [('PRINT AT 100 % ("actual size"), no fit to page.', 2.3, True, (0, 0, 0))]
    return [(f"PRINT AT {pct} % (scale of your PDF viewer).", 2.3, True, (0, 0, 0)),
            (f"The drawing is pre-scaled to {100 / print_scale:.2f} % (100/{pct}).", 2.2, False, (0, 0, 0)),
            (f'Printed at 100 % ("actual size") it is {(1 / print_scale - 1) * 100:.1f} % too large.', 2.2, False,
             (0, 0, 0))]


def plate_lines(g, title, print_scale):
    k_ = (0, 0, 0)
    return [(title, 3.0, True, k_), ("", 1.2, False, k_)] + print_lines(print_scale) + [
        ("Check both 100 mm bars with a ruler before use.", 2.2, False, k_),
        ("", 1.2, False, k_),
        ("Top view (side without countersinks): place the plate with the countersinks facing down.", 2.2, False, k_),
        (f"Red: through holes Ø{g['hole_d']:g} mm with centre cross. Dashed circles: countersinks "
         f"Ø{g['csk_d']:g} mm (bottom face).", 2.2, False, k_),
        ("Scaled to caliper values: width 99.98 mm, H11 to H23 %.2f mm (centres)." % hole_distance(g, "H11", "H23"),
         2.2, False, DARK),
        ("Origin: x = 0 centre line, y = 0 end edge with H01 to H04 (End B).", 2.2, False, DARK),
    ]


def canvas_for(path, pagesize, title, subject):
    c = canvas.Canvas(path, pagesize=pagesize)
    c.setTitle(title)
    c.setAuthor("prototyping.rc.speedrun")
    c.setSubject(subject)
    return c


def plate_a3(path, g, print_scale):
    k = mm / print_scale
    pw, ph = A3[0] / k, A3[1] / k                       # page size in printed mm
    c = canvas_for(path, A3, f"Chassis plate - 1:1 template ({print_scale * 100:g} %)",
                   "Carten T410R chassis plate, A3 portrait")
    c.saveState()
    c.scale(k, k)
    write_notes(c, 12, ph - 12, plate_lines(g, "Carten T410R chassis plate - 1:1 template, A3", print_scale))
    bar(c, 12, 14, True, "100 mm (x)")
    bar(c, 30, 40, False, "100 mm (y)")
    c.translate(pw / 2, 30)                              # plate coordinates
    draw_part(c, g)
    text(c, 0, -5, "End B (H01 to H04)", 2.4, anchor="c")
    text(c, 0, extent(g)[3] + 4, "End A (H34 to H36)", 2.4, anchor="c")
    c.restoreState()
    c.showPage()
    c.save()


def plate_a4x2(path, g, print_scale):
    k = mm / print_scale
    pw, ph = A4[0] / k, A4[1] / k
    xmax = pw / 2 - 5
    ytop = extent(g)[3] + 6
    if any(ZONE[0] - g["csk_d"] / 2 < h["y"] < ZONE[1] + g["csk_d"] / 2 for h in g["holes"]):
        raise ValueError("a hole lies in the overlap zone")
    # (plate y range, page y of plate y = 0, notes y, notes at the top)
    pages = [((-6.0, ZONE[1] + 10), 22.0, ph - 10, True),
             ((ZONE[0] - 10, ytop), ph - 5 - ytop, 88.0, False)]
    c = canvas_for(path, A4, f"Chassis plate - 1:1 template on 2 x A4 ({print_scale * 100:g} %)",
                   "Carten T410R chassis plate, 2 x A4 portrait")
    for n, ((y0, y1), oy, ny, top) in enumerate(pages, start=1):
        c.saveState()
        c.scale(k, k)
        lines = plate_lines(g, f"Carten T410R chassis plate - 1:1 template, A4 page {n} of 2", print_scale) + [
            ("", 1.2, False, (0, 0, 0)),
            ("Blue dashed: 20 mm overlap zone. Lay page 2 over page 1 so that", 2.2, False, BLUE),
            ("both pairs of lines coincide.", 2.2, False, BLUE)]
        write_notes(c, 8, ny, lines)
        bar(c, pw / 2 - 50, 9 if top else 12, True, "100 mm (x)")
        bar(c, 22, 40 if top else 105, False, "100 mm (y)")
        c.translate(pw / 2, oy)
        clip = c.beginPath()
        clip.rect(-xmax, y0, 2 * xmax, y1 - y0)
        c.clipPath(clip, stroke=0, fill=0)
        draw_part(c, g)
        c.setStrokeColorRGB(*BLUE)
        c.setLineWidth(0.3)
        c.setDash([2.0, 1.2])
        for yz in ZONE:
            c.line(-xmax, yz, xmax, yz)
        text(c, -xmax + 1, ZONE[1] + 1.2, "overlap zone (20 mm)", 2.2, BLUE)
        if top:
            text(c, 0, -5, "End B (H01 to H04)", 2.4, anchor="c")
        else:
            text(c, 0, ytop - 2, "End A (H34 to H36)", 2.4, anchor="c")
        c.restoreState()
        c.showPage()
    c.save()


def brace_a4(path, g, print_scale):
    k = mm / print_scale
    pw, ph = A4[0] / k, A4[1] / k
    k_ = (0, 0, 0)
    lines = [("Carten T410R top brace - 1:1 template, A4", 3.0, True, k_), ("", 1.2, False, k_)] + \
        print_lines(print_scale) + [
        ("Check both 100 mm bars with a ruler before use.", 2.2, False, k_),
        ("", 1.2, False, k_),
        (f"Red: through holes Ø{g['hole_d']:g} mm with centre cross (not countersunk).", 2.2, False, k_),
        ("Scaled to the caliper value of the bar width: %.2f mm." % width_at(g, 120.0), 2.2, False, DARK),
        ("Origin: x = 0 centre line, y = 0 end edge with the hexagon cutout.", 2.2, False, DARK),
    ]
    c = canvas_for(path, A4, f"Top brace - 1:1 template ({print_scale * 100:g} %)", "Carten T410R top brace, A4 portrait")
    c.saveState()
    c.scale(k, k)
    write_notes(c, 8, ph - 12, lines)
    bar(c, 12, 15, True, "100 mm (x)")
    bar(c, 190, 40, False, "100 mm (y)")
    c.translate(150, 22)
    draw_part(c, g)
    c.restoreState()
    c.showPage()
    c.save()


# ---------------------------------------------------------------- drawing (PNG)
def draw_png_part(ax, g):
    ax.add_patch(MPoly(contour_points(g["outline"]), closed=True, fc=FILL, ec=EDGE, lw=1.0, zorder=2))
    for contour in g["cutouts"].values():
        ax.add_patch(MPoly(contour_points(contour), closed=True, fc="white", ec=EDGE, lw=0.8, zorder=3))
    for h in g["holes"]:
        ax.add_patch(Circle((h["x"], h["y"]), g["hole_d"] / 2, fc="white", ec=EDGE, lw=0.5, zorder=5))
        if g.get("csk_d", 0) > g["hole_d"]:
            ax.add_patch(Circle((h["x"], h["y"]), g["csk_d"] / 2, fill=False, ec=CSK_PNG, lw=0.9,
                                ls=(0, (3, 2)), zorder=5))
        ax.annotate(h["id"], (h["x"], h["y"]), xytext=(5, 5), textcoords="offset points",
                    fontsize=6.5, color=LABEL, zorder=6)
    ax.set_aspect("equal")
    ax.grid(True, color="#ededed", lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")


def dim_arrows(ax, x0, x1, y_dim, label_w, xd, ymin, ymax):
    ax.annotate("", (x0, y_dim), (x1, y_dim), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text((x0 + x1) / 2, y_dim - 4, label_w, ha="center", va="top", fontsize=9)
    ax.annotate("", (xd, ymin), (xd, ymax), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text(xd + 2, (ymin + ymax) / 2, f"{ymax - ymin:.2f}", rotation=90, va="center", fontsize=9)


def drawing(path, plate, brace):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.8, 14.93), gridspec_kw=dict(width_ratios=[2.45, 1.0]))
    draw_png_part(a1, plate)
    x0, x1, y0, y1 = extent(plate)
    dim_arrows(a1, x0, x1, -10, f"{x1 - x0:.2f} (main section)", x1 + 6, y0, y1)
    a1.text(0, -24, f"Countersinks (dashed, Ø{plate['csk_d']:g} × {plate['csk_angle']:g}°) on BOTTOM face "
                    f"· through Ø{plate['hole_d']:g} · t = {plate['thickness']:.1f}", ha="center", va="top", fontsize=8.5)
    a1.set_xlim(-56, 64)
    a1.set_ylim(-34, 340)
    a1.set_title("Chassis plate (original shape) - top view")
    draw_png_part(a2, brace)
    x0, x1, y0, y1 = extent(brace)
    wb = width_at(brace, 120.0)
    dim_arrows(a2, -wb / 2, wb / 2, -10, f"{wb:.2f} bar", x1 + 6, y0, y1)
    a2.text(0, -24, f"Plain Ø{brace['hole_d']:g} holes · t = {brace['thickness']:.1f}", ha="center", va="top",
            fontsize=8.5)
    a2.set_xlim(-22, 30)
    a2.set_ylim(-34, 262)
    a2.set_title("Top brace - top view")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Drawing and 1:1 templates of the chassis plate and the top brace.")
    parser.add_argument("--print-scale", type=float, default=1.0, help="scale of the PDF viewer (default 1.0)")
    parser.add_argument("--suffix", default="", help="added to the PDF file names, for example _print97")
    parser.add_argument("--drawing", default="photos/cad_chassis_drawing.png")
    args = parser.parse_args()

    plate, brace = load(PLATE_JSON), load(BRACE_JSON)
    out = {
        "a3": f"{CAD}/chassis_plate/chassis_plate_T410R_1to1_A3{args.suffix}.pdf",
        "a4x2": f"{CAD}/chassis_plate/chassis_plate_T410R_1to1_A4x2{args.suffix}.pdf",
        "brace": f"{CAD}/top_brace/top_brace_T410R_1to1_A4{args.suffix}.pdf",
    }
    plate_a3(out["a3"], plate, args.print_scale)
    plate_a4x2(out["a4x2"], plate, args.print_scale)
    brace_a4(out["brace"], brace, args.print_scale)
    drawing(args.drawing, plate, brace)
    for p in list(out.values()) + [args.drawing]:
        print(f"Wrote {p}")


if __name__ == "__main__":
    main()
