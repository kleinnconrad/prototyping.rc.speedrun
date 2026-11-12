"""Check the speedrun chassis plate (wide) with the longer motor window.

The checks compare the STEP file of the variant with the longer motor window
(method A: generated from the geometry data) with a second solid that is made by
cutting the longer window into the STEP file of the speedrun chassis plate (wide)
(method B). The script prints:

* number of solids, validity, bounding box and volume
* volume difference between method A and method B
* window size in a section at half thickness
* number of hole faces (cylinders r = 1.6 mm and countersink cones)
* distance from the window to the countersink rims (circles on the bottom face)

Usage (from the root directory of the repository):
    python scripts/cad/check_motor_window.py

Requires the package cadquery (pip install cadquery).
"""
import argparse
import json
from collections import Counter

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface

CAD = "cad/chassis"
WIDE = f"{CAD}/chassis_plate_speedrun_wide"
MOTOR10 = f"{CAD}/chassis_plate_speedrun_wide_motor10"


def window_bounds(geometry):
    pts = [p[k] for p in geometry["cutouts"]["window"] for k in ("start", "end")]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    radius = [p["r"] for p in geometry["cutouts"]["window"] if p["type"] == "arc"][0]
    return min(xs), max(xs), min(ys), max(ys), radius


def window_cutter(x0, x1, y0, y1, radius, z0=-1.0, height=4.0):
    return (cq.Workplane("XY").workplane(offset=z0)
            .center((x0 + x1) / 2, (y0 + y1) / 2).rect(x1 - x0, y1 - y0).extrude(height)
            .edges("|Z").fillet(radius))


def main():
    parser = argparse.ArgumentParser(description="Check the plate with the longer motor window.")
    parser.add_argument("--old-step", default=f"{WIDE}/chassis_plate_T410R_speedrun_wide.step")
    parser.add_argument("--new-step", default=f"{MOTOR10}/chassis_plate_T410R_speedrun_wide_motor10.step")
    parser.add_argument("--old-geometry", default=f"{WIDE}/chassis_plate_speedrun_wide_geometry.json")
    parser.add_argument("--new-geometry", default=f"{MOTOR10}/chassis_plate_speedrun_wide_motor10_geometry.json")
    args = parser.parse_args()

    with open(args.old_geometry, encoding="utf-8") as f:
        g_old = json.load(f)
    with open(args.new_geometry, encoding="utf-8") as f:
        g_new = json.load(f)
    old = cq.importers.importStep(args.old_step).solids().vals()[0]
    new_solids = cq.importers.importStep(args.new_step).solids().vals()
    a = new_solids[0]

    # method B: cut the longer window into the old STEP file
    x0, x1, y0, y1, radius = window_bounds(g_new)
    b = cq.importers.importStep(args.old_step).cut(window_cutter(x0, x1, y0, y1, radius)).solids().vals()[0]

    bb = a.BoundingBox()
    width = x1 - x0
    extension = y1 - window_bounds(g_old)[3]
    print(f"Solids: {len(new_solids)}, valid: {a.isValid()}")
    print(f"Bounding box: x {bb.xmin:.3f} to {bb.xmax:.3f}, y {bb.ymin:.3f} to {bb.ymax:.3f}, "
          f"z {bb.zmin:.3f} to {bb.zmax:.3f}")
    print(f"Volume: before {old.Volume():.2f} mm3, after {a.Volume():.2f} mm3, "
          f"difference {a.Volume() - old.Volume():.2f} mm3 "
          f"(expected -{width * extension * g_new['thickness']:.2f})")
    print(f"Method A minus method B: {a.cut(b).Volume():.6f} mm3, "
          f"method B minus method A: {b.cut(a).Volume():.6f} mm3")

    plane = cq.Face.makePlane(600, 600, basePnt=cq.Vector(0, 160, g_new["thickness"] / 2))
    loops = [w for f in a.intersect(plane).Faces() for w in f.innerWires()]
    win = max(loops, key=lambda w: w.BoundingBox().xlen * w.BoundingBox().ylen).BoundingBox()
    print(f"Section at z = {g_new['thickness'] / 2:g}: window x {win.xmin:.3f} to {win.xmax:.3f}, "
          f"y {win.ymin:.3f} to {win.ymax:.3f} ({win.xlen:.3f} x {win.ylen:.3f})")

    rh = g_new["hole_d"] / 2
    cylinders = sum(1 for f in a.Faces() if f.geomType() == "CYLINDER"
                    and abs(BRepAdaptor_Surface(f.wrapped).Cylinder().Radius() - rh) < 1e-6)
    cones = sum(1 for f in a.Faces() if f.geomType() == "CONE")
    print(f"Holes: {cylinders} cylinders r = {rh:g} mm, {cones} countersink cones, "
          f"hole positions identical to the old geometry data: {g_new['holes'] == g_old['holes']}")

    rc = g_new["csk_d"] / 2
    rims = [e for e in a.Edges() if e.geomType() == "CIRCLE"
            and abs(e.radius() - rc) < 1e-6 and abs(e.Center().z) < 1e-6]
    old_win = window_cutter(*window_bounds(g_old), z0=0.0, height=1.0).val()
    new_win = window_cutter(x0, x1, y0, y1, radius, z0=0.0, height=1.0).val()
    rows = []
    for e in rims:
        c = e.Center()
        hole = min(g_new["holes"], key=lambda h: (h["x"] - c.x) ** 2 + (h["y"] - c.y) ** 2)
        rows.append((e.distance(new_win), e.distance(old_win), hole["id"]))
    print(f"Distance from the window to the countersink rims (Ø{g_new['csk_d']:g} mm, bottom face):")
    for d_new, d_old, hole_id in sorted(rows)[:6]:
        print(f"  {hole_id}: {d_old:.2f} mm before, {d_new:.2f} mm after")


if __name__ == "__main__":
    main()
