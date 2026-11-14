"""Measurement sheet of the stock parts that are not measured yet (wishbones, bearing seat of the motor mount).

The sheet shows each caliper measurement as a dimension line with a letter on drawings of the
models, explains how to measure it and lists the current value of the model with an empty field
for the measured value. The stock parts are not part of the speedrun design.

* page 1: front wishbone (plan view and side view)
* page 2: rear wishbone (plan view and side view)
* page 3: table of the wishbone measurements A to T
* page 4: bearing seat of the motor mount (MM1 to MM7)

Usage (from the root directory of the repository):
    python scripts/cad/generate_measurement_sheets.py

Output: cad/stock_parts/stock_parts_measurement_sheet.pdf (A4). Requires cadquery and matplotlib.
"""
import os
import sys
import textwrap

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_bulkhead_lower import load_params  # noqa: E402
from generate_wishbones import PARAMS as ARM_PARAMS, arm_solid, tess  # noqa: E402
from mesh_views import draw_mesh, subdivide  # noqa: E402

OUT = "cad/stock_parts/stock_parts_measurement_sheet.pdf"
DRIVE = "cad/stock_parts/driveshaft/driveshaft_parameters.json"
RED = "#b42318"
A4 = (8.27, 11.69)


def letter(ax, x, y, text, fs=8):
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=RED, fontweight="bold",
            bbox=dict(boxstyle="circle,pad=0.2" if len(text) == 1 else "round,pad=0.2", fc="white", ec=RED, lw=0.8),
            zorder=10)


def dimh(ax, x0, x1, y, text, ext=(), side=1):
    """Horizontal dimension from x0 to x1 on the line y; ext: (x, y_from) of the extension lines."""
    for xe, ye in ext:
        ax.plot([xe, xe], [ye, y + side * 0.8], color=RED, lw=0.5)
    ax.annotate("", (x0, y), (x1, y), arrowprops=dict(arrowstyle="<|-|>", lw=0.7, color=RED, shrinkA=0, shrinkB=0,
                                                      mutation_scale=7))
    letter(ax, (x0 + x1) / 2, y + side * 1.6, text)


def dimv(ax, y0, y1, x, text, ext=(), side=-1):
    """Vertical dimension from y0 to y1 on the line x; ext: (x_from, y) of the extension lines."""
    for xe, ye in ext:
        ax.plot([xe, x + side * 0.8], [ye, ye], color=RED, lw=0.5)
    ax.annotate("", (x, y0), (x, y1), arrowprops=dict(arrowstyle="<|-|>", lw=0.7, color=RED, shrinkA=0, shrinkB=0,
                                                      mutation_scale=7))
    letter(ax, x + side * 1.8, (y0 + y1) / 2, text)


def tag(ax, xy, to, text):
    ax.annotate("", xy, to, arrowprops=dict(arrowstyle="-|>", lw=0.6, color=RED, mutation_scale=7))
    letter(ax, to[0], to[1], text)


