"""Technical drawings (manufacturing drawings) of the lower and the upper bulkhead.

The views and sections are projected from the STEP files with hidden line removal (OCCT HLR). The
holes are read from the STEP files (cylindrical faces with the tap drill 2.5 mm or the clearance
hole 3.2 mm); the dimensions refer to the parameter files of the parts. The STEP file is the master
geometry: dimensions that are not shown on the drawing are taken from the model.

Each part gets 2 sheets A3 (landscape, scale 2:1, first angle projection):
    sheet 1: front view, top view, side view, isometric view, main dimensions, hole labels
    sheet 2: view from below, sections through the diff axis and the pinion axis, hole table, notes

Usage (from the root directory of the repository):
    python scripts/cad/generate_bulkhead_technical_drawings.py

Outputs:
    cad/speedrun_parts/bulkhead/bulkhead_lower_technical_drawing.pdf (2 pages), ..._sheet_1.png, ..._sheet_2.png
    cad/speedrun_parts/bulkhead/bulkhead_upper_technical_drawing.pdf (2 pages), ..._sheet_1.png, ..._sheet_2.png

Requires the packages cadquery and matplotlib.
"""
import argparse
import datetime
import json
import os
import sys

import numpy as np
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import technical_drawing as TD  # noqa: E402
from technical_drawing import (A3, SCALE, LABEL_FS, DENSITY_7075, AUTHOR, View, draw_view, draw_section,  # noqa: E402
                               linear, leader, centre_line, centre_mark, balloon, view_label, section_marker,
                               hole_table, sheet, iso_inset, origin_mark, view_arrow, save, text)

OUT = "cad/speedrun_parts/bulkhead"


def load(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v["value"] for k, v in data["parameters"].items()}


# ------------------------------------------------------------------ holes
def find_holes(solid, z0):
    """Holes of the part: concave cylindrical faces with the tap drill (2.5) or the clearance (3.2) diameter, with the
    coaxial counterbores and recesses. Returns a list of dicts (axis direction, position, extent, open ends)."""
    groups = {}
    for f in solid.Faces():
        if f.geomType() != "CYLINDER":
            continue
        cyl = f._geomAdaptor().Cylinder()
        r = round(cyl.Radius(), 3)
        d = cyl.Axis().Direction()
        dv = np.round(np.abs([d.X(), d.Y(), d.Z()]), 6)
        k = int(np.argmax(dv))
        if dv[k] < 0.999:
            continue
        loc = cyl.Axis().Location()
        lp = np.array([loc.X(), loc.Y(), loc.Z()])
        pos = tuple(np.round(np.delete(lp, k), 3))
        c = np.array(f.Center().toTuple())                   # concave: the outward normal points to the axis
        pnt = f.positionAt(0.5, 0.5)
        nrm = np.array(f.normalAt(pnt).toTuple())
        foot = lp + np.eye(3)[k] * ((np.array(pnt.toTuple()) - lp)[k])
        if nrm @ (foot - np.array(pnt.toTuple())) <= 0:
            continue
        bb = f.BoundingBox()
        ext = [(bb.xmin, bb.xmax), (bb.ymin, bb.ymax), (bb.zmin, bb.zmax)][k]
        groups.setdefault((k, pos), []).append((r, ext))
        del c
    holes = []
    for (k, pos), feats in groups.items():
        drill = [f for f in feats if f[0] in (1.25, 1.6)]
        if not drill:
            continue
        lo = min(f[1][0] for f in feats)
        hi = max(f[1][1] for f in feats)
        axis = np.eye(3)[k]
        p = np.insert(np.array(pos, float), k, 0.0)
        open_lo = not solid.isInside(cq.Vector(*(p + axis * (lo - 0.05))))
        open_hi = not solid.isInside(cq.Vector(*(p + axis * (hi + 0.05))))
        holes.append({"k": k, "pos": p, "lo": lo, "hi": hi, "open": (open_lo, open_hi), "feats": sorted(feats),
                      "d": 2 * drill[0][0]})
    return holes


HOLE_GROUPS = {
    "lower": [("A", lambda h: h["k"] == 2 and h["lo"] < 0.1, "M3", 6.5, "chassis plate: screws M3x8 countersunk from below"),
              ("B", lambda h: h["k"] == 2 and h["hi"] > 19.0, "M3", 6.0, "screws M3x8 (outer side) and M3x10 (pinion side) through the upper part"),
              ("C", lambda h: h["k"] == 2 and h["open"] == (True, True), "M3", None, "sway bar holders, screws M3x6 from above")],
    "upper": [("D", lambda h: h["k"] == 2 and abs(h["d"] - 3.2) < 0.01, "Ø3.2", None, "screws to the lower part"),
              ("E", lambda h: h["k"] == 2 and abs(h["d"] - 2.5) < 0.01, "M3", 6.0, "top brace: screws M3x8"),
              ("F", lambda h: h["k"] == 1, "M3", None, "shock tower: screws M3x8 button head")]}


