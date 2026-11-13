"""Generate the lower bulkhead (gear box lower half) of the Carten T410R.

The solid is built from the parameter file of the part. The body is the
intersection of the footprint of the upper part (extruded in z) and the side
profile (extruded in x): a flat contact face on the chassis plate and one
straight chamfer per side, below which the pivot blocks of the wishbones are
mounted. A rectangular block under the pinion, the bosses for the upper
bulkhead and the tabs for the sway bar mounts are added. The vertical inside
corners are rounded with inside_corner_r (end mill radius). Then the gear cavity,
the bearing seats and the M3 holes are cut, so the radii cannot change the inside
of the part.

Coordinate system: origin at the centre of the 4 bottom holes on the bottom face,
x along the diff axis, +y toward the pinion, z = 0 bottom face.

Usage (from the root directory of the repository):
    python scripts/cad/generate_bulkhead_lower.py

The script writes the STEP and STL file of the part (nominal dimensions, for CNC
manufacturing) and an STL file for a test print (bearing seats enlarged by
print_seat_allowance, M3 holes with print_hole_d for self-tapping screws). It
checks the solid and compares it with the model without radii, which has the
verified inside of the part (functional check).

Requires the package cadquery (pip install cadquery).
"""
import argparse
import json
import math

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


def boss_positions(p):
    """Positions (x, y) of the 4 bosses for the screws of the upper bulkhead: pinion side,
    outer side (the two pairs have different spacings)."""
    bosses = [(sx * p["top_boss_x_pinion"], p["top_boss_y_pinion"]) for sx in (-1, 1)]
    bosses += [(sx * p["top_boss_x_outer"], p["top_boss_y_outer"]) for sx in (-1, 1)]
    return bosses


def side_profile_lower(p):
    """Side profile of the body (y, z), extruded in x over the full width: flat contact face on
    the chassis plate and one straight chamfer per side up to a short end face below the parting
    face (space for the pivot blocks below the chamfers)."""
    zc, w = p["axis_z"], p["body_half_width"]
    y0, y1 = p["body_y_outer_end"], p["body_y_pinion_end"]
    a, hb, he = p["base_half_length"], p["base_height"], p["end_face_h"]
    pts = [(y0, zc), (y0, zc - he), (-a, hb), (-a, 0.0), (a, 0.0), (a, hb), (y1, zc - he), (y1, zc)]
    return cq.Workplane("YZ").polyline(pts).close().extrude(w + 5, both=True)


def outer_body_lower(p):
    """Outer shape of the lower part (cadquery Workplane): body, blocks, tabs and bosses,
    before the inside corners are rounded and the functional voids are cut."""
    zc = p["axis_z"]
    w = p["body_half_width"]

    # body: footprint of the upper part, extruded to the parting face
    y0, y1 = p["body_y_outer_end"], p["body_y_pinion_end"]
    plan = (cq.Workplane("XY").center(0, (y0 + y1) / 2)
            .rect(2 * w, y1 - y0).extrude(zc + 5).edges("|Z").fillet(p["body_corner_r"]))

    body = plan.intersect(side_profile_lower(p))

    # stepped block under the pinion: wide and deep under the pinion pocket, narrow under the
    # pinion seats and beyond the end of the footprint (outer pinion bearing)
    a = p["base_half_length"]
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

    # bosses for the screws of the upper bulkhead
    br = p["top_boss_d"] / 2
    ztop = zc + p["top_boss_protrusion"]
    for (x, y) in boss_positions(p):
        body = body.union(cq.Workplane().add(cyl_z(br, p["top_boss_z_base"], ztop, x, y)))
    return body


def concave_vertical_edges(solid, eps=0.01, n=72, limit=0.55):
    """Straight edges parallel to z with an inside (concave) angle between their two faces.

    A small circle around the middle of the edge (in the xy plane) is tested: at an inside
    corner, more than half of the circle lies in the material (3/4 at a 90 degree corner, 1/2
    at a tangent transition, 1/4 at an outside corner)."""
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_IN
    from OCP.gp import gp_Pnt
    clf = BRepClass3d_SolidClassifier(solid.wrapped)
    found = []
    for e in solid.Edges():
        if e.geomType() != "LINE" or abs(e.tangentAt(0.5).z) < 0.999:
            continue
        m = e.positionAt(0.5)
        k = 0
        for i in range(n):
            ang = 2 * math.pi * i / n
            clf.Perform(gp_Pnt(m.x + eps * math.cos(ang), m.y + eps * math.sin(ang), m.z), 1e-7)
            k += clf.State() == TopAbs_IN
        if k / n > limit:
            found.append(e)
    return found


