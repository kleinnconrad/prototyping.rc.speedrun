"""Generate the centre driveshaft of the Carten T410R (NHA413) (stock part, not part of the speedrun
design) and the simple bodies of the drive line around it for the assembly picture.

The centre driveshaft connects the cup joints of the two pinion shafts. Each ball end carries a
metal pin (NBA255 2.0x7.6), which is fixed on the shaft and runs in the slots of the cup joint, so
the shaft turns with the cup joints. In the centred position, each pin has half of the axial play
to the closed end of its slot, so the shaft can move a little back and forth.

* End A: the cup joint sits on the front pinion shaft beside the bulkhead.
* End B (motor): the rear pinion shaft NBA205 runs from the pinion in the bulkhead through a
  flange with the spur gear and the bearing NBA298 in the motor mount NBA201 (manual steps 5, 10
  and 12). The cup joint sits on its end beyond the motor mount.

Derived from the models of this project: the pinion axis, the end faces of the pinion housings,
the motor mount (holes H09/H10 of the chassis plate) and the spur gear (slot of the chassis plate
below the pinion axis). Cup joints: measurements of the owner. The other dimensions are typical
values (cad/stock_parts/driveshaft/driveshaft_parameters.json). The shaft is a stock part: it is
not part of the speedrun design and is modelled for the completeness of the build. The cup
joints, the rear drive line, the motor mount with its cap and the diff outdrives are stock parts as
well; the script writes the STEP and STL files of all these parts.

Usage (from the root directory of the repository):
    python scripts/cad/generate_driveshaft.py

The script writes the STEP and STL files of all parts (cad/stock_parts/driveshaft, rear_drive,
motor_mount and diff_outdrive) and the drawing photos/cad_driveshaft_drawing.png, and checks the
play and the fit.

Requires the packages cadquery and matplotlib.
"""
import argparse
import json
import os
import sys

import numpy as np
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_bulkhead_lower import box, bulkhead_lower, cyl_x, cyl_y, cyl_z, load_params  # noqa: E402
from generate_bulkhead_upper import bulkhead_upper  # noqa: E402
from generate_top_brace_speedrun import BULKHEAD_Y, GEOM as BRACE_GEOM, brace_offset, brace_solid  # noqa: E402

PARAMS = "cad/stock_parts/driveshaft/driveshaft_parameters.json"
LOWER = "cad/bulkhead/bulkhead_lower_parameters.json"
UPPER = "cad/bulkhead/bulkhead_upper_parameters.json"
PLATE_STEP = "cad/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_T410R_speedrun_wide_motor10.step"
STOCK = "cad/stock_parts"
DRAWING = "photos/cad_driveshaft_drawing.png"
PLATE_T = 2.0
INCH = 25.4


def layout(p, lp):
    """Positions on the chassis plate (y along the car, End B at y = 0): pinion axis height, end
    faces of the pinion housings, motor mount, spur gear, cup joints (back face, open end, closed end
    of the slots), metal pins and shaft ends in the centred position. Index 0: End B, 1: End A."""
    he = lp["pinion_seat_y_inner"] + lp["pinion_seat_length"]   # end face of the pinion housing
    housing = (BULKHEAD_Y["rear"] + he, BULKHEAD_Y["front"] - he)
    mount = (p["mount_y"] - p["mount_t"] / 2, p["mount_y"] + p["mount_t"] / 2)
    back = (mount[1] + p["rear_cup_gap"], housing[1] - p["cup_gap"])
    open_end = (back[0] + p["cup_length"], back[1] - p["cup_length"])
    slot_end = (open_end[0] - p["cup_slot_len"], open_end[1] + p["cup_slot_len"])
    bottom = (open_end[0] - p["cup_bore_depth"], open_end[1] + p["cup_bore_depth"])
    dp = p["pin_d"] / 2 + p["axial_play"] / 2
    pins = (slot_end[0] + dp, slot_end[1] - dp)
    r = p["ball_d"] / 2
    shaft = (pins[0] - r, pins[1] + r)
    flange = (housing[0] + p["flange_gap"], housing[0] + p["flange_gap"] + p["flange_t"])
    spur = (flange[1], flange[1] + p["spur_t"])           # spur gear on the collar, against the flange
    seat = (BULKHEAD_Y["rear"] + lp["pinion_seat_y_inner"], BULKHEAD_Y["front"] - lp["pinion_seat_y_inner"])
    return {"z": PLATE_T + lp["axis_z"], "housing": housing, "seat": seat, "mount": mount, "spur": spur, "flange": flange,
            "spur_od": (p["spur_teeth"] + 2) / p["spur_dp"] * INCH, "back": back, "open": open_end,
            "slot_end": slot_end, "bottom": bottom, "pins": pins, "shaft": shaft, "length": shaft[1] - shaft[0]}


