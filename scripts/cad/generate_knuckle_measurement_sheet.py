"""Measurement sheet of the front steering knuckle (original part of the T410R as the reference).

The re-engineered knuckle of the running gear follows the original knuckle (photos of the owner, manual
step 15). The sheet shows the dimensions that are missing or uncertain as letters K1 to K20 on three views
of the current model and lists the model values with an empty field for the values measured on the
original part.

* page 1: view along the axle, view along the kingpin axis, section along the axle
* page 2: table K1 to K20 and questions

Usage (from the root directory of the repository):
    python scripts/cad/generate_knuckle_measurement_sheet.py

Output: cad/running_gear/front_corner/steering_knuckle_measurement_sheet.pdf (A4).
Requires cadquery and matplotlib.
"""
import os
import sys
import textwrap

import numpy as np
import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_running_gear as G  # noqa: E402
from generate_measurement_sheets import A4, RED, dimh, dimv, tag  # noqa: E402
from mesh_views import draw_mesh, subdivide  # noqa: E402

OUT = "cad/running_gear/front_corner/steering_knuckle_measurement_sheet.pdf"


def knuckle_local():
    """Knuckle of the front right corner in the frame of the kingpin axis (x along the axle toward the wheel,
    y along the car, z along the kingpin axis, origin in the centre of the outer CVD joint)."""
    p = G.load_params(G.PARAMS)
    c = G.corners(p, G.load_params(G.LOWER))["front"]
    parts, _, _ = G.front_corner(p, G.load_params(G.DRIVE), c)
    R, J = c["R_k"], c["J"]
    return p, G.place(parts["steering knuckle"][1], R.T, -R.T @ J)


def tris(s):
    v, idx = s.tessellate(0.02, 0.15)
    return subdivide(np.array([[q.x, q.y, q.z] for q in v])[np.array(idx)], 0.5)


def view(ax, solid, basis, lim):
    draw_mesh(ax, tris(solid), basis, color=(0.72, 0.74, 0.78), depth_cue=0.25)
    ax.set_xlim(*lim[:2])
    ax.set_ylim(*lim[2:])
    ax.set_aspect("equal")
    ax.axis("off")


def axis_line(ax, a, b):
    ax.plot([a[0], b[0]], [a[1], b[1]], color="#777777", lw=0.5, ls="-.")


def rows(p):
    kz0, kz1, r_boss, r_ring, xr0, xr1, d_lip, r_cup = p["knuckle"]
    sax, say, t_arm, t_web, d2, z_arm = p["steering_arm_ball"]
    return [
        ("K1", "Outer diameter of the bearing ring.", f"{2 * r_ring:g}"),
        ("K2", "Length of the ring along the axle, end face to end face.", f"{xr1 - xr0:g} (model: the ring also "
               "surrounds the joint cup)"),
        ("K3", "Diameter of the bearing seats (bearings 5x10x4, manual step 15). Tight press fit or slip fit?", "10.0"),
        ("K4", "Depth of each bearing seat from the end face of the ring to the lip (outer seat, inner seat).",
               f"{xr1 - 10.0:g} / 4.5 (inner seat open to the joint cup)"),
        ("K5", "Thickness of the lip between the bearings (along the axle).", "1.0"),
        ("K6", "Inner diameter of the lip.", f"{d_lip:g}"),
        ("K7", "Outer diameter of the kingpin bosses.", f"{2 * r_boss:g}"),
        ("K8", "Distance between the end faces of the two bosses (along the kingpin axis).", f"{kz1 - kz0:g}"),
        ("K9", "Bore of the bosses: diameter and depth. Are bushings pressed in (manual: flanged bushings)? "
               "If so: outer diameter, flange diameter and length of a bushing.", "3.1; 2.4 (top) and 2.9 (bottom); "
               "no bushings"),
        ("K10", "Position of the kingpin axis along the axle: inner end face of the ring to the axis of the bosses.",
                f"{-xr0:g} (axis inside the ring)"),
        ("K11", "Offset of the kingpin axis from the axle axis along the car (0 = the axes cross).", "0"),
        ("K12", "Steering arm: kingpin axis to the centre of the outer hole, along the car (square to the axle).",
                f"{-say:g}"),
        ("K13", "Steering arm: kingpin axis to the centre of the outer hole, along the axle (+ toward the wheel).",
                f"{sax - p['kingpin_x']:g} (photo: approx. -4.5; see note)"),
        ("K14", "Distance between the 2 holes of the end tab and their diameters (thread or through hole?).",
                f"{d2:g}; thread M3 (2.5)"),
        ("K15", "Thickness of the arm at the end tab (along the kingpin axis).", f"{t_arm:g}"),
        ("K16", "Height of the gussets between the arm and the ring at the bosses (top to bottom).", f"{t_web:g}"),
        ("K17", "Height of the arm: distance of its middle plane from the axle axis (0 = centred).", f"{z_arm:g}"),
        ("K18", "Width of the end tab around the holes (square to the arm).", "7.0"),
        ("K19", "Ball of the steering link: ball diameter, screw (manual: M3x8 from below with a ball on top), "
                "counterbore of the outer hole (photo).", "on top of the arm, ball 4.8 on a stud M3"),
        ("K20", "Recessed triangle and rib on the faces of the arm (photo): depth of the recess, height and width of "
                "the rib.", "not modelled"),
    ]