def plane_section(solid, z):
    """Faces of the section of the solid with the horizontal plane at the height z."""
    plane = cq.Face.makePlane(2 * BIG, 2 * BIG, basePnt=cq.Vector(0, 0, z), dir=cq.Vector(0, 0, 1))
    return solid.intersect(plane).Faces()


def closing_2d(faces, r):
    """Closing of horizontal faces with the radius r: offset by +r, union, offset by -r.

    The result is the shape that an end mill with the radius r leaves: inside corners are
    rounded with r, gaps narrower than 2 r are filled, outside corners are not changed."""
    def offset(fs, d):
        out = None
        for f in fs:
            if f.innerWires():
                raise ValueError("closing_2d: faces with holes are not supported")
            for wire in f.outerWire().offset2D(d, "arc"):
                g = cq.Face.makeFromWires(wire)
                out = g if out is None else out.fuse(g)
        return out.clean().Faces()
    return offset(offset(faces, r), -r)


def round_inside_corners(body, r, zc, envelope=None):
    """Round the vertical inside corners of the outer shape with the radius r.

    An end mill cannot cut a sharp inside corner parallel to its axis: it leaves its own
    radius, and it cannot enter a gap narrower than its diameter. For each vertical inside
    edge, the section at the end of the edge away from the parting face (zc) is closed with
    the radius r (see closing_2d). The added faces next to the edge are extruded from there
    to the parting face. Above the chamfers, they lie inside the body. The fillets add material
    only in the inside corners and not beyond the end of the edge, with one exception: where a
    fillet runs onto a wall that reaches further (the footprint corner above a chamfer), its end
    follows the envelope (side profile of the body), at most r beyond the end of the edge."""
    if r <= 0:
        return body
    s = body.val()
    levels = {}
    for e in concave_vertical_edges(s):
        z0, z1 = sorted((e.startPoint().z, e.endPoint().z))
        zf = z0 if abs(z0 - zc) > abs(z1 - zc) else z1      # end away from the parting face
        levels.setdefault(round(zf, 6), []).append(e.positionAt(0.5))
    fills = []
    for zf, mids in levels.items():
        zs = zf + 0.01 if zf < zc else zf - 0.01            # section just inside the edge
        sec = plane_section(s, zs)
        sec_shape = sec[0]
        for f in sec[1:]:
            sec_shape = sec_shape.fuse(f)
        for f in closing_2d(sec, r):
            for piece in f.cut(sec_shape).Faces():
                if piece.Area() < 1e-4:
                    continue                                # numerical slivers along unchanged edges
                if min(piece.distance(cq.Vertex.makeVertex(m.x, m.y, zs)) for m in mids) > 1e-3:
                    continue                                # not at an inside edge of this level
                fills.append(prism_z(piece, zf, zc))
                if envelope is not None:
                    ext = prism_z(piece, zf - r if zf < zc else zf + r, zf).intersect(envelope)
                    if ext.Volume() > 1e-9:
                        fills.append(ext)
    for fill in fills:
        s = s.fuse(fill)
    return cq.Workplane().add(s.clean())


def prism_z(face, za, zb):
    """Prism of a horizontal face between the heights za and zb."""
    face = face.translate(cq.Vector(0, 0, za - face.Center().z))
    return cq.Solid.extrudeLinear(face.outerWire(), face.innerWires(), cq.Vector(0, 0, zb - za))


