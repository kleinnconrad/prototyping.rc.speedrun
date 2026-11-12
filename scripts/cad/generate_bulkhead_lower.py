"""Generate the lower bulkhead (gear box lower half) of the Carten T410R.

The solid is built from the parameter file of the part. The body is the
intersection of the footprint of the upper part (extruded in z) and the side
profile (extruded in x): a flat contact face on the chassis plate and one
straight chamfer per side, below which the pivot blocks of the wishbones are
mounted. A rectangular block under the pinion, the bosses for the upper
bulkhead and the tabs for the sway bar mounts are added. The gear cavity, the
bearing seats and the M3 holes are cut.

Coordinate system: origin at the centre of the 4 bottom holes on the bottom face,
x along the diff axis, +y toward the pinion, z = 0 bottom face.

Usage (from the root directory of the repository):
    python scripts/cad/generate_bulkhead_lower.py

The script writes the STEP and STL file of the part (nominal dimensions, for CNC
manufacturing) and an STL file for a test print (bearing seats enlarged by
print_seat_allowance, M3 holes with print_hole_d for self-tapping screws).

Requires the package cadquery (pip install cadquery).
"""
import argparse
import json

import cadquery as cq

BIG = 200.0


def load_params(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v["value"] for k, v in data["parameters"].items()}


def cyl_x(r, x0, x1, y, z):
    """Cylinder along x from x0 to x1 with the axis at (y, z)."""
    return cq.Solid.makeCylinder(r, x1 - x0, cq.Vector(x0, y, z), cq.Vector(1, 0, 0))


def cyl_y(r, y0, y1, x, z):
    """Cylinder along y from y0 to y1 with the axis at (x, z)."""
    return cq.Solid.makeCylinder(r, y1 - y0, cq.Vector(x, y0, z), cq.Vector(0, 1, 0))


