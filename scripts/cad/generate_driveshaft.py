"""Generate the centre driveshaft of the Carten T410R (NHA413) (stock part, not part of the speedrun
design).

The centre driveshaft connects the pinions of the two bulkheads. Each end runs in a cup on the
pinion shaft (cup joint): a ball end with a cross hole for a metal pin (NBA255 2.0x7.6), which
fixes the shaft in the slots of the cup in the direction of rotation. The shaft is shorter than
the distance between the bottoms of the cups by the axial play, so it can move a little back and
forth. The shaft is a stock part: it is not part of the speedrun design and is modelled for the
completeness of the build. The metal pins, the cups on the pinions and the cups of the diff
outdrives are simple bodies for the assembly picture only (no CAD files).

Derived from the models of this project: the pinion axis (x = 0, axis_z of the lower bulkhead
above the chassis plate), the end faces of the pinion housings (pinion seats of the lower
bulkhead) and the positions of the bulkheads on the chassis plate. The dimensions of the cups,
the shaft and the cross pins are typical values of 1:10 touring cars
(cad/stock_parts/driveshaft/driveshaft_parameters.json).

Usage (from the root directory of the repository):
    python scripts/cad/generate_driveshaft.py

The script writes the STEP and STL files of the shaft and the drawing
photos/cad_driveshaft_drawing.png, and checks the play and the fit in the cups.

Requires the packages cadquery and matplotlib.
"""
import argparse
import os
import sys

import numpy as np
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_bulkhead_lower import box, bulkhead_lower, cyl_x, cyl_y, load_params  # noqa: E402
from generate_bulkhead_upper import bulkhead_upper  # noqa: E402
from generate_top_brace_speedrun import BULKHEAD_Y  # noqa: E402

PARAMS = "cad/stock_parts/driveshaft/driveshaft_parameters.json"
LOWER = "cad/bulkhead/bulkhead_lower_parameters.json"
UPPER = "cad/bulkhead/bulkhead_upper_parameters.json"
OUT = "cad/stock_parts/driveshaft"
DRAWING = "photos/cad_driveshaft_drawing.png"
PLATE_T = 2.0


def layout(p, lp):
    """Positions on the chassis plate (y along the car): pinion axis height, end faces of the pinion
    housings, back faces and bottoms of the cups, shaft length and shaft ends (centred)."""
    he = lp["pinion_seat_y_inner"] + lp["pinion_seat_length"]   # end face of the pinion housing
    housing = (BULKHEAD_Y["rear"] + he, BULKHEAD_Y["front"] - he)  # End B (+y), End A (rotated, -y)
    back = (housing[0] + p["cup_gap"], housing[1] - p["cup_gap"])
    open_end = (back[0] + p["cup_length"], back[1] - p["cup_length"])
    bottom = (open_end[0] - p["cup_bore_depth"], open_end[1] + p["cup_bore_depth"])
    length = bottom[1] - bottom[0] - p["axial_play"]
    y0 = bottom[0] + p["axial_play"] / 2
    return {"z": PLATE_T + lp["axis_z"], "housing": housing, "back": back, "open": open_end, "bottom": bottom,
            "length": length, "shaft": (y0, y0 + length)}


def shaft_solid(p, length):
    """Shaft along y from 0 to length (axis x = 0, z = 0): ball ends with cross holes along x for the
    metal pins."""
    r = p["shaft_d"] / 2
    s = cyl_y(r, r, length - r, 0, 0)
    for yc in (r, length - r):
        s = s.fuse(cq.Solid.makeSphere(r, cq.Vector(0, yc, 0), angleDegrees1=-90, angleDegrees2=90))
    for yc in (r, length - r):
        s = s.cut(cyl_x(p["pin_hole_d"] / 2, -r - 1, r + 1, yc, 0))
    return s.clean()


def pin_solid(p):
    """Metal cross pin along x, centred at the origin (picture only)."""
    return cyl_x(p["pin_d"] / 2, -p["pin_length"] / 2, p["pin_length"] / 2, 0, 0)