def bearing_voids(p, seat_add=0.0):
    """Bearing seats and openings of the lower and the upper part: diff bearing seats (limited
    only by the outer lips, open toward the gear cavity), lip openings, pinion pocket, pinion
    bearing seats with the rib between them."""
    zc, yd, w = p["axis_z"], p["diff_axis_y"], p["body_half_width"]
    xl = p["diff_lip_inner_x"]                 # inner face of the outer lip
    xs = xl - p["diff_seat_width"]             # inner end of the seat
    rs = (p["diff_bearing"][1] + seat_add) / 2
    voids = []
    for sx in (-1, 1):
        xa, xb = sorted((sx * (xs - 0.01), sx * xl))
        voids.append(cyl_x(rs, xa, xb, yd, zc))
        xa, xb = sorted((sx * (xl - 0.01), sx * (w + 5)))
        voids.append(cyl_x(p["diff_lip_d"] / 2, xa, xb, yd, zc))

    # pinion pocket up to the inner end of the pinion seat (no shoulder in front of the bearings).
    # In the lower part, the pocket ends exactly at the end of the wide block below it: a pocket
    # that runs past the block leaves a slit through the bottom.
    yp_in = p["pinion_seat_y_inner"]
    yp_end = yp_in + p["pinion_seat_length"]
    voids.append(cyl_y(p["pinion_pocket_r"], p["pinion_pocket_y_min"], yp_in, 0.0, zc))
    # pinion bearing seats: inner bearing, rib, outer bearing
    rp = (p["pinion_bearing"][1] + seat_add) / 2
    yr0 = yp_in + p["pinion_bearing"][2]       # rib between the two bearings
    yr1 = yr0 + p["pinion_rib_t"]
    voids.append(cyl_y(rp, yp_in - 0.01, yr0, 0.0, zc))
    voids.append(cyl_y(p["pinion_rib_d"] / 2, yr0 - 0.01, yr1 + 0.01, 0.0, zc))
    voids.append(cyl_y(rp, yr1, yp_end + 5, 0.0, zc))
    return voids


def voids_lower(p, test_print=False):
    """Functional voids of the lower part (the inside of the part): gear cavity, floor opening,
    bearing seats, lip openings, pinion pocket, rib, M3 holes."""
    zc, yd = p["axis_z"], p["diff_axis_y"]
    seat_add = p["print_seat_allowance"] if test_print else 0.0
    hole_d = p["print_hole_d"] if test_print else None
    xs = p["diff_lip_inner_x"] - p["diff_seat_width"]
    voids = []

    # gear cavity: diff case between the bearing seats, deepening for the ring gear on one side
    floor = box(-BIG, BIG, -BIG, BIG, p["floor_z"], BIG)
    cav = cyl_x(p["case_cavity_r"], -xs, xs, yd, zc)
    s = 1 if p["ring_gear_side"] > 0 else -1
    xa, xb = sorted((s * p["ring_recess_x_inner"], s * min(p["ring_recess_x_outer"], xs)))
    cav = cav.fuse(cyl_x(p["ring_recess_r"], xa, xb, yd, zc))
    voids.append(cav.intersect(floor))

    # through opening in the floor below the ring gear deepening (closed by the chassis plate)
    hl = p.get("ring_floor_opening_half_length", 0.0)
    if hl > 0:
        window = (cq.Workplane("XY").box(xb - xa, 2 * hl, p["floor_z"] + 4.0, centered=False)
                  .translate((xa, yd - hl, -1.0)).edges("|Z").fillet(p["ring_floor_opening_r"]))
        voids.append(window.val())

    voids += bearing_voids(p, seat_add)

    # M3 holes
    hx, hy = p["bottom_hole_dx"] / 2, p["bottom_hole_dy"] / 2
    r = (hole_d or p["bottom_hole_d"]) / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            voids.append(cyl_z(r, -1.0, p["bottom_hole_depth"], sx * hx, sy * hy))
    ztop = zc + p["top_boss_protrusion"]
    r = (hole_d or p["top_hole_d"]) / 2
    for (x, y) in boss_positions(p):
        voids.append(cyl_z(r, ztop - p["top_hole_depth"], ztop + 1, x, y))
    r = (hole_d or p["swaybar_hole_d"]) / 2
    for sx in (-1, 1):
        voids.append(cyl_z(r, zc - p["swaybar_tab_t"] - 1, zc + 1, sx * p["swaybar_hole_x"],
                           p["swaybar_hole_y"]))
    return voids