def cyl_z(r, z0, z1, x, y):
    """Cylinder along z from z0 to z1 with the axis at (x, y)."""
    return cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1))


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def bulkhead_lower(p, test_print=False):
    """Build the solid (cadquery Workplane) from the parameters."""
    zc = p["axis_z"]
    yd = p["diff_axis_y"]
    w = p["body_half_width"]
    seat_add = p["print_seat_allowance"] if test_print else 0.0
    hole_d = p["print_hole_d"] if test_print else None

    # body: footprint of the upper part, extruded to the parting face
    y0, y1 = p["body_y_outer_end"], p["body_y_pinion_end"]
    plan = (cq.Workplane("XY").center(0, (y0 + y1) / 2)
            .rect(2 * w, y1 - y0).extrude(zc + 5).edges("|Z").fillet(p["body_corner_r"]))

    # body: side profile (y, z), flat contact face on the chassis plate and one straight chamfer
    # per side up to a short end face (space for the pivot blocks below the chamfers)
    a, hb, he = p["base_half_length"], p["base_height"], p["end_face_h"]
    pts = [(y0, zc), (y0, zc - he), (-a, hb), (-a, 0.0), (a, 0.0), (a, hb), (y1, zc - he), (y1, zc)]
    side = cq.Workplane("YZ").polyline(pts).close().extrude(w + 5, both=True)
    body = plan.intersect(side)

    # stepped block under the pinion: wide and deep under the pinion pocket, narrow under the
    # pinion seats and beyond the end of the footprint (outer pinion bearing)
    yp_in = p["pinion_seat_y_inner"]
    yp_end = yp_in + p["pinion_seat_length"]
    k = p["pinion_pocket_r"] + p["pinion_pocket_wall"]
    kh = p["pinion_housing_r"]
    body = body.union(cq.Workplane().add(box(-k, k, a, yp_in + p["pinion_pocket_wall"], zc - k, zc)))
    body = body.union(cq.Workplane().add(box(-kh, kh, yp_in - 0.01, yp_end, zc - kh, zc)))

    # tabs for the sway bar mounts (top face in the parting face)
    tx, ty, tr, tt = p["swaybar_hole_x"], p["swaybar_hole_y"], p["swaybar_tab_r"], p["swaybar_tab_t"]
    for sx in (-1, 1):
        tab = (cq.Workplane("XY").workplane(offset=zc - tt)
               .center(sx * tx, ty).circle(tr).extrude(tt))
        bridge = box(sx * tx - tr, sx * tx + tr, ty, -a, zc - tt, zc)
        body = body.union(tab).union(cq.Workplane().add(bridge))

    # remove everything above the parting face
    body = body.cut(cq.Workplane().add(box(-BIG, BIG, -BIG, BIG, zc, BIG)))

    # bosses for the screws of the upper bulkhead (the two pairs have different spacings)
    br = p["top_boss_d"] / 2
    ztop = zc + p["top_boss_protrusion"]
    bosses = [(sx * p["top_boss_x_pinion"], p["top_boss_y_pinion"]) for sx in (-1, 1)]
    bosses += [(sx * p["top_boss_x_outer"], p["top_boss_y_outer"]) for sx in (-1, 1)]
    for (x, y) in bosses:
        body = body.union(cq.Workplane().add(cyl_z(br, p["top_boss_z_base"], ztop, x, y)))

    # diff bearing seats: limited only by the outer lip, open toward the gear cavity
    xl = p["diff_lip_inner_x"]                 # inner face of the outer lip
    xs = xl - p["diff_seat_width"]             # inner end of the seat
    d_out = p["diff_bearing"][1]
    rs = (d_out + seat_add) / 2

    # gear cavity: diff case between the bearing seats, deepening for the ring gear on one side
    floor = box(-BIG, BIG, -BIG, BIG, p["floor_z"], BIG)
    cav = cyl_x(p["case_cavity_r"], -xs, xs, yd, zc)
    s = 1 if p["ring_gear_side"] > 0 else -1
    xa, xb = sorted((s * p["ring_recess_x_inner"], s * min(p["ring_recess_x_outer"], xs)))
    cav = cav.fuse(cyl_x(p["ring_recess_r"], xa, xb, yd, zc))
    cav = cav.intersect(floor)
    body = body.cut(cq.Workplane().add(cav))

    # through opening in the floor below the ring gear deepening (closed by the chassis plate)
    hl = p.get("ring_floor_opening_half_length", 0.0)
    if hl > 0:
        xa, xb = sorted((s * p["ring_recess_x_inner"], s * min(p["ring_recess_x_outer"], xs)))
        window = (cq.Workplane("XY").box(xb - xa, 2 * hl, p["floor_z"] + 4.0, centered=False)
                  .translate((xa, yd - hl, -1.0)).edges("|Z").fillet(p["ring_floor_opening_r"]))
        body = body.cut(window)

    for sx in (-1, 1):
        xa, xb = sorted((sx * (xs - 0.01), sx * xl))
        body = body.cut(cq.Workplane().add(cyl_x(rs, xa, xb, yd, zc)))
        xa, xb = sorted((sx * (xl - 0.01), sx * (w + 5)))
        body = body.cut(cq.Workplane().add(cyl_x(p["diff_lip_d"] / 2, xa, xb, yd, zc)))

    # pinion pocket up to the inner end of the pinion seat (no shoulder in front of the bearings).
    # The pocket ends exactly at the end of the wide block below it: a pocket that runs past
    # the block leaves a slit through the bottom.
    body = body.cut(cq.Workplane().add(cyl_y(p["pinion_pocket_r"], p["pinion_pocket_y_min"],
                                             yp_in, 0.0, zc)))
    # pinion bearing seats: inner bearing, rib, outer bearing
    rp = (p["pinion_bearing"][1] + seat_add) / 2
    bp = p["pinion_bearing"][2]
    yr0 = yp_in + bp                           # rib between the two bearings
    yr1 = yr0 + p["pinion_rib_t"]
    body = body.cut(cq.Workplane().add(cyl_y(rp, yp_in - 0.01, yr0, 0.0, zc)))
    body = body.cut(cq.Workplane().add(cyl_y(p["pinion_rib_d"] / 2, yr0 - 0.01, yr1 + 0.01, 0.0, zc)))
    body = body.cut(cq.Workplane().add(cyl_y(rp, yr1, yp_end + 5, 0.0, zc)))

    # M3 holes
    hx, hy = p["bottom_hole_dx"] / 2, p["bottom_hole_dy"] / 2
    r = (hole_d or p["bottom_hole_d"]) / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            body = body.cut(cq.Workplane().add(cyl_z(r, -1.0, p["bottom_hole_depth"], sx * hx, sy * hy)))
    r = (hole_d or p["top_hole_d"]) / 2
    for (x, y) in bosses:
        body = body.cut(cq.Workplane().add(cyl_z(r, ztop - p["top_hole_depth"], ztop + 1, x, y)))
    r = (hole_d or p["swaybar_hole_d"]) / 2
    for sx in (-1, 1):
        body = body.cut(cq.Workplane().add(cyl_z(r, zc - tt - 1, zc + 1, sx * tx, ty)))
    return body


