"""Generate the pivot blocks of the Carten T410R (stock parts, not part of the speedrun design).

The pivot blocks hold the hinge pins of the wishbones (suspension arms). They are stock parts:
they are not part of the speedrun design and are not manufactured in this project. They are
modelled for the completeness of the build: the assembly of the speedrun chassis contains them,
so that the space below the bulkheads can be checked.

* long block: 1 piece, at the outer end of the rear axle (End B), on the holes H01/H02
* short block: 3 pieces, inner block of the rear axle (H07/H08) and both blocks of the front
  axle (H26/H27, H32/H33)

The dimensions are measurements of the owner (cad/stock_parts/pivot_block/pivot_block_parameters.json).
The distances of the mounting holes are taken from the hole pattern of the speedrun chassis
plate. Block coordinates: x along the block (across the car), y across the block (along the
car), z = 0 bottom face.

Usage (from the root directory of the repository):
    python scripts/cad/generate_pivot_blocks.py

The script writes the STEP and STL files of both blocks and the drawing
photos/cad_pivot_blocks_drawing.png. It checks the mounting holes against the holes of the
chassis plate and the clearance of the placed blocks to the bulkheads.

Requires the packages cadquery and matplotlib.
"""
import argparse
import json
import os
import sys

import numpy as np
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_bulkhead_lower import box, bulkhead_lower, cyl_y, cyl_z, load_params  # noqa: E402
from generate_bulkhead_upper import bulkhead_upper  # noqa: E402
from generate_top_brace_speedrun import BULKHEAD_Y  # noqa: E402

PARAMS = "cad/stock_parts/pivot_block/pivot_block_parameters.json"
PLATE_GEOM = "cad/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_speedrun_wide_motor10_geometry.json"
LOWER = "cad/bulkhead/bulkhead_lower_parameters.json"
UPPER = "cad/bulkhead/bulkhead_upper_parameters.json"
OUT = "cad/stock_parts/pivot_block"
DRAWING = "photos/cad_pivot_blocks_drawing.png"
PLATE_T = 2.0
# positions on the speedrun chassis plate: (name, kind, holes of the chassis plate, end of the car)
POSITIONS = [("End B, outer", "long", ("H02", "H01"), "rear"),
             ("End B, inner", "short", ("H08", "H07"), "rear"),
             ("End A, inner", "short", ("H26", "H27"), "front"),
             ("End A, outer", "short", ("H32", "H33"), "front")]


def dims(p, kind):
    """(length, distance of the bores, distance of the mounting holes, length of the shoulder)."""
    return (p[f"{kind}_length"], p[f"{kind}_pin_spacing"], p[f"{kind}_mount_spacing"], p[f"{kind}_shoulder_len"])


def block_solid(p, kind):
    """Solid of a pivot block in block coordinates (cadquery Solid)."""
    length, pins, mounts, shoulder = dims(p, kind)
    c, w = pins / 2, p["width"]
    xs = length / 2 - shoulder                              # step from the shoulder down to the bar
    s = box(-c, c, -w / 2, w / 2, 0, p["bar_h"])
    for sx in (-1, 1):
        xa, xb = sorted((sx * xs, sx * c))
        s = s.fuse(box(xa, xb, -w / 2, w / 2, 0, p["shoulder_h"]))
        s = s.fuse(cyl_y(p["lobe_r"], -w / 2, w / 2, sx * c, p["pin_h"]))
    for sx in (-1, 1):
        # blind bores of the hinge pin seats, open at y = +w/2
        s = s.cut(cyl_y(p["pin_bore_d"] / 2, w / 2 - p["pin_bore_depth"], w / 2 + 1, sx * c, p["pin_h"]))
        s = s.cut(cyl_z(p["mount_hole_d"] / 2, -1, p["height_max"] + 1, sx * mounts / 2, 0))
    return s.clean()


def plate_holes():
    with open(PLATE_GEOM, encoding="utf-8") as f:
        return {h["id"]: (h["x"], h["y"]) for h in json.load(f)["holes"]}


