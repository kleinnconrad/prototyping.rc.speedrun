"""Study: dual motor mount on the speedrun chassis plate (wide) with a second motor window on the left side.

The study is not part of the build: the parts of the speedrun chassis and the assembly are not changed.

* Dual motor mount: the verified motor mount (scripts/cad/generate_driveshaft.py) made symmetric: the tall part
  with the long holes of the motor shaft and of the motor screws on both sides of the bearing seat; the hook beside
  the bearing seat is replaced by the mirrored tall part. Plate 6.0 mm at y = 59.48 to 65.48 mm, bearing seat and
  cap unchanged. Threads M3 from below on H09, H10 and a new hole H37 (H09 mirrored).
* Study chassis plate: speedrun chassis plate (wide) with the longer motor window, plus the mirrored motor window
  on the left side (-x) and the new hole H37. The holes H12 and H15 lie in the new window; the holes H11 and H14
  keep a thin wall only and their countersinks open into the window: these 4 holes are closed.
* 2 motors 3660 (simple bodies: can 36 x 60 mm, shaft 5 mm) with pinions 48T 48DP (simplified tooth profile as the
  spur gear) on the spur gear 72T: standard centre distance plus a backlash of 0.15 mm, motor axes on the height of
  the pinion axis.

Outputs (in the directory of this script, or the directory given with --out):
* dual_motor_mount_study.step / .stl: dual motor mount in the part coordinates of the motor mount (x = 0 pinion
  axis, y = 0 middle of the plate of the mount, z = 0 bottom face of the mount)
* chassis_plate_dual_motor_study.step / .stl and chassis_plate_dual_motor_study_geometry.json: study chassis plate
  in the coordinates of the chassis plate
* dual_motor_study_assembly.step: assembly of the speedrun chassis (cad/assembly/speedrun_chassis_T410R.step) with
  the study chassis plate, the dual motor mount instead of the motor mount, the 2 motors, motor shafts and pinions
* dual_motor_study_assembly.png and dual_motor_study_drawing.png: shaded views and a drawing with the check results

The script checks the new and changed parts for interference with all parts of the assembly and reports clearances.

Usage (from the root directory of the repository, after generate_speedrun_assembly.py):
    python cad/studies/dual_motor/generate_dual_motor_study.py [--out <directory>] [--no-picture]

Requires the packages cadquery and matplotlib.
"""
import argparse
import json
import math
import os
import sys
import textwrap
import time

import numpy as np
import cadquery as cq

sys.path.insert(0, os.path.abspath("scripts/cad"))
import palette as P  # noqa: E402
from generate_bulkhead_lower import box, cyl_y, cyl_z, load_params  # noqa: E402
from generate_driveshaft import (LOWER, PARAMS, PLATE_T, INCH, layout, motor_axis_range,  # noqa: E402
                                 motor_mount_cap_solid, motor_mount_solid, mount_outline, section_polys)
from generate_solid import contour_samples, plate_solid  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ASSEMBLY = "cad/assembly/speedrun_chassis_T410R.step"
# battery of the build with its tray and straps (added after the study): not part of the study, which places 2
# batteries beside the ESCs (generate_dual_motor_electronics.py)
BUILD_BATTERY = ("battery", "speedrun_battery_tray", "velcro")
PLATE_GEOM = "cad/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_speedrun_wide_motor10_geometry.json"
PINION_TEETH = 48                       # 72T/48T = 1.50: same ratio as 68T/45T (over 130 km/h, spec_gearing.yaml)
PINION_FACE = 6.0                       # face width of the pinion (assumed)
PINION_HUB = (14.0, 1.8)                # hub of the pinion with the set screw: diameter, length (assumed)
BACKLASH = 0.15                         # centre distance above the standard value (the simplified teeth are clear)
MOTOR_D, MOTOR_L, MOTOR_SHAFT = 36.0, 60.0, 5.0       # 3660 motor (spec_brushless_combo.yaml)
NEW_HOLE = {"id": "H37", "x": -45.333, "y": 62.475}   # H09 mirrored
CLOSED_HOLES = ("H11", "H12", "H14", "H15")
DENSITY = {"6082": 2.70, "7075": 2.81}
COLOURS = {"dualmount": P.rgb("study"), "motor": P.rgb("motor"), "motorshaft": (0.75, 0.76, 0.78),   # palette.py
           "pinion": P.rgb("gear")}
HIDE_IN_CLOSEUP = ("speedrun top brace", "speedrun rear shock tower End B", "speedrun front shock tower End A")


# ------------------------------------------------------------------ parts
def mirror_seg(seg):
    kind, q = seg
    return kind, [(-x, z) for x, z in reversed(q)]


