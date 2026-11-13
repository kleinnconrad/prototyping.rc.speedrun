"""Generate the upper bulkhead (gear box upper half) of the Carten T410R, new design.

The upper part is a new design. Only its interfaces follow the stock part:
* parting face, diff and pinion bearing seats, gear cavities and the 4 screws to the
  lower part: taken from the parameter file of the lower bulkhead
* shock tower: contact face and 4 tapped holes M3 (screws M3x8 through the 3 mm tower)
* top brace: flat contact face at the height of the stock part with 2 tapped holes M3

Design: the footprint of the lower part, extruded to 4 flat levels along y: a flange for the
heads of the outer screws, a block over the diff and the ring gear, one shock tower wall
(instead of two ears) and a flat face for the top brace on the pinion side. The wall and the
gear block are narrowed to 2 x wall_half_width: side steps beside them give space for the rod
ends of the camber links behind the shock towers and for the camber link lobes of the towers.
All outer faces are flat. The edges get the same treatment as the lower part (radii and edge
chamfers), the root of the shock tower wall a radius (wall_root_r). The only other curved faces
are the bores and the cavities.

Coordinate system: as for the lower bulkhead (origin at the centre of the 4 bottom holes of
the lower part on its bottom face, x along the diff axis, +y toward the pinion, +z up).

Usage (from the root directory of the repository):
    python scripts/cad/generate_bulkhead_upper.py

The script writes the STEP and STL file of the upper part, an STL file for a test print
(bearing seats enlarged by print_seat_allowance, tapped holes with print_tap_d) and a STEP
file of the assembly of the lower and the upper part. It checks the assembly for
interference and compares the part with the model without radii, which has the verified
inside of the part.

Requires the package cadquery (pip install cadquery).
"""
import argparse
import json
import math

import cadquery as cq
from cadquery.occ_impl.exporters.assembly import exportAssembly

from generate_bulkhead_lower import (BIG, bearing_voids, box, bulkhead_lower, chamfer_outside_edges,
                                     concave_vertical_edges, cyl_x, cyl_y, cyl_z, edge_report, enclosed_voids,
                                     functional_check, load_params, round_inside_corners, round_outside_corners,
                                     thin_gaps, without_edge_treatment)


def screw_positions(lp):
    """Positions (x, y) of the 4 screws to the lower part: outer side, pinion side."""
    outer = [(sx * lp["top_boss_x_outer"], lp["top_boss_y_outer"]) for sx in (-1, 1)]
    pinion = [(sx * lp["top_boss_x_pinion"], lp["top_boss_y_pinion"]) for sx in (-1, 1)]
    return outer, pinion


def head_heights(lp, up):
    """z of the screw head seats (outer side, pinion side) for the chosen thread engagement."""
    zb = lp["axis_z"] + lp["top_boss_protrusion"]          # top of the bosses of the lower part
    return (zb + up["screw_len_outer"] - up["thread_engagement"],
            zb + up["screw_len_pinion"] - up["thread_engagement"])


def outer_body_upper(lp, up):
    """Outer shape of the upper part (cadquery Workplane): footprint with the 4 levels and the
    block over the outer pinion bearing, before the inside corners are rounded and the
    functional voids are cut. lp: lower part parameters, up: upper part."""
    zc = lp["axis_z"]
    yd = lp["diff_axis_y"]
    w = lp["body_half_width"]

    def h(v):
        return zc + v

    def add(body, solid):
        return body.union(cq.Workplane().add(solid))

    def cut(body, solid):
        return body.cut(cq.Workplane().add(solid))

    z_out, _ = head_heights(lp, up)

    # footprint of the lower part, extruded to the top of the shock tower wall
    y0, y1 = up["outer_end_y"], lp["body_y_pinion_end"]
    ztop = h(up["wall_top_h"])
    body = (cq.Workplane("XY").workplane(offset=zc).center(0, (y0 + y1) / 2)
            .rect(2 * w, y1 - y0).extrude(ztop - zc).edges("|Z").fillet(up["corner_r"]))

    # 4 flat levels along y: flange, gear block, shock tower wall, gear block, top brace face
    fy, wt = up["tower_face_y"], up["wall_t"]
    yg0 = yd - lp["ring_recess_r"] - up["cover_wall"]      # front face of the gear block
    yg1 = up["deck_end_y"] - 0.5                            # back face of the gear block
    zg = h(up["gear_block_h"])
    body = cut(body, box(-BIG, BIG, -BIG, yg0, z_out, BIG))           # flange (outer screw heads)
    body = cut(body, box(-BIG, BIG, yg0, fy, zg, BIG))                # gear block in front of the wall
    body = cut(body, box(-BIG, BIG, fy + wt, yg1, zg, BIG))           # gear block behind the wall
    body = cut(body, box(-BIG, BIG, yg1, BIG, h(up["deck_h"]), BIG))  # top brace face

    # side steps beside the narrowed wall and gear block: space for the rod ends of the camber links
    # behind the shock towers and for the camber link lobes of the towers
    xw = up.get("wall_half_width", w)
    if xw < w:
        for sx in (-1, 1):
            xa, xb = sorted((sx * xw, sx * BIG))
            body = cut(body, box(xa, xb, -BIG, up["side_step_end_y"], h(up["side_step_h"]), BIG))

    # block over the outer pinion bearing beyond the end of the footprint
    yp_end = lp["pinion_seat_y_inner"] + lp["pinion_seat_length"]
    e = up["pinion_end_r"]
    body = add(body, box(-e, e, y1 - 1.0, yp_end, zc, zc + e))

    # keep only the material above the parting face
    return cut(body, box(-BIG, BIG, -BIG, BIG, -BIG, zc))


