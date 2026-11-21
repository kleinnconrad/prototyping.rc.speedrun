"""Measurement sheet of the front steering knuckle (original part of the T410R as the reference).

The knuckle of the running gear (own design) is based on the original knuckle (photos of the owner, manual
step 15). The sheet shows the dimensions of the original part as letters K1 to K21 on three views of the
current model and lists the model values next to the values measured by the owner (empty field: still
open).

* page 1: view along the axle, view along the kingpin axis, section along the axle
* page 2: table K1 to K21 with the model and the measured values

Usage (from the root directory of the repository):
    python scripts/cad/generate_knuckle_measurement_sheet.py

Output: cad/generic_parts/front_corner/steering_knuckle_measurement_sheet.pdf (A4).
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

OUT = "cad/generic_parts/front_corner/steering_knuckle_measurement_sheet.pdf"


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


def layout(p):
    """Positions along the axle (x, kingpin frame): end of the entry bore, faces of the lip."""
    xr0, xr1 = p["knuckle"][4:6]
    d_seat, t_seat, x_cup, d_kp = p["knuckle_bores"]
    return xr0 + x_cup, xr0 + x_cup + t_seat, xr1 - t_seat


def rows(p):
    """(letter, what to measure, model value, measured value of the owner; empty: open)."""
    kz0, kz1, r_boss, r_ring, xr0, xr1, d_lip, r_cup = p["knuckle"]
    d_seat, t_seat, x_cup, d_kp = p["knuckle_bores"]
    sax, say, t_arm, t_web, d2, z_arm, w_tab = p["steering_arm_ball"]
    xs0, xl0, xl1 = layout(p)
    t_lip = xl1 - xl0
    return [
        ("K1", "Outer diameter of the bearing ring.", f"{2 * r_ring:g}", "14.1"),
        ("K2", "Length of the ring along the axle, end face to end face.", f"{xr1 - xr0:g}", "16.7"),
        ("K3", "Diameter of the bearing seats (bearings 5x10x4, manual step 15). Tight press fit or slip fit?",
               f"{d_seat:.1f} (nominal)", "9.98 (press fit)"),
        ("K4", "Depth of each bearing seat from the end face of the ring to the lip (outer seat, inner seat).",
               f"{t_seat:g} / {t_seat:g} (bearings on the lip)", "4.29 (each seat)"),
        ("K5", "Thickness of the lip between the bearings (along the axle).",
               f"{t_lip:.2f} = K2 - K21 (length) - 2 x K4", "2.33 (calculated by the owner)"),
        ("K6", "Inner diameter of the lip.", f"{d_lip:g}", "lip approx. 1 high"),
        ("K7", "Outer diameter of the kingpin bosses.", f"{2 * r_boss:g}", "7"),
        ("K8", "Distance between the end faces of the two bosses (along the kingpin axis).",
               f"{kz1 - kz0:g} (symmetric to the axle axis)", "21.1"),
        ("K9", "Bore of the bosses: diameter and depth.", f"{d_kp:g}, to the entry bore ({kz1 - r_cup:.2f}); set "
               "screws M3x8 as kingpins", "2.7, depth 4.5"),
        ("K10", "Position of the kingpin axis along the axle: inner end face of the ring to the axis of the bosses.",
                f"{abs(xr0):g}", "0"),
        ("K11", "Offset of the kingpin axis from the axle axis along the car (0 = the axes cross).", "0", ""),
        ("K12", "Steering arm: kingpin axis to the centre of the outer hole, along the car (square to the axle).",
                f"{-say:g}", "25"),
        ("K13", "Steering arm: kingpin axis to the centre of the outer hole, along the axle (+ toward the wheel).",
                f"{sax:g}", "-5 (5 toward the chassis)"),
        ("K14", "Distance between the 2 holes of the end tab and their diameters (thread or through hole?).",
                f"{d2:g}; thread M3 (2.5)", ""),
        ("K15", "Thickness of the arm at the end tab (along the kingpin axis).", f"{t_arm:g}", "4.9"),
        ("K16", "Height of the gussets between the arm and the ring at the bosses (top to bottom).", f"{t_web:g}", ""),
        ("K17", "Height of the arm: distance of its middle plane from the axle axis (0 = centred).", f"{z_arm:g}",
                "0 (in the middle)"),
        ("K18", "Width of the end tab around the holes (square to the arm).", f"{w_tab:g}", "7.4"),
        ("K19", "Ball of the steering link: ball diameter, screw (manual: M3x8 from below with a ball on top), "
                "counterbore of the outer hole (photo).", "on top of the arm, ball 4.8 on a stud M3", ""),
        ("K20", "Recessed triangle and rib on the faces of the arm (photo): depth of the recess, height and width of "
                "the rib.", "not modelled", "not needed (design without function)"),
        ("K21", "Entry bore from the inner end face up to the inner bearing (around the joint cup of the axle): "
                "diameter. The step to the bearing seat holds the end of the CVD drive shaft.",
                f"{2 * r_cup:g}, {xs0 - xr0:g} long", "12.4, 5.79 long"),
    ]


def drawing_page(pdf, p, k):
    kz0, kz1, r_boss, r_ring, xr0, xr1, d_lip, r_cup = p["knuckle"]
    d_seat, t_seat, x_cup, d_kp = p["knuckle_bores"]
    sax, say, t_arm, t_web, d2, z_arm, w_tab = p["steering_arm_ball"]
    wt = w_tab / 2
    xs0, xl0, xl1 = layout(p)
    bx, by = sax, say                                    # outer hole (front right: -y toward the middle)
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Measurement sheet: front steering knuckle (2 pieces)", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.945, "Own design, partly based on the T410R knuckle. The drawings show the current model with "
             "the measured values (page 2).", fontsize=7.5)
    # 1: view along the axle from the outside (horizontal: along the car, arm to the right; vertical: kingpin axis)
    ax = fig.add_axes([0.04, 0.55, 0.5, 0.36])
    view(ax, k, (np.array([-1.0, 0, 0]), np.array([0, -1.0, 0]), np.array([0, 0, 1.0])), (-15, -by + 9, -15, 15))
    axis_line(ax, (0, kz0 - 2), (0, kz1 + 2))
    axis_line(ax, (-9, 0), (-by + 4, 0))
    dimv(ax, -r_ring, r_ring, -8.0, "K1", ext=[(-1, -r_ring), (-1, r_ring)])
    dimv(ax, kz0, kz1, -11.5, "K8", ext=[(-r_boss - 0.5, kz0), (-r_boss - 0.5, kz1)])
    dimh(ax, -r_boss, r_boss, kz1 + 2.2, "K7")
    dimv(ax, z_arm - t_arm / 2, z_arm + t_arm / 2, -by + wt + 2.0, "K15", side=1)
    dimv(ax, z_arm - t_web / 2, z_arm + t_web / 2, 6.6, "K16", ext=[(6.0, z_arm + t_web / 2)], side=1)
    tag(ax, (0, -d_lip / 2 + 0.2), (-4.5, -9.5), "K6")
    tag(ax, (-by - 6, z_arm), (-by - 4, -8.0), "K17")
    ax.set_title("1  View along the axle from the outside (the wheel side)", fontsize=9, loc="left")
    # 2: view along the kingpin axis from above (horizontal: along the axle; vertical: along the car)
    ax = fig.add_axes([0.56, 0.55, 0.4, 0.36])
    view(ax, k, (np.array([0, 0, -1.0]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0])), (bx - wt - 6, 22, by - 7, 16))
    axis_line(ax, (-6, 0), (xr1 + 3, 0))
    ax.plot(0, 0, "+", color=RED, ms=9, mew=0.9)
    dimh(ax, xr0, xr1, r_ring + 2.5, "K2", ext=[(xr0, r_ring), (xr1, r_ring)])
    dimh(ax, xr0, 0, r_ring + 6.2, "K10", ext=[(0, 1.0)])
    dimv(ax, 0, by, bx - wt - 2.0, "K12", ext=[(-1.5, 0), (bx - wt, by)])
    dimh(ax, 0, bx, by - wt - 1.5, "K13", ext=[(0, -2.0), (bx, by - wt)], side=-1)
    dimv(ax, by, by + d2, bx + wt + 2.0, "K14", ext=[(bx + wt, by), (bx + wt, by + d2)], side=1)
    dimh(ax, bx - wt, bx + wt, by + d2 / 2, "K18")
    tag(ax, (0.3, 0.3), (-6.0, 4.0), "K11")
    ax.set_title("2  View along the kingpin axis from above", fontsize=9, loc="left")
    # 3: section along the axle (plane of the kingpin axis), arm side removed
    ax = fig.add_axes([0.04, 0.12, 0.6, 0.38])
    half = k.cut(cq.Solid.makeBox(60, 60, 60, cq.Vector(-30, -60, -30)))
    view(ax, half, (np.array([0, 1.0, 0]), np.array([1.0, 0, 0]), np.array([0, 0, 1.0])), (-9, 24, -14, 14))
    axis_line(ax, (-7, 0), (xr1 + 4, 0))
    axis_line(ax, (0, kz0 - 2), (0, kz1 + 2))
    dimv(ax, -d_seat / 2, d_seat / 2, xr1 + 2.5, "K3", ext=[(xr1, -d_seat / 2), (xr1, d_seat / 2)], side=1)
    dimh(ax, xl1, xr1, r_ring + 0.6, "K4", ext=[(xl1, d_seat / 2), (xr1, r_ring)])
    dimh(ax, xs0, xl0, r_ring + 0.6, "K4", ext=[(xs0, d_seat / 2), (xl0, d_seat / 2)])
    dimh(ax, xl0, xl1, -r_ring - 0.6, "K5", ext=[(xl0, -d_lip / 2), (xl1, -d_lip / 2)], side=-1)
    dimv(ax, -r_cup, r_cup, xs0 / 2, "K21", side=1)
    tag(ax, (0, kz1 - 1.0), (4.5, kz1 + 3.0), "K9")
    ax.set_title("3  Section along the axle through the kingpin axis (the arm half is removed)", fontsize=9, loc="left")
    fig.text(0.67, 0.42, "Notes", fontsize=9, fontweight="bold")
    fig.text(0.67, 0.405, "\n".join(textwrap.wrap(
        "The kingpin axis lies on the inner end face of the ring (K10 = 0) and passes through the centre of the "
        "outer CVD joint. From the inner end face the entry bore (K21) surrounds the joint cup of the axle up to "
        "the inner bearing; the bearings 5x10x4 are pressed in from both ends against the lip. Kingpins: set "
        "screws M3x8 threaded into the bores of the bosses (K9), they turn with the knuckle in the C-hub. "
        "Dash-dot lines: axle axis and kingpin axis (+). K5 cannot be measured: it is the rest of K2 after the "
        "entry bore (K21, section of the joint cup) and the two bearing seats (K4): 16.7 - 5.79 - 2 x 4.29 = 2.33. "
        "Still open: K11, K14, K16 and K19.", 46)), fontsize=7.2,
        va="top",
        linespacing=1.4)
    pdf.savefig(fig)
    plt.close(fig)


def table_page(pdf, p):
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Measurement sheet: front steering knuckle, values", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.948, "Model: current value in the model. Measured: caliper value of the original part (owner); "
             "an empty field is still open. Dimensions in mm.", fontsize=7.5)
    y = 0.925
    for x, head in ((0.05, "No."), (0.11, "What to measure"), (0.6, "Model"), (0.8, "Measured")):
        fig.text(x, y, head, fontsize=7.5, fontweight="bold", va="top")
    y -= 0.02
    for row, (no, text, val, meas) in enumerate(rows(p)):
        lines = textwrap.wrap(text, 72)
        vals = textwrap.wrap(val, 26)
        meas_l = textwrap.wrap(meas, 20)
        hgt = 0.0125 * max(len(lines), len(vals), len(meas_l), 2) + 0.008
        if row % 2 == 0:
            fig.add_artist(Rectangle((0.04, y - hgt + 0.004), 0.92, hgt, transform=fig.transFigure, fc="#f2f3f5",
                                     ec="none", zorder=0))
        fig.text(0.05, y, no, fontsize=8, fontweight="bold", color=RED, va="top")
        fig.text(0.11, y, "\n".join(lines), fontsize=7.2, va="top", linespacing=1.35)
        fig.text(0.6, y, "\n".join(vals), fontsize=7.2, va="top", linespacing=1.35)
        if meas:
            fig.text(0.8, y, "\n".join(meas_l), fontsize=7.2, va="top", linespacing=1.35, color="#1f5fa8")
        else:
            fig.add_artist(plt.Line2D([0.8, 0.95], [y - hgt + 0.012] * 2, transform=fig.transFigure, color="#999999",
                                      lw=0.5))
        y -= hgt
    fig.text(0.06, y - 0.01, "\n".join(textwrap.wrap(
        "The measured values are applied to the model; K3 is modelled with the nominal 10.0 (press fit of the bearings), "
        "K6 as 8.0 (lip approx. 1 high), K5 is calculated. Still open: K11, K14, K16 and K19.", 110)),
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