def dual_outline(p, lay):
    """Symmetric outline in the x-z plane: base, both tall parts (outline of the verified motor mount), top face of
    the low part between them."""
    right = mount_outline(p, lay)[1:8]           # bottom outer corner ... fillet to the top face of the low part
    xb_bot = right[0][1][0][0]                    # x of the start of the bottom outer corner
    xs_fil = right[-1][1][-1]                     # end of the fillet on the top face of the low part
    seg = [("line", [(-xb_bot, PLATE_T), (xb_bot, PLATE_T)])] + right
    seg.append(("line", [xs_fil, (-xs_fil[0], xs_fil[1])]))
    seg += [mirror_seg(s) for s in reversed(right)]
    return seg


def dual_mount_solid(p, lay):
    """Dual motor mount in chassis plate coordinates."""
    z, (m0, m1) = lay["z"], lay["mount"]
    zl = p["mount_low_top"]
    seg = dual_outline(p, lay)
    wp = cq.Workplane("XZ").moveTo(*seg[0][1][0])
    for kind, q in seg:
        if kind == "line":
            wp = wp.lineTo(*q[1])
        else:
            wp = wp.threePointArc(q[1], q[2])
    s = wp.close().extrude(m1 - m0).val().translate(cq.Vector(0, m1, 0))          # XZ: extrusion toward -y
    rb, (lw, ld) = p["mount_notch_d"] / 2, p["mount_lip"]
    s = s.cut(cyl_y(rb, m0 - 1, m1 - lw, 0, z)).cut(box(-rb, rb, m0 - 1, m1 - lw, z, zl + 1))   # U notch, bearing
    s = s.cut(cyl_y(ld / 2, m1 - lw - 1, m1 + 1, 0, z)).cut(box(-ld / 2, ld / 2, m1 - lw - 1, m1 + 1, z, zl + 1))  # lip

    def long_hole(x0, x1, zc, w):
        x0, x1 = sorted((x0, x1))
        h = cq.Workplane("XZ").center((x0 + x1) / 2, zc).slot2D(x1 - x0 + w, w).extrude(p["mount_t"] / 2 + 1, both=True)
        return h.val().translate(cq.Vector(0, p["mount_y"], 0))
    dz, up, lo = p["motor_screw_slots"]
    ws, wm = p["motor_screw_slot_w"], p["motor_shaft_slot_w"]
    for sx in (1, -1):
        for (hx0, hx1), hz, w in ((p["motor_slot_x"], z, wm), (up, z + dz, ws), (lo, z - dz, ws)):
            s = s.cut(long_hole(sx * hx0, sx * hx1, hz, w))
    rt, dep = p["tap_d"] / 2, p["mount_tap_depth"]
    for x, y in p["mount_bottom_screws"] + [[NEW_HOLE["x"], NEW_HOLE["y"]]]:
        s = s.cut(cyl_z(rt, PLATE_T - 1, PLATE_T + dep, x, y))
    for x, y in p["cap_screws"]:
        s = s.cut(cyl_z(rt, zl - dep, zl + 1, x, y))
    return s.clean()


def mirrored_contour(contour):
    out = []
    for prim in contour:
        q = dict(prim)
        for key in ("start", "mid", "end", "center"):
            if key in q:
                q[key] = [-q[key][0], q[key][1]]
        out.append(q)
    return out


def study_plate_geometry():
    """Geometry data of the chassis plate with the longer motor window, the mirrored window, H37 and without the
    closed holes. Returns (study geometry, original geometry)."""
    with open(PLATE_GEOM, encoding="utf-8") as f:
        g0 = json.load(f)
    g = json.loads(json.dumps(g0))
    g["basis"] = ("study: " + g0["basis"] + "; second motor window on the left side (mirrored), new hole H37 (H09 "
                  "mirrored), holes H11, H12, H14, H15 closed")
    g["cutouts"]["window_left"] = mirrored_contour(g0["cutouts"]["window"])
    g["holes"] = [h for h in g0["holes"] if h["id"] not in CLOSED_HOLES] + [dict(NEW_HOLE)]
    return g, g0


def gear_solid(n, m, face, phase, bore):
    """Gear with the simplified trapezoidal tooth profile of generate_driveshaft.spur_gear_solid, axis along +y from
    y = 0 to face, centre x = z = 0. The angle a in the gear plane points in the direction (cos a, 0, -sin a)."""
    rp = n * m / 2
    rt, rr = rp + m, rp - 1.25 * m
    tan20 = np.tan(np.radians(20.0))
    half_tip = (np.pi * m / 4 - m * tan20) / rt
    half_root = (np.pi * m / 4 + 1.25 * m * tan20) / rr
    pts = []
    for k in range(n):
        c = phase + 2 * np.pi * k / n
        for a, r in ((c - half_root, rr), (c - half_tip, rt), (c + half_tip, rt), (c + half_root, rr)):
            pts.append((r * np.cos(a), r * np.sin(a)))
    g = cq.Workplane("XY").polyline(pts).close().extrude(face).val()
    g = g.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -90)
    return g.cut(cyl_y(bore / 2, -1, face + 1, 0, 0)).clean()


