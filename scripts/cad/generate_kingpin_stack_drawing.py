"""Explanation picture of the kingpins of the front C-hub: brass spacer sleeves and washers M3 (owner, 2026-11-22).

Section through the kingpin axis of the front right corner (plane of the kingpin axis and the axle), read from the
assembly STEP file: C-hub, steering knuckle, washers, sleeves, screw M3x8 (bottom) and ball stud of the camber link
(top). Left: the corner; right: details of the upper and the lower kingpin with the values from the parameter file.
The parts to buy (sleeves and washers) are marked.

Run from the root directory of the repository, after scripts/cad/generate_speedrun_assembly.py:
    python scripts/cad/generate_kingpin_stack_drawing.py
Output: cad/generic_parts/front_corner/kingpin_sleeves_and_washers.png
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.path import Path  # noqa: E402
from matplotlib.patches import PathPatch, Rectangle  # noqa: E402
import cadquery as cq  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_assembly_drawing as AD  # noqa: E402
import technical_drawing as TD  # noqa: E402
import palette as P  # noqa: E402
from generate_bulkhead_lower import load_params  # noqa: E402

ASSEMBLY = "cad/assembly/speedrun_chassis_T410R.step"
PARAMS = "cad/generic_parts/running_gear_parameters.json"
OUT = "cad/generic_parts/front_corner/kingpin_sleeves_and_washers.png"
BUY = "#c2410c"                       # annotation colour of the parts to buy (annotations keep their own colours)
TXT = "#1f2933"
# parts of the front right corner in the section: (start of the name in the assembly, colour key, legend text)
PARTS = [("running_gear_C-hub", "spring", "C-hub (printed part, fixed on the wishbone)"),
         ("running_gear_steering_knuckle", "upright", "steering knuckle (turns about the kingpin axis)"),
         ("running_gear_kingpin_washers", "drive", "washer M3 DIN 125-A (to buy)"),
         ("running_gear_guide_sleeves", "battery", "brass spacer sleeve (to buy)"),
         ("running_gear_kingpins", "link", "screw M3x8 (bottom), ball stud of the camber link (top)"),
         ("running_gear_axle_with_joint_cup", "ghost", "axle and wheel bearings (for orientation)"),
         ("running_gear_wheel_bearings_5x10x4", "ghost", None)]


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def closest_point(p1, d1, p2, d2):
    """Point on line 1 closest to line 2."""
    w = p1 - p2
    a, b, c, d, e = d1 @ d1, d1 @ d2, d2 @ d2, d1 @ w, d2 @ w
    t = (b * e - c * d) / (a * c - b * b)
    return p1 + t * d1


def kingpin_frame(parts):
    """Origin (kingpin axis at the height of the axle), x toward the wheel (axle direction square to the axis),
    z along the kingpin axis (up)."""
    pk, kd = AD.cylinder_axis(AD.part(parts, "running_gear_kingpins", "A", "right"))
    pa, ad = AD.cylinder_axis(AD.part(parts, "running_gear_axle_with_joint_cup", "A", "right"))
    kd = kd if kd[2] > 0 else -kd
    xd = unit(ad - (ad @ kd) * kd)
    xd = xd if xd[0] > 0 else -xd
    return closest_point(pk, kd, pa, ad), xd, kd


def section_rings(shape, origin, xd, kd):
    """Cut faces of a part in the plane of x and z: list of faces, each a list of rings (outer first) in (x, z)."""
    n = np.cross(xd, kd)
    plane = cq.Face.makePlane(300, 300, cq.Vector(*origin), cq.Vector(*n))
    cut = shape.intersect(plane)
    view = TD.View(np.cross(xd, kd), xd, (0.0, 0.0), origin, 1.0)       # paper x = xd, paper y = kd
    out = []
    for f in cut.Faces():
        rings = []
        for i, w in enumerate([f.outerWire()] + f.innerWires()):
            p = TD.wire_polygon(w, view)
            if len(p) < 3:
                continue
            a = TD.signed_area(p)
            if (i == 0 and a < 0) or (i > 0 and a > 0):
                p = p[::-1]
            rings.append(p)
        if rings:
            out.append(rings)
    return out


def fill(ax, faces, color):
    for rings in faces:
        verts, codes = [], []
        for p in rings:
            verts += list(p) + [p[0]]
            codes += [Path.MOVETO] + [Path.LINETO] * (len(p) - 1) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), facecolor=color, edgecolor="k", lw=0.6, zorder=2))


def label(ax, xy, xytext, text, buy=False, ha="left"):
    kw = dict(fontsize=9, color=BUY if buy else TXT, ha=ha, va="center",
              arrowprops=dict(arrowstyle="-", lw=0.8, color=BUY if buy else "0.25", shrinkA=0, shrinkB=0))
    if buy:
        kw["fontweight"] = "bold"
        kw["bbox"] = dict(boxstyle="round,pad=0.3", fc="white", ec=BUY, lw=1.2)
    ax.annotate(text, xy, xytext, zorder=8, **kw)


def vdim(ax, x, z0, z1, text, tx, tz=None):
    """Distance along the kingpin axis: arrows between z0 and z1 at x; text at (tx, tz), with a leader from the
    middle of the arrows when the text is placed away from them."""
    zm = (z0 + z1) / 2
    ax.annotate("", (x, z0), (x, z1), arrowprops=dict(arrowstyle="<|-|>", lw=0.7, color=TXT, mutation_scale=7,
                                                        shrinkA=0, shrinkB=0), zorder=7)
    if tz is None:
        ax.text(tx, zm, text, fontsize=8.5, color=TXT, ha="left", va="center", zorder=7)
    else:
        ax.annotate(text, (x, zm), (tx, tz), fontsize=8.5, color=TXT, ha="left", va="center", zorder=7,
                    arrowprops=dict(arrowstyle="-", lw=0.6, color="0.45", shrinkA=0, shrinkB=0))


def main():
    p = load_params(PARAMS)
    kz0, kz1, r_boss = p["knuckle"][:3]
    d_sl, d_in, l_sl, d_w, t_w, h_d, h_h, d_bore = p["guide_sleeve"]
    gap = p["front_c_hub"][3]
    proud = p["guide_sleeve_proud"]
    zst, zsb = kz1 + t_w + l_sl, kz0 - t_w - l_sl                  # outer ends of the sleeves
    parts = AD.read_named_solids(ASSEMBLY)
    origin, xd, kd = kingpin_frame(parts)
    sec = [(section_rings(AD.part(parts, start, "A", "right"), origin, xd, kd), P.rgb(key), text)
           for start, key, text in PARTS]

    fig = plt.figure(figsize=(16.5, 11.0))
    fig.patch.set_facecolor("white")
    ax0 = fig.add_axes([0.02, 0.13, 0.40, 0.74])
    ax1 = fig.add_axes([0.45, 0.52, 0.53, 0.35])
    ax2 = fig.add_axes([0.45, 0.13, 0.53, 0.35])
    for ax in (ax0, ax1, ax2):
        for faces, color, _ in sec:
            fill(ax, faces, color)
        ax.plot([0, 0], [-40, 40], color="0.35", lw=0.7, ls=(0, (8, 2, 2, 2)), zorder=6)
        ax.set_aspect("equal")
        ax.axis("off")

    # corner
    ax0.set_xlim(-13.0, 19.0)
    ax0.set_ylim(-19.5, 23.5)
    ax0.text(0.3, 22.6, "kingpin axis", fontsize=8.5, color="0.3")
    ax0.set_title("Section through the kingpin axis (front right corner, seen from the rear of the car)",
                  fontsize=10.5, loc="left", color=TXT)
    for z0, z1 in ((kz1 - 1.0, zst + 6.5), (zsb - 3.6, kz0 + 1.0)):
        ax0.add_patch(Rectangle((-6.2, z0), 12.4, z1 - z0, fc="none", ec=BUY, lw=0.9, ls="--", zorder=7))
    ax0.text(-6.0, zst + 6.9, "detail top", fontsize=8.5, color=BUY)
    ax0.text(-6.0, zsb - 4.4, "detail bottom", fontsize=8.5, color=BUY)

    # detail top: ball stud clamps the top sleeve and washer to the upper boss
    ax1.set_xlim(-13.0, 24.0)
    ax1.set_ylim(kz1 - 1.6, zst + 6.8)
    ax1.set_title("Detail top: the ball stud of the camber link clamps sleeve and washer to the knuckle",
                  fontsize=10.5, loc="left", color=TXT)
    label(ax1, (-d_sl / 2 + 0.25, kz1 + t_w + l_sl * 0.55), (-12.5, zst + 2.6),
          f"to buy: brass spacer sleeve\nØ{d_sl:g} x Ø{d_in:g} x {l_sl:g} mm", buy=True)
    label(ax1, (-d_w / 2 + 0.35, kz1 + t_w / 2), (-12.5, kz1 - 0.6),
          f"to buy: washer M3 DIN 125-A\nØ{d_in:g} x Ø{d_w:g} x {t_w:g} mm", buy=True)
    label(ax1, (r_boss - 0.8, kz1 - 0.5), (8.5, kz1 - 0.9), "boss of the knuckle (turns)")
    label(ax1, (d_bore / 2 + 0.6, zst - proud - 0.6), (8.5, zst + 0.9), f"C-hub: bore Ø{d_bore:g}, no counterbore (fixed)")
    vdim(ax1, 5.0, kz1, kz1 + gap, f"gap {gap:g} = washer {t_w:g} + play {gap - t_w:.2f}", 5.5)
    vdim(ax1, 3.3, kz1 + t_w, zst, f"sleeve length {l_sl:g}", 5.5)
    label(ax1, (d_sl / 2 - 0.1, zst - 0.02), (8.5, zst + 3.4), f"sleeve {proud:g} proud of the top face")
    label(ax1, (1.5, zst + 2.2), (8.5, zst + 5.6), "ball stud 4.8x9 of the camber link (screwed into the boss)")

    # detail bottom: screw M3x8 clamps the lower sleeve and washer to the lower boss
    ax2.set_xlim(-13.0, 24.0)
    ax2.set_ylim(zsb - 4.6, kz0 + 1.6)
    ax2.set_title("Detail bottom: the screw M3x8 clamps sleeve and washer to the knuckle", fontsize=10.5, loc="left",
                  color=TXT)
    label(ax2, (-d_sl / 2 + 0.25, zsb + l_sl * 0.45), (-12.5, zsb - 2.4),
          f"to buy: brass spacer sleeve\nØ{d_sl:g} x Ø{d_in:g} x {l_sl:g} mm", buy=True)
    label(ax2, (-d_w / 2 + 0.35, kz0 - t_w / 2), (-12.5, kz0 + 0.6),
          f"to buy: washer M3 DIN 125-A\nØ{d_in:g} x Ø{d_w:g} x {t_w:g} mm", buy=True)
    tx = 11.5                                                       # labels right of the tube on the hinge pin
    label(ax2, (r_boss - 0.8, kz0 + 0.5), (tx, kz0 + 0.9), "boss of the knuckle (turns)")
    vdim(ax2, 5.0, kz0 - gap, kz0, f"gap {gap:g} = washer {t_w:g} + play {gap - t_w:.2f}", tx, kz0 - 0.6)
    vdim(ax2, 3.3, zsb, kz0 - t_w, f"sleeve length {l_sl:g}", tx, zsb + l_sl / 2 + 0.3)
    label(ax2, (d_sl / 2 - 0.1, zsb + 0.02), (tx, zsb - 0.6), f"sleeve {proud:g} proud of the bottom face")
    label(ax2, (h_d / 2 - 0.4, zsb - h_h / 2), (tx, zsb - 2.4), "socket head screw M3x8 (screwed into the boss)")

    handles = [Rectangle((0, 0), 1, 1, fc=color, ec="k", lw=0.6) for _, color, t in sec if t]
    fig.legend(handles, [t for _, _, t in sec if t], loc="lower left", bbox_to_anchor=(0.02, 0.015), ncol=3, fontsize=9,
               frameon=False)
    fig.text(0.02, 0.975, "Kingpin of the front C-hub: brass spacer sleeve and washer M3 in place of the Carten flanged "
             "sleeve", fontsize=13.5, ha="left", va="top", color=TXT, fontweight="bold")
    fig.text(0.02, 0.935, "The screw (bottom) and the ball stud (top) clamp sleeve and washer to the boss of the knuckle: "
             "knuckle, washer, sleeve and screw turn together as one unit.\nThe sleeve turns in the bore Ø4.9 of the "
             "C-hub (radial bearing); the washer slides on the face of the C-hub toward the boss (axial bearing) and "
             "takes the place of the flange of the Carten sleeve.", fontsize=10, ha="left", va="top", color=TXT)
    fig.savefig(OUT, dpi=120)
    plt.close(fig)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