def keepouts_upper(lp, up):
    """Keep-out zones (spaces of other parts): top brace above its contact face, shock tower in
    front of the contact face of the wall, and beside the narrowed wall the camber link lobes of
    the towers and the rod ends of the camber links (above the side steps, 0.2 mm from their faces)."""
    zc, fy = lp["axis_z"], up["tower_face_y"]
    zones = [box(-BIG, BIG, up["deck_end_y"] - 0.5, BIG, zc + up["deck_h"], BIG),
             box(-BIG, BIG, fy - up["tower_plate_t"] - 1.0, fy, zc + up["tower_keepout_h"], BIG)]
    xw = up.get("wall_half_width", lp["body_half_width"])
    if xw < lp["body_half_width"]:
        y_end = up["side_step_end_y"] - lp.get("inside_corner_r", 0.0) - 0.2
        for sx in (-1, 1):
            xa, xb = sorted((sx * (xw + 0.2), sx * BIG))
            zones.append(box(xa, xb, fy - up["tower_plate_t"] - 1.0, y_end, zc + up["side_step_h"] + 0.2, BIG))
    return zones


def voids_upper(lp, up, test_print=False, keepouts=True):
    """Functional voids of the upper part: keep-out zones of the top brace and the shock tower
    (keepouts=True), gear cavity, bearing seats (as the lower part), recesses for the bosses of the
    lower part, screw holes, counterbores, tapped holes (the inside of the part)."""
    zc = lp["axis_z"]
    yd = lp["diff_axis_y"]
    seat_add = lp["print_seat_allowance"] if test_print else 0.0
    tap_d = up["print_tap_d"] if test_print else None

    def h(v):
        return zc + v

    outer, pinion = screw_positions(lp)
    _, z_pin = head_heights(lp, up)
    fy, wt = up["tower_face_y"], up["wall_t"]

    voids = keepouts_upper(lp, up) if keepouts else []

    xs = lp["diff_lip_inner_x"] - lp["diff_seat_width"]
    s = 1 if lp["ring_gear_side"] > 0 else -1
    # gear cavity: diff case between the bearing seats, ring gear on one side (as the lower part)
    cav = cyl_x(lp["case_cavity_r"], -xs, xs, yd, zc)
    xa, xb = sorted((s * lp["ring_recess_x_inner"], s * min(up["ring_dome_x_outer"], xs)))
    voids.append(cav.fuse(cyl_x(lp["ring_recess_r"], xa, xb, yd, zc)))

    # diff bearing seats limited by the outer lips, pinion pocket, two pinion bearing seats with
    # the rib between them (the only axial stop): as the lower part
    voids += bearing_voids(lp, seat_add)

    # recesses for the bosses of the lower part, clearance holes for the 4 screws,
    # counterbores for the heads of the pinion side screws
    rr = (lp["top_boss_d"] + up["boss_recess_clearance"]) / 2
    zr = zc + lp["top_boss_protrusion"] + up["boss_recess_extra_depth"]
    for (x, y) in outer + pinion:
        voids.append(cyl_z(rr, zc - 1, zr, x, y))
        voids.append(cyl_z(up["screw_hole_d"] / 2, zc - 1, zc + 60, x, y))
    for (x, y) in pinion:
        voids.append(cyl_z(up["counterbore_d"] / 2, z_pin, zc + 60, x, y))

    # tapped holes: top brace (vertical), shock tower (through the wall along y)
    r = (tap_d or up["deck_hole_d"]) / 2
    zd = h(up["deck_h"])
    for sx in (-1, 1):
        voids.append(cyl_z(r, zd - up["deck_hole_depth"], zd + 1, sx * up["deck_screw_x"],
                           up["deck_screw_y"]))
    r = (tap_d or up["tower_hole_d"]) / 2
    for sx in (-1, 1):
        for hz in (up["tower_hole_h_lower"], up["tower_hole_h_upper"]):
            voids.append(cyl_y(r, fy - 1, fy + wt, sx * up["tower_hole_x"], h(hz)))
    return voids