def motor_parts(p, lay, sx, centre):
    """Motor 3660 (simple body) with shaft and pinion at the side sx (+1 right, -1 left): list of (name, key, solid).
    The motor face lies on the mount; the pinion is centred on the spur gear. Pinion phase: a tooth gap faces the
    spur gear (the spur gear has a tooth at +x and at -x)."""
    z, (m0, m1) = lay["z"], lay["mount"]
    xm = sx * centre
    side = "right" if sx > 0 else "left"
    r = MOTOR_D / 2
    can = cyl_y(r, m1, m1 + MOTOR_L, xm, z)
    ch = 1.0                                                    # chamfers at both ends of the can
    for y0, dy in ((m1, 1), (m1 + MOTOR_L, -1)):
        ring = cq.Solid.makeCone(r - ch, r + 0.01, ch, cq.Vector(xm, y0, z), cq.Vector(0, dy, 0))
        can = can.cut(cyl_y(r + 1, min(y0, y0 + dy * ch), max(y0, y0 + dy * ch), xm, z).cut(ring))
    m = INCH / p["spur_dp"]
    yp0 = sum(lay["spur"]) / 2 - PINION_FACE / 2
    shaft = cyl_y(MOTOR_SHAFT / 2, yp0, m1, xm, z).fuse(cyl_y(MOTOR_SHAFT / 2, m1 + MOTOR_L, m1 + MOTOR_L + 3.0, xm, z))
    pinion = gear_solid(PINION_TEETH, m, PINION_FACE, np.pi / PINION_TEETH, MOTOR_SHAFT)
    pinion = pinion.fuse(cyl_y(PINION_HUB[0] / 2, PINION_FACE, PINION_FACE + PINION_HUB[1], 0, 0)
                         .cut(cyl_y(MOTOR_SHAFT / 2, PINION_FACE - 1, PINION_FACE + PINION_HUB[1] + 1, 0, 0))).clean()
    pinion = pinion.translate(cq.Vector(xm, yp0, z))
    return [(f"motor 3660 {side}", "motor", can.clean()), (f"motor shaft {side}", "motorshaft", shaft.clean()),
            (f"pinion {PINION_TEETH}T {side}", "pinion", pinion)]


def read_assembly(path):
    """Parts of an assembly STEP file: list of (name, shape, colour as linear RGB or None)."""
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TDocStd import TDocStd_Document
    from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType
    from OCP.TDF import TDF_Label, TDF_LabelSequence
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.Quantity import Quantity_Color
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetColorMode(True)
    reader.ReadFile(path)
    reader.Transfer(doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ctool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    kinds = (XCAFDoc_ColorType.XCAFDoc_ColorSurf, XCAFDoc_ColorType.XCAFDoc_ColorGen)
    labels = TDF_LabelSequence()
    tool.GetFreeShapes(labels)
    out = []

    def colour(lab, shape):
        col = Quantity_Color()
        ref = TDF_Label()
        targets = [lab] + ([ref] if tool.GetReferredShape_s(lab, ref) else [])
        for t in targets:
            for ct in kinds:
                if ctool.GetColor_s(t, ct, col):
                    return col.Red(), col.Green(), col.Blue()
        for ct in kinds:
            if ctool.GetColor(shape, ct, col):
                return col.Red(), col.Green(), col.Blue()
        return None

    def walk(lab):
        if tool.IsAssembly_s(lab):
            comps = TDF_LabelSequence()
            tool.GetComponents_s(lab, comps)
            for i in range(1, comps.Length() + 1):
                walk(comps.Value(i))
            return
        name = TDataStd_Name()
        nm = name.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), name) else ""
        shape = tool.GetShape_s(lab)
        out.append((nm, cq.Shape.cast(shape), colour(lab, shape)))
    for i in range(1, labels.Length() + 1):
        walk(labels.Value(i))
    return out


def srgb(c):
    """Linear RGB of the STEP file to the display colour."""
    return tuple(min(1.0, max(0.0, v)) ** (1 / 2.2) for v in c) if c else (0.6, 0.6, 0.6)


# ------------------------------------------------------------------ pictures
def tess(shape, tol=0.05):
    verts, idx = shape.tessellate(tol, 0.2)
    v = np.array([[q.x, q.y, q.z] for q in verts])
    return v[np.array(idx)]


def mesh(parts, region=None, hidden=(), edge=2.0, tol=0.05):
    """Triangles and colours of the parts, optionally cut to the box region (x0, y0, z0, dx, dy, dz)."""
    from mesh_views import subdivide
    tris, cols = [], []
    reg = cq.Solid.makeBox(region[3], region[4], region[5], cq.Vector(*region[:3])) if region else None
    for name, key, s, col in parts:
        if name in hidden:
            continue
        if reg is not None:
            bb = s.BoundingBox()
            x0, y0, z0, dx, dy, dz = region
            if bb.xmin > x0 + dx or bb.xmax < x0 or bb.ymin > y0 + dy or bb.ymax < y0 or bb.zmin > z0 + dz or bb.zmax < z0:
                continue
            s = s.intersect(reg)
            if s.Volume() < 1e-3:
                continue
        t = subdivide(tess(s, tol), 6.0 if "chassis plate" in name else edge)
        tris.append(t)
        cols.append(np.tile(col, (len(t), 1)))
    return np.concatenate(tris), np.concatenate(cols)


