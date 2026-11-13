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
import math

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


def contour_samples(p, n):
    """Points and unit tangents along a line or arc of a contour (in the direction of the contour)."""
    if p["type"] == "line":
        a, b = np.array(p["start"]), np.array(p["end"])
        t = (b - a) / np.linalg.norm(b - a)
        return [(a + (b - a) * k / (n - 1), t) for k in range(n)]
    c = np.array(p["center"])
    a0, am, a1 = (math.atan2(q[1] - c[1], q[0] - c[0]) for q in (p["start"], p["mid"], p["end"]))
    s_mid, s_end = (am - a0) % (2 * math.pi), (a1 - a0) % (2 * math.pi)
    sweep = s_end if s_mid < s_end else s_end - 2 * math.pi
    out = []
    for k in range(n):
        a = a0 + sweep * k / (n - 1)
        out.append((c + p["r"] * np.array([math.cos(a), math.sin(a)]),
                    np.sign(sweep) * np.array([-math.sin(a), math.cos(a)])))
    return out


def edge_chamfer_tools(prims, z_face, into, size, eps=0.01, material_inside=True):
    """Cutting tools of an edge chamfer along a contour on the face z = z_face (material on the side
    +into in z). size(point) gives the leg length of the chamfer at a point of the contour.
    material_inside: the material lies inside the contour (outline) or outside (cutout).

    Each tool is a triangle with the given legs on the face and on the side wall of the contour,
    swept along a line or arc of the contour (ruled for lines, smooth for arcs). The triangles
    of adjacent lines and arcs are the same at their common point (tangent contours)."""
    pts = np.array([q for p in prims for q, _ in contour_samples(p, 12)])
    area = 0.5 * np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1])
    ccw = (area > 0) == material_inside
    tools = []
    for p in prims:
        n = 2 if p["type"] == "line" else 9
        if p["type"] == "line":
            a, b = np.array(p["start"]), np.array(p["end"])
            if any(abs(size(a + (b - a) * k / 4) - size(a)) > 1e-9 for k in range(5)):
                n = 9                                       # leg length changes along the line
        wires = []
        for q, t in contour_samples(p, n):
            out = np.array([t[1], -t[0]]) if ccw else np.array([-t[1], t[0]])
            d = size(q)
            corner = [(q + out * eps, z_face - into * eps), (q - out * d, z_face - into * eps),
                      (q + out * eps, z_face + into * d)]
            wires.append(cq.Wire.makePolygon([cq.Vector(x, y, z) for (x, y), z in corner], close=True))
        tools.append(cq.Solid.makeLoft(wires, ruled=(p["type"] == "line")))
    return tools


def hole_chamfer_cones(x, y, r, c, t):
    """Cones of a chamfer c on both ends of a through hole with the radius r in a plate 0 <= z <= t."""
    return [cq.Solid.makeCone(r + c + 0.01, r - 0.01, c + 0.02, cq.Vector(x, y, z0 - dz * 0.01), cq.Vector(0, 0, dz))
            for z0, dz in ((0.0, 1), (t, -1))]


def chamfered_plate_solid(geometry, edge, hole_edge):
    """Plate solid (cadquery Solid) with edge chamfers: chamfer edge on both faces of the outline and
    of the cutouts, chamfer hole_edge on both ends of the holes (plain through holes, no countersinks)."""
    t = geometry["thickness"]
    s = wire_from_prims(geometry["outline"]).extrude(t).val()
    for contour in geometry["cutouts"].values():
        s = s.cut(wire_from_prims(contour, -1).extrude(t + 2).val())

    def size(q):
        return edge
    tools = []
    for prims, inside in [(geometry["outline"], True)] + [(c, False) for c in geometry["cutouts"].values()]:
        for z_face, into in ((0.0, 1), (t, -1)):
            tools += edge_chamfer_tools(prims, z_face, into, size, material_inside=inside)
    for tool in tools:
        s = s.cut(tool)
    r = geometry["hole_d"] / 2
    for h in geometry["holes"]:
        s = s.cut(cq.Solid.makeCylinder(r, t + 2, cq.Vector(h["x"], h["y"], -1)))
        for cone in hole_chamfer_cones(h["x"], h["y"], r, hole_edge, t):
            s = s.cut(cone)
    return s.clean()


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