def blocks_in_plate(p=None):
    """Pivot blocks placed on the speedrun chassis plate (coordinates of the chassis plate, bottom
    face on the top face of the plate): list of (name, kind, solid, largest offset of the mounting
    holes to the holes of the plate). The blind bores open toward the bulkhead: blocks on the far
    side of their bulkhead (toward -y) are turned by 180 degrees about z."""
    p = p or load_params(PARAMS)
    holes = plate_holes()
    solids = {k: block_solid(p, k) for k in ("long", "short")}
    placed = []
    for name, kind, (ha, hb), end in POSITIONS:
        (xa, ya), (xb, yb) = holes[ha], holes[hb]
        xm, ym = (xa + xb) / 2, (ya + yb) / 2
        block = solids[kind]
        if BULKHEAD_Y[end] < ym:                            # bulkhead toward -y: bores open toward -y
            block = block.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180)
        m = dims(p, kind)[2] / 2
        offset = max(abs((xm - m) - min(xa, xb)), abs((xm + m) - max(xa, xb)), abs(ya - yb) / 2)
        placed.append((name, kind, block.translate(cq.Vector(xm, ym, PLATE_T)), offset))
    return placed


def bulkheads_at(lp, up, end):
    """Lower and upper bulkhead at one end, in the coordinates of the chassis plate."""
    out = []
    for solid in (bulkhead_lower(lp).val(), bulkhead_upper(lp, up).val()):
        s = solid.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180) if end == "front" else solid
        out.append(s.translate(cq.Vector(0, BULKHEAD_Y[end], PLATE_T)))
    return out


