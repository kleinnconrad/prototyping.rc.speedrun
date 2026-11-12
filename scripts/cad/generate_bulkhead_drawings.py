"""Preview image and caliper measurement sheet of the lower bulkhead.

The views are rendered from the STL file of the part, the sections are cut from
the STEP file. The numbered dimensions of the measurement sheet refer to the
parameter file of the part.

Usage (from the root directory of the repository):
    python scripts/cad/generate_bulkhead_drawings.py

Outputs:
    photos/cad_bulkhead_lower_preview.png
    cad/bulkhead/bulkhead_lower_measurement_sheet.pdf

Requires the packages cadquery and matplotlib.
"""
import argparse
import json
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
import cadquery as cq  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh_views import load_stl, subdivide, draw_mesh, iso_basis  # noqa: E402

A4_LANDSCAPE = (11.69, 8.27)
DIM_COLOR = "#c0392b"
SEC_COLOR = (0.62, 0.68, 0.75)


def load(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data, {k: v["value"] for k, v in data["parameters"].items()}


# ---------------------------------------------------------------- dimensions
def balloon(ax, x, y, n, r=2.3):
    ax.add_patch(plt.Circle((x, y), r, facecolor="white", edgecolor=DIM_COLOR, lw=1.0, zorder=6))
    ax.text(x, y, str(n), ha="center", va="center", fontsize=7.5, color=DIM_COLOR,
            fontweight="bold", zorder=7)


def dim(ax, p1, p2, offset, n, side="mid", ext=True, txt_shift=0.0):
    """Linear dimension between p1 and p2, dimension line shifted by offset (vector)."""
    p1, p2, off = np.asarray(p1, float), np.asarray(p2, float), np.asarray(offset, float)
    a, b = p1 + off, p2 + off
    if ext and np.linalg.norm(off) > 0:
        u = off / np.linalg.norm(off)
        for p, q in ((p1, a), (p2, b)):
            ax.plot([p[0], q[0] + 0.8 * u[0]], [p[1], q[1] + 0.8 * u[1]], color=DIM_COLOR, lw=0.5, zorder=5)
    ax.annotate("", xy=a, xytext=b, arrowprops=dict(arrowstyle="<|-|>", color=DIM_COLOR, lw=0.8,
                                                    shrinkA=0, shrinkB=0, mutation_scale=7), zorder=5)
    t = (a + b) / 2
    d = (b - a) / max(np.linalg.norm(b - a), 1e-9)
    t = t + d * txt_shift
    balloon(ax, t[0], t[1], n)


def circles(ax, centers, d, sx=1.0):
    """Outlines of holes (diameter d) at the centres (x, y); sx = -1 mirrors x."""
    for (x, y) in centers:
        ax.add_patch(plt.Circle((sx * x, y), d / 2, fill=False, edgecolor="k", lw=0.6, zorder=4))


def hdim(ax, x1, z1, x2, z2, zd, n, txt_shift=0.0):
    """Horizontal dimension at the height zd between the points (x1, z1) and (x2, z2)."""
    for x, z in ((x1, z1), (x2, z2)):
        ax.plot([x, x], [z, zd + (0.8 if zd > z else -0.8)], color=DIM_COLOR, lw=0.5, zorder=5)
    dim(ax, (x1, zd), (x2, zd), (0, 0), n, ext=False, txt_shift=txt_shift)


def vdim(ax, x1, y1, x2, y2, xd, n, txt_shift=0.0):
    """Vertical dimension at the screen x position xd between the points (x1, y1) and (x2, y2)."""
    for x, y in ((x1, y1), (x2, y2)):
        ax.plot([x, xd + (0.8 if xd > x else -0.8)], [y, y], color=DIM_COLOR, lw=0.5, zorder=5)
    dim(ax, (xd, y1), (xd, y2), (0, 0), n, ext=False, txt_shift=txt_shift)


def seat_x(p):
    """Inner face of the outer lip and inner end of the bearing seat (|x|)."""
    xl = p["diff_lip_inner_x"]
    return xl, xl - p["diff_seat_width"]


def leader(ax, p, q, n):
    """Balloon at q with a leader line to the point p."""
    ax.plot([p[0], q[0]], [p[1], q[1]], color=DIM_COLOR, lw=0.6, zorder=5)
    ax.plot([p[0]], [p[1]], "o", color=DIM_COLOR, ms=2, zorder=5)
    balloon(ax, q[0], q[1], n)


# ---------------------------------------------------------------- sections
def section(solid, origin, normal, right, up):
    """2D triangles and boundary polylines of the section of the solid with a plane."""
    face = cq.Face.makePlane(400, 400, basePnt=cq.Vector(*origin), dir=cq.Vector(*normal))
    sec = solid.intersect(face)
    r, u = np.asarray(right, float), np.asarray(up, float)
    tris, lines = [], []
    for f in sec.Faces():
        verts, idx = f.tessellate(0.01, 0.1)
        v = np.array([[p.x, p.y, p.z] for p in verts])
        for t in idx:
            tris.append(np.stack([v[list(t)] @ r, v[list(t)] @ u], axis=1))
        for e in f.Edges():
            pts = np.array([[p.x, p.y, p.z] for p in e.sample(60)[0]])
            lines.append(np.stack([pts @ r, pts @ u], axis=1))
    return tris, lines


def draw_section(ax, tris, lines):
    ax.add_collection(PolyCollection(tris, facecolors=[SEC_COLOR], edgecolors=[SEC_COLOR], lw=0.3))
    # hatch lines clipped visually by drawing over the section only
    for ln in lines:
        ax.plot(ln[:, 0], ln[:, 1], color="k", lw=0.8)


def frame(ax, lo, hi, pad=(4, 4, 4, 4), title=None):
    ax.set_xlim(lo[0] - pad[0], hi[0] + pad[1])
    ax.set_ylim(lo[1] - pad[2], hi[1] + pad[3])
    ax.set_aspect("equal")
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=10, loc="left")