def drawing_page(pdf, p, k):
    kz0, kz1, r_boss, r_ring, xr0, xr1, d_lip, r_cup = p["knuckle"]
    sax, say, t_arm, t_web, d2, z_arm = p["steering_arm_ball"]
    bx, by = sax - p["kingpin_x"], say                                    # outer hole (front right: -y toward the middle)
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Measurement sheet: front steering knuckle (2 pieces)", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.945, "Own design, re-engineered from the T410R knuckle. Please measure the original part. "
             "The drawings show the current model. Dimensions in mm.", fontsize=7.5)
    # 1: view along the axle from the outside (horizontal: along the car, arm to the right; vertical: kingpin axis)
    ax = fig.add_axes([0.04, 0.55, 0.5, 0.36])
    view(ax, k, (np.array([-1.0, 0, 0]), np.array([0, -1.0, 0]), np.array([0, 0, 1.0])), (-15, 26, -14, 14))
    axis_line(ax, (0, kz0 - 2), (0, kz1 + 2))
    axis_line(ax, (-9, 0), (-by + 4, 0))
    dimv(ax, -r_ring, r_ring, -8.0, "K1", ext=[(-1, -r_ring), (-1, r_ring)])
    dimv(ax, kz0, kz1, -11.5, "K8", ext=[(-r_boss - 0.5, kz0), (-r_boss - 0.5, kz1)])
    dimh(ax, -r_boss, r_boss, kz1 + 2.2, "K7")
    dimv(ax, z_arm - t_arm / 2, z_arm + t_arm / 2, -by + 5, "K15", side=1)
    dimv(ax, z_arm - t_web / 2, z_arm + t_web / 2, 6.6, "K16", ext=[(6.0, z_arm + t_web / 2)], side=1)
    tag(ax, (0, -d_lip / 2 + 0.2), (-4.5, -9.5), "K6")
    tag(ax, (-by - 6, z_arm), (-by - 4, -8.0), "K17")
    ax.set_title("1  View along the axle from the outside (the wheel side)", fontsize=9, loc="left")
    # 2: view along the kingpin axis from above (horizontal: along the axle; vertical: along the car)
    ax = fig.add_axes([0.56, 0.55, 0.4, 0.36])
    view(ax, k, (np.array([0, 0, -1.0]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0])), (-9, 22, by - 7, 16))
    axis_line(ax, (-6, 0), (xr1 + 3, 0))
    ax.plot(0, 0, "+", color=RED, ms=9, mew=0.9)
    dimh(ax, xr0, xr1, r_ring + 2.5, "K2", ext=[(xr0, r_ring), (xr1, r_ring)])
    dimh(ax, xr0, 0, r_ring + 6.2, "K10", ext=[(0, 1.0)])
    dimv(ax, 0, by, -5.5, "K12", ext=[(-1.5, 0), (bx - 3.5, by)])
    dimh(ax, 0, bx, by - 4.6, "K13", ext=[(0, -2.0), (bx, by - 3.5)], side=-1)
    dimv(ax, by, by + d2, bx + 5.5, "K14", ext=[(bx + 3.5, by), (bx + 3.5, by + d2)], side=1)
    dimh(ax, bx - 3.5, bx + 3.5, by + d2 / 2, "K18")
    tag(ax, (0.3, 0.3), (-6.0, 4.0), "K11")
    ax.set_title("2  View along the kingpin axis from above", fontsize=9, loc="left")
    # 3: section along the axle (plane of the kingpin axis), arm side removed
    ax = fig.add_axes([0.04, 0.12, 0.6, 0.38])
    half = k.cut(cq.Solid.makeBox(60, 60, 60, cq.Vector(-30, -60, -30)))
    view(ax, half, (np.array([0, 1.0, 0]), np.array([1.0, 0, 0]), np.array([0, 0, 1.0])), (-9, 24, -14, 14))
    axis_line(ax, (-7, 0), (xr1 + 4, 0))
    axis_line(ax, (0, kz0 - 2), (0, kz1 + 2))
    dimv(ax, -5.0, 5.0, xr1 + 2.5, "K3", ext=[(xr1, -5.0), (xr1, 5.0)], side=1)
    dimh(ax, 10.0, xr1, 7.6, "K4", ext=[(10.0, 5.0), (xr1, r_ring)])
    dimh(ax, 4.5, 9.0, 7.6, "K4", ext=[(4.5, 5.0)])
    dimh(ax, 9.0, 10.0, -8.6, "K5", ext=[(9.0, -d_lip / 2), (10.0, -d_lip / 2)], side=-1)
    tag(ax, (0, kz1 - 1.0), (4.5, kz1 + 3.0), "K9")
    ax.set_title("3  Section along the axle through the kingpin axis (the arm half is removed)", fontsize=9, loc="left")
    fig.text(0.67, 0.42, "Notes", fontsize=9, fontweight="bold")
    fig.text(0.67, 0.405, "\n".join(textwrap.wrap(
        "In the model the kingpin axis passes through the centre of the outer CVD joint (x = 0), so the ring also "
        "surrounds the joint cup of the axle. On the original part the bosses sit at the inner end of the ring (K10). "
        "The bearings 5x10x4 are pressed in from both ends against the lip. Dash-dot lines: axle axis and kingpin "
        "axis (+). K20: recess and rib on the arm faces (photo), not modelled. K13: on the original the ball lies "
        "inboard of the kingpin axis; with the bellcranks of the model this gives approx. 170 % Ackermann, so the "
        "model places it 1.5 outboard (Ackermann approx. 100 %).", 46)), fontsize=7.2, va="top",
        linespacing=1.4)
    pdf.savefig(fig)
    plt.close(fig)