def shaft_solid(p, length):
    """Shaft along y from 0 to length (axis x = 0, z = 0): ball ends with the fixed metal pins along x
    at their centres."""
    r, rr, neck = p["ball_d"] / 2, p["shaft_d"] / 2, 4.0
    s = cyl_y(r, r, length - r, 0, 0).fuse(cyl_y(rr, r + neck, length - r - neck, 0, 0))   # neck and rod
    for yc in (r, length - r):
        s = s.fuse(cq.Solid.makeSphere(r, cq.Vector(0, yc, 0), angleDegrees1=-90, angleDegrees2=90))
        s = s.fuse(cyl_x(p["pin_d"] / 2, -p["pin_length"] / 2, p["pin_length"] / 2, yc, 0))
    return s.clean()


def cup_solid(p):
    """Cup joint along y: back face at y = 0, open end at y = cup_length, bore for the ball end and
    two slots for the metal pin (along x, through both walls)."""
    rc, lc = p["cup_od"] / 2, p["cup_length"]
    s = cyl_y(rc, 0, lc, 0, 0)
    s = s.cut(cyl_y(p["cup_bore_d"] / 2, lc - p["cup_bore_depth"], lc + 1, 0, 0))
    s = s.cut(box(-rc - 1, rc + 1, lc - p["cup_slot_len"], lc + 1, -p["cup_slot_w"] / 2, p["cup_slot_w"] / 2))
    # back end: bore for the pinion shaft, groove for the O-ring and cross hole for the retaining pin
    bd, bdep = p["cup_back_bore"]
    g0, g1, gd = p["cup_groove"]
    f = p["press_fit_flats"] / 2                           # press fit shape of the pinion shaft: bore with two flats
    s = s.cut(cyl_y(bd / 2, -1, bdep, 0, 0).intersect(box(-bd / 2 - 1, bd / 2 + 1, -2, bdep + 1, -f, f)))
    s = s.cut(cyl_y(rc + 1, g0, g1, 0, 0).cut(cyl_y(gd / 2, g0, g1, 0, 0)))
    s = s.cut(cyl_x(p["cup_pin_d"] / 2, -rc - 1, rc + 1, (g0 + g1) / 2, 0))
    return s.clean()


def outdrive_solid(p):
    """Diff outdrive along +x: back face at x = 0, open end at x = outdrive_length, bore for the end
    of the dogbone and two slots for its holding pin (along z, through both walls)."""
    lo, ro = p["outdrive_length"], p["outdrive_od"] / 2
    s = cyl_x(ro, 0, lo, 0, 0)
    s = s.cut(cyl_x(p["outdrive_bore_d"] / 2, lo - p["outdrive_bore_depth"], lo + 1, 0, 0))
    s = s.cut(box(lo - p["outdrive_slot_len"], lo + 1, -p["outdrive_slot_w"] / 2, p["outdrive_slot_w"] / 2,
                  -ro - 1, ro + 1))
    return s.clean()


def spur_gear_solid(p, lay):
    """Spur gear (chassis plate coordinates): teeth with a simplified trapezoidal profile (tip and root
    circles of the standard gear, not involute), centre bore for the pinion shaft and 4 screw holes
    for the flange of the rear pinion shaft."""
    n, m = int(p["spur_teeth"]), INCH / p["spur_dp"]
    rp = n * m / 2
    rt, rr = rp + m, rp - 1.25 * m
    tan20 = np.tan(np.radians(20.0))
    half_tip = (np.pi * m / 4 - m * tan20) / rt             # angular half widths of a tooth
    half_root = (np.pi * m / 4 + 1.25 * m * tan20) / rr
    pts = []
    for k in range(n):
        c = 2 * np.pi * k / n
        for a, r in ((c - half_root, rr), (c - half_tip, rt), (c + half_tip, rt), (c + half_root, rr)):
            pts.append((r * np.cos(a), r * np.sin(a)))
    y0, y1 = lay["spur"]
    gear = cq.Workplane("XY").polyline(pts).close().extrude(y1 - y0).val()
    gear = gear.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -90)   # axis along +y, from y = 0 to the thickness
    gear = gear.cut(cyl_y(p["spur_bore_d"] / 2, -1, y1 - y0 + 1, 0, 0))
    for k in range(4):
        a = np.pi / 4 + k * np.pi / 2
        rs = p["spur_screw_r"]
        gear = gear.cut(cyl_y(p["spur_screw_d"] / 2, -1, y1 - y0 + 1, rs * np.cos(a), rs * np.sin(a)))
    for r, dh, n, off in p["spur_holes"]:                  # lightening holes
        for k in range(int(n)):
            a = np.radians(off) + k * 2 * np.pi / n
            gear = gear.cut(cyl_y(dh / 2, -1, y1 - y0 + 1, r * np.cos(a), r * np.sin(a)))
    return gear.clean().translate(cq.Vector(0, y0, lay["z"]))