def view(ax, tris, cols, basis, title, pad=2):
    from mesh_views import draw_mesh
    lo, hi = draw_mesh(ax, tris, basis, tri_colors=cols, depth_cue=0.3)
    ax.set_xlim(lo[0] - pad, hi[0] + pad)
    ax.set_ylim(lo[1] - pad, hi[1] + pad)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=10, loc="left")
    return lo, hi


def assembly_picture(path, parts):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from mesh_views import iso_basis
    fig = plt.figure(figsize=(16, 13))
    fig.suptitle("Study: dual motor mount on the speedrun chassis plate (wide) with a second motor window on the left "
                 "side (not part of the build)", fontsize=13, y=0.985)
    tris, cols = mesh(parts)
    ax = fig.add_axes([0.0, 0.47, 0.6, 0.47])
    view(ax, tris, cols, iso_basis(-35, 28), "Complete build with 2 motors 3660 (simple bodies, blue) and the dual "
                                             "motor mount (bright blue)")
    top = tuple(np.asarray(v, float) for v in ((0, 0, -1), (1, 0, 0), (0, 1, 0)))
    tb, cb = mesh(parts, (-101, -12, -5, 202, 150, 80), edge=1.5, tol=0.03)
    ax = fig.add_axes([0.6, 0.47, 0.4, 0.47])
    lo, hi = view(ax, tb, cb, top, "Top view of End B (y = -12 to 138 mm)")
    ax.text(lo[0] + 2, hi[1] - 2, "left side (-x)", fontsize=9, va="top")
    ax.text(hi[0] - 2, hi[1] - 2, "right side (+x)", fontsize=9, va="top", ha="right")
    ax.text(0, lo[1] - 1, "End B", fontsize=9, ha="center", va="top")
    ax.set_ylim(lo[1] - 7, hi[1] + 2)
    # drive line seen from End B, cut at y = 50.5 (bulkhead, pinion seat and top brace not shown)
    tc, cc = mesh(parts, (-62, 50.5, -4, 124, 80, 48), hidden=HIDE_IN_CLOSEUP, edge=1.0, tol=0.02)
    ax = fig.add_axes([0.0, 0.01, 0.5, 0.43])
    view(ax, tc, cc, iso_basis(-108, 22), f"Spur gear 72T with 2 pinions {PINION_TEETH}T, dual motor mount with cap, "
                                          "view from End B\n(section at y = 50.5 mm; bulkhead, top brace and shock "
                                          "tower not shown)")
    below = tuple(np.asarray(v, float) for v in ((0, 0, 1), (-1, 0, 0), (0, 1, 0)))
    td, cd = mesh(parts, (-80, 40, -5, 160, 100, 45), hidden=HIDE_IN_CLOSEUP, edge=1.5, tol=0.03)
    ax = fig.add_axes([0.52, 0.01, 0.47, 0.43])
    lo, hi = view(ax, td, cd, below, "View from below (y = 40 to 140 mm): motors 0.8 mm deep in both motor windows")
    ax.text(lo[0] + 2, hi[1] - 1, "right side (+x)", fontsize=9, va="top")
    ax.text(hi[0] - 2, hi[1] - 1, "left side (-x)", fontsize=9, va="top", ha="right")
    handles = [Patch(color=COLOURS[k], label=t) for k, t in (("dualmount", "dual motor mount (study)"),
                                                            ("motor", "motors 3660 (simple bodies: can 36 x 60 mm)"),
                                                            ("pinion", f"pinions {PINION_TEETH}T 48DP (simplified "
                                                                       "teeth)"))]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.01, 0.955), fontsize=9, frameon=False, ncol=3)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def prims_polyline(prims):
    pts = []
    for q in prims:
        pts += [tuple(pt) for pt, _ in contour_samples(q, 2 if q["type"] == "line" else 24)]
    return pts