def arm_page(pdf, p, kind, solid):
    fig = plt.figure(figsize=A4)
    name = "Front wishbone (End A, 2 pieces)" if kind == "front" else "Rear wishbone (End B, 2 pieces)"
    fig.text(0.06, 0.965, f"Measurement sheet: {name}", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.945, "Stock part of the Carten T410R (NHA402), not part of the speedrun design. Dimensions in mm. "
             "The drawing is the current model (estimate from the photos).", fontsize=7.5)
    length, half = p[f"{kind}_arm_length"], p["inner_width"] / 2
    yi, yo = p[f"{kind}_rail_y"]
    b0, b1 = p[f"{kind}_inner_bar_x"]
    c0, c1 = p[f"{kind}_cross_x"]
    q0, q1 = p[f"{kind}_shock_plate_x"]
    z0, z1 = p["shock_plate_z"]
    gap, lo = p[f"{kind}_outer_gap"], p[f"{kind}_outer_lug_len"]
    dx, dy, h = p["droop_x"], p[f"{kind}_droop_y"], p["rail_h"] / 2
    t = subdivide(tess(solid), 1.0)
    grey = (0.72, 0.74, 0.78)
    # plan view
    ax = fig.add_axes([0.04, 0.47, 0.92, 0.45])
    draw_mesh(ax, t, "top", color=grey, depth_cue=0.25)
    ax.plot([-4, length + 4], [0, 0], color="#777777", lw=0.5, ls="-.")
    ax.plot([0, 0], [-half - 2, half + 2], color="#777777", lw=0.5, ls="-.")
    ax.plot([length, length], [-yo - 2, yo + 2], color="#777777", lw=0.5, ls="-.")
    dimv(ax, -half, half, -9, "A", ext=[(-3, -half), (-3, half)])
    dimv(ax, half - p["inner_lug_len"], half, -5, "B", ext=[(-3, half - p["inner_lug_len"])])
    dimh(ax, 0, length, -half - 7, "J", ext=[(0, -half), (length, -gap / 2 - lo)], side=-1)
    dimh(ax, 0, dx, -half - 3.5, "H", ext=[(dx, -dy)], side=-1)
    dimv(ax, 0, -dy, dx + 0.0, "I", side=1)
    dimh(ax, 0, b0, 2.5, "G")
    dimh(ax, 0, c0, half + 4, "P", ext=[(0, half), (c0, yi)])
    xe = (c1 + length) / 2 if kind == "front" else (b1 + c0) / 2 + 4
    dimv(ax, -yo, yo, xe, "E", side=1)
    xf = (b1 + c0) / 2 - 3
    dimv(ax, yi, yo, xf, "F", side=1)
    dimv(ax, -gap / 2, gap / 2, length + 9, "O", ext=[(length, -gap / 2), (length, gap / 2)], side=1)
    dimv(ax, gap / 2, gap / 2 + lo, length + 5, "M", ext=[(length + 3, gap / 2 + lo)], side=1)
    if kind == "front":
        l0, l1, ly, _ = p["front_loop"]
        dimh(ax, length, length + l1, -ly - 3, "T", ext=[(length + l1, -ly)], side=-1)
    ax.text(-12, -half - 12.5, "Plan view from above. Rail A (with the octagonal shock plate) at the bottom, rail B (sway "
            "bar holes) at the top.\nInner hinge pin on the left, outer hinge pin on the right (dash-dot lines: pin axes "
            "and middle of the arm).", fontsize=7, va="top")
    ax.set_xlim(-14, length + 14)
    ax.set_ylim(-half - 16, half + 9)
    ax.set_aspect("equal")
    ax.axis("off")
    # side view, rail A
    ax2 = fig.add_axes([0.04, 0.2, 0.92, 0.25])
    draw_mesh(ax2, t, "end_outer", color=grey, depth_cue=0.25)
    ax2.plot([-6, length + 6], [0, 0], color="#777777", lw=0.5, ls="-.")
    dimv(ax2, -p["inner_lug_d"] / 2, p["inner_lug_d"] / 2, -6, "C", ext=[(0, -3), (0, 3)])
    dimv(ax2, -h, h, (b1 + q0) / 2 - 6, "D", side=1)
    dimv(ax2, -p["outer_lug_d"] / 2, p["outer_lug_d"] / 2, length + 6, "L",
         ext=[(length, -p["outer_lug_d"] / 2), (length, p["outer_lug_d"] / 2)], side=1)
    tag(ax2, (length, p["outer_pin_z"]), (length + 4, z1 + 1), "K")
    tag(ax2, (length - 1.5, p["outer_pin_z"]), (length - 6, z0 - 1.5), "N")
    dimh(ax2, q0, q1, z1 + 2, "Q", ext=[(q0, z1 - 1.5), (q1, z1 - 1.5)])
    dimv(ax2, z0, z1, q1 + 3.5, "Q", ext=[(q1 - 1.5, z0), (q1 - 1.5, z1)], side=1)
    hx, hz = p[f"{kind}_shock_holes"][0]
    for x, z in p[f"{kind}_shock_holes"]:
        ax2.plot(x, z, "+", color=RED, ms=7, mew=0.8)
    dimh(ax2, 0, hx, z0 - 2.5, "R", ext=[(0, -3), (hx, hz)], side=-1)
    for x, z in p[f"{kind}_sway_holes"]:
        ax2.add_patch(Circle((x, z), p["ball_tap_d"] / 2, fill=False, ec=RED, lw=0.7, ls="--"))
    sx = p[f"{kind}_sway_holes"][0][0]
    tag(ax2, (sx, 1.3), (sx - 4, z1 + 1), "S")
    ax2.text(-12, z0 - 5.5, "Side view of rail A. R: holes of the shock ball stud (+). S: holes of the sway bar ball "
             "stud in rail B (dashed, behind).\nK: diameter of the outer hinge pin. N: height of the outer pin axis above "
             "the inner pin axis (0 = same height).", fontsize=7, va="top")
    ax2.set_xlim(-14, length + 14)
    ax2.set_ylim(z0 - 9, z1 + 4.5)
    ax2.set_aspect("equal")
    ax2.axis("off")
    fig.text(0.06, 0.05, "All x values: distance from the axis of the inner hinge pin toward the wheel. All z values: "
             "height above the axis of the inner hinge pin.\nHole positions: measure from the edge of the bore of the "
             "inner hinge pin to the edge of the hole and add half of both diameters.\nThe instructions for each letter "
             "are on page 3. Write the values in the table on page 3.", fontsize=7.5, va="bottom")
    pdf.savefig(fig)
    plt.close(fig)


