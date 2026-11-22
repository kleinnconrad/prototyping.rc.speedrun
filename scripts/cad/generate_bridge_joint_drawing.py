"""Explanation picture of the joint of the steering bridge on the bellcrank arm: brass spacer sleeve and washers M3,
the same generic parts as the kingpins of the C-hub (owner, 2026-11-22).

Section through the 3 holes of the right bellcrank (plane through the axis of the post and the axis of the bridge
tower), read from the assembly STEP file: steering post with the bellcrank on its 2 ball bearings (unchanged), steering
bridge, washers, sleeve, screw M3x16 and lock nut. Left: the bellcrank with the post and the bridge; right: detail of
the joint with the values from the parameter file. The parts to buy (sleeves and washers) are marked.

Run from the root directory of the repository, after scripts/cad/generate_speedrun_assembly.py:
    python scripts/cad/generate_bridge_joint_drawing.py
Output: cad/generic_parts/steering/bridge_joint_sleeves_and_washers.png
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_assembly_drawing as AD  # noqa: E402
import palette as P  # noqa: E402
from generate_bulkhead_lower import load_params  # noqa: E402
from generate_kingpin_stack_drawing import section_rings, fill, label, vdim, BUY, TXT  # noqa: E402

ASSEMBLY = "cad/assembly/speedrun_chassis_T410R.step"
PARAMS = "cad/generic_parts/running_gear_parameters.json"
OUT = "cad/generic_parts/steering/bridge_joint_sleeves_and_washers.png"
POST = (21.7, 242.69)                     # right steering post (H25)
WASHER = "washer"                         # thin solids of the hardware group: washers
# parts in the section: (name in the assembly, colour key, legend text)
PARTS = [("running_gear_steering_post_right", "brace", "steering post (fixed on the chassis plate)"),
         ("running_gear_bellcrank_bearings_5x8x2.5_right", "ghost", "ball bearings 5x8x2.5 of the bellcrank (unchanged)"),
         ("running_gear_bellcrank_right", "upright", "bellcrank (turns on the post)"),
         ("running_gear_steering_bridge", "spring", "steering bridge (turns on the bellcrank arm)"),
         ("running_gear_bridge_guide_sleeves", "battery", "brass spacer sleeve (to buy)"),
         ("running_gear_bridge_washers,_screws_M3x16_and_lock_nuts", None, None),
         ("running_gear_washer_and_screw_M3x6_of_the_post_right", "link", None),
         ("running_gear_bellcrank_ball_right", "link", None),
         ("running_gear_bellcrank_ball_screw_M3x10_right", "link", "screws, lock nut, ball of the steering link")]


def named(parts, name):
    hits = [s for n, s in parts if n == name]
    if len(hits) != 1:
        raise SystemExit(f"{name}: {len(hits)} parts found")
    return hits[0]


def main():
    p = load_params(PARAMS)
    bz0, bz1 = p["bellcrank"][:2]
    r_b = p["bellcrank"][4]
    d_sl, d_in, l_sl, d_w, t_w, _, _, d_bore = p["guide_sleeve"]
    play, l_scr = p["bridge_joint"]
    zb0, zb1, _, d_tw, d_acc, _ = p["bridge"]
    yb = -r_b                                                         # axis of the tower (frame of the post: y toward End A)
    zt0 = bz1 + t_w                                                   # bottom face of the tower
    zs1 = zt0 + l_sl                                                  # upper end of the sleeve
    zh = zs1 + t_w                                                    # under the screw head
    parts = AD.read_named_solids(ASSEMBLY)
    origin, xd, kd = np.array([POST[0], POST[1], 0.0]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])
    origin[1] = POST[1]
    sec = []
    for name, key, text in PARTS:
        shape = named(parts, name)
        if key is None:                                               # hardware group: washers and screws apart
            for s in shape.Solids():
                bb = s.BoundingBox()
                thin = bb.zmax - bb.zmin < t_w + 0.05
                sec.append((section_rings(s, origin, xd, kd), P.rgb("drive" if thin else "link"),
                            "washer M3 DIN 125-A (to buy)" if thin else None))
        else:
            sec.append((section_rings(shape, origin, xd, kd), P.rgb(key), text))

    fig = plt.figure(figsize=(16.5, 10.0))
    fig.patch.set_facecolor("white")
    ax0 = fig.add_axes([0.02, 0.14, 0.42, 0.70])
    ax1 = fig.add_axes([0.47, 0.12, 0.30, 0.74])
    for ax in (ax0, ax1):
        for faces, color, _ in sec:
            fill(ax, faces, color)
        for yc in (0.0, yb):
            ax.plot([yc, yc], [0, 40], color="0.35", lw=0.7, ls=(0, (8, 2, 2, 2)), zorder=6)
        ax.set_aspect("equal")
        ax.axis("off")

    ax0.set_xlim(-26.0, 22.0)
    ax0.set_ylim(8.0, 33.0)
    ax0.set_title("Section through the 3 holes of the right bellcrank\n(seen from the right side, End A to the right)",
                  fontsize=10.5, loc="left", color=TXT)
    ax0.text(0.3, 32.0, "post", fontsize=8.5, color="0.3")
    ax0.text(yb + 0.3, 32.0, "bridge", fontsize=8.5, color="0.3")
    ax0.add_patch(Rectangle((yb - 7.5, bz0 - 5.5), 15.0, zb1 - bz0 + 7.0, fc="none", ec=BUY, lw=0.9, ls="--", zorder=7))
    ax0.text(yb - 7.3, zb1 + 2.0, "detail", fontsize=8.5, color=BUY)
    label(ax0, (2.8, bz0 + 1.2), (6.0, 11.0), "bellcrank on 2 ball bearings\n5x8x2.5 on the post (unchanged)")
    label(ax0, (yb + 5.0, zb1 - 1.0), (-2.0, 31.0), "steering bridge (bar unchanged)")

    ax1.set_xlim(yb - 15.0, yb + 7.5)
    ax1.set_ylim(bz0 - 6.5, zb1 + 2.5)
    ax1.set_title("Detail: the screw clamps washer, sleeve and washer to the bellcrank arm;\nthe tower of the bridge "
                  "turns on the sleeve", fontsize=10.5, loc="left", color=TXT)
    lx, tx = yb - 14.7, yb + 8.0                                      # labels left in the axes, right beside them
    label(ax1, (yb - d_w / 2 + 0.3, zs1 + t_w / 2), (lx, zb1 + 1.0),
          f"to buy: washer M3 DIN 125-A\nØ{d_in:g} x Ø{d_w:g} x {t_w:g} mm", buy=True)
    label(ax1, (yb - d_sl / 2 + 0.25, zt0 + l_sl * 0.5), (lx, zt0 + l_sl * 0.5),
          f"to buy: brass spacer sleeve\nØ{d_sl:g} x Ø{d_in:g} x {l_sl:g} mm", buy=True)
    label(ax1, (yb - d_w / 2 + 0.3, bz1 + t_w / 2), (lx, bz1 - 2.0),
          f"to buy: washer M3 DIN 125-A\nØ{d_in:g} x Ø{d_w:g} x {t_w:g} mm", buy=True)
    label(ax1, (yb + 1.0, zh + 1.2), (tx, zb1 + 1.0), f"button head screw M3x{l_scr:g} (ISO 7380)")
    label(ax1, (yb + d_acc / 2 - 0.3, zs1 + 0.8), (tx, zs1 + 1.0), f"access bore Ø{d_acc:g}: washer and screw head")
    vdim(ax1, yb + 2.6, zt0, zs1, f"sleeve length {l_sl:g}", tx, zt0 + l_sl * 0.6)
    label(ax1, (yb + d_bore / 2 + 0.6, zt0 + 1.0), (tx, zt0 + 0.5),
          f"tower: bore Ø{d_bore:g}, turns on the sleeve (radial)\nand slides between the washers ({play:g} axial play)")
    label(ax1, (yb + 5.0, bz1 - 1.5), (tx, bz1 - 2.2), "rear arm of the bellcrank (through hole Ø3.2)")
    label(ax1, (yb + 2.5, bz0 - 2.5), (tx, bz0 - 3.0), "washer 3.2x7x0.5 and lock nut M3 (DIN 985)")

    seen, handles, texts = set(), [], []
    for _, color, text in sec:
        if text and text not in seen:
            seen.add(text)
            handles.append(Rectangle((0, 0), 1, 1, fc=color, ec="k", lw=0.6))
            texts.append(text)
    fig.legend(handles, texts, loc="lower left", bbox_to_anchor=(0.02, 0.015), ncol=3, fontsize=9, frameon=False)
    fig.text(0.02, 0.975, "Joint of the steering bridge on the bellcrank arm: brass spacer sleeve and washers M3, as the "
             "kingpins of the C-hub", fontsize=13.5, ha="left", va="top", color=TXT, fontweight="bold")
    fig.text(0.02, 0.935, "The screw M3x16 (with washer and lock nut under the arm) clamps washer, sleeve and washer to the "
             "rear arm of the bellcrank. The tower of the bridge turns on the brass sleeve in its bore Ø4.9 (radial bearing)\n"
             "and slides between the 2 washers (axial bearing). The bellcranks keep their ball bearings on the posts.",
             fontsize=10, ha="left", va="top", color=TXT)
    fig.savefig(OUT, dpi=120)
    plt.close(fig)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