def hole_rows(holes, part, z0):
    """Rows of the hole table: (id, x, y, z, direction, size, depth, use) and the hole of each id. z from z0."""
    rows, ids = [], {}
    used = set()
    for letter, test, size, tdepth, use in HOLE_GROUPS[part]:
        sel = [h for h in holes if id(h) not in used and test(h)]
        sel.sort(key=lambda h: (-h["pos"][1] if h["k"] == 2 else -h["pos"][2], h["pos"][0]))
        for i, h in enumerate(sel, 1):
            used.add(id(h))
            hid = f"{letter}{i}"
            ids[hid] = h
            x, y, z = h["pos"]
            through = h["open"] == (True, True)
            if h["k"] == 2:
                from_below = h["open"][0] and not h["open"][1]
                start = h["lo"] if (from_below or through) else h["hi"]
                direction = "through (z)" if through else ("from below" if from_below else "from above")
                pos3 = (x, y, start - z0)
            else:
                direction = "through (y)"
                pos3 = (x, h["lo"], z - z0)
            drill = [f for f in h["feats"] if f[0] in (1.25, 1.6)][0]
            if through:
                dtxt = f"through ({drill[1][1] - drill[1][0]:.2f})"
            else:
                dtxt = f"drill {drill[1][1] - drill[1][0]:.1f}" + (f", thread {tdepth:.1f}" if tdepth else "")
            extra = []
            for r, e in [f for f in h["feats"] if f[0] not in (1.25, 1.6)]:
                if abs(e[0] - z0) < 0.01:
                    extra.append(f"recess Ø{2 * r:.2f} x {e[1] - e[0]:.2f} from the parting face")
                else:
                    extra.append(f"counterbore Ø{2 * r:.2f}, bottom at z = {e[0] - z0:.2f}")
            size_txt = "M3 (tap drill Ø2.5)" if size == "M3" else size
            rows.append((hid, f"{pos3[0]:+.2f}", f"{pos3[1]:+.2f}", f"{pos3[2]:.2f}", direction, size_txt, dtxt,
                         "; ".join([use] + extra)))
    return rows, ids


# ------------------------------------------------------------------ parts
ISO_RECT = [250 / A3[0], 74 / A3[1], 155 / A3[0], 112 / A3[1]]       # isometric view: below the side view