def drawing(path, r):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon as MPoly
    p, lay, centre, dual, cap, geom, g0 = (r[k] for k in ("p", "lay", "centre", "dual", "cap", "geom", "geom0"))
    m = INCH / p["spur_dp"]
    spur_od, pinion_od = (p["spur_teeth"] + 2) * m, (PINION_TEETH + 2) * m
    fig = plt.figure(figsize=(16, 11.3))
    fig.suptitle("Study: dual motor mount and chassis plate with 2 motor windows (not part of the build)", fontsize=13,
                 y=0.985)
    z, yv = lay["z"], p["mount_y"]
    # ---- dual motor mount from the motor side
    ax = fig.add_axes([0.04, 0.47, 0.55, 0.47])
    for solid, col in ((dual, P.hexcolor("study")), (cap, "#b3b8bf")):
        sec = section_polys(solid, "y", yv)
        for outer, poly in sec:
            if outer:
                ax.add_patch(MPoly(poly, closed=True, fc=col, ec="#1d2025", lw=0.6))
        for outer, poly in sec:
            if not outer:
                ax.add_patch(MPoly(poly, closed=True, fc="white", ec="#1d2025", lw=0.6))
    ax.add_patch(Circle((0, z), spur_od / 2, fill=False, ec="#5d636b", lw=0.8, ls="--"))
    dz = p["motor_screw_slots"][0]
    dx = math.sqrt((p["motor_screw_spacing"] / 2) ** 2 - dz ** 2)
    x0, x1 = r["range"]
    for sx in (1, -1):
        xm = sx * centre
        ax.add_patch(Circle((xm, z), MOTOR_D / 2, fill=False, ec="#2c5d8a", lw=0.9, ls=":"))
        ax.add_patch(Circle((xm, z), pinion_od / 2, fill=False, ec=P.hexcolor("gear"), lw=0.8, ls="--"))
        ax.plot([xm], [z], "+", color="#2c5d8a", ms=8)
        for xx, zz in ((xm - sx * dx, z + dz), (xm + sx * dx, z - dz)):        # motor screws on the diagonal
            ax.add_patch(Circle((xx, zz), 1.5, fill=False, ec="#2c5d8a", lw=0.7))
        ax.annotate("", (sx * x0, -4.0), (sx * x1, -4.0), arrowprops=dict(arrowstyle="<->", lw=0.7))
        ax.text(sx * (x0 + x1) / 2, -4.6, f"usable motor axis\n{x0:.2f} to {x1:.2f}", ha="center", va="top",
                fontsize=7.5)
        ax.text(xm, z - pinion_od / 2 - 0.5, f"pinion {PINION_TEETH}T", ha="center", va="top", fontsize=7,
                color="#3d4a5c")
    ax.annotate("", (-centre, 46.0), (centre, 46.0), arrowprops=dict(arrowstyle="<->", lw=0.7))
    ax.text(0, 46.4, f"motor axes {2 * centre:.2f} (x = +-{centre:.2f}), z = {z:.2f}", ha="center", va="bottom",
            fontsize=8)
    bb, bs = dual.BoundingBox(), r["single"].BoundingBox()
    ax.annotate("", (bb.xmin, 53.0), (bb.xmax, 53.0), arrowprops=dict(arrowstyle="<->", lw=0.7))
    ax.text(0, 53.4, f"{bb.xmax - bb.xmin:.1f} (single mount: {bs.xmax - bs.xmin:.1f})", ha="center", va="bottom",
            fontsize=8)
    ax.annotate("", (bb.xmax + 3, PLATE_T), (bb.xmax + 3, bb.zmax), arrowprops=dict(arrowstyle="<->", lw=0.7))
    ax.text(bb.xmax + 3.6, 18.5, f"{bb.zmax - PLATE_T:.1f}", rotation=90, va="center", fontsize=8)
    screws = [(x, "H09" if x > 1 else "H10") for x, _ in p["mount_bottom_screws"]] + [(NEW_HOLE["x"], "H37 (new)")]
    for x, lab in screws:
        ax.plot([x, x], [-1.0, 9.0], color="#c0392b", lw=0.8, ls="-.")
        ax.text(x, -1.3, lab, ha="center", va="top", fontsize=7.5, color="#c0392b")
    ax.text(0, 4.0, "bearing in\nthe U notch", ha="center", va="center", fontsize=7)
    ax.annotate("cap (unchanged, 2 x M3x18 from the top brace)", (-p["cap_w"] / 2 + 1, p["mount_low_top"] + 6),
                (-58, 41), fontsize=7.5, ha="left", va="center", arrowprops=dict(arrowstyle="-", lw=0.5))
    ax.text(centre + 12, z + 21, f"motors 3660 (dotted),\npinions {PINION_TEETH}T (dashed)", fontsize=7.5, ha="left")
    ax.text(0, z + spur_od / 2 + 0.5, f"spur gear {p['spur_teeth']:g}T (dashed)", ha="center", va="bottom",
            fontsize=7)
    ax.axhline(PLATE_T, color="#666", lw=0.6)
    ax.axhline(0.0, color="#666", lw=0.6)
    ax.text(-70, 0.9, "chassis plate", fontsize=7, va="center")
    ax.set_xlim(-72, 72)
    ax.set_ylim(-12, 58)
    ax.set_aspect("equal")
    ax.grid(True, color="#eeeeee", lw=0.5)
    ax.set_title(f"Dual motor mount from the motor side (section y = {yv:.2f}; the motors are behind the mount)",
                 fontsize=10, loc="left")
    ax.set_xlabel("x [mm] (across the car; + right side)", fontsize=8)
    # ---- study chassis plate, top view
    ax = fig.add_axes([0.645, 0.04, 0.35, 0.91])
    ax.add_patch(MPoly(prims_polyline(geom["outline"]), closed=True, fc="#d9dce1", ec="#1d2025", lw=0.8))
    for name, c in geom["cutouts"].items():
        new = name == "window_left"
        ax.add_patch(MPoly(prims_polyline(c), closed=True, fc="white", ec="#c0392b" if new else "#1d2025",
                           lw=1.2 if new else 0.8))
    m0, m1 = lay["mount"]
    ax.add_patch(MPoly([(bb.xmin, m0), (bb.xmax, m0), (bb.xmax, m1), (bb.xmin, m1)], closed=True, fc=P.hexcolor("study"),
                       ec="#1d2025", lw=0.6, alpha=0.45, zorder=1))
    ax.text(bb.xmax + 1.5, m0 - 1.0, "dual motor\nmount", ha="left", va="top", fontsize=7)
    ids = {h["id"] for h in geom["holes"]}
    for h in g0["holes"] + [dict(NEW_HOLE)]:
        if h["y"] > 236:
            continue
        x, y = h["x"], h["y"]
        if h["id"] not in ids:
            ax.plot([x - 2, x + 2], [y - 2, y + 2], color="#c0392b", lw=1.2)
            ax.plot([x - 2, x + 2], [y + 2, y - 2], color="#c0392b", lw=1.2)
            left = x < -30
            ax.text(x - 3.0 if left else x + 3.0, y, h["id"] + "\nclosed", ha="right" if left else "left", va="center",
                    fontsize=7, color="#c0392b", zorder=5)
            continue
        new = h["id"] == NEW_HOLE["id"]
        ax.add_patch(Circle((x, y), geom["hole_d"] / 2, fc="white", ec="#1e8449" if new else "#1d2025",
                            lw=1.2 if new else 0.7))
        ax.add_patch(Circle((x, y), geom["csk_d"] / 2, fill=False, ec="#888", lw=0.5, ls="--"))
        ax.text(x + 3.6, y + (2.6 if abs(y - NEW_HOLE["y"]) < 1 else 0), h["id"] + (" (new)" if new else ""),
                fontsize=7, va="center", color="#1e8449" if new else "#1d2025", zorder=5)
    for sx in (1, -1):
        xm = sx * centre
        ax.add_patch(MPoly([(xm - MOTOR_D / 2, m1), (xm + MOTOR_D / 2, m1), (xm + MOTOR_D / 2, m1 + MOTOR_L),
                            (xm - MOTOR_D / 2, m1 + MOTOR_L)], closed=True, fill=False, ec="#2c5d8a", lw=0.9, ls=":"))
        ax.text(xm + sx * 3.5, m1 + MOTOR_L / 2 + 3, "motor 3660 (dotted)", ha="center", va="center", fontsize=7,
                color="#2c5d8a", rotation=90)
    wl = prims_polyline(geom["cutouts"]["window_left"])
    ax.annotate("new motor window\n(window of the right\nside mirrored)",
                (min(q[0] for q in wl), (min(q[1] for q in wl) + max(q[1] for q in wl)) / 2 + 20),
                (-98, 160), fontsize=7.5, color="#c0392b", arrowprops=dict(arrowstyle="-", lw=0.6, color="#c0392b"))
    ax.text(-98, 236, "left side: battery on the car (photo),\nholes H11 to H23", fontsize=7.5, va="top")
    ax.set_xlim(-102, 102)
    ax.set_ylim(-4, 238)
    ax.set_aspect("equal")
    ax.grid(True, color="#eeeeee", lw=0.5)
    ax.set_title("Chassis plate (study), y = 0 to 236 mm, top view", fontsize=10, loc="left")
    ax.set_xlabel("x [mm] (+ right side)", fontsize=8)
    ax.set_ylabel("y [mm] (End B at y = 0)", fontsize=8)
    # ---- notes: headings and items ("* ...")
    y = 0.445
    for item in r["notes"]:
        if not item.startswith("*"):
            y -= 0.006
            fig.text(0.04, y, item, fontsize=9.5, va="top", weight="bold")
            y -= 0.024
            continue
        for k, line in enumerate(textwrap.wrap(item[1:].strip(), 142)):
            fig.text(0.04, y, ("- " if k == 0 else "  ") + line, fontsize=8.6, va="top")
            y -= 0.0178
    fig.savefig(path, dpi=110)
    plt.close(fig)