def outdrive_solid(p):
    """Cup of a diff outdrive along +x: back face at x = 0, open end at x = outdrive_length (picture
    only)."""
    lo = p["outdrive_length"]
    s = cyl_x(p["outdrive_od"] / 2, 0, lo, 0, 0)
    return s.cut(cyl_x(p["outdrive_bore_d"] / 2, lo - p["outdrive_bore_depth"], lo + 1, 0, 0)).clean()


def cup_solid(p):
    """Cup along y: back face at y = 0, open end at y = cup_length, bore for the ball end and two
    slots for the cross pin (along x, through both walls)."""
    rc, lc = p["cup_od"] / 2, p["cup_length"]
    y_b = lc - p["cup_bore_depth"]
    s = cyl_y(rc, 0, lc, 0, 0)
    s = s.cut(cyl_y(p["cup_bore_d"] / 2, y_b, lc + 1, 0, 0))
    s = s.cut(box(-rc - 1, rc + 1, y_b, lc + 1, -p["cup_slot_w"] / 2, p["cup_slot_w"] / 2))
    return s.clean()


def parts_in_plate(p=None, lp=None):
    """Parts in the coordinates of the chassis plate: list of (name, kind, solid). kind: "shaft"
    (CAD file), "pin" and "cup" (simple bodies for the assembly picture only): metal pins, cups on
    the pinions and cups of the diff outdrives on both sides of each bulkhead."""
    p = p or load_params(PARAMS)
    lp = lp or load_params(LOWER)
    lay = layout(p, lp)
    z = lay["z"]
    zrot = (cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180)
    cup = cup_solid(p)
    r = p["shaft_d"] / 2
    y0, y1 = lay["shaft"]
    parts = [("centre driveshaft", "shaft", shaft_solid(p, lay["length"]).translate(cq.Vector(0, y0, z))),
             ("metal pin End B", "pin", pin_solid(p).translate(cq.Vector(0, y0 + r, z))),
             ("metal pin End A", "pin", pin_solid(p).translate(cq.Vector(0, y1 - r, z))),
             ("cup End B", "cup", cup.translate(cq.Vector(0, lay["back"][0], z))),
             ("cup End A", "cup", cup.rotate(*zrot).translate(cq.Vector(0, lay["back"][1], z)))]
    od = outdrive_solid(p)
    xo = lp["body_half_width"] + p["outdrive_gap"]
    for end, label, yd in (("rear", "End B", BULKHEAD_Y["rear"] + lp["diff_axis_y"]),
                           ("front", "End A", BULKHEAD_Y["front"] - lp["diff_axis_y"])):
        for sx, side in ((1, "+x"), (-1, "-x")):
            s = od if sx > 0 else od.rotate(*zrot)
            parts.append((f"diff outdrive {label} {side}", "cup", s.translate(cq.Vector(sx * xo, yd, z))))
    return parts