def thin_gaps(solid, limit=0.25):
    """Thin slits and thin walls: pairs of faces without a common edge or vertex that are
    closer than limit (exact distance between the faces).

    Returns (kind, distance, point) per pair: kind "slit" (no material between the closest
    points, an unwanted opening or step) or "wall" (material between them, a thin wall).
    """
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    faces = solid.Faces()
    boxes = [f.BoundingBox() for f in faces]
    found = []
    for a in range(len(faces)):
        for b in range(a + 1, len(faces)):
            ba, bb = boxes[a], boxes[b]
            if (ba.xmin - bb.xmax > limit or bb.xmin - ba.xmax > limit or ba.ymin - bb.ymax > limit
                    or bb.ymin - ba.ymax > limit or ba.zmin - bb.zmax > limit or bb.zmin - ba.zmax > limit):
                continue
            ext = BRepExtrema_DistShapeShape(faces[a].wrapped, faces[b].wrapped)
            d = ext.Value()
            if not 1e-4 < d < limit:
                continue                     # touching faces (common edge or vertex) or far apart
            p1, p2 = ext.PointOnShape1(1), ext.PointOnShape2(1)
            mid = cq.Vector((p1.X() + p2.X()) / 2, (p1.Y() + p2.Y()) / 2, (p1.Z() + p2.Z()) / 2)
            kind = "wall" if solid.isInside(mid) else "slit"
            found.append((kind, round(d, 3), (round(mid.x, 2), round(mid.y, 2), round(mid.z, 2))))
    return found


def enclosure_lower(body, p):
    """Close the intended openings of the lower part with plugs and return the volumes of the
    enclosed voids. Intended openings: parting face, lip openings, pinion seat end, floor
    opening below the ring gear. The gear cavity is closed if it is one of the voids (the
    other voids are the screw holes, which the plug on the parting face closes)."""
    zc, yd, w = p["axis_z"], p["diff_axis_y"], p["body_half_width"]
    yp_end = p["pinion_seat_y_inner"] + p["pinion_seat_length"]
    plugs = [box(-w - 1, w + 1, p["body_y_outer_end"] - 8, yp_end + 2, zc, zc + 0.5),
             cyl_y(p["pinion_bearing"][1] / 2 + 0.2, yp_end - 0.5, yp_end + 1.0, 0.0, zc)]
    for sx in (-1, 1):
        xa, xb = sorted((sx * (p["diff_lip_inner_x"] + 0.5), sx * (w + 1)))
        plugs.append(cyl_x(p["diff_lip_d"] / 2 + 0.2, xa, xb, yd, zc))
    hl = p.get("ring_floor_opening_half_length", 0.0)
    if hl > 0:
        plugs.append(box(-w, w, yd - hl - 0.5, yd + hl + 0.5, -0.5, p["floor_z"] / 2))
    return enclosed_voids(body, plugs)


def enclosed_voids(body, plugs):
    """Volumes of the voids that are enclosed after the plugs are added (inner shells)."""
    solid = body.val() if hasattr(body, "val") else body
    for plug in plugs:
        solid = solid.fuse(plug)
    solid = solid.clean()
    shells = solid.Shells()
    outer = max(shells, key=lambda sh: sh.BoundingBox().DiagonalLength)
    return [round(abs(cq.Solid.makeSolid(sh).Volume()), 1) for sh in shells if not sh.isSame(outer)]


def main():
    parser = argparse.ArgumentParser(description="Generate the lower bulkhead of the T410R.")
    parser.add_argument("--params", default="cad/bulkhead/bulkhead_lower_parameters.json")
    parser.add_argument("--out", default="cad/bulkhead/bulkhead_lower_T410R",
                        help="output path without extension (STEP and STL)")
    parser.add_argument("--testprint", default="cad/bulkhead/testprint_bulkhead_lower.stl",
                        help="output path of the test print STL")
    args = parser.parse_args()

    p = load_params(args.params)
    solid = bulkhead_lower(p)
    cq.exporters.export(solid, args.out + ".step")
    cq.exporters.export(solid, args.out + ".stl", tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(bulkhead_lower(p, test_print=True), args.testprint,
                        tolerance=0.01, angularTolerance=0.1)

    solids = cq.importers.importStep(args.out + ".step").solids().vals()
    s = solids[0]
    bb = s.BoundingBox()
    vol = s.Volume()
    print(f"Wrote {args.out}.step, {args.out}.stl and {args.testprint}")
    print(f"  solids: {len(solids)}, valid: {s.isValid()}")
    print(f"  bounding box: x {bb.xmin:.2f} to {bb.xmax:.2f}, y {bb.ymin:.2f} to {bb.ymax:.2f}, "
          f"z {bb.zmin:.2f} to {bb.zmax:.2f}")
    print(f"  volume: {vol / 1000:.2f} cm3, mass 7075 (2.81 g/cm3): {vol / 1000 * 2.81:.1f} g, "
          f"PLA (1.24 g/cm3): {vol / 1000 * 1.24:.1f} g")
    cavity = [v for v in enclosure_lower(s, p) if v > 1000.0]
    print(f"  enclosure check (intended openings plugged): "
          + (f"gear cavity closed ({cavity[0] / 1000:.2f} cm3)" if cavity
             else "UNWANTED OPENING: the gear cavity is open to the outside"))
    gaps = thin_gaps(s)
    print(f"  check for thin slits and walls (faces closer than 0.25 mm): {len(gaps)} found")
    for g in gaps:
        print(f"    {g[0]}: {g[1]} mm at {g[2]}")


if __name__ == "__main__":
    main()