def lower_drawing(pdf_path, png_stem, lp, date):
    solid = cq.importers.importStep(f"{OUT}/bulkhead_lower_T410R.step").val()
    z0, zpf, y_d = 0.0, lp["axis_z"], lp["diff_axis_y"]
    holes = find_holes(solid, z0)
    rows, ids = hole_rows(holes, "lower", z0)
    ox0, ox1 = lp["ring_recess_x_inner"], lp["ring_recess_x_outer"]
    oh = lp["ring_floor_opening_half_length"]
    rows.append(("G", f"{ox0:+.2f}", f"{y_d - oh:+.2f}", "0.00", "through (z)", f"{ox1 - ox0:.2f} x {2 * oh:.2f}",
                 "through the floor", f"floor opening below the ring gear, corner radius R{lp['ring_floor_opening_r']:g}; "
                 "x, y: corner of the opening"))
    vol = solid.Volume() / 1000
    bb = solid.BoundingBox()
    tb = title_rows("Lower bulkhead (gear box), End A and End B", "bulkhead_lower_T410R.step (master geometry), "
                    "parameters: bulkhead_lower_parameters.json", vol, date, "BH-L")
    figs = []
    # ---------------- sheet 1: front view, top view (below), side view (right), isometric view
    fig, ax = sheet(tb, 1)
    F = View((0, -1, 0), (1, 0, 0), (85, 205))
    T = View((0, 0, 1), (1, 0, 0), (85, 112))
    S = View((-1, 0, 0), (0, -1, 0), (248, 205))
    for V in (F, T, S):
        draw_view(ax, solid, V)
    for V in (F, S):
        TD.auto_angles(ax, solid, V, max_groups=2)
    xl, xr = F.P((bb.xmin, 0, 0))[0], F.P((bb.xmax, 0, 0))[0]
    view_label(ax, (85, 258), "Front view (from the outer end)")
    view_label(ax, (S.P((0, 0, 0))[0], 258), "Side view (from the left, -x)")
    text(ax, (24, 172), "Top view", fs=LABEL_FS, ha="left", weight="bold")
    centre_line(ax, F.P((-20, 0, zpf)), F.P((20, 0, zpf)))
    centre_line(ax, F.P((0, 0, zpf - 9)), F.P((0, 0, zpf + 4)))
    centre_line(ax, T.P((-20, y_d, 0)), T.P((20, y_d, 0)))
    centre_line(ax, T.P((0, -34, 0)), T.P((0, 31, 0)))
    centre_line(ax, S.P((0, -34, zpf)), S.P((0, 31, zpf)))
    # front view
    linear(ax, F.P((bb.xmin, 0, bb.zmax)), F.P((bb.xmax, 0, bb.zmax)), "h", F.P((0, 0, bb.zmax))[1] + 6, f"{bb.xlen:.2f}")
    linear(ax, F.P((bb.xmin, 0, 0)), F.P((bb.xmin, 0, zpf)), "v", xl - 8, f"{zpf:.2f}")
    linear(ax, F.P((bb.xmin, 0, 0)), F.P((bb.xmin, 0, bb.zmax)), "v", xl - 16, f"{bb.zmax:.2f}")
    leader(ax, F.P((bb.xmax, 0, zpf)), F.P((bb.xmax, 0, zpf)) + (12, 8), "parting face")
    view_arrow(ax, (xr + 5, F.P((0, 0, 0))[1] - 5), "A")
    # top view
    linear(ax, T.P((bb.xmax, bb.ymin, 0)), T.P((bb.xmax, bb.ymax, 0)), "v", xr + 16, f"{bb.ylen:.2f}", tside="r")
    b2, b4 = ids["B2"]["pos"], ids["B4"]["pos"]
    linear(ax, T.P(b2), T.P(b4), "v", xr + 8, f"{abs(b2[1] - b4[1]):.2f}", tside="r")
    linear(ax, T.P((bb.xmin, bb.ymin, 0)), T.P((bb.xmin, 0, 0)), "v", xl - 9, f"{-bb.ymin:.2f}")
    linear(ax, T.P((bb.xmin, 0, 0)), T.P((bb.xmin, y_d, 0)), "v", xl - 9, f"{y_d:.2f}", inside=False, shift=6)
    for hid, h in ids.items():
        if hid[0] in "BC":
            x, y, _ = h["pos"]
            centre_mark(ax, T.P((x, y, 0)), 1.25 * SCALE)
            off = {"B": (8, 6 if y > 0 else -6), "C": (7, -6)}[hid[0]]
            balloon(ax, T.P((x, y, 0)), T.P((x, y, 0)) + np.array([off[0] * np.sign(x), off[1]]), hid)
    origin_mark(ax, T.P((0, 0, 0)))
    section_marker(ax, T.P((-18.5, y_d, 0)), T.P((18.5, y_d, 0)), (0, 1), "B")
    section_marker(ax, T.P((0, -34.0, 0)), T.P((0, 30.5, 0)), (1, 0), "C")
    # side view
    linear(ax, S.P((0, bb.ymax, 0)), S.P((0, bb.ymin, 0)), "h", S.P((0, 0, 0))[1] - 9, f"{bb.ylen:.2f}")
    linear(ax, S.P((0, bb.ymin, 0)), S.P((0, bb.ymin, lp["base_height"])), "v", S.P((0, bb.ymin, 0))[0] + 8,
           f"{lp['base_height']:.2f}", tside="r")
    iso_inset(fig, f"{OUT}/bulkhead_lower_T410R.stl", ISO_RECT, -55)
    text(ax, (328, 72), "Isometric view (not to scale)", fs=8, color="0.3")
    notes_short(ax, (24, 14))
    figs.append(fig)
    # ---------------- sheet 2: view A (from below), sections B-B and C-C, hole table, notes
    fig, ax = sheet(tb, 2)
    A = View((0, 0, -1), (1, 0, 0), (90, 170))
    B = View((0, -1, 0), (1, 0, 0), (205, 207))
    C = View((-1, 0, 0), (0, -1, 0), (342, 207))
    draw_view(ax, solid, A)
    draw_section(ax, solid, B, (0, y_d, 0))
    draw_section(ax, solid, C, (0, 0, 0))
    top_a = A.P((0, bb.ymin, 0))[1]
    text(ax, (24, top_a + 16), "View A (from below)", fs=LABEL_FS, ha="left", weight="bold")
    view_label(ax, (B.op[0], 270), "Section B-B (diff axis)")
    view_label(ax, (C.P((0, 0, 0))[0], 270), "Section C-C (pinion axis)")
    centre_line(ax, A.P((-20, 0, 0)), A.P((20, 0, 0)))
    centre_line(ax, A.P((0, -34, 0)), A.P((0, 31, 0)))
    for hid, h in ids.items():
        if hid[0] == "A":
            x, y, _ = h["pos"]
            centre_mark(ax, A.P((x, y, 0)), 1.25 * SCALE)
            balloon(ax, A.P((x, y, 0)), A.P((x, y, 0)) + np.array([7 * np.sign(x), 6 * np.sign(-y)]), hid)
    balloon(ax, A.P((ox1 - 1.2, y_d + oh - 1.2, 0)), A.P((ox1 - 1.2, y_d + oh - 1.2, 0)) + np.array([8, 8]), "G")
    a1, a2, a3 = ids["A1"]["pos"], ids["A2"]["pos"], ids["A3"]["pos"]
    xra = A.P((bb.xmax, 0, 0))[0]
    linear(ax, A.P(a1), A.P(a2), "h", A.P((0, bb.ymax, 0))[1] - 8, f"{abs(a2[0] - a1[0]):.2f}")
    linear(ax, A.P(a1), A.P(a3), "v", xra + 8, f"{abs(a3[1] - a1[1]):.2f}", tside="r")
    linear(ax, A.P((0, y_d - oh, 0)), A.P((ox0, y_d - oh, 0)), "h", top_a + 6, f"{ox0:.2f}", inside=False, shift=-7)
    linear(ax, A.P((ox0, y_d - oh, 0)), A.P((ox1, y_d - oh, 0)), "h", top_a + 6, f"{ox1 - ox0:.2f}")
    # section B-B: diff bearing seats (half bores below the parting face)
    seat_in, seat_out, lip_out = lp["diff_lip_inner_x"] - lp["diff_seat_width"], lp["diff_lip_inner_x"], bb.xmax
    top = B.P((0, 0, bb.zmax))[1]
    linear(ax, B.P((seat_in, 0, zpf)), B.P((seat_out, 0, zpf)), "h", top + 6, f"{seat_out - seat_in:.2f}")
    linear(ax, B.P((seat_out, 0, zpf)), B.P((lip_out, 0, zpf)), "h", top + 6, f"{lip_out - seat_out:.2f}", inside=False, shift=7)
    linear(ax, B.P((-seat_out, 0, zpf)), B.P((seat_out, 0, zpf)), "h", top + 12, f"{2 * seat_out:.2f}")
    linear(ax, B.P((bb.xmin, 0, zpf)), B.P((bb.xmax, 0, zpf)), "h", top + 18, f"{bb.xlen:.2f}")
    leader(ax, B.P((seat_in + 2.6, 0, zpf - 7.5)), B.P((bb.xmax, 0, zpf - 7.5)) + (9, -6), "Ø15 H7 (2x)")
    leader(ax, B.P((-lip_out + 0.9, 0, zpf - lp["diff_lip_d"] / 2)), B.P((bb.xmin, 0, zpf)) + (-8, 6), "Ø12.28 (2x)", ha="right")
    leader(ax, B.P((-6.0, 0, zpf - 13.5)), B.P((-6.0, 0, 0)) + (-8, -9), "R13.5", ha="right")
    leader(ax, B.P((7.0, 0, zpf - 16.4)), B.P((7.0, 0, 0)) + (7, -9), "R16.4")
    centre_line(ax, B.P((-20, 0, zpf)), B.P((20, 0, zpf)))
    # section C-C: pinion bearing seats, rib, pinion pocket
    ys = lp["pinion_seat_y_inner"]
    y1, y2, y3 = ys + 4.0, ys + 4.0 + lp["pinion_rib_t"], ys + lp["pinion_seat_length"]
    linear(ax, C.P((0, ys, zpf)), C.P((0, y1, zpf)), "h", top + 6, f"{y1 - ys:.2f}")
    linear(ax, C.P((0, y1, zpf)), C.P((0, y2, zpf)), "h", top + 12, f"{y2 - y1:.2f}", inside=False, shift=-11)
    linear(ax, C.P((0, y_d, zpf)), C.P((0, ys, zpf)), "h", top + 12, f"{ys - y_d:.2f}")
    linear(ax, C.P((0, y2, zpf)), C.P((0, y3, zpf)), "h", top + 18, f"{y3 - y2:.2f}")
    leader(ax, C.P((0, ys + 1.5, zpf - 5.0)), C.P((0, bb.ymax, 0)) + (-4, -9), "Ø10 H7 (2x)", ha="right")
    leader(ax, C.P((0, (y1 + y2) / 2, zpf - lp["pinion_rib_d"] / 2)), C.P((0, bb.ymax, 0)) + (-4, -3),
           f"rib Ø{lp['pinion_rib_d']:.2f} x {lp['pinion_rib_t']:.2f}", ha="right")
    leader(ax, C.P((0, 14.0, zpf - lp["pinion_pocket_r"])), C.P((0, 14.0, 0)) + (2, -9), f"R{lp['pinion_pocket_r']:g}")
    cang = np.radians(-60)
    leader(ax, C.P((0, y_d + 13.5 * np.cos(cang), zpf + 13.5 * np.sin(cang))), C.P((0, -12.0, 0)) + (6, -9), "R13.5")
    centre_line(ax, C.P((0, -34, zpf)), C.P((0, 31, zpf)))
    text(ax, (140, 190), "Holes and openings (x, y from O: centre of the holes A1 to A4; z from the bottom face)",
         ha="left", fs=8, weight="bold")
    y_end = hole_table(ax, 140, 187, rows)
    notes(ax, (24, 96), "lower", y_end)
    figs.append(fig)
    save(figs, pdf_path, png_stem)


