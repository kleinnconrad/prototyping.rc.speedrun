"""Generate a STEP and an STL file of a plate from a geometry JSON file.

The plate is extruded from the outline in the geometry data. The cutouts are
cut through the plate. Each hole is a through hole (hole_d) with a 90 degree
countersink (csk_d) on the bottom face (z = 0). The countersinks are omitted if
csk_d is 0.

Usage (from the root directory of the repository):
    python scripts/cad/generate_solid.py <geometry.json> <output_stem>

The script writes <output_stem>.step and <output_stem>.stl (STL tolerance
0.01 mm, angular tolerance 0.1 rad). Example:
    python scripts/cad/generate_solid.py \\
        cad/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_speedrun_wide_motor10_geometry.json \\
        cad/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_T410R_speedrun_wide_motor10

Requires the package cadquery (pip install cadquery).
"""
import argparse
import json

import numpy as np
import cadquery as cq


def wire_from_prims(prims, z=0.0):
    """Closed wire from the lines and arcs of a contour at the height z."""
    wp = cq.Workplane("XY").workplane(offset=z).moveTo(*prims[0]["start"])
    for p in prims:
        if p["type"] == "line":
            if np.hypot(p["end"][0] - p["start"][0], p["end"][1] - p["start"][1]) > 1e-6:
                wp = wp.lineTo(*p["end"])
        else:
            wp = wp.threePointArc(tuple(p["mid"]), tuple(p["end"]))
    return wp.close()


def plate_solid(geometry):
    """Build the plate solid (cadquery Workplane) from the geometry data."""
    t = geometry["thickness"]
    body = wire_from_prims(geometry["outline"]).extrude(t)
    for contour in geometry["cutouts"].values():
        body = body.cut(wire_from_prims(contour, -1).extrude(t + 2))
    rh, rc = geometry["hole_d"] / 2, geometry.get("csk_d", 0) / 2
    k = np.tan(np.radians(geometry.get("csk_angle", 90.0) / 2))
    cutter = None
    for h in geometry["holes"]:
        s = cq.Solid.makeCylinder(rh, t + 2, cq.Vector(h["x"], h["y"], -1))
        if rc > rh:
            depth = (rc - rh) / k          # 1.5 mm for 3.2 / 6.2 / 90 degrees
            ext = 0.5                      # the cone starts 0.5 mm below the bottom face
            cone = cq.Solid.makeCone(rc + ext * k, rh, depth + ext,
                                     cq.Vector(h["x"], h["y"], -ext), cq.Vector(0, 0, 1))
            s = s.fuse(cone)
        cutter = s if cutter is None else cutter.fuse(s)
    return body.cut(cq.Workplane().add(cutter))


def main():
    parser = argparse.ArgumentParser(description="Generate STEP and STL files from a geometry JSON file.")
    parser.add_argument("geometry", help="geometry JSON file (*_geometry.json)")
    parser.add_argument("output_stem", help="output path without extension")
    args = parser.parse_args()

    with open(args.geometry, encoding="utf-8") as f:
        geometry = json.load(f)
    solid = plate_solid(geometry)
    cq.exporters.export(solid, args.output_stem + ".step")
    cq.exporters.export(solid, args.output_stem + ".stl", tolerance=0.01, angularTolerance=0.1)

    # report from the written STEP file
    solids = cq.importers.importStep(args.output_stem + ".step").solids().vals()
    bb = solids[0].BoundingBox()
    print(f"Wrote {args.output_stem}.step and .stl")
    print(f"  solids: {len(solids)}, valid: {solids[0].isValid()}")
    print(f"  bounding box: x {bb.xmin:.3f} to {bb.xmax:.3f}, y {bb.ymin:.3f} to {bb.ymax:.3f}, "
          f"z {bb.zmin:.3f} to {bb.zmax:.3f}")
    print(f"  volume: {solids[0].Volume():.2f} mm3")


if __name__ == "__main__":
    main()