def rear_drive_line(p, lay):
    """Rear pinion shaft from the inner end of the pinion seat of the bulkhead to the cup joint, with
    the flange, the spur gear, the bearing and the motor mount with its cap (chassis plate
    coordinates): list of (name, kind, solid), with the pinion NBA207 and the 2 bearings of the bulkhead.
    Not modelled: the screw of the pinion, the shims between the bearings."""
    z = lay["z"]
    rs = p["pinion_shaft_d"] / 2
    bd, bdep = p["cup_back_bore"]
    d, dd, b = p["mount_bearing"]
    m0, m1 = lay["mount"]
    yb = m1 - p["mount_lip"][0] - b                         # bearing against the lip (toward End A)
    teeth, od, root_d, plen, cone = p["pinion"]
    cs_d, cs_h = p["pinion_countersink"]
    y_pin_front = lay["seat"][0] - plen                     # pinion against the inner bearing of the bulkhead
    y0 = y_pin_front + cs_h + 0.15                          # end of the shaft below the head of the pinion screw
    y_end = lay["back"][0] + bdep - 0.5                     # end in the cup joint, 0.5 before the bottom of its bore

    def flats(y_a, y_b):
        """Press fit shape: round shaft with two flats (width across flats press_fit_flats, normals along z)."""
        f = p["press_fit_flats"] / 2
        return cyl_y(rs, y_a, y_b, 0, z).intersect(box(-rs - 1, rs + 1, y_a - 1, y_b + 1, z - f, z + f))
    shaft = flats(y0, lay["seat"][0])                                       # pinion seat
    shaft = shaft.fuse(cyl_y(rs, lay["seat"][0], lay["flange"][0], 0, z))   # 2 bearings of the bulkhead
    shaft = shaft.fuse(cyl_y(p["flange_d"] / 2, *lay["flange"], 0, z))      # flange (mounting plate of the spur gear)
    sd, sl = p["spur_spigot"]
    y_sp = lay["spur"][1] + sl
    shaft = shaft.fuse(cyl_y(sd / 2, lay["flange"][1], y_sp, 0, z))        # spigot through the spur gear
    shaft = shaft.fuse(cyl_y(p["bearing_shoulder_d"] / 2, y_sp, yb, 0, z))  # shoulder against the inner ring of the bearing
    shaft = shaft.fuse(cyl_y(rs, yb, yb + b, 0, z))                         # bearing NBA298 in the motor mount
    shaft = shaft.fuse(flats(yb + b, y_end))                                # cup joint seat
    yp = lay["back"][0] + sum(p["cup_groove"][:2]) / 2                      # retaining pin NBA255 in the groove
    shaft = shaft.fuse(cyl_x(p["cup_pin_d"] / 2, -p["cup_pin_length"] / 2, p["cup_pin_length"] / 2, yp, z))
    shaft = shaft.cut(cyl_y(p["tap_d"] / 2, y0 - 0.1, y0 + p["pinion_thread_depth"], 0, z))  # axial thread M3
    for k in range(4):     # threads M3 of the 4 screws of the spur gear in the flange (tap drill, through)
        ang = np.pi / 4 + k * np.pi / 2
        rs = p["spur_screw_r"]
        shaft = shaft.cut(cyl_y(p["tap_d"] / 2, lay["flange"][0] - 0.1, lay["flange"][1] + 0.1, rs * np.cos(ang),
                                z + rs * np.sin(ang)))
    spur = spur_gear_solid(p, lay)
    pinion = pinion_solid(p, lay, y_pin_front, y0)
    bearing = cyl_y(dd / 2, yb, yb + b, 0, z).cut(cyl_y(d / 2, yb - 1, yb + b + 1, 0, z))
    lp = load_params(LOWER)
    ys = lay["seat"][0]                                     # 2 bearings NBA298 in the pinion seat of the bulkhead
    bulk = [cyl_y(dd / 2, y, y + b, 0, z).cut(cyl_y(d / 2, y - 1, y + b + 1, 0, z))
            for y in (ys, ys + b + lp["pinion_rib_t"])]
    mount = motor_mount_solid(p, lay)
    cap = motor_mount_cap_solid(p, lay)
    return [("rear pinion shaft with flange", "drive", shaft.clean()), ("spur gear", "drive", spur.clean()),
            ("pinion NBA207", "drive", pinion),
            ("bearing NBA298 in the bulkhead, inner", "drive", bulk[0].clean()),
            ("bearing NBA298 in the bulkhead, outer", "drive", bulk[1].clean()),
            ("bearing NBA298 in the motor mount", "drive", bearing.clean()), ("motor mount", "mount", mount.clean()),
            ("cap of the motor mount", "mount", cap)]