ARM_ROWS = [
    ("A", "Length along the inner hinge pin over the outer faces of the two inner lugs.", "inner_width", None),
    ("B", "Length of one inner lug along the hinge pin.", "inner_lug_len", None),
    ("C", "Outer diameter of the inner lugs.", "inner_lug_d", None),
    ("D", "Height of the side rails (top face to bottom face).", "rail_h", None),
    ("E", "Width over the outer faces of the two side rails.", "{k}_rail_y", "E"),
    ("F", "Width of one side rail.", "{k}_rail_y", "F"),
    ("G", "Inner pin axis to the inner cross bar at the end of the notch between the inner lugs (start).",
     "{k}_inner_bar_x", 0),
    ("H", "Inner pin axis to the axis of the droop screw bosses (M4 thread).", "droop_x", None),
    ("I", "Middle of the arm to the axis of a droop screw boss (or: distance of the two axes / 2).", "{k}_droop_y", None),
    ("J", "Inner pin axis to outer pin axis: outer edges of the two bores minus one bore diameter.", "{k}_arm_length",
     None),
    ("K", "Diameter of the outer hinge pin (or of the bore of the outer lugs).", "outer_pin_d", None),
    ("L", "Outer diameter of the outer lugs.", "outer_lug_d", None),
    ("M", "Length of one outer lug along the outer hinge pin.", "{k}_outer_lug_len", None),
    ("N", "Arm on a flat surface: height of the outer pin axis minus height of the inner pin axis.", "outer_pin_z",
     None),
    ("O", "Gap between the two outer lugs.", "{k}_outer_gap", None),
    ("P", "Inner pin axis to the outer cross bar (start of the cross bar).", "{k}_cross_x", 0),
    ("Q", "Octagonal shock plate: inner pin axis to its start and to its end (x); how far it reaches above and below "
     "the inner pin axis (z).", "{k}_shock_plate_x", "Q"),
    ("R", "Each hole of the shock ball stud: x and z of its centre.", "{k}_shock_holes", None),
    ("S", "Each hole of the sway bar ball stud in rail B: x and z of its centre.", "{k}_sway_holes", None),
    ("T", "Front arm only: outer pin axis to the outer edge of the thin loop beyond the outer lugs; width of the loop.",
     "front_loop", "T"),
]


def fmt(v):
    if isinstance(v, list):
        return "  ".join(f"({fmt(x)})" for x in v) if isinstance(v[0], list) else " / ".join(fmt(x) for x in v)
    return f"{v:g}"


def model_value(p, key, mode, k):
    if "{k}" not in key and k == "rear" and key.startswith("front"):
        return "-"
    v = p[key.format(k=k)]
    if mode == "E":
        return fmt(2 * v[1])
    if mode == "F":
        return fmt(round(v[1] - v[0], 2))
    if mode == "Q":
        return f"x {fmt(v)}; z {fmt(p['shock_plate_z'])}"
    if mode == "T":
        return f"{fmt(v[1])}; width {fmt(2 * v[2])}"
    if isinstance(mode, int):
        return fmt(v[mode])
    return fmt(v)