def table_page(pdf, p):
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Measurement sheet: front steering knuckle, values", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.948, "Model: current value in the model (design or estimate from the photos). Measured: write the "
             "caliper value of the original part. Dimensions in mm.", fontsize=7.5)
    y = 0.925
    for x, head in ((0.05, "No."), (0.11, "What to measure"), (0.6, "Model"), (0.8, "Measured")):
        fig.text(x, y, head, fontsize=7.5, fontweight="bold", va="top")
    y -= 0.02
    for row, (no, text, val) in enumerate(rows(p)):
        lines = textwrap.wrap(text, 72)
        vals = textwrap.wrap(val, 26)
        hgt = 0.0125 * max(len(lines), len(vals), 2) + 0.008
        if row % 2 == 0:
            fig.add_artist(Rectangle((0.04, y - hgt + 0.004), 0.92, hgt, transform=fig.transFigure, fc="#f2f3f5",
                                     ec="none", zorder=0))
        fig.text(0.05, y, no, fontsize=8, fontweight="bold", color=RED, va="top")
        fig.text(0.11, y, "\n".join(lines), fontsize=7.2, va="top", linespacing=1.35)
        fig.text(0.6, y, "\n".join(vals), fontsize=7.2, va="top", linespacing=1.35)
        fig.add_artist(plt.Line2D([0.8, 0.95], [y - hgt + 0.012] * 2, transform=fig.transFigure, color="#999999",
                                  lw=0.5))
        y -= hgt
    fig.text(0.06, y - 0.01, "\n".join(textwrap.wrap(
        "Most important for the fit in the C-hub and the steering geometry: K1, K2, K7, K8, K10, K12, K13 and K17. "
        "A photo of the knuckle from above next to a ruler (at the height of the arm) helps to check K12 to K14.", 110)),
        fontsize=7.5, va="top", linespacing=1.4)
    pdf.savefig(fig)
    plt.close(fig)


def main():
    p, k = knuckle_local()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with PdfPages(OUT) as pdf:
        drawing_page(pdf, p, k)
        table_page(pdf, p)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