def pinion_solid(p, lay, y_front, y_shaft):
    """Pinion NBA207 (chassis plate coordinates): simplified straight bevel gear (tooth profile with
    straight flanks, tapered by the cone angle), back face against the inner bearing of the bulkhead,
    bore with the press fit shape of the shaft, countersink and hole for the screw M3x6 (manual step 5)."""
    z = lay["z"]
    teeth, od, root_d, plen, cone = p["pinion"]
    pts, n = [], int(teeth)
    for k in range(n):
        a, pitch = 2 * np.pi * k / n, 2 * np.pi / n
        for r, da in ((root_d / 2, -0.32), (od / 2, -0.13), (od / 2, 0.13), (root_d / 2, 0.32)):
            pts.append((r * np.cos(a + da * pitch), r * np.sin(a + da * pitch)))
    g = cq.Workplane("XY").polyline(pts).close().extrude(plen, taper=cone).val()
    g = g.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90).translate(cq.Vector(0, y_front + plen, z))   # back face at the seat
    rs, f = p["pinion_shaft_d"] / 2, p["press_fit_flats"] / 2
    bore = cyl_y(rs, y_shaft, y_front + plen + 1, 0, z).intersect(box(-rs - 1, rs + 1, y_shaft - 1, y_front + plen + 2,
                                                                       z - f, z + f))
    cs_d, cs_h = p["pinion_countersink"]
    g = g.cut(bore).cut(cyl_y(1.6, y_front - 1, y_shaft + 0.1, 0, z))
    g = g.cut(cq.Solid.makeCone(cs_d / 2, 1.6, cs_h, cq.Vector(0, y_front - 0.001, z), cq.Vector(0, 1, 0)))
    return g.clean()


def motor_mount_solid(p, lay):
    """Motor mount NBA201 for 540 motors (manual step 10), chassis plate coordinates:
    low part on the bulkhead side with a U-shaped notch for the bearing NBA298 at the pinion axis,
    tall part on the motor side with rounded top corners and three long holes along x: the motor
    shaft (middle, at the height of the pinion axis) and the two motor screws (above and below)."""
    z, (m0, m1) = lay["z"], lay["mount"]
    xa, xb = p["mount_x"]
    xs, zl, zt = p["mount_step_x"], p["mount_low_top"], p["mount_top"]
    tall = cq.Workplane().add(box(xs, xb, m0, m1, PLATE_T, zt)).edges("|Y and >Z").fillet(p["mount_corner_r"]).val()
    s = box(xa, xs, m0, m1, PLATE_T, zl).fuse(tall)
    rb, (lw, ld) = p["mount_notch_d"] / 2, p["mount_lip"]
    s = s.cut(cyl_y(rb, m0 - 1, m1 - lw, 0, z)).cut(box(-rb, rb, m0 - 1, m1 - lw, z, zl + 1))   # U notch, bearing
    s = s.cut(cyl_y(ld / 2, m1 - lw - 1, m1 + 1, 0, z)).cut(box(-ld / 2, ld / 2, m1 - lw - 1, m1 + 1, z, zl + 1))  # lip

    def long_hole(zc, w):
        """Long hole through the plate: centres of the end radii at motor_slot_x, width w."""
        x0, x1 = p["motor_slot_x"]
        h = cq.Workplane("XZ").center((x0 + x1) / 2, zc).slot2D(x1 - x0 + w, w).extrude(p["mount_t"] / 2 + 1, both=True)
        return h.val().translate(cq.Vector(0, p["mount_y"], 0))
    hs = p["motor_screw_spacing"] / 2
    for zc, w in ((z, p["motor_shaft_slot_w"]), (z + hs, p["motor_screw_slot_w"]), (z - hs, p["motor_screw_slot_w"])):
        s = s.cut(long_hole(zc, w))
    # threads M3 (tap drill): screws from below through the chassis plate (H09, H10) and screws M3x18 of the cap
    rt, dep = p["tap_d"] / 2, p["mount_tap_depth"]
    for x, y in p["mount_bottom_screws"]:
        s = s.cut(cyl_z(rt, PLATE_T - 1, PLATE_T + dep, x, y))
    for x, y in p["cap_screws"]:
        s = s.cut(cyl_z(rt, zl - dep, zl + 1, x, y))
    return s.clean()