def table_page(pdf, p):
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Measurement sheet: wishbones, values", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.948, "Model: current value in the model (estimate). Measured: write the caliper value. "
             "Dimensions in mm.", fontsize=7.5)
    cols = [(0.05, "Letter"), (0.1, "What to measure"), (0.52, "Front: model"), (0.63, "Front: measured"),
            (0.75, "Rear: model"), (0.85, "Rear: measured")]
    y = 0.925
    for x, head in cols:
        fig.text(x, y, head, fontsize=7.5, fontweight="bold", va="top")
    y -= 0.018
    for row, (let, text, key, mode) in enumerate(ARM_ROWS):
        lines = textwrap.wrap(text, 58)
        vals = [textwrap.wrap(model_value(p, key, mode, k), 14) for k in ("front", "rear")]
        n = max(len(lines), len(vals[0]), len(vals[1]), 2)
        hgt = 0.0125 * n + 0.008
        if row % 2 == 0:
            fig.add_artist(Rectangle((0.04, y - hgt + 0.004), 0.92, hgt, transform=fig.transFigure, fc="#f2f3f5",
                                     ec="none", zorder=0))
        fig.text(0.06, y, let, fontsize=8.5, fontweight="bold", color=RED, va="top")
        fig.text(0.1, y, "\n".join(lines), fontsize=7.2, va="top", linespacing=1.35)
        fig.text(0.52, y, "\n".join(vals[0]), fontsize=7.2, va="top", linespacing=1.35)
        fig.text(0.75, y, "\n".join(vals[1]), fontsize=7.2, va="top", linespacing=1.35)
        for x in (0.63, 0.85):
            fig.add_artist(plt.Line2D([x, x + 0.09], [y - hgt + 0.012] * 2, transform=fig.transFigure, color="#999999",
                                      lw=0.5))
        y -= hgt
    fig.text(0.06, y - 0.01, "Also please answer: does the octagonal shock plate reach equally far above and below the "
             "side rail? (Q: write both values.)\nIf not everything can be measured: J, A, O and Q are the most "
             "important values for the fit on the car.", fontsize=7.5, va="top")
    pdf.savefig(fig)
    plt.close(fig)