def axis_marks(ax, origin, labels, length=6):
    """Small coordinate arrows: labels = ((dx, dy, text), ...) in screen directions."""
    for dx, dy, t in labels:
        ax.annotate("", xy=(origin[0] + dx * length, origin[1] + dy * length), xytext=origin,
                    arrowprops=dict(arrowstyle="-|>", color="#2c3e50", lw=0.8, mutation_scale=7))
        ax.text(origin[0] + dx * (length + 1.5), origin[1] + dy * (length + 1.5), t, fontsize=7,
                ha="center", va="center", color="#2c3e50")


# ---------------------------------------------------------------- pages
def page_header(fig, title, subtitle):
    fig.text(0.04, 0.955, title, fontsize=14, fontweight="bold")
    fig.text(0.04, 0.925, subtitle, fontsize=8.5, color="#444")
    fig.text(0.96, 0.02, "Carten T410R - lower bulkhead - measurement sheet", fontsize=7,
             ha="right", color="#666")


def views_page(pdf, tris, p):
    yd, w, zc = p["diff_axis_y"], p["body_half_width"], p["axis_z"]
    hx, hy = p["bottom_hole_dx"] / 2, p["bottom_hole_dy"] / 2
    bxp, bxo = p["top_boss_x_pinion"], p["top_boss_x_outer"]
    byp, byo = p["top_boss_y_pinion"], p["top_boss_y_outer"]
    sx, sy = p["swaybar_hole_x"], p["swaybar_hole_y"]
    y0 = p["body_y_outer_end"]
    yend = p["pinion_seat_y_inner"] + p["pinion_seat_length"]
    rs = p["diff_bearing"][1] / 2

    fig = plt.figure(figsize=A4_LANDSCAPE)
    page_header(fig, "Measurement sheet - lower bulkhead - page 1: top and bottom view",
                "Top view: part standing on its bottom face, looking at the parting face. "
                "Bottom view: part upside down, looking at the face that sits on the chassis plate.")
    ax = fig.add_axes([0.03, 0.06, 0.5, 0.84])
    lo, hi = draw_mesh(ax, tris, "top")
    bosses = [(s * bxp, byp) for s in (-1, 1)] + [(s * bxo, byo) for s in (-1, 1)]
    circles(ax, bosses, p["top_hole_d"])
    circles(ax, [(-sx, sy), (sx, sy)], p["swaybar_hole_d"])
    dim(ax, (-bxp, byp), (bxp, byp), (0, 31.5 - byp), 7)
    dim(ax, (-bxo, byo), (bxo, byo), (0, -40 - byo), 8)
    vdim(ax, bxo, byo, bxp, byp, 27.5, 9)
    vdim(ax, sx, sy, bxo, byo, 22.5, 24)
    dim(ax, (-sx, sy), (sx, sy), (0, -35.5 - sy), 23)
    dim(ax, (-w, y0), (-w, yend), (-29 + w, 0), 21)
    dim(ax, (-w, y0), (-w, yd - rs), (-23.5 + w, 0), 16)
    dim(ax, (-w, yd + rs), (-w, yend), (-23.5 + w, 0), 17)
    axis_marks(ax, (30, -38), ((1, 0, "x"), (0, 1, "y")))
    ax.text(0, 36.5, "pinion side (centre shaft)", ha="center", fontsize=8, color="#2c3e50")
    ax.text(30, -43.5, "outer side", ha="center", fontsize=8, color="#2c3e50")
    frame(ax, (-33, -46), (36, 38), pad=(0, 0, 0, 0))

    ax = fig.add_axes([0.53, 0.06, 0.45, 0.84])
    draw_mesh(ax, tris, "bottom")
    # bottom view: screen x = -x, screen y = y
    circles(ax, [(a * hx, b * hy) for a in (-1, 1) for b in (-1, 1)], p["bottom_hole_d"], sx=-1)
    circles(ax, [(-sx, sy), (sx, sy)], p["swaybar_hole_d"], sx=-1)
    dim(ax, (-hx, -hy), (hx, -hy), (0, -19 + hy), 1)
    dim(ax, (-hx, -hy), (-hx, hy), (-22 + hx, 0), 2)
    leader(ax, (hx, hy), (22, 18), 3)
    vdim(ax, -sx, sy, -hx, -hy, -24, 39)
    dim(ax, (hx + 3.5, -p["base_half_length"]), (hx + 3.5, p["base_half_length"]), (25 - hx - 3.5, 0), 22)
    axis_marks(ax, (24, -38), ((-1, 0, "x"), (0, 1, "y")))
    frame(ax, (-33, -46), (33, 38), pad=(0, 0, 0, 0))
    pdf.savefig(fig, dpi=250)
    plt.close(fig)