def motor_mount_cap_solid(p, lay):
    """Cap of the motor mount (second part of NBA201, manual step 25), chassis plate coordinates,
    block between the low part of the motor mount and the top brace, with a
    semicircular notch along y in its top face and two through holes for the screws M3x18 from the
    top brace into the motor mount."""
    m0, m1 = lay["mount"]
    z0 = p["mount_low_top"]
    z1, w = z0 + p["cap_h"], p["cap_w"] / 2
    s = box(-w, w, m0, m1, z0, z1).cut(cyl_y(p["cap_notch_r"], m0 - 1, m1 + 1, 0, z1))
    for x, y in p["cap_screws"]:
        s = s.cut(cyl_z(p["cap_hole_d"] / 2, z0 - 1, z1 + 1, x, y))
    return s.clean()


def parts_in_plate(p=None, lp=None):
    """Parts in the coordinates of the chassis plate: list of (name, kind, solid). kind: "shaft"
    (with the fixed metal pins); "cup" (cup
    joints and diff outdrives), "drive" (rear pinion shaft, spur gear, bearing), "mount" (motor
    mount)."""
    p = p or load_params(PARAMS)
    lp = lp or load_params(LOWER)
    lay = layout(p, lp)
    z = lay["z"]
    zrot = (cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180)
    cup = cup_solid(p)
    parts = [("centre driveshaft", "shaft", shaft_solid(p, lay["length"]).translate(cq.Vector(0, lay["shaft"][0], z))),
             ("cup joint End B", "cup", cup.translate(cq.Vector(0, lay["back"][0], z))),
             ("cup joint End A", "cup", cup.rotate(*zrot).translate(cq.Vector(0, lay["back"][1], z)))]
    parts += rear_drive_line(p, lay)
    od = outdrive_solid(p)
    xo = lp["body_half_width"] + p["outdrive_gap"]
    for label, yd in (("End B", BULKHEAD_Y["rear"] + lp["diff_axis_y"]), ("End A", BULKHEAD_Y["front"] - lp["diff_axis_y"])):
        for sx, side in ((1, "+x"), (-1, "-x")):
            s = od if sx > 0 else od.rotate(*zrot)
            parts.append((f"diff outdrive {label} {side}", "cup", s.translate(cq.Vector(sx * xo, yd, z))))
    return parts


def section_polys(solid, normal="x", offset=0.0):
    """Polygons of the section of a solid: plane x = offset with the coordinates (y, z), or plane
    y = offset with the coordinates (x, z). List of (outer, points)."""
    from OCP.BRepTools import BRepTools_WireExplorer
    if normal == "x":
        plane = cq.Face.makePlane(800, 800, cq.Vector(offset, 150, 0), cq.Vector(1, 0, 0))
        uv = (lambda v: v.y)
    else:
        plane = cq.Face.makePlane(800, 800, cq.Vector(0, offset, 0), cq.Vector(0, 1, 0))
        uv = (lambda v: v.x)
    out = []
    for f in solid.intersect(plane).Faces():
        for outer, wire in [(True, f.outerWire())] + [(False, w) for w in f.innerWires()]:
            ex = BRepTools_WireExplorer(wire.wrapped)
            poly, count = [], 0

            def gap(a, b):
                return float(np.hypot(*(np.array(a) - np.array(b))))
            while ex.More():
                ed = cq.Edge(ex.Current())
                n = 2 if ed.geomType() == "LINE" else 40
                seg = [(uv(ed.positionAt(k / (n - 1))), ed.positionAt(k / (n - 1)).z) for k in range(n)]
                if count == 1 and min(gap(seg[0], poly[0]), gap(seg[-1], poly[0])) < \
                        min(gap(seg[0], poly[-1]), gap(seg[-1], poly[-1])):
                    poly.reverse()                          # first edge was in the opposite direction
                if poly and gap(seg[0], poly[-1]) > gap(seg[-1], poly[-1]):
                    seg = seg[::-1]
                poly += seg
                count += 1
                ex.Next()
            out.append((outer, poly))
    return out