def drawing(path, p, solids):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon as MPoly, Rectangle
    from OCP.BRepTools import BRepTools_WireExplorer

    def section_polys(solid):
        """Polygons (x, z) of the section at y = 0: outer wires and inner wires."""
        plane = cq.Face.makePlane(200, 200, cq.Vector(0, 0, 0), cq.Vector(0, 1, 0))
        out = []
        for f in solid.intersect(plane).Faces():
            for outer, wire in [(True, f.outerWire())] + [(False, iw) for iw in f.innerWires()]:
                ex = BRepTools_WireExplorer(wire.wrapped)
                poly = []
                while ex.More():
                    ed = cq.Edge(ex.Current())
                    n = 2 if ed.geomType() == "LINE" else 40
                    seg = [(ed.positionAt(k / (n - 1)).x, ed.positionAt(k / (n - 1)).z) for k in range(n)]
                    if poly and np.hypot(*(np.array(seg[0]) - poly[-1])) > np.hypot(*(np.array(seg[-1]) - poly[-1])):
                        seg = seg[::-1]
                    poly += seg
                    ex.Next()
                out.append((outer, poly))
        return out

    fig = plt.figure(figsize=(15, 9.5))
    fig.suptitle("Carten T410R pivot blocks: stock parts, not part of the speedrun design (modelled for the "
                 "completeness of the build)",
                 fontsize=12, y=0.985)
    w = p["width"]
    for row, kind in enumerate(("long", "short")):
        length, pins, mounts, shoulder = dims(p, kind)
        n = "1 piece: End B, outer (H01/H02)" if kind == "long" else "3 pieces: End B inner, End A inner and outer"
        # section along the block
        ax = fig.add_axes([0.04, 0.53 - 0.47 * row, 0.6, 0.4])
        for outer, poly in section_polys(solids[kind]):
            ax.add_patch(MPoly(poly, closed=True, fc="#3b4048" if outer else "white", ec="#1d2025", lw=0.8))
        ax.set_title(f"{kind.capitalize()} block ({n}): section y = 0", fontsize=10, loc="left")
        yd = -2.5
        for k, (xd, label) in enumerate(((length / 2, f"{length:.1f}"), (pins / 2, f"{pins:.1f} (hinge pins)"),
                                         (mounts / 2, f"{mounts:.2f} (mounting holes, chassis plate)"))):
            yy = yd - 2.6 * k
            ax.annotate("", (-xd, yy), (xd, yy), arrowprops=dict(arrowstyle="<->", lw=0.8))
            ax.text(0, yy + 0.25, label, ha="center", va="bottom", fontsize=8)
        xr = length / 2 + 2
        for zz in (p["height_max"], p["shoulder_h"], p["pin_h"], p["bar_h"]):
            ax.plot([xr - 1, xr + 1], [zz, zz], color="k", lw=0.7)
            ax.text(xr + 1.5, zz, f"{zz:.1f}", va="center", fontsize=8)
        ax.text(xr - 1, p["height_max"] + 1.2, "height above the\nbottom face", fontsize=7.5, va="bottom")
        ys = p["height_max"] + 1.0
        ax.annotate("", (length / 2 - shoulder, ys), (length / 2, ys), arrowprops=dict(arrowstyle="<->", lw=0.8))
        ax.text(length / 2 - shoulder / 2, ys + 0.25, f"shoulder {shoulder:g}", ha="center", va="bottom", fontsize=8)
        ax.text(0, p["bar_h"] + 0.4, "bar", ha="center", fontsize=8)
        ax.set_xlim(-length / 2 - 3, length / 2 + 9)
        ax.set_ylim(yd - 2.6 * 3, p["height_max"] + 4.5)
        ax.set_aspect("equal")
        ax.grid(True, color="#eeeeee", lw=0.6)
        # top view
        ax2 = fig.add_axes([0.68, 0.53 - 0.47 * row, 0.3, 0.4])
        ax2.add_patch(Rectangle((-length / 2, -w / 2), length, w, fc="#3b4048", ec="#1d2025", lw=0.8))
        for sx in (-1, 1):
            ax2.add_patch(Circle((sx * mounts / 2, 0), p["mount_hole_d"] / 2, fc="white", ec="#1d2025", lw=0.6))
            yb = w / 2 - p["pin_bore_depth"]                     # bottom of the blind bore
            for xe in (pins / 2 - p["pin_bore_d"] / 2, pins / 2 + p["pin_bore_d"] / 2):
                ax2.plot([sx * xe] * 2, [yb, w / 2], color="#bbbbbb", lw=0.6, ls="--")
            ax2.plot([sx * (pins / 2 - p["pin_bore_d"] / 2), sx * (pins / 2 + p["pin_bore_d"] / 2)], [yb, yb],
                     color="#bbbbbb", lw=0.6, ls="--")
        ax2.annotate("", (length / 2 + 1.2, -w / 2), (length / 2 + 1.2, w / 2), arrowprops=dict(arrowstyle="<->", lw=0.8))
        ax2.text(length / 2 + 1.6, 0, f"{w:.2f}", va="center", fontsize=8)
        ax2.set_title(f"Top view (blind bores {p['pin_bore_depth']:g} deep dashed, open at the top edge,\n"
                      "the side that faces the bulkhead)", fontsize=10, loc="left")
        ax2.set_xlim(-length / 2 - 2, length / 2 + 6)
        ax2.set_ylim(-w / 2 - 6, w / 2 + 6)
        ax2.set_aspect("equal")
        ax2.axis("off")
    fig.text(0.04, 0.008, f"Bores {p['pin_bore_d']:g} x {p['pin_bore_depth']:g} deep (blind, open toward the bulkhead) for the hinge pins "
             "with inserts (inserts not modelled). Mounting holes: tap drill 2.5 for the M3 countersunk screws from below\n"
             "through the chassis plate (assumed through). Heights, lengths and bores: measurements of the owner; "
             "shoulder lengths from photos.", fontsize=8, va="bottom")
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Generate the pivot blocks of the T410R (stock parts, not part of the speedrun design).")
    parser.parse_args()
    p = load_params(PARAMS)
    assert abs(p["lobe_r"] - (p["long_length"] - p["long_pin_spacing"]) / 2) < 1e-9
    assert abs(p["short_length"] - (p["short_pin_spacing"] + 2 * p["lobe_r"])) < 1e-9
    assert abs(p["pin_h"] - (p["height_max"] - p["lobe_r"])) < 1e-9
    solids = {k: block_solid(p, k) for k in ("long", "short")}
    for kind, s in solids.items():
        stem = f"{OUT}/pivot_block_{kind}_T410R"
        valid, bb, vol = s.isValid(), s.BoundingBox(), s.Volume()
        cq.exporters.export(cq.Workplane().add(s), stem + ".step")
        cq.exporters.export(cq.Workplane().add(s), stem + ".stl", tolerance=0.01, angularTolerance=0.1)
        print(f"{kind} block: wrote {stem}.step/.stl, solid valid: {valid}, size {bb.xlen:.2f} x {bb.ylen:.2f} x "
              f"{bb.zlen:.2f} mm, volume {vol / 1000:.2f} cm3")
    drawing(DRAWING, p, solids)
    print(f"Wrote {DRAWING}")

    lp, up = load_params(LOWER), load_params(UPPER)
    ends = {e: bulkheads_at(lp, up, e) for e in ("rear", "front")}
    print("checks (blocks on the speedrun chassis plate)")
    for (name, kind, s, offset), (_, _, holes, end) in zip(blocks_in_plate(p), POSITIONS):
        faces = cq.Compound.makeCompound(s.Faces())
        res = []
        for label, b in zip(("lower", "upper"), ends[end]):
            inter = s.intersect(b).Volume()
            dist = faces.distance(cq.Compound.makeCompound(b.Faces()))
            res.append(f"{label} bulkhead: overlap {inter:.4f} mm3, distance {dist:.2f} mm")
        print(f"  {name} ({kind}, holes {holes[0]}/{holes[1]}): mounting holes offset {offset:.3f} mm; " + "; ".join(res))


if __name__ == "__main__":
    main()