def bulkhead_lower(p, test_print=False):
    """Build the solid (cadquery Workplane) from the parameters: outer shape, rounded inside
    corners, functional voids. The voids are cut last, so the radii cannot change them."""
    body = round_inside_corners(outer_body_lower(p), p.get("inside_corner_r", 0.0), p["axis_z"],
                                envelope=side_profile_lower(p).val())
    for v in voids_lower(p, test_print):
        body = body.cut(cq.Workplane().add(v))
    return body


def functional_check(solid, ref, voids, r):
    """Compare the solid with the reference solid without the radii of the outer shape
    (inside_corner_r = 0). The reference has the verified inside of the part. Returns (ok, lines).

    * The inside of the part must not change: no added or removed material may touch a
      functional void (cavities, bearing seats, lip openings, pinion pocket, rib, holes,
      counterbores, recesses, keep-out zones). The smallest distance must be larger than 0.
    * Each added piece must lie within the height range of the material beside it (within r): no
      radius reaches lower or higher than the existing faces next to it, for example into the
      space of the pivot blocks."""
    added, removed = solid.cut(ref), ref.cut(solid)
    changed = added.Solids() + removed.Solids()
    dist = min((c.distance(v) for c in changed for v in voids), default=float("inf"))
    pieces = added.Solids()
    ok = dist > 1e-3
    lines = ["  comparison with the verified inside of the part (model without radii of the outer shape):",
             f"    smallest distance of the changed material to the cavities, bearing seats, holes, recesses and "
             f"keep-out zones: {dist:.2f} mm (inside of the part {'unchanged' if ok else 'CHANGED'})",
             f"    removed material: {removed.Volume():.2f} mm3",
             f"    added material (radii of the outer shape): {added.Volume():.2f} mm3 in {len(pieces)} pieces"]
    for sol in sorted(pieces, key=lambda q: (q.BoundingBox().ymin, q.BoundingBox().xmin)):
        bb = sol.BoundingBox()
        near = ref.intersect(box(bb.xmin - r, bb.xmax + r, bb.ymin - r, bb.ymax + r, -BIG, BIG)).BoundingBox()
        inside = bb.zmin >= near.zmin - 1e-6 and bb.zmax <= near.zmax + 1e-6
        ok = ok and inside
        lines.append(f"      x {bb.xmin:6.2f} to {bb.xmax:6.2f}, y {bb.ymin:6.2f} to {bb.ymax:6.2f}, "
                     f"z {bb.zmin:5.2f} to {bb.zmax:5.2f}, {sol.Volume():5.2f} mm3 (material beside it: "
                     f"z {near.zmin:5.2f} to {near.zmax:5.2f}{'' if inside else ', OUTSIDE'})")
    return ok, lines


def thin_gaps(solid, limit=0.25):
    """Thin slits and thin walls: pairs of faces without a common edge or vertex that are
    closer than limit (exact distance between the faces).

    Returns (kind, distance, point) per pair: kind "slit" (no material between the closest
    points, an unwanted opening or step), "wall" (material between them, a thin wall) or
    "narrow face" (the point between the two faces lies on the surface or closer to it than a
    quarter of the distance: the faces are separated by other faces, not by a gap, for example
    the short flat between a radius and the end of a block). In a slit or a wall, the point
    between the two faces is about half the distance away from the surface.
    """
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.TopAbs import TopAbs_IN, TopAbs_OUT
    from OCP.gp import gp_Pnt
    clf = BRepClass3d_SolidClassifier(solid.wrapped)
    faces = solid.Faces()
    surface = cq.Compound.makeCompound(faces)
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
            clf.Perform(gp_Pnt(mid.x, mid.y, mid.z), 1e-6)
            state = clf.State()
            if cq.Vertex.makeVertex(mid.x, mid.y, mid.z).distance(surface) < 0.25 * d:
                kind = "narrow face"         # other faces lie between the two faces, close to the gap
            else:
                kind = "wall" if state == TopAbs_IN else ("slit" if state == TopAbs_OUT else "narrow face")
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
    print(f"  vertical inside corners without radius: {len(concave_vertical_edges(s))}")
    ref = bulkhead_lower(dict(p, inside_corner_r=0.0)).val()
    ok, lines = functional_check(s, ref, voids_lower(p), p["inside_corner_r"])
    print("\n".join(lines))
    print(f"  functional check: {'passed' if ok else 'FAILED'}")


if __name__ == "__main__":
    main()