def drawing(path, p, lay, items):
    """items: list of (solid, colour). Section x = 0: overview and both cup joints."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly

    polys = [(section_polys(s), c) for s, c in items]

    def draw(ax):
        for sec, col in polys:
            for outer, poly in sec:
                if outer:
                    ax.add_patch(MPoly(poly, closed=True, fc=col, ec="#1d2025", lw=0.5))
            for outer, poly in sec:
                if not outer:
                    ax.add_patch(MPoly(poly, closed=True, fc="white", ec="#1d2025", lw=0.5))
        ax.set_aspect("equal")
        ax.grid(True, color="#eeeeee", lw=0.5)

    def dim(ax, a, b, y, text, below=False):
        ax.annotate("", (a, y), (b, y), arrowprops=dict(arrowstyle="<->", lw=0.7))
        ax.text((a + b) / 2, y + (-0.4 if below else 0.3), text, ha="center", va="top" if below else "bottom",
                fontsize=7.5)

    z = lay["z"]
    fig = plt.figure(figsize=(15, 10))
    fig.suptitle("Carten T410R centre driveshaft with the drive line: stock parts, not part of the speedrun design "
                 "(not verified, work in progress)", fontsize=12, y=0.985)
    ax = fig.add_axes([0.04, 0.57, 0.92, 0.36])
    draw(ax)
    y0, y1 = lay["shaft"]
    dim(ax, y0, y1, z + 21, f"shaft {lay['length']:.2f}")
    h0, h1 = lay["housing"]
    dim(ax, h0, h1, z - 14, f"end faces of the pinion housings {h1 - h0:.2f}", below=True)
    ax.text(-4, 54, "End B (rear, motor)", fontsize=9)
    ax.text(318, 54, "End A (front)", fontsize=9, ha="right")
    ax.set_xlim(-10, 320)
    ax.set_ylim(-4, 60)
    ax.set_title("Section along the pinion axis (x = 0), height above the bottom face of the chassis plate",
                 fontsize=10, loc="left")
    pr = p["pin_d"] / 2
    for k, (end, sign) in enumerate((("End B: spur gear, motor mount and cup joint", 1),
                                     ("End A: cup joint on the front pinion shaft", -1))):
        i = 0 if sign > 0 else 1
        ax2 = fig.add_axes([0.04 + 0.64 * k, 0.075, 0.31, 0.44])
        draw(ax2)
        hy, pin, se, bk, op = lay["housing"][i], lay["pins"][i], lay["slot_end"][i], lay["back"][i], lay["open"][i]
        lo, hi = sorted((hy - sign * 8, pin + sign * 16))
        ax2.set_xlim(lo, hi)
        ax2.set_ylim(z - 21 if sign > 0 else z - 12, z + 21 if sign > 0 else z + 12)
        ax2.set_title(end, fontsize=10, loc="left")
        dim(ax2, se, pin - sign * pr, z + 6.6, f"play {abs(pin - sign * pr - se):.1f}")
        rc = p["cup_od"] / 2                                 # closed end of the slots (across the section)
        ax2.plot([se, se], [z - rc, z + 6.8], color="#1d2025", lw=0.7, ls="--")
        ax2.plot([se, op], [z + p["cup_slot_w"] / 2] * 2, color="#1d2025", lw=0.5, ls="--")
        ax2.plot([se, op], [z - p["cup_slot_w"] / 2] * 2, color="#1d2025", lw=0.5, ls="--")
        dim(ax2, bk, op, z - 6.6, f"cup joint {p['cup_length']:g}", below=True)
        dim(ax2, op, se, z - 9.6, f"slot {p['cup_slot_len']:g}", below=True)
        ax2.annotate(f"metal pin {p['pin_d']:g} x {p['pin_length']:g} (fixed)", (pin, z), (pin + sign * 9, z + 9.5),
                     fontsize=7.5, ha="center", arrowprops=dict(arrowstyle="-", lw=0.6))
        ax2.text(pin + sign * 11, z - 1.0, "shaft", ha="center", fontsize=8, color="white")
        if sign > 0:
            ax2.text(lo + 0.5, z + 19.3, "pinion housing", ha="left", fontsize=7.5)
        else:
            ax2.text(hy - sign * 4, z + 7.5, "pinion housing", ha="center", fontsize=7.5)
        if sign > 0:
            m0, m1 = lay["mount"]
            ax2.text(m1 + 0.8, 7.0, "motor\nmount", ha="left", va="center", fontsize=7.5)
            ax2.text(p["mount_y"], p["mount_low_top"] + (p["cap_h"] - p["cap_notch_r"]) / 2, "cap", ha="center",
                     va="center", fontsize=7)
            ax2.text(sum(lay["spur"]) / 2, z + lay["spur_od"] / 2 - 4, "spur\ngear", ha="center", fontsize=7.5)
            ax2.text(p["mount_y"], z - 4.2, "bearing", ha="center", va="top", fontsize=7)
            dim(ax2, m1, bk, z + 5.0, f"{p['rear_cup_gap']:g}")
        else:
            dim(ax2, hy, bk, z + 5.0, f"{p['cup_gap']:g}")
    # motor mount seen from the motor side (section y = middle of the motor mount)
    ax3 = fig.add_axes([0.37, 0.075, 0.29, 0.44])
    yv = p["mount_y"]
    for solid, col in items:
        sec = section_polys(solid, "y", yv)
        for outer, poly in sec:
            if outer:
                ax3.add_patch(MPoly(poly, closed=True, fc=col, ec="#1d2025", lw=0.5))
        for outer, poly in sec:
            if not outer:
                ax3.add_patch(MPoly(poly, closed=True, fc="white", ec="#1d2025", lw=0.5))
    from matplotlib.patches import Circle
    ax3.add_patch(Circle((0, z), lay["spur_od"] / 2, fill=False, ec="#5d636b", lw=0.7, ls="--"))
    xm = sum(p["motor_slot_x"]) / 2
    ax3.add_patch(Circle((xm, z), 18.0, fill=False, ec="#2c3e50", lw=0.7, ls=":"))
    hs = p["motor_screw_spacing"] / 2
    for zz in (z + hs, z - hs):
        ax3.add_patch(Circle((xm, zz), 1.5, fill=False, ec="#2c3e50", lw=0.6, ls=":"))
    x0, x1 = p["motor_slot_x"]
    ax3.annotate("", (x0, p["mount_top"] + 2.0), (x1, p["mount_top"] + 2.0), arrowprops=dict(arrowstyle="<->", lw=0.7))
    ax3.text(xm, p["mount_top"] + 2.3, f"motor axis x = {x0:g} to {x1:g}", ha="center", va="bottom", fontsize=7.5)
    ax3.text(p["mount_x"][1] + 1.0, z + 12, "540 motor\n(dotted)", fontsize=7, ha="left")
    ax3.text(0, z + lay["spur_od"] / 2 + 0.6, f"spur gear {p['spur_teeth']:g}T (dashed)", ha="center", va="bottom",
             fontsize=7)
    ax3.text(0, 4.0, "bearing in\nthe U notch", ha="center", va="center", fontsize=7)
    ax3.annotate("cap of the motor mount (2 x M3x18 from the top brace)", (-p["cap_w"] / 2 + 1, p["mount_low_top"] + 5),
                 (-23, 48.5), fontsize=7, ha="left", va="center", arrowprops=dict(arrowstyle="-", lw=0.5))
    ax3.set_xlim(-24, 68)
    ax3.set_ylim(-3, 52)
    ax3.set_aspect("equal")
    ax3.grid(True, color="#eeeeee", lw=0.5)
    ax3.set_title("Motor mount from the motor side (section y = 62.48)", fontsize=10, loc="left")
    ax3.set_xlabel("x [mm] (across the car)", fontsize=8)
    fig.text(0.04, 0.006, f"Shaft {p['shaft_d']:g} mm with ball ends and fixed metal pins NBA255 {p['pin_d']:g} x "
             f"{p['pin_length']:g} mm in the slots of the cup joints; total axial play {p['axial_play']:g} mm (pins to the "
             f"closed ends of the slots). Cup joints {p['cup_od']:g} / {p['cup_bore_d']:g} x {p['cup_length']:g} mm, slots "
             f"{p['cup_slot_len']:g} mm (owner).\nSpur gear {p['spur_teeth']:g}T {p['spur_dp']:g}DP ({lay['spur_od']:.1f} mm) "
             f"in the slot of the chassis plate, motor mount {p['mount_t']:g} mm (owner) for 540 motors on the holes "
             "H09/H10. Thicknesses of the spur gear and the flange, outline of the motor mount and the gaps: typical "
             "values; teeth of the spur gear simplified.\nDashed: slots of the cup joints (across the section). CAD files of all "
             "parts: cad/stock_parts (driveshaft, rear_drive, motor_mount, diff_outdrive).",
             fontsize=8, va="bottom")
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Generate the centre driveshaft of the T410R (stock part, not part "
                                                 "of the speedrun design).")
    parser.parse_args()
    p, lp, up = load_params(PARAMS), load_params(LOWER), load_params(UPPER)
    lay = layout(p, lp)
    parts = {name: solid for name, _, solid in parts_in_plate(p, lp)}
    z, yb = lay["z"], lay["mount"][1] - p["mount_lip"][0] - p["mount_bearing"][2]
    exports = [   # (directory, file name, solid in part coordinates)
        ("driveshaft", "driveshaft_T410R", shaft_solid(p, lay["length"])),
        ("driveshaft", "cup_joint_T410R", cup_solid(p)),
        ("rear_drive", "rear_pinion_shaft_T410R",
         parts["rear pinion shaft with flange"].translate(cq.Vector(0, -lay["housing"][0], -z))),
        ("rear_drive", f"pinion_{p['pinion'][0]:g}T_NBA207", parts["pinion NBA207"].translate(cq.Vector(0, -lay["housing"][0], -z))),
        ("rear_drive", f"spur_gear_{p['spur_teeth']:g}T_T410R", parts["spur gear"].translate(cq.Vector(0, -lay["spur"][0], -z))),
        ("rear_drive", "bearing_5x10x4", parts["bearing NBA298 in the motor mount"].translate(cq.Vector(0, -yb, -z))),
        ("motor_mount", "motor_mount_T410R", parts["motor mount"].translate(cq.Vector(0, -p["mount_y"], -PLATE_T))),
        ("motor_mount", "motor_mount_cap_T410R",
         parts["cap of the motor mount"].translate(cq.Vector(0, -p["mount_y"], -PLATE_T))),
        ("diff_outdrive", "diff_outdrive_T410R", outdrive_solid(p))]
    for folder, name, s in exports:
        os.makedirs(f"{STOCK}/{folder}", exist_ok=True)
        stem = f"{STOCK}/{folder}/{name}"
        valid, bb, vol = s.isValid(), s.BoundingBox(), s.Volume()
        cq.exporters.export(cq.Workplane().add(s), stem + ".step")
        cq.exporters.export(cq.Workplane().add(s), stem + ".stl", tolerance=0.01, angularTolerance=0.1)
        print(f"{name}: wrote {stem}.step/.stl, solid valid: {valid}, size {bb.xlen:.2f} x {bb.ylen:.2f} x "
              f"{bb.zlen:.2f} mm, volume {vol / 1000:.2f} cm3")
    bulkheads = []
    for end in ("rear", "front"):
        for solid in (bulkhead_lower(lp).val(), bulkhead_upper(lp, up).val()):
            b = solid.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180) if end == "front" else solid
            bulkheads.append(b.translate(cq.Vector(0, BULKHEAD_Y[end], PLATE_T)))
    plate = cq.importers.importStep(PLATE_STEP).val()
    with open(BRACE_GEOM, encoding="utf-8") as f:
        brace_g = json.load(f)
    c = sum(brace_offset(brace_g, up["deck_screw_y"])) / 2
    brace = brace_solid(brace_g).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180).translate(
        cq.Vector(0, c, PLATE_T + lp["axis_z"] + up["deck_h"]))
    items = [(plate, "#5b5f66"), (brace, "#9aa7b8")]
    items += [(b, "#8c96a3" if k % 2 == 0 else "#d9a35f") for k, b in enumerate(bulkheads)]
    items += [(parts["motor mount"], "#c9ccd1"), (parts["cap of the motor mount"], "#b3b8bf"),
              (parts["rear pinion shaft with flange"], "#6b7078"),
              (parts["spur gear"], "#7d8590"), (parts["bearing NBA298 in the motor mount"], "#a0a6ad"),
              (parts["cup joint End B"], "#b8bcc2"), (parts["cup joint End A"], "#b8bcc2"),
              (parts["centre driveshaft"], "#c0392b")]
    drawing(DRAWING, p, lay, items)
    print(f"Wrote {DRAWING}")

    print("layout on the chassis plate (y along the car, End B at y = 0)")
    print(f"  pinion axis: x = 0, z = {lay['z']:.2f}")
    print(f"  end faces of the pinion housings: y = {lay['housing'][0]:.2f} (End B), {lay['housing'][1]:.2f} (End A)")
    print(f"  End B: flange {lay['flange'][0]:.2f} to {lay['flange'][1]:.2f}, spur gear {lay['spur'][0]:.2f} to "
          f"{lay['spur'][1]:.2f} (outer diameter {lay['spur_od']:.2f}), motor mount {lay['mount'][0]:.2f} to "
          f"{lay['mount'][1]:.2f}")
    for i, end in enumerate(("End B", "End A")):
        print(f"  {end}: cup joint from {lay['back'][i]:.2f} to {lay['open'][i]:.2f}, closed end of the slots "
              f"{lay['slot_end'][i]:.2f}, pin {lay['pins'][i]:.2f}, end of the shaft {lay['shaft'][i]:.2f}, "
              f"space to the bottom of the bore {abs(lay['shaft'][i] - lay['bottom'][i]):.2f}")
    print(f"  centre driveshaft: length {lay['length']:.2f} (pins {abs(lay['pins'][1] - lay['pins'][0]):.2f} apart), "
          f"axial play {p['axial_play']:g} ({p['axial_play'] / 2:g} at each pin to the closed end of its slot)")
    print("checks")
    shaft_p = parts["centre driveshaft"]
    for name in ("cup joint End B", "cup joint End A"):
        print(f"  shaft / {name}: overlap {shaft_p.intersect(parts[name]).Volume():.4f} mm3")
    others = bulkheads + [plate, brace]
    for name, solid in parts.items():
        worst = max(solid.intersect(o).Volume() for o in others)
        print(f"  {name} / bulkheads, chassis plate and top brace: largest overlap {worst:.4f} mm3")
    print(f"  radial clearance of the ball ends in the cup joints: {(p['cup_bore_d'] - p['ball_d']) / 2:.3f}, pins in "
          f"the slots: {(p['cup_slot_w'] - p['pin_d']) / 2:.2f} per side, pin ends inside the cup joints: "
          f"{(p['cup_od'] - p['pin_length']) / 2:.2f}")


if __name__ == "__main__":
    main()