def upper_drawing(pdf_path, png_stem, lp, up, date):
    solid = cq.importers.importStep(f"{OUT}/bulkhead_upper_T410R.step").val()
    zpf, y_d = lp["axis_z"], lp["diff_axis_y"]
    holes = find_holes(solid, zpf)
    rows, ids = hole_rows(holes, "upper", zpf)
    vol = solid.Volume() / 1000
    bb = solid.BoundingBox()
    tb = title_rows("Upper bulkhead (gear box), End A and End B", "bulkhead_upper_T410R.step (master geometry), "
                    "parameters: bulkhead_upper_parameters.json", vol, date, "BH-U")
    figs = []
    # ---------------- sheet 1
    fig, ax = sheet(tb, 1)
    F = View((0, -1, 0), (1, 0, 0), (85, 196), om=(0, 0, zpf))
    T = View((0, 0, 1), (1, 0, 0), (85, 108))
    S = View((-1, 0, 0), (0, -1, 0), (248, 196), om=(0, 0, zpf))
    for V in (F, T, S):
        draw_view(ax, solid, V)
    for V in (F, S):
        TD.auto_angles(ax, solid, V, max_groups=2)
    xl, xr = F.P((bb.xmin, 0, zpf))[0], F.P((bb.xmax, 0, zpf))[0]
    ztop = F.P((0, 0, bb.zmax))[1]
    view_label(ax, (85, ztop + 15), "Front view (from the outer end)")
    view_label(ax, (S.P((0, 0, zpf))[0], ztop + 15), "Side view (from the left, -x)")
    text(ax, (24, 172), "Top view", fs=LABEL_FS, ha="left", weight="bold")
    centre_line(ax, F.P((0, 0, zpf - 3)), F.P((0, 0, bb.zmax + 3)))
    centre_line(ax, T.P((-20, y_d, 0)), T.P((20, y_d, 0)))
    centre_line(ax, T.P((0, -28, 0)), T.P((0, 31, 0)))
    centre_line(ax, S.P((0, -28, zpf)), S.P((0, 31, zpf)))
    # front view
    wh = up["wall_half_width"]
    linear(ax, F.P((-wh, 0, bb.zmax)), F.P((wh, 0, bb.zmax)), "h", ztop + 7, f"{2 * wh:.2f}")
    linear(ax, F.P((bb.xmin, 0, zpf)), F.P((bb.xmax, 0, zpf)), "h", F.P((0, 0, zpf))[1] - 8, f"{bb.xlen:.2f}")
    fpos = [h["pos"] for k, h in ids.items() if k[0] == "F"]
    xs_f = sorted({round(p[0], 2) for p in fpos})
    zs_f = sorted({round(p[2], 2) for p in fpos})
    linear(ax, F.P((xs_f[0], 0, zs_f[1])), F.P((xs_f[1], 0, zs_f[1])), "h", ztop + 2.5, f"{xs_f[1] - xs_f[0]:.2f}")
    for hid, h in ids.items():
        if hid[0] == "F":
            x, _, z = h["pos"]
            centre_mark(ax, F.P((x, 0, z)), 1.25 * SCALE)
            balloon(ax, F.P((x, 0, z)), F.P((x, 0, z)) + np.array([11 * np.sign(x), 0]), hid)
    linear(ax, F.P((bb.xmax, 0, zpf)), F.P((xs_f[1], 0, zs_f[0])), "v", xr + 14, f"{zs_f[0] - zpf:.2f}", tside="r")
    linear(ax, F.P((bb.xmax, 0, zpf)), F.P((xs_f[1], 0, zs_f[1])), "v", xr + 22, f"{zs_f[1] - zpf:.2f}", tside="r")
    linear(ax, F.P((bb.xmin, 0, zpf)), F.P((bb.xmin, 0, bb.zmax)), "v", xl - 9, f"{bb.zmax - zpf:.2f}")
    leader(ax, F.P((bb.xmin, 0, zpf)), F.P((bb.xmin, 0, zpf)) + (-6, -9), "parting face", ha="right")
    view_arrow(ax, (xr + 5, F.P((0, 0, zpf))[1] - 5), "A")
    # top view
    yt = T.P((0, bb.ymax, 0))[1]
    linear(ax, T.P((bb.xmax, bb.ymin, 0)), T.P((bb.xmax, bb.ymax, 0)), "v", xr + 16, f"{bb.ylen:.2f}", tside="r")
    for hid, h in ids.items():
        if hid[0] in "DE":
            x, y, _ = h["pos"]
            centre_mark(ax, T.P((x, y, 0)), (1.6 if hid[0] == "D" else 1.25) * SCALE)
            off = {"D": (9, 7 if y > 0 else -7), "E": (9, -5)}[hid[0]]
            balloon(ax, T.P((x, y, 0)), T.P((x, y, 0)) + np.array([off[0] * np.sign(x), off[1]]), hid)
    e1, e2 = ids["E1"]["pos"], ids["E2"]["pos"]
    linear(ax, T.P(e1), T.P(e2), "h", yt + 11, f"{abs(e2[0] - e1[0]):.2f}")
    linear(ax, T.P((bb.xmin, 0, 0)), T.P((bb.xmin, e1[1], 0)), "v", xl - 9, f"{e1[1]:.2f}")
    linear(ax, T.P((bb.xmin, bb.ymin, 0)), T.P((bb.xmin, 0, 0)), "v", xl - 9, f"{-bb.ymin:.2f}")
    dp = sorted([h["pos"] for k, h in ids.items() if k[0] == "D"], key=lambda p: (p[1], p[0]))
    linear(ax, T.P(dp[1]), T.P(dp[3]), "v", xr + 8, f"{abs(dp[3][1] - dp[1][1]):.2f}", tside="r")
    origin_mark(ax, T.P((0, 0, 0)))
    section_marker(ax, T.P((-18.5, y_d, 0)), T.P((18.5, y_d, 0)), (0, 1), "B")
    section_marker(ax, T.P((0, -28.0, 0)), T.P((0, 30.5, 0)), (1, 0), "C")
    # side view: lengths of the levels (y) and their heights above the parting face
    ys = [up["outer_end_y"], -17.9, up["tower_face_y"], up["tower_face_y"] + up["wall_t"], 10.5, lp["body_y_pinion_end"], bb.ymax]
    base_y = S.P((0, 0, zpf))[1] - 8
    for a, b in zip(ys[:-1], ys[1:]):
        small = (b - a) < 5
        linear(ax, S.P((0, b, zpf)), S.P((0, a, zpf)), "h", base_y, f"{b - a:.2f}", inside=not small, shift=-7 if small else 0)
    xo = S.P((0, ys[0], zpf))[0]
    for z, yy, off in ((4.92, -21.0, 8), (17.8, -12.0, 16), (bb.zmax - zpf, -2.3, 24)):
        linear(ax, S.P((0, ys[0], zpf)), S.P((0, yy, zpf + z)), "v", xo + off, f"{z:.2f}", tside="r")
    linear(ax, S.P((0, bb.ymax, zpf)), S.P((0, 18.0, zpf + up["deck_h"])), "v", S.P((0, bb.ymax, 0))[0] - 8, f"{up['deck_h']:.2f}")
    rr = up["wall_root_r"]
    leader(ax, S.P((0, ys[2] - rr * (1 - np.sqrt(0.5)), zpf + 17.8 + rr * (1 - np.sqrt(0.5)))),
           S.P((0, ys[2], zpf + 17.8)) + (10, 8), f"R{rr:g} (2x)")
    iso_inset(fig, f"{OUT}/bulkhead_upper_T410R.stl", ISO_RECT, 125)
    text(ax, (328, 72), "Isometric view (not to scale)", fs=8, color="0.3")
    notes_short(ax, (24, 14))
    figs.append(fig)
    # ---------------- sheet 2
    fig, ax = sheet(tb, 2)
    A = View((0, 0, -1), (1, 0, 0), (90, 172))
    B = View((0, -1, 0), (1, 0, 0), (205, 198), om=(0, 0, zpf))
    C = View((-1, 0, 0), (0, -1, 0), (350, 198), om=(0, 0, zpf))
    draw_view(ax, solid, A)
    draw_section(ax, solid, B, (0, y_d, 0))
    draw_section(ax, solid, C, (0, 0, 0))
    top_a = A.P((0, bb.ymin, 0))[1]
    text(ax, (24, top_a + 9), "View A (from below, parting face)", fs=LABEL_FS, ha="left", weight="bold")
    view_label(ax, (B.op[0], 270), "Section B-B (diff axis)")
    view_label(ax, (C.P((0, 0, zpf))[0], 270), "Section C-C (pinion axis)")
    for hid, h in ids.items():
        if hid[0] == "D":
            x, y, _ = h["pos"]
            centre_mark(ax, A.P((x, y, 0)), 2.53 * SCALE)
            balloon(ax, A.P((x, y, 0)), A.P((x, y, 0)) + np.array([9 * np.sign(x), 6 * np.sign(-y)]), hid)
    centre_line(ax, A.P((-20, y_d, 0)), A.P((20, y_d, 0)))
    centre_line(ax, A.P((0, -28, 0)), A.P((0, 31, 0)))
    xra = A.P((bb.xmax, 0, 0))[0]
    linear(ax, A.P(dp[1]), A.P(dp[3]), "v", xra + 8, f"{abs(dp[3][1] - dp[1][1]):.2f}", tside="r")
    linear(ax, A.P(dp[0]), A.P(dp[1]), "h", A.P((0, bb.ymin, 0))[1] + 4, f"{abs(dp[1][0] - dp[0][0]):.2f}")
    linear(ax, A.P(dp[2]), A.P(dp[3]), "h", A.P((0, bb.ymax, 0))[1] - 6, f"{abs(dp[3][0] - dp[2][0]):.2f}")
    # section B-B (half bores above the parting face)
    seat_in, seat_out, lip_out = lp["diff_lip_inner_x"] - lp["diff_seat_width"], lp["diff_lip_inner_x"], bb.xmax
    bot = B.P((0, 0, zpf))[1]
    linear(ax, B.P((seat_in, 0, zpf)), B.P((seat_out, 0, zpf)), "h", bot - 6, f"{seat_out - seat_in:.2f}")
    linear(ax, B.P((seat_out, 0, zpf)), B.P((lip_out, 0, zpf)), "h", bot - 6, f"{lip_out - seat_out:.2f}", inside=False, shift=7)
    linear(ax, B.P((-seat_out, 0, zpf)), B.P((seat_out, 0, zpf)), "h", bot - 12, f"{2 * seat_out:.2f}")
    leader(ax, B.P((seat_in + 2.6, 0, zpf + 7.5)), B.P((bb.xmax, 0, zpf)) + (6, 48), "Ø15 H7 (2x)")
    leader(ax, B.P((-lip_out + 0.9, 0, zpf + lp["diff_lip_d"] / 2)), B.P((bb.xmin, 0, zpf)) + (-8, 20), "Ø12.28 (2x)", ha="right")
    leader(ax, B.P((-6.0, 0, zpf + 13.5)), B.P((bb.xmin, 0, zpf)) + (-8, 32), "R13.5", ha="right")
    leader(ax, B.P((7.0, 0, zpf + 16.4)), B.P((bb.xmax, 0, zpf)) + (6, 56), "R16.4")
    centre_line(ax, B.P((-20, 0, zpf)), B.P((20, 0, zpf)))
    ys = lp["pinion_seat_y_inner"]
    y1, y2, y3 = ys + 4.0, ys + 4.0 + lp["pinion_rib_t"], ys + lp["pinion_seat_length"]
    linear(ax, C.P((0, ys, zpf)), C.P((0, y1, zpf)), "h", bot - 6, f"{y1 - ys:.2f}")
    linear(ax, C.P((0, y1, zpf)), C.P((0, y2, zpf)), "h", bot - 12, f"{y2 - y1:.2f}", inside=False, shift=-11)
    linear(ax, C.P((0, y_d, zpf)), C.P((0, ys, zpf)), "h", bot - 12, f"{ys - y_d:.2f}")
    linear(ax, C.P((0, y2, zpf)), C.P((0, y3, zpf)), "h", bot - 18, f"{y3 - y2:.2f}")
    leader(ax, C.P((0, ys + 1.5, zpf + 5.0)), C.P((0, bb.ymax, zpf)) + (-6, 8), "Ø10 H7 (2x)", ha="right")
    leader(ax, C.P((0, (y1 + y2) / 2, zpf + lp["pinion_rib_d"] / 2)), C.P((0, bb.ymax, zpf)) + (-6, 16),
           f"rib Ø{lp['pinion_rib_d']:.2f} x {lp['pinion_rib_t']:.2f}", ha="right")
    leader(ax, C.P((0, 14.0, zpf + lp["pinion_pocket_r"])), C.P((0, bb.ymax, zpf)) + (-6, 24), f"R{lp['pinion_pocket_r']:g}", ha="right")
    centre_line(ax, C.P((0, -28, zpf)), C.P((0, 31, zpf)))
    text(ax, (140, 172), "Holes (x, y from O as on the lower part; z from the parting face)", ha="left", fs=8, weight="bold")
    y_end = hole_table(ax, 140, 169, rows)
    notes(ax, (24, 96), "upper", y_end)
    figs.append(fig)
    save(figs, pdf_path, png_stem)


