"""Create the geometry data of a plate from the outline of a STEP file.

The outer outline is read from the top face of the STEP solid. The holes, the
cutouts, the thickness and the countersink parameters are copied from a
reference geometry file. This is used for the speedrun chassis plate (wide):
its outline differs from the chassis plate v2, all other features are
identical.

Usage (from the root directory of the repository):
    python scripts/cad/geometry_from_step.py [--check]

Without arguments, the script reads the STEP file of the speedrun chassis plate
(wide) and the geometry data of the chassis plate v2 and writes
chassis_plate_speedrun_wide_geometry.json. With --check, it rebuilds the solid
from the new geometry data and compares it with the STEP file.

Requires the package cadquery (pip install cadquery).
"""
import argparse
import copy
import json
import os
import sys

import numpy as np
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Line

CAD = "cad/chassis_v2"
DEFAULT_STEP = f"{CAD}/chassis_plate_speedrun_wide/chassis_plate_T410R_speedrun_wide.step"
DEFAULT_REFERENCE = f"{CAD}/chassis_plate/chassis_plate_v2_geometry.json"
DEFAULT_OUTPUT = f"{CAD}/chassis_plate_speedrun_wide/chassis_plate_speedrun_wide_geometry.json"
TOL = 1e-5  # mm, tolerance for connecting the edges of the outline


def edge_prim(edge):
    """Line or arc primitive (geometry JSON format) of an edge."""
    c = BRepAdaptor_Curve(edge.wrapped)
    t0, t1 = c.FirstParameter(), c.LastParameter()
    point = lambda t: [c.Value(t).X(), c.Value(t).Y()]
    a, b = point(t0), point(t1)
    if c.GetType() == GeomAbs_Line:
        return {"type": "line", "start": a, "end": b}
    if c.GetType() != GeomAbs_Circle:
        raise ValueError("outline contains an edge that is neither a line nor an arc")
    circle = c.Circle()
    return {"type": "arc", "start": a, "mid": point((t0 + t1) / 2), "end": b,
            "center": [circle.Location().X(), circle.Location().Y()], "r": circle.Radius()}


def reverse(p):
    q = dict(p)
    q["start"], q["end"] = p["end"], p["start"]
    return q


def signed_area(prims):
    pts = np.array([p["start"] for p in prims])
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def outline_from_step(step_path, thickness, reference_outline):
    """Ordered outline primitives of the top face, in the direction of the reference outline."""
    solid = cq.importers.importStep(step_path).solids().vals()[0]
    top = [f for f in solid.Faces() if f.geomType() == "PLANE" and abs(f.Center().z - thickness) < 1e-6]
    top = max(top, key=lambda f: f.Area())
    pool = [edge_prim(e) for e in top.outerWire().Edges()]
    dist = lambda u, v: float(np.hypot(u[0] - v[0], u[1] - v[1]))
    chain = [pool.pop(0)]
    while pool:
        cur = chain[-1]["end"]
        for i, p in enumerate(pool):
            if dist(p["start"], cur) < TOL:
                chain.append(pool.pop(i))
                break
            if dist(p["end"], cur) < TOL:
                chain.append(reverse(pool.pop(i)))
                break
        else:
            raise ValueError(f"outline is not closed at {cur}")
    if dist(chain[-1]["end"], chain[0]["start"]) > TOL:
        raise ValueError("outline is not closed")
    if signed_area(chain) * signed_area(reference_outline) < 0:
        chain = [reverse(p) for p in reversed(chain)]
    return chain


def main():
    parser = argparse.ArgumentParser(description="Create geometry data from the outline of a STEP file.")
    parser.add_argument("--step", default=DEFAULT_STEP, help="STEP file with the outline")
    parser.add_argument("--reference", default=DEFAULT_REFERENCE, help="geometry JSON with holes and cutouts")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="geometry JSON file to write")
    parser.add_argument("--check", action="store_true", help="rebuild the solid and compare it with the STEP file")
    args = parser.parse_args()

    with open(args.reference, encoding="utf-8") as f:
        reference = json.load(f)
    geometry = copy.deepcopy(reference)
    geometry["outline"] = outline_from_step(args.step, reference["thickness"], reference["outline"])
    geometry["version"] = ("speedrun wide (outline from " + os.path.basename(args.step)
                           + "; holes, cutouts and thickness from " + reference["version"] + ")")
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(geometry, f, indent=1)
    print(f"Wrote {args.output}: outline with {len(geometry['outline'])} edges")

    if args.check:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from generate_solid import plate_solid
        rebuilt = plate_solid(geometry).val()
        original = cq.importers.importStep(args.step).solids().vals()[0]
        print(f"  volume rebuilt {rebuilt.Volume():.4f} mm3, STEP {original.Volume():.4f} mm3")
        print(f"  difference volumes: rebuilt minus STEP {rebuilt.cut(original).Volume():.6f} mm3, "
              f"STEP minus rebuilt {original.cut(rebuilt).Volume():.6f} mm3")


if __name__ == "__main__":
    main()