def motor_mount_page(pdf, d):
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Measurement sheet: bearing seat of the motor mount (NBA201)", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.945, "Stock part, not part of the speedrun design. Bearing NBA298 5x10x4 (manual step 5). "
             "Dimensions in mm.", fontsize=7.5)
    z = 2.0 + 17.2
    low, cap_h, cap_w = d["mount_low_top"], d["cap_h"], d["cap_w"]
    xa, xs = d["mount_x"][0], d["mount_step_x"]
    t = d["mount_t"]
    rb = d["mount_bearing"][1] / 2
    # view along the pinion shaft
    ax = fig.add_axes([0.05, 0.5, 0.5, 0.42])
    ax.add_patch(Rectangle((-16, 0), 40, 2.0, fc="#555555", ec="k", lw=0.6))                       # chassis plate
    body = [(xa, 2), (xs + 6, 2), (xs + 6, low), (rb, low), (rb, z), (-rb, z), (-rb, low), (xa, low)]
    ax.add_patch(Polygon(body, closed=True, fc="#c9ccd2", ec="k", lw=0.8))
    ang = np.linspace(np.pi, 2 * np.pi, 40)
    ax.add_patch(Polygon(np.c_[rb * np.cos(ang), z + rb * np.sin(ang)].tolist() + [(rb, z), (-rb, z)], closed=True,
                         fc="white", ec="none"))
    ax.add_patch(Circle((0, z), rb, fc="#e8d9b8", ec="k", lw=0.8))                                  # bearing
    ax.add_patch(Circle((0, z), d["mount_bearing"][0] / 2, fc="white", ec="k", lw=0.6))
    ax.add_patch(Rectangle((-cap_w / 2, low), cap_w, cap_h, fc="#9aa3ad", ec="k", lw=0.8))           # cap
    ax.text(0, low + cap_h / 2, "cap", ha="center", va="center", fontsize=7)
    ax.text(xa + 1, 5, "motor mount\n(low part)", fontsize=7, va="bottom")
    ax.text(-15.5, 0.4, "chassis plate", fontsize=6.5, color="white")
    dimh(ax, -rb, rb, z - rb - 3, "MM1", side=-1)
    dimv(ax, z - rb, low, -rb - 4, "MM2", ext=[(-rb, z - rb), (xa + 2, low)])
    dimv(ax, 2, low, xa - 3, "MM3", ext=[(xa, low)])
    dimv(ax, low, low + cap_h, cap_w / 2 + 3, "MM4", ext=[(cap_w / 2, low), (cap_w / 2, low + cap_h)], side=1)
    tag(ax, (0, z + rb + 0.2), (8, low + cap_h + 4), "MM5")
    ax.set_xlim(-18, 27)
    ax.set_ylim(-2, low + cap_h + 8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("View along the pinion shaft", fontsize=9, loc="left")
    # section through the seat along the shaft
    ax2 = fig.add_axes([0.6, 0.5, 0.36, 0.42])
    ax2.add_patch(Rectangle((-t / 2, 2), t, low - 2, fc="#c9ccd2", ec="k", lw=0.8))
    ax2.add_patch(Rectangle((-t / 2, z - rb), t, low - (z - rb), fc="white", ec="none"))
    bw = d["mount_bearing"][2]
    ax2.add_patch(Rectangle((-bw / 2, z - rb), bw, 2 * rb, fc="#e8d9b8", ec="k", lw=0.8))
    ax2.add_patch(Rectangle((-t / 2, low), t, cap_h, fc="#9aa3ad", ec="k", lw=0.8))
    ax2.plot([-t / 2 - 3, t / 2 + 3], [z, z], color="#777777", lw=0.5, ls="-.")
    dimh(ax2, -t / 2, t / 2, 2 - 2.5, "MM6", side=-1)
    tag(ax2, (t / 2 - 0.4, z - rb + 1), (t / 2 + 4, z - rb - 3), "MM7")
    ax2.set_xlim(-10, 10)
    ax2.set_ylim(-4, low + cap_h + 8)
    ax2.set_aspect("equal")
    ax2.axis("off")
    ax2.set_title("Section along the shaft", fontsize=9, loc="left")
    rows = [("MM1", "Width of the U notch (bearing seat).", f"{2 * rb:g}"),
            ("MM2", "Depth of the U notch: top face of the low part to the bottom of the U.", f"{low - (z - rb):.1f}"),
            ("MM3", "Height of the low part: bottom face of the motor mount to its top face (below the cap).", f"{low - 2:.1f}"),
            ("MM4", "Height of the cap.", f"{cap_h:g}"),
            ("MM5", "Does the cap touch the bearing? If not: gap between the bearing and the cap.", "0.4 gap"),
            ("MM6", "Thickness of the motor mount at the bearing seat (along the shaft).", f"{t:g}"),
            ("MM7", "Is there a step (shoulder) in the seat beside the bearing? On which side: spur gear or cup joint? "
                    "Diameter of the smaller bore and width of the seat.", "no step"),
            ("MM8", "Where does the set screw M3x3 of the cap go, and what does it press on?", "-")]
    y = 0.44
    fig.text(0.06, y, "No.", fontsize=7.5, fontweight="bold", va="top")
    fig.text(0.13, y, "What to measure", fontsize=7.5, fontweight="bold", va="top")
    fig.text(0.7, y, "Model", fontsize=7.5, fontweight="bold", va="top")
    fig.text(0.8, y, "Measured", fontsize=7.5, fontweight="bold", va="top")
    y -= 0.02
    for no, text, val in rows:
        lines = textwrap.wrap(text, 75)
        hgt = 0.0125 * max(len(lines), 2) + 0.008
        fig.text(0.06, y, no, fontsize=8, fontweight="bold", color=RED, va="top")
        fig.text(0.13, y, "\n".join(lines), fontsize=7.2, va="top", linespacing=1.35)
        fig.text(0.7, y, val, fontsize=7.2, va="top")
        fig.add_artist(plt.Line2D([0.8, 0.94], [y - hgt + 0.012] * 2, transform=fig.transFigure, color="#999999",
                                  lw=0.5))
        y -= hgt
    pdf.savefig(fig)
    plt.close(fig)


def main():
    p = load_params(ARM_PARAMS)
    with PdfPages(OUT) as pdf:
        for kind in ("front", "rear"):
            arm_page(pdf, p, kind, arm_solid(p, kind))
        table_page(pdf, p)
        motor_mount_page(pdf, load_params(DRIVE))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