def title_rows(title, subtitle, vol, date, number):
    mass = vol * DENSITY_7075
    return {"title": title, "subtitle": subtitle, "grid": [
        [("Drawn", AUTHOR), ("Date", date), ("Drawing number", f"RC-SR-{number}, revision A")],
        [("Material", "EN AW-7075-T6"), ("Quantity", "2 (End A and End B, same part)"), ("Scale", "2:1 (A3)")],
        [("General tolerances", "ISO 2768-mK"), ("Mass", f"{mass:.0f} g ({vol:.2f} cm³)"), ("Units", "mm")],
        [("Edges", "as modelled; break others 0.1 to 0.2"), ("Threads", "ISO M3 x 0.5, 6H"), ("Projection", "first angle")],
        [("Surface", "Ra 3.2, bearing seats Ra 1.6"), ("Model", "STEP = master geometry"), ("Status", "draft for the CNC order")],
    ]}


def notes_short(ax, P):
    text(ax, P, "Dimensions in mm. Dimensions that are not shown are taken from the STEP model. Hole sizes, threads "
         "and depths: hole table on sheet 2.", ha="left", va="bottom", fs=7.5)


def notes(ax, P, part, y_end):
    lines = [
        "Notes",
        "1. The STEP file is the master geometry. Dimensions that are not shown are taken from the model.",
        "2. Material EN AW-7075-T6. General tolerances ISO 2768-mK.",
        "3. Bearing seats (half bores): Ø15 H7 (diff, 10x15x4) and Ø10 H7 (pinion, 5x10x4). The bore axes lie",
        "    in the parting face: position of the axes to the parting face ±0.02. Flatness of the parting face 0.02.",
        "4. Threads ISO M3 x 0.5, tolerance 6H, depths as in the hole table. The model shows the tap drill Ø2.5.",
        "5. Edges: radii and chamfers as modelled (R1 in the vertical corners, chamfers 0.5 x 45°" +
        (", root radius R2 of the shock tower wall)." if part == "upper" else ")."),
        "    Break all other edges 0.1 to 0.2. Bearing seats and lips free of burrs.",
        "6. The inside of the part (cavities, floor opening, bearing seats, lips, rib, pinion pocket, holes," if part == "lower" else
        "6. The inside of the part (cavities, bearing seats, lips, rib, pinion pocket, holes, counterbores,",
        "    bosses) is verified with test prints and must not be changed." if part == "lower" else
        "    recesses) is verified with test prints and must not be changed.",
        "7. Tolerances of note 3: proposal, to be confirmed before the order.",
        "8. Coordinates: x across the car (diff axis), y along the pinion axis (+y to the pinion), O: centre",
        "    of the screw holes between the halves (y = ±21.30) and of the holes A1 to A4" + (" of the lower part." if part == "upper" else "."),
    ]
    x, y = P
    for i, s in enumerate(lines):
        text(ax, (x, y - i * 4.4), s, ha="left", va="top", fs=7.6 if i else 9, weight="bold" if i == 0 else "normal")


def main():
    parser = argparse.ArgumentParser(description="Technical drawings of the lower and the upper bulkhead.")
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    args = parser.parse_args()
    lp = load(f"{OUT}/bulkhead_lower_parameters.json")
    up = load(f"{OUT}/bulkhead_upper_parameters.json")
    lower_drawing(f"{OUT}/bulkhead_lower_technical_drawing.pdf", f"{OUT}/bulkhead_lower_technical_drawing", lp, args.date)
    print(f"Wrote {OUT}/bulkhead_lower_technical_drawing.pdf and _sheet_1.png, _sheet_2.png")
    upper_drawing(f"{OUT}/bulkhead_upper_technical_drawing.pdf", f"{OUT}/bulkhead_upper_technical_drawing", lp, up, args.date)
    print(f"Wrote {OUT}/bulkhead_upper_technical_drawing.pdf and _sheet_1.png, _sheet_2.png")


if __name__ == "__main__":
    main()