# ------------------------------------------------------------------ main
def build_and_check(out):
    t0 = time.time()
    p, lp = load_params(PARAMS), load_params(LOWER)
    lay = layout(p, lp)
    m = INCH / p["spur_dp"]
    centre = (p["spur_teeth"] + PINION_TEETH) / 2 * m + BACKLASH
    x0, x1 = motor_axis_range(p)
    assert x0 <= centre <= x1, f"motor axis {centre:.2f} outside the range {x0:.2f} to {x1:.2f}"
    single, dual, cap = motor_mount_solid(p, lay), dual_mount_solid(p, lay), motor_mount_cap_solid(p, lay)
    geom, geom0 = study_plate_geometry()
    plate, plate0 = plate_solid(geom).val(), plate_solid(geom0).val()
    motors = motor_parts(p, lay, 1, centre) + motor_parts(p, lay, -1, centre)
    print(f"motor axes x = +-{centre:.2f} mm, z = {lay['z']:.2f} mm; usable range of the mount {x0:.2f} to {x1:.2f} mm")
    # part files
    with open(os.path.join(out, "chassis_plate_dual_motor_study_geometry.json"), "w", encoding="utf-8") as f:
        json.dump(geom, f, indent=1)
    to_part = dual.translate(cq.Vector(0, -p["mount_y"], -PLATE_T))       # part coordinates of the motor mount
    for name, s in (("dual_motor_mount_study", to_part), ("chassis_plate_dual_motor_study", plate)):
        cq.exporters.export(s, os.path.join(out, name + ".step"))
        cq.exporters.export(s, os.path.join(out, name + ".stl"), tolerance=0.01, angularTolerance=0.1)
    vol_d, vol_s, vol_p, vol_p0 = (s.Volume() / 1000 for s in (dual, single, plate, plate0))
    bb = dual.BoundingBox()
    print(f"dual motor mount: valid {dual.isValid()}, {bb.xmax - bb.xmin:.1f} x {bb.ymax - bb.ymin:.1f} x "
          f"{bb.zmax - bb.zmin:.1f} mm, {vol_d:.2f} cm3, 7075 {vol_d * DENSITY['7075']:.1f} g "
          f"(single mount {vol_s:.2f} cm3, {vol_s * DENSITY['7075']:.1f} g)")
    print(f"study chassis plate: valid {plate.isValid()}, {vol_p:.2f} cm3, 6082 {vol_p * DENSITY['6082']:.0f} g "
          f"(plate with one motor window {vol_p0:.2f} cm3, {vol_p0 * DENSITY['6082']:.0f} g)")
    # walls of the holes beside the new window
    wl = prims_polyline(geom["cutouts"]["window_left"])
    wx0, wx1 = min(q[0] for q in wl), max(q[0] for q in wl)
    wy0, wy1 = min(q[1] for q in wl), max(q[1] for q in wl)
    walls = {h["id"]: wx0 - h["x"] - geom["hole_d"] / 2 for h in geom0["holes"]
             if h["id"] in CLOSED_HOLES and h["x"] < wx0}
    print("closed holes: " + ", ".join(f"{h} wall {w:.2f} mm" for h, w in walls.items()) + "; the others lie in the window")
    # assembly: study chassis plate and dual motor mount instead of the parts of the build, motors added
    parts = []
    for nm, s, col in read_assembly(ASSEMBLY):
        if nm.startswith(BUILD_BATTERY):
            continue                       # the study has its own batteries (electronics layout) instead of the build's
        if nm == "chassis_plate":
            parts.append(("chassis plate (study, 2 motor windows)", "plate", plate, srgb(col)))
        elif nm == "motor_mount":
            parts.append(("dual motor mount (study)", "dualmount", dual, COLOURS["dualmount"]))
        else:
            parts.append((nm.replace("_", " "), "base", s, srgb(col)))
    parts += [(n, k, s, COLOURS[k]) for n, k, s in motors]
    # interference: the new and changed parts with all parts
    new = [q for q in parts if q[1] != "base"]
    boxes = [q[2].BoundingBox() for q in parts]
    worst = 0.0
    for i, a in enumerate(parts):
        if a[1] == "base":
            continue
        for j, b in enumerate(parts):
            if j == i or (b[1] != "base" and j < i):
                continue
            ba, bo = boxes[i], boxes[j]
            if ba.xmin > bo.xmax or bo.xmin > ba.xmax or ba.ymin > bo.ymax or bo.ymin > ba.ymax \
                    or ba.zmin > bo.zmax or bo.zmin > ba.zmax:
                continue                                         # bounding boxes apart: no overlap possible
            v = a[2].intersect(b[2]).Volume()
            worst = max(worst, v)
            if v > 1e-4:
                print(f"  interference {a[0]} / {b[0]}: {v:.4f} mm3")
    print(f"interference check of the {len(new)} new or changed parts with all {len(parts)} parts: largest "
          f"{worst:.4f} mm3")
    names = {q[0]: q[2] for q in parts}
    ml, mr, pl, pt = "motor 3660 left", "dual motor mount (study)", f"pinion {PINION_TEETH}T left", "chassis plate " \
        "(study, 2 motor windows)"
    cl = {}
    for a, b in ((ml, pt), (ml, "speedrun top brace"), (ml, "cup joint End B"), (ml, "motor 3660 right"),
                 (pl, "spur gear"), (pl, mr), (pl, "lower bulkhead End B"), (pl, "upper bulkhead End B"),
                 (mr, "speedrun top brace"), (mr, "upper bulkhead End B")):
        cl[(a, b)] = names[a].distance(names[b])
        print(f"  clearance {a} / {b}: {cl[(a, b)]:.2f} mm")
    assy = cq.Assembly(name="dual_motor_study")
    for i, (nm, key, s, col) in enumerate(parts):
        assy.add(s, name=f"{nm.replace(' ', '_')}_{i}", color=cq.Color(*[c ** 2.2 for c in col]))
    from cadquery.occ_impl.exporters.assembly import exportAssembly
    exportAssembly(assy, os.path.join(out, "dual_motor_study_assembly.step"))
    print(f"wrote the part files and the assembly in {out} ({time.time() - t0:.0f} s)")
    closed = ", ".join(h for h in CLOSED_HOLES if h not in walls)
    thin = " and ".join(walls)
    notes = [
        "Design (study, not part of the build)",
        f"* Dual motor mount: the verified motor mount with the tall part mirrored to the left side instead of the "
        f"hook; plate {p['mount_t']:g} mm (y = {lay['mount'][0]:.2f} to {lay['mount'][1]:.2f} mm), "
        f"{bb.xmax - bb.xmin:.1f} mm wide, {bb.zmax - PLATE_T:.1f} mm above the chassis plate. Bearing seat, cap and "
        f"screws of the cap unchanged. 3 screws M3 from below: H09, H10 and the new hole H37 (H09 mirrored).",
        f"* Motors: 2 x 3660 (simple bodies {MOTOR_D:g} x {MOTOR_L:g} mm) at x = +-{centre:.2f} mm, z = "
        f"{lay['z']:.2f} mm (pinion axis); pinions {PINION_TEETH}T on the spur gear {p['spur_teeth']:g}T (ratio "
        f"{p['spur_teeth'] / PINION_TEETH:.2f}, as 45T on 68T), centre distance {centre - BACKLASH:.2f} mm + "
        f"{BACKLASH:.2f} mm backlash. Usable range of the long holes per side: {x0:.2f} to {x1:.2f} mm. Both motors "
        f"turn in the same direction.",
        f"* Chassis plate (study): left motor window = right window mirrored (x = {wx0:.2f} to {wx1:.2f} mm, y = "
        f"{wy0:.2f} to {wy1:.2f} mm). {closed.replace(', ', ' and ')} lie in the window; {thin} keep walls of "
        f"{' and '.join(f'{w:.2f}' for w in walls.values())} mm and their countersinks open into the window: these {len(CLOSED_HOLES)} holes "
        f"are closed.",
        "Checks",
        f"* No overlap of the new or changed parts (plate, mount, 2 motors, 2 shafts, 2 pinions) with the "
        f"{len(parts) - len(new)} other parts of the assembly (largest {worst:.4f} mm3).",
        f"* Clearances: motor to chassis plate {cl[(ml, pt)]:.2f} mm (between the mount face and the window, as with "
        f"the single mount), motor to top brace {cl[(ml, 'speedrun top brace')]:.2f} mm, motor to cup joint End B "
        f"{cl[(ml, 'cup joint End B')]:.2f} mm, between the motors {cl[(ml, 'motor 3660 right')]:.1f} mm, pinion to "
        f"spur gear {cl[(pl, 'spur gear')]:.2f} mm, pinion to bulkheads {cl[(pl, 'lower bulkhead End B')]:.2f} mm, "
        f"pinion to mount {cl[(pl, mr)]:.2f} mm, mount to top brace {cl[(mr, 'speedrun top brace')]:.2f} mm.",
        f"* Mass: dual mount {vol_d * DENSITY['7075']:.1f} g in 7075 (single mount {vol_s * DENSITY['7075']:.1f} g); "
        f"chassis plate {vol_p * DENSITY['6082']:.0f} g in 6082 (plate with one window "
        f"{vol_p0 * DENSITY['6082']:.0f} g).",
        "Open points",
        "* Battery: on the car the battery lies on the left side (photo); the left motor takes this place. A new "
        "battery position is needed.",
        "* 2 ESCs (or one ESC for 2 motors) with the same throttle signal; torque on the spur gear, the pinion shaft "
        "and the drive line doubles (not evaluated).",
        f"* The motor axes are fixed by the spur gear: x = +-{x0:.2f} to {x1:.2f} mm, so the left window cannot be "
        f"moved clear of H11 to H15.",
    ]
    return {"parts": parts, "p": p, "lay": lay, "centre": centre, "range": (x0, x1), "dual": dual, "single": single,
            "cap": cap, "geom": geom, "geom0": geom0, "notes": notes}


def main():
    parser = argparse.ArgumentParser(description="Dual motor study: parts, assembly, checks and pictures.")
    parser.add_argument("--out", default=HERE, help="output directory (default: the directory of this script)")
    parser.add_argument("--no-picture", action="store_true", help="skip the pictures")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    r = build_and_check(args.out)
    if not args.no_picture:
        assembly_picture(os.path.join(args.out, "dual_motor_study_assembly.png"), r["parts"])
        drawing(os.path.join(args.out, "dual_motor_study_drawing.png"), r)
        print(f"wrote dual_motor_study_assembly.png and dual_motor_study_drawing.png in {args.out}")


if __name__ == "__main__":
    main()