def root_fillet_solid(y_face, sign, z_floor, w, rr, rc):
    """Radius rr at the root of a wall face y = y_face on a floor at the height z_floor. The wall
    lies on the side +sign of the face, the radius on the side -sign, over the width |x| <= w.
    The vertical corners of the wall have the radius rc: the root radius runs around them (profile
    revolved about the corner axis) and is trimmed at the side faces |x| = w."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
    from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt
    xs = w - rc

    def profile(x0):
        def pt(d, h):
            return cq.Vector(x0, y_face - sign * d, z_floor + h)
        c = rr - rr / math.sqrt(2)
        edges = [cq.Edge.makeLine(pt(0, 0), pt(rr, 0)),
                 cq.Edge.makeThreePointArc(pt(rr, 0), pt(c, c), pt(0, rr)),
                 cq.Edge.makeLine(pt(0, rr), pt(0, 0))]
        return cq.Face.makeFromWires(cq.Wire.assembleEdges(edges))

    sol = cq.Solid.extrudeLinear(profile(-xs).outerWire(), [], cq.Vector(2 * xs, 0, 0))
    for sx in (-1, 1):
        axis = gp_Ax1(gp_Pnt(sx * xs, y_face + sign * rc, z_floor), gp_Dir(0, 0, 1))
        for a in (math.pi / 2, -math.pi / 2):
            rev = cq.Solid(BRepPrimAPI_MakeRevol(profile(sx * xs).wrapped, axis, a).Shape())
            if sx * (rev.Center().x - sx * xs) > 0:     # the revolution that runs around the corner
                sol = sol.fuse(rev)
                break
    return sol.intersect(box(-w, w, -BIG, BIG, z_floor - 1, z_floor + rr + 1)).clean()


_OUTER_SHAPES = {}


def outer_shape_upper(lp, up):
    """Outer shape of the upper part with the edge treatment: radii of the vertical outside edges,
    root radius of the shock tower wall on both sides, radii in the vertical inside corners,
    chamfers of the other hard outside edges. The underside (parting face) is not changed.
    Returns (Workplane, chamfered edges, shortened edges, skipped edges), cached per parameter set."""
    key = json.dumps([lp, up], sort_keys=True)
    if key not in _OUTER_SHAPES:
        zc = lp["axis_z"]

        def joint(f):
            return f.BoundingBox().zmax <= zc + 1e-6     # parting face

        body = round_outside_corners(outer_body_upper(lp, up), lp.get("outside_corner_r", 0.0), joint)
        rr = up.get("wall_root_r", 0.0)
        if rr > 0:
            fy, wt, zg = up["tower_face_y"], up["wall_t"], zc + up["gear_block_h"]
            s = body.val()
            for y_face, sign in ((fy, 1), (fy + wt, -1)):
                s = s.fuse(root_fillet_solid(y_face, sign, zg, up.get("wall_half_width", lp["body_half_width"]),
                                             rr, lp.get("outside_corner_r", 0.0))).clean()
            body = cq.Workplane().add(s)
        body = round_inside_corners(body, lp.get("inside_corner_r", 0.0), zc)
        _OUTER_SHAPES[key] = chamfer_outside_edges(body, lp.get("edge_chamfer", 0.0), joint)
    return _OUTER_SHAPES[key]


def bulkhead_upper(lp, up, test_print=False):
    """Build the upper part (cadquery Workplane): outer shape with the edge treatment, then the
    functional voids and keep-out zones. The voids are cut last, so the radii and chamfers cannot
    change the inside of the part. lp: lower part parameters, up: upper part."""
    body = outer_shape_upper(lp, up)[0]
    for v in voids_upper(lp, up, test_print):
        body = body.cut(cq.Workplane().add(v))
    return body


def enclosure_upper(body, lp):
    """Close the intended openings of the upper part (parting face, lip openings, pinion seat
    end) with plugs and return the volumes of the enclosed voids (see enclosure_lower)."""
    zc, yd, w = lp["axis_z"], lp["diff_axis_y"], lp["body_half_width"]
    yp_end = lp["pinion_seat_y_inner"] + lp["pinion_seat_length"]
    plugs = [box(-w - 1, w + 1, -40, yp_end + 2, zc - 0.5, zc),
             cyl_y(lp["pinion_bearing"][1] / 2 + 0.2, yp_end - 0.5, yp_end + 1.0, 0.0, zc)]
    for sx in (-1, 1):
        xa, xb = sorted((sx * (lp["diff_lip_inner_x"] + 0.5), sx * (w + 1)))
        plugs.append(cyl_x(lp["diff_lip_d"] / 2 + 0.2, xa, xb, yd, zc))
    return enclosed_voids(body, plugs)


def main():
    parser = argparse.ArgumentParser(description="Generate the upper bulkhead of the T410R (new design).")
    parser.add_argument("--lower-params", default="cad/bulkhead/bulkhead_lower_parameters.json")
    parser.add_argument("--params", default="cad/bulkhead/bulkhead_upper_parameters.json")
    parser.add_argument("--out", default="cad/bulkhead/bulkhead_upper_T410R",
                        help="output path without extension (STEP and STL)")
    parser.add_argument("--testprint", default="cad/bulkhead/testprint_bulkhead_upper.stl")
    parser.add_argument("--assembly", default="cad/bulkhead/bulkhead_assembly_T410R.step")
    args = parser.parse_args()

    lp = load_params(args.lower_params)
    up = load_params(args.params)
    upper = bulkhead_upper(lp, up)
    cq.exporters.export(upper, args.out + ".step")
    cq.exporters.export(upper, args.out + ".stl", tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(bulkhead_upper(lp, up, test_print=True), args.testprint,
                        tolerance=0.01, angularTolerance=0.1)

    lower = bulkhead_lower(lp)
    assy = (cq.Assembly(name="bulkhead_T410R")
            .add(lower, name="lower", color=cq.Color(0.45, 0.5, 0.56))
            .add(upper, name="upper", color=cq.Color(0.75, 0.55, 0.3)))
    exportAssembly(assy, args.assembly)

    s = cq.importers.importStep(args.out + ".step").solids().vals()
    bb = s[0].BoundingBox()
    vol = sum(v.Volume() for v in s)
    zc = lp["axis_z"]
    print(f"Wrote {args.out}.step, {args.out}.stl, {args.testprint} and {args.assembly}")
    print(f"  solids: {len(s)}, valid: {all(v.isValid() for v in s)}")
    print(f"  bounding box: x {bb.xmin:.2f} to {bb.xmax:.2f}, y {bb.ymin:.2f} to {bb.ymax:.2f}, "
          f"z {bb.zmin:.2f} to {bb.zmax:.2f} (height above the parting face {bb.zmax - zc:.2f})")
    print(f"  volume: {vol / 1000:.2f} cm3, mass 7075 (2.81 g/cm3): {vol / 1000 * 2.81:.1f} g, "
          f"PLA (1.24 g/cm3): {vol / 1000 * 1.24:.1f} g")

    cavity = [v for v in enclosure_upper(s[0], lp) if v > 1000.0]
    print(f"  enclosure check (intended openings plugged): "
          + (f"gear cavity closed ({cavity[0] / 1000:.2f} cm3)" if cavity
             else "UNWANTED OPENING: the gear cavity is open to the outside"))
    gaps = thin_gaps(s[0])
    print(f"  check for thin slits and walls (faces closer than 0.25 mm): {len(gaps)} found")
    for g in gaps:
        print(f"    {g[0]}: {g[1]} mm at {g[2]}")
    long_corners = [e for e in concave_vertical_edges(s[0]) if e.Length() > 1.0]
    print(f"  vertical inside corners without radius (longer than 1 mm): {len(long_corners)}")
    print("\n".join(edge_report(*outer_shape_upper(lp, up)[1:])))
    ref = bulkhead_upper(without_edge_treatment(lp), dict(up, wall_root_r=0.0)).val()
    ok, lines = functional_check(s[0], ref, voids_upper(lp, up, keepouts=False), lp["inside_corner_r"],
                                 keepouts_upper(lp, up))
    print("\n".join(lines))
    print(f"  functional check: {'passed' if ok else 'FAILED'}")
    if up.get("wall_half_width", lp["body_half_width"]) < lp["body_half_width"]:
        full = outer_body_upper(lp, dict(up, wall_half_width=lp["body_half_width"])).val()
        removed = full.cut(outer_body_upper(lp, up).val())
        inside = cq.Compound.makeCompound([f for v in voids_upper(lp, up, keepouts=False) for f in v.Faces()])
        print(f"  side steps beside the wall: removed {removed.Volume() / 1000:.2f} cm3, "
              f"distance to the inside of the part (cavities, seats, holes) "
              f"{cq.Compound.makeCompound(removed.Faces()).distance(inside):.2f} mm")
    inter = lower.val().intersect(upper.val())
    print(f"  interference with the lower part: {inter.Volume():.4f} mm3")
    z_out, z_pin = head_heights(lp, up)
    print(f"  screw head seats above the parting face: outer {z_out - zc:.2f}, pinion {z_pin - zc:.2f} "
          f"(thread engagement {up['thread_engagement']:.1f}, lower hole depth {lp['top_hole_depth']:.1f})")


if __name__ == "__main__":
    main()