def section_polys(solid):
    """Polygons (y, z) of the section of a solid at x = 0: list of (outer, points)."""
    from OCP.BRepTools import BRepTools_WireExplorer
    plane = cq.Face.makePlane(800, 800, cq.Vector(0, 150, 0), cq.Vector(1, 0, 0))
    out = []
    for f in solid.intersect(plane).Faces():
        for outer, wire in [(True, f.outerWire())] + [(False, w) for w in f.innerWires()]:
            ex = BRepTools_WireExplorer(wire.wrapped)
            poly = []
            while ex.More():
                ed = cq.Edge(ex.Current())
                n = 2 if ed.geomType() == "LINE" else 40
                seg = [(ed.positionAt(k / (n - 1)).y, ed.positionAt(k / (n - 1)).z) for k in range(n)]
                if poly and np.hypot(*(np.array(seg[0]) - poly[-1])) > np.hypot(*(np.array(seg[-1]) - poly[-1])):
                    seg = seg[::-1]
                poly += seg
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

    z = lay["z"]
    fig = plt.figure(figsize=(15, 9.5))
    fig.suptitle("Carten T410R centre driveshaft with cup joints: stock parts, not part of the speedrun design "
                 "(modelled for the completeness of the build)", fontsize=12, y=0.985)
    ax = fig.add_axes([0.04, 0.55, 0.92, 0.38])
    draw(ax)
    y0, y1 = lay["shaft"]
    ax.annotate("", (y0, z + 9), (y1, z + 9), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text((y0 + y1) / 2, z + 9.4, f"shaft {lay['length']:.2f} (provisional: at End B the spur gear and a bearing "
            "lie between the housing and the cup)", ha="center", va="bottom", fontsize=9)
    h0, h1 = lay["housing"]
    ax.annotate("", (h0, z - 12), (h1, z - 12), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text((h0 + h1) / 2, z - 11.6, f"end faces of the pinion housings {h1 - h0:.2f}", ha="center", va="bottom",
            fontsize=9)
    ax.text(-4, 54, "End B (rear)", fontsize=9)
    ax.text(318, 54, "End A (front)", fontsize=9, ha="right")
    ax.set_xlim(-10, 320)
    ax.set_ylim(-2, 60)
    ax.set_title("Section along the pinion axis (x = 0), height above the bottom face of the chassis plate",
                 fontsize=10, loc="left")
    for k, (end, sign) in enumerate((("End B", 1), ("End A", -1))):
        i = 0 if sign > 0 else 1
        ax2 = fig.add_axes([0.04 + 0.48 * k, 0.05, 0.44, 0.44])
        draw(ax2)
        hy, bot, sh = lay["housing"][i], lay["bottom"][i], lay["shaft"][i]
        lo, hi = sorted((hy - sign * 14, hy + sign * 22))
        ax2.set_xlim(lo, hi)
        ax2.set_ylim(z - 11, z + 10)
        ax2.set_title(f"{end}: cup joint on the pinion", fontsize=10, loc="left")
        ax2.annotate("", (bot, z + 6.5), (sh, z + 6.5), arrowprops=dict(arrowstyle="<->", lw=0.8))
        ax2.plot([bot, bot], [z + 3.2, z + 7], color="k", lw=0.5)
        ax2.plot([sh, sh], [z + 2.6, z + 7], color="k", lw=0.5)
        ax2.text((bot + sh) / 2, z + 7.0, f"play {abs(sh - bot):.1f}", ha="center", va="bottom", fontsize=8)
        ax2.annotate("", (hy, z - 7.5), (lay["back"][i], z - 7.5), arrowprops=dict(arrowstyle="<->", lw=0.8))
        ax2.text((hy + lay["back"][i]) / 2, z - 8.0, f"gap {p['cup_gap']:g}", ha="center", va="top", fontsize=8)
        ax2.text(lay["back"][i] + sign * p["cup_length"] / 2, z - 5.6, "cup", ha="center", va="top", fontsize=8)
        ax2.text(hy - sign * 7, z + 8.0, "pinion housing", ha="center", fontsize=8)
        ax2.text(sh + sign * 12, z + 3.5, "shaft", ha="center", fontsize=8)
        yp = sh + sign * p["shaft_d"] / 2                    # metal pin at the centre of the ball end
        ax2.annotate(f"metal pin {p['pin_d']:g} x {p['pin_length']:g}", (yp, z), (yp + sign * 9, z - 3.5),
                     fontsize=8, ha="center", arrowprops=dict(arrowstyle="-", lw=0.6))
    fig.text(0.04, 0.008, f"Shaft {p['shaft_d']:g} mm with ball ends and cross holes {p['pin_hole_d']:g} mm for the metal "
             f"pins NBA255 {p['pin_d']:g} x {p['pin_length']:g} mm, which fix the shaft in the slots of the cups in the "
             f"direction of rotation. Total axial play {p['axial_play']:g} mm.\nCups {p['cup_od']:g} x "
             f"{p['cup_length']:g} mm, bore {p['cup_bore_d']:g} x {p['cup_bore_depth']:g} mm, slots {p['cup_slot_w']:g} mm "
             "(typical values, not measured). Metal pins and cups: simple bodies, no CAD files.", fontsize=8, va="bottom")
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Generate the centre driveshaft of the T410R (stock part, not part "
                                                 "of the speedrun design).")
    parser.parse_args()
    p, lp, up = load_params(PARAMS), load_params(LOWER), load_params(UPPER)
    lay = layout(p, lp)
    s = shaft_solid(p, lay["length"])
    stem = f"{OUT}/driveshaft_T410R"
    valid, bb, vol = s.isValid(), s.BoundingBox(), s.Volume()
    cq.exporters.export(cq.Workplane().add(s), stem + ".step")
    cq.exporters.export(cq.Workplane().add(s), stem + ".stl", tolerance=0.01, angularTolerance=0.1)
    print(f"driveshaft: wrote {stem}.step/.stl, solid valid: {valid}, size {bb.xlen:.2f} x {bb.ylen:.2f} x "
          f"{bb.zlen:.2f} mm, volume {vol / 1000:.2f} cm3, cross holes {p['pin_hole_d']:g} for the metal pins")

    parts = {name: solid for name, _, solid in parts_in_plate(p, lp)}
    bulkheads = []
    for end in ("rear", "front"):
        for solid in (bulkhead_lower(lp).val(), bulkhead_upper(lp, up).val()):
            s = solid.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180) if end == "front" else solid
            bulkheads.append(s.translate(cq.Vector(0, BULKHEAD_Y[end], PLATE_T)))
    plate = cq.importers.importStep("cad/chassis/chassis_plate_speedrun_wide_motor10/"
                                    "chassis_plate_T410R_speedrun_wide_motor10.step").val()
    items = [(plate, "#5b5f66")] + [(b, "#8c96a3" if k % 2 == 0 else "#d9a35f") for k, b in enumerate(bulkheads)]
    items += [(parts["cup End B"], "#b8bcc2"), (parts["cup End A"], "#b8bcc2"), (parts["centre driveshaft"], "#c0392b"),
              (parts["metal pin End B"], "#5d636b"), (parts["metal pin End A"], "#5d636b")]
    drawing(DRAWING, p, lay, items)
    print(f"Wrote {DRAWING}")

    h0, h1 = lay["housing"]
    print("layout on the chassis plate (y along the car)")
    print(f"  pinion axis: x = 0, z = {lay['z']:.2f} (height above the bottom face of the chassis plate)")
    print(f"  end faces of the pinion housings: y = {h0:.2f} (End B) and {h1:.2f} (End A), {h1 - h0:.2f} apart")
    print(f"  bottoms of the cups: y = {lay['bottom'][0]:.2f} and {lay['bottom'][1]:.2f}, "
          f"{lay['bottom'][1] - lay['bottom'][0]:.2f} apart")
    print(f"  shaft: length {lay['length']:.2f}, from y = {lay['shaft'][0]:.2f} to {lay['shaft'][1]:.2f}, "
          f"play {lay['shaft'][0] - lay['bottom'][0]:.2f} at End B and {lay['bottom'][1] - lay['shaft'][1]:.2f} at End A")
    print("checks")
    shaft_p = parts["centre driveshaft"]
    for name in ("cup End B", "cup End A"):
        print(f"  shaft / {name}: overlap {shaft_p.intersect(parts[name]).Volume():.4f} mm3")
    for end in ("End B", "End A"):
        pin = parts[f"metal pin {end}"]
        print(f"  metal pin {end}: overlap with the cup {pin.intersect(parts['cup ' + end]).Volume():.4f} mm3, "
              f"with the shaft (pin in the cross hole) {pin.intersect(shaft_p).Volume():.4f} mm3")
    for name, s in parts.items():
        worst = max(s.intersect(b).Volume() for b in bulkheads + [plate])
        print(f"  {name} / bulkheads and chassis plate: largest overlap {worst:.4f} mm3")
    print(f"  radial clearance of the ball ends in the cups: {(p['cup_bore_d'] - p['shaft_d']) / 2:.2f}, "
          f"cross pins in the slots: {(p['cup_slot_w'] - p['pin_d']) / 2:.2f} per side, pin ends inside the cups: "
          f"{(p['cup_od'] - p['pin_length']) / 2:.2f}")


if __name__ == "__main__":
    main()