def sections_page(pdf, solid, p):
    yd, w, zc = p["diff_axis_y"], p["body_half_width"], p["axis_z"]
    xl, xs = seat_x(p)
    rs, lip = p["diff_bearing"][1] / 2, p["diff_lip_d"] / 2
    yin, L = p["pinion_seat_y_inner"], p["pinion_seat_length"]
    rp = p["pinion_bearing"][1] / 2

    fig = plt.figure(figsize=A4_LANDSCAPE)
    page_header(fig, "Measurement sheet - lower bulkhead - page 2: sections",
                "Section A-A along the pinion axis (x = 0), seen from the side. "
                "Section B-B through the diff axis, seen from the pinion side.")
    ax = fig.add_axes([0.03, 0.08, 0.52, 0.8])
    tris, lines = section(solid, (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
    draw_section(ax, tris, lines)
    dim(ax, (yin, zc), (yin + L, zc), (0, 4.5), 19)
    leader(ax, (yin, zc - rp), (yin - 5, zc - rp - 6), 20)
    yr = yin + p["pinion_bearing"][2] + p["pinion_rib_t"] / 2
    leader(ax, (yr, zc - p["pinion_rib_d"] / 2 - 0.3), (yr + 4, 24), 38)
    dim(ax, (-p["base_half_length"], 0), (-p["base_half_length"], zc), (-14, 0), 4)
    ax.plot([yd, yd], [-2, zc + 6], color="#2c3e50", lw=0.6, ls="-.")
    ax.text(yd, zc + 7, "diff axis", ha="center", fontsize=7, color="#2c3e50")
    ax.plot([-34, 32], [zc, zc], color="#2c3e50", lw=0.6, ls="-.")
    ax.text(-34, zc + 0.8, "parting face", fontsize=7, color="#2c3e50")
    axis_marks(ax, (-30, -6), ((1, 0, "y"), (0, 1, "z")))
    frame(ax, (-36, -12), (34, 28), pad=(0, 0, 0, 0), title="Section A-A (x = 0)")

    ax = fig.add_axes([0.55, 0.08, 0.43, 0.8])
    # seen from the pinion side: screen right = -x
    tris, lines = section(solid, (0, yd, 0), (0, 1, 0), (-1, 0, 0), (0, 0, 1))
    draw_section(ax, tris, lines)
    # screen x = -x: the ring gear side (sign sg in x) is at screen -sg
    sg = 1 if p["ring_gear_side"] > 0 else -1
    zcase = zc - p["case_cavity_r"]
    fz = p["floor_z"]
    a_out = -sg * min(p["ring_recess_x_outer"], xs)
    a_in = -sg * p["ring_recess_x_inner"]
    xm = (a_out + a_in) / 2
    dim(ax, (-w, 0), (w, 0), (0, -4), 10)
    hdim(ax, -xl, zc - rs, xl, zc - rs, 14.5, 14, txt_shift=-sg * 4)
    leader(ax, (sg * (xl - 2), zc - rs), (sg * 8, 25), 11)
    leader(ax, (sg * (xl + 0.5), zc - lip), (sg * 22, 26), 12)
    hdim(ax, sg * xl, zc - lip, sg * w, zc - lip, 12.5, 13, txt_shift=sg * 4.5)
    hdim(ax, sg * xs, zc - rs, sg * xl, zc - rs, 1.5, 15, txt_shift=-sg * 4)
    hdim(ax, -sg * w, zc - lip, a_out, zcase, 20.5, 31)
    hdim(ax, -sg * w, zc - lip, a_in, zcase, 23.5, 32)
    dim(ax, (xm, fz), (xm, zc), (0, 0), 33, ext=False)
    dim(ax, (sg * 6, zcase), (sg * 6, zc), (0, 0), 34, ext=False)
    leader(ax, (xm, fz / 2), (-sg * 21.5, 4), 26)
    ax.text(-sg * 12, -9.5, "ring gear side", ha="center", fontsize=7.5, color="#2c3e50")
    ax.plot([-24, 24], [zc, zc], color="#2c3e50", lw=0.6, ls="-.")
    ax.text(-23.5, zc + 0.8, "parting face", fontsize=7, color="#2c3e50")
    axis_marks(ax, (19, -9), ((-1, 0, "x"), (0, 1, "z")), length=5)
    frame(ax, (-24, -12), (24, 28), pad=(0, 0, 0, 0), title="Section B-B (diff axis, seen from the pinion side)")
    pdf.savefig(fig, dpi=250)
    plt.close(fig)


def side_page(pdf, tris, p):
    zc = p["axis_z"]
    ztop = zc + p["top_boss_protrusion"]
    bx = p["top_boss_x_pinion"]
    tt, sy = p["swaybar_tab_t"], p["swaybar_hole_y"]
    rp = p["pinion_bearing"][1] / 2
    br = p["top_boss_d"] / 2

    fig = plt.figure(figsize=A4_LANDSCAPE)
    page_header(fig, "Measurement sheet - lower bulkhead - page 3: side and end view",
                "Side view: looking at a diff bearing wall. End view: looking at the pinion housing.")
    ax = fig.add_axes([0.03, 0.08, 0.55, 0.8])
    draw_mesh(ax, tris, "side")
    dim(ax, (-33, 0), (-33, ztop), (-3, 0), 5)
    dim(ax, (p["base_half_length"], 0), (p["base_half_length"], p["base_height"]), (5, 0), 22,
        txt_shift=0)
    dim(ax, (sy - 2.8, zc - tt), (sy - 2.8, zc), (-6, 0), 25, txt_shift=0)
    axis_marks(ax, (24, -6), ((1, 0, "y"), (0, 1, "z")))
    ax.text(28, 22, "pinion side", ha="right", fontsize=8, color="#2c3e50")
    ax.text(-32, 22, "outer side", ha="left", fontsize=8, color="#2c3e50")
    frame(ax, (-42, -12), (32, 26), pad=(0, 0, 0, 0), title="Side view")

    ax = fig.add_axes([0.6, 0.08, 0.38, 0.8])
    draw_mesh(ax, tris, "end_pinion")
    # end view from the pinion side: screen x = -x
    dim(ax, (-rp, zc), (rp, zc), (0, 5.5), 18)
    dim(ax, (bx - br, ztop), (bx + br, ztop), (0, 3.5), 6)
    axis_marks(ax, (19, -9), ((-1, 0, "x"), (0, 1, "z")), length=5)
    frame(ax, (-22, -12), (22, 26), pad=(0, 0, 0, 0), title="End view (pinion side)")
    pdf.savefig(fig, dpi=250)
    plt.close(fig)


ROWS = [
    # (no, priority, feature, how to measure, model, caliper value)
    (1, "A", "Bottom holes: spacing across (x)", "inside jaws, far edge to far edge, minus hole diameter", "28.0", "28.0"),
    (2, "A", "Bottom holes: spacing along (y)", "as no. 1", "20.0", "20.0"),
    (3, "B", "Bottom holes: diameter / depth", "inside jaws / depth rod", "M3: 2.5 / 8.0", "3.2 / 6.25"),
    (4, "A", "Height: bottom face to parting face", "part on a flat surface, depth rod", "17.2", "17.2"),
    (5, "A", "Height: bottom face to top of the bosses", "as no. 4", "19.62", "19.62"),
    (6, "B", "Top bosses: outer diameter", "outside jaws", "4.86", "4.86"),
    (7, "A", "Top boss holes: spacing across, pinion side (M3x10)", "as no. 1", "18.7", "18.7"),
    (8, "A", "Top boss holes: spacing across, outer side (M3x8)", "as no. 1", "21.6", "21.6"),
    (9, "A", "Top boss holes: spacing along (y)", "as no. 1", "42.6", "42.6"),
    (10, "B", "Width over the outer faces of the diff bearing walls", "outside jaws", "34.48", "34.2"),
    (11, "A", "Diff bearing seat: width of the half bore at the parting face", "inside jaws", "15.0 (fit)", "15.6"),
    (12, "A", "Diff bearing lip: opening diameter", "inside jaws at the outer face", "12.28", "12.28"),
    (13, "A", "Diff bearing lip: thickness", "outside jaws or depth rod", "1.89", "1.89"),
    (14, "A", "Spacing of the inner faces of the two lips", "inside jaws across the cavity", "30.7", "30.7"),
    (15, "A", "Diff bearing seat: length from the lip inward / inner shoulder", "depth rod", "4.0 / none",
     "4.0 / none"),
    (16, "A", "Outer end face to the near edge of the diff half bore at the parting face", "depth rod",
     "18.2 (design)", "21.12"),
    (17, "A", "Pinion housing end face to the near edge of the diff half bore", "as no. 16", "19.6", "19.6"),
    (18, "A", "Pinion bearing seat: width of the half bore at the parting face", "inside jaws", "10.0 (fit)",
     "10.5"),
    (19, "A", "Pinion bearing seat: length (inner end of the seat to housing end face)", "depth rod", "9.25",
     "9.25"),
    (20, "A", "Pinion bearing seat: shoulder at the inner end", "look", "none", "none"),
    (21, "B", "Overall length at the parting face (outer end to pinion housing end)", "outside jaws", "53.4 (design)", ""),
    (22, "B", "Contact block on the chassis plate: length (y) / height of the end faces", "outside jaws",
     "24.8 / 5.0", "- / 5.0"),
    (23, "A", "Sway bar holes: spacing", "as no. 1", "16.2", "16.2"),
    (24, "A", "Sway bar hole to the outer top boss hole, along (y)", "inside jaws, far edges, minus diameters",
     "7.4", "7.4"),
    (25, "B", "Sway bar tabs: thickness", "outside jaws", "4.35", "4.35"),
    (26, "B", "Floor below the ring gear deepening", "-", "open 6.85 x 5", "open (test print)"),
    (27, "A", "Diff: outer diameter of the ring gear", "outside jaws on the diff", "max. 31.9", "31.93"),
    (28, "A", "Diff with both bearings: distance over the outer faces of the bearings", "outside jaws on the diff",
     "30.0", "30.0"),
    (29, "A", "Pinion gear (17T): outer diameter", "outside jaws", "max. 14.1", "14.1"),
    (30, "B", "4 small holes on the outer end face: function, diameter, positions", "photo with ruler",
     "not modelled", ""),
    (31, "A", "Ring gear deepening: outer face of the diff wall (ring gear side) to the outer end", "depth rod",
     "5.89", ""),
    (32, "A", "Ring gear deepening: outer face of the diff wall (ring gear side) to the inner end", "depth rod",
     "12.74", ""),
    (33, "A", "Ring gear deepening: depth below the parting face", "depth rod", "16.4", ""),
    (34, "B", "Floor below the diff case: depth below the parting face", "depth rod", "13.5", "test print"),
    (35, "A", "Diff: largest outer diameter of the diff case (without the ring gear)", "outside jaws on the diff",
     "max. 24.0", ""),
    (36, "A", "Diff: back face of the ring gear to the outer face of the bearing on that side", "depth rod",
     "min. 4.0", ""),
    (37, "A", "Ring gear side: seen from the pinion housing, is the deepening on the left?", "look", "left",
     "left (photo)"),
    (38, "A", "Pinion seat: rib between the two bearings: width / opening diameter", "depth rod / inside jaws",
     "0.9 / 9.4", "test print"),
    (39, "A", "Bottom side: sway bar hole to the nearest bottom hole, along (y)", "as no. 24", "18.7", ""),
    (40, "A", "Parting face: outer top boss hole to the near edge of the diff half bore, along (y)",
     "depth rod or inside jaws", "14.3", ""),
    (41, "B", "Sway bar tabs: top face below the parting face", "depth rod", "0", ""),
]


def table_page(pdf, rows):
    fig = plt.figure(figsize=A4_LANDSCAPE)
    page_header(fig, "Measurement sheet - lower bulkhead - page 4: values",
                "Priority A: interfaces. Priority B: shape. Rows without a caliper value are open. "
                "Nos. 16 and 17 refer to the edge of the seat (15.6 at the parting face). Values in mm.")
    ax = fig.add_axes([0.03, 0.05, 0.94, 0.85])
    ax.axis("off")
    cols = [0.0, 0.033, 0.065, 0.53, 0.775, 0.865]
    heads = ["No.", "Prio", "Feature", "How to measure", "Model", "Caliper value"]
    ytop = 0.98
    for c, h in zip(cols, heads):
        ax.text(c, ytop, h, fontsize=8.5, fontweight="bold", va="center", transform=ax.transAxes)
    dy = 0.93 / (len(rows) + 1)
    for i, (n, pr, feat, how, val, meas) in enumerate(rows):
        y = ytop - (i + 1) * dy
        if i % 2 == 0:
            ax.add_patch(plt.Rectangle((0, y - dy / 2), 1, dy, transform=ax.transAxes,
                                       color="#eef2f6", zorder=0))
        for c, t in zip(cols, (str(n), pr, feat, how, val, meas)):
            ax.text(c, y, t, fontsize=6.9, va="center", transform=ax.transAxes)
        if not meas:
            ax.plot([cols[5], 0.995], [y - dy * 0.3, y - dy * 0.3], color="#888", lw=0.5, transform=ax.transAxes)
    pdf.savefig(fig, dpi=250)
    plt.close(fig)


def preview(path, tris):
    fig = plt.figure(figsize=(14, 9.5))
    specs = [([0.0, 0.48, 0.5, 0.44], iso_basis(-55, 32), "View from the outer side"),
             ([0.5, 0.48, 0.5, 0.44], iso_basis(125, 32), "View from the pinion side"),
             ([0.02, 0.02, 0.3, 0.44], "top", "Top view"),
             ([0.34, 0.02, 0.3, 0.44], "bottom", "Bottom view"),
             ([0.66, 0.02, 0.33, 0.44], "side", "Side view")]
    for rect, view, title in specs:
        ax = fig.add_axes(rect)
        lo, hi = draw_mesh(ax, tris, view)
        frame(ax, lo, hi, pad=(2, 2, 2, 2), title=title)
    fig.suptitle("Carten T410R lower bulkhead, design matching the upper part (verified)",
                 fontsize=13, y=0.985)
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Preview and measurement sheet of the lower bulkhead.")
    parser.add_argument("--params", default="cad/bulkhead/bulkhead_lower_parameters.json")
    parser.add_argument("--stem", default="cad/bulkhead/bulkhead_lower_T410R")
    parser.add_argument("--sheet", default="cad/bulkhead/bulkhead_lower_measurement_sheet.pdf")
    parser.add_argument("--preview", default="photos/cad_bulkhead_lower_preview.png")
    args = parser.parse_args()

    _, p = load(args.params)
    tris = subdivide(load_stl(args.stem + ".stl"), max_edge=1.0)
    solid = cq.importers.importStep(args.stem + ".step").val()

    preview(args.preview, tris)
    with PdfPages(args.sheet) as pdf:
        views_page(pdf, tris, p)
        sections_page(pdf, solid, p)
        side_page(pdf, tris, p)
        table_page(pdf, ROWS)
        d = pdf.infodict()
        d["Title"] = "T410R lower bulkhead - measurement sheet"
    print(f"Wrote {args.preview} and {args.sheet}")


if __name__ == "__main__":
    main()
