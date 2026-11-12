"""Generate the upper bulkhead (gear box upper half) of the Carten T410R, new design.

The upper part is a new design. Only its interfaces follow the stock part:
* parting face, diff and pinion bearing seats, gear cavities and the 4 screws to the
  lower part: taken from the parameter file of the lower bulkhead
* shock tower: contact face and 4 tapped holes M3 (screws M3x8 through the 3 mm tower)
* top brace: flat contact face at the height of the stock part with 2 tapped holes M3

Design: the footprint of the lower part, extruded to 4 flat levels along y: a flange for the
heads of the outer screws, a block over the diff and the ring gear, one shock tower wall over
the full width (instead of two ears) and a flat face for the top brace on the pinion side.
All outer faces are flat. The only curved faces are the bores and the cavities.

Coordinate system: as for the lower bulkhead (origin at the centre of the 4 bottom holes of
the lower part on its bottom face, x along the diff axis, +y toward the pinion, +z up).

Usage (from the root directory of the repository):
    python scripts/cad/generate_bulkhead_upper.py

The script writes the STEP and STL file of the upper part, an STL file for a test print
(bearing seats enlarged by print_seat_allowance, tapped holes with print_tap_d) and a STEP
file of the assembly of the lower and the upper part. It checks the assembly for
interference.

Requires the package cadquery (pip install cadquery).
"""
import argparse

import cadquery as cq
from cadquery.occ_impl.exporters.assembly import exportAssembly

from generate_bulkhead_lower import BIG, box, bulkhead_lower, cyl_x, cyl_y, cyl_z, load_params


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


def bulkhead_upper(lp, up, test_print=False):
    """Build the upper part (cadquery Workplane). lp: lower part parameters, up: upper part."""
    zc = lp["axis_z"]
    yd = lp["diff_axis_y"]
    w = lp["body_half_width"]
    seat_add = lp["print_seat_allowance"] if test_print else 0.0
    tap_d = up["print_tap_d"] if test_print else None

    def h(v):
        return zc + v

    def add(body, solid):
        return body.union(cq.Workplane().add(solid))

    def cut(body, solid):
        return body.cut(cq.Workplane().add(solid))

    outer, pinion = screw_positions(lp)
    z_out, z_pin = head_heights(lp, up)

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

    # half cylinder over the outer pinion bearing beyond the end of the footprint
    yp_in = lp["pinion_seat_y_inner"]
    yp_end = yp_in + lp["pinion_seat_length"]
    body = add(body, cyl_y(up["pinion_end_r"], y1 - 1.0, yp_end, 0.0, zc))

    # keep only the material above the parting face
    body = cut(body, box(-BIG, BIG, -BIG, BIG, -BIG, zc))
    # keep-out zones: top brace (above its contact face) and shock tower plate (in front of the face)
    body = cut(body, box(-BIG, BIG, up["deck_end_y"] - 0.5, BIG, h(up["deck_h"]), BIG))
    body = cut(body, box(-BIG, BIG, fy - up["tower_plate_t"] - 1.0, fy, h(up["tower_keepout_h"]), BIG))

    xl = lp["diff_lip_inner_x"]
    xs = xl - lp["diff_seat_width"]
    s = 1 if lp["ring_gear_side"] > 0 else -1
    # gear cavity: diff case between the bearing seats, ring gear on one side (as the lower part)
    cav = cyl_x(lp["case_cavity_r"], -xs - 0.01, xs + 0.01, yd, zc)
    xa, xb = sorted((s * lp["ring_recess_x_inner"], s * xs))
    cav = cav.fuse(cyl_x(lp["ring_recess_r"], xa, xb, yd, zc))
    body = cut(body, cav)

    # diff bearing seats, limited by the outer lips
    rs = (lp["diff_bearing"][1] + seat_add) / 2
    for sx in (-1, 1):
        xa, xb = sorted((sx * (xs - 0.01), sx * xl))
        body = cut(body, cyl_x(rs, xa, xb, yd, zc))
        xa, xb = sorted((sx * (xl - 0.01), sx * (w + 5)))
        body = cut(body, cyl_x(lp["diff_lip_d"] / 2, xa, xb, yd, zc))

    # pinion pocket up to the bearing seats, two bearing seats with the rib between them
    # (the rib is the only axial stop, as on the lower part)
    body = cut(body, cyl_y(lp["pinion_pocket_r"], lp["pinion_pocket_y_min"], yp_in + 0.01, 0.0, zc))
    rp = (lp["pinion_bearing"][1] + seat_add) / 2
    yr0 = yp_in + lp["pinion_bearing"][2]
    yr1 = yr0 + lp["pinion_rib_t"]
    body = cut(body, cyl_y(rp, yp_in, yr0, 0.0, zc))
    body = cut(body, cyl_y(lp["pinion_rib_d"] / 2, yr0 - 0.01, yr1 + 0.01, 0.0, zc))
    body = cut(body, cyl_y(rp, yr1, yp_end + 5, 0.0, zc))

    # recesses for the bosses of the lower part, clearance holes for the 4 screws,
    # counterbores for the heads of the pinion side screws
    rr = (lp["top_boss_d"] + up["boss_recess_clearance"]) / 2
    zr = zc + lp["top_boss_protrusion"] + up["boss_recess_extra_depth"]
    for (x, y) in outer + pinion:
        body = cut(body, cyl_z(rr, zc - 1, zr, x, y))
        body = cut(body, cyl_z(up["screw_hole_d"] / 2, zc - 1, zc + 60, x, y))
    for (x, y) in pinion:
        body = cut(body, cyl_z(up["counterbore_d"] / 2, z_pin, zc + 60, x, y))

    # tapped holes: top brace (vertical), shock tower (through the wall along y)
    r = (tap_d or up["deck_hole_d"]) / 2
    zd = h(up["deck_h"])
    for sx in (-1, 1):
        body = cut(body, cyl_z(r, zd - up["deck_hole_depth"], zd + 1, sx * up["deck_screw_x"],
                               up["deck_screw_y"]))
    r = (tap_d or up["tower_hole_d"]) / 2
    for sx in (-1, 1):
        for hz in (up["tower_hole_h_lower"], up["tower_hole_h_upper"]):
            body = cut(body, cyl_y(r, fy - 1, fy + wt, sx * up["tower_hole_x"], h(hz)))
    return body


def main():
    parser = argparse.ArgumentParser(description="Generate the upper bulkhead of the T410R (new design).")
    parser.add_argument("--lower-params", default="cad/bulkhead/bulkhead_lower_v2_parameters.json")
    parser.add_argument("--params", default="cad/bulkhead/bulkhead_upper_v1_parameters.json")
    parser.add_argument("--out", default="cad/bulkhead/bulkhead_upper_T410R_v1",
                        help="output path without extension (STEP and STL)")
    parser.add_argument("--testprint", default="cad/bulkhead/testprint_bulkhead_upper_v1.stl")
    parser.add_argument("--assembly", default="cad/bulkhead/bulkhead_assembly_T410R_v1.step")
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

    inter = lower.val().intersect(upper.val())
    print(f"  interference with the lower part: {inter.Volume():.4f} mm3")
    z_out, z_pin = head_heights(lp, up)
    print(f"  screw head seats above the parting face: outer {z_out - zc:.2f}, pinion {z_pin - zc:.2f} "
          f"(thread engagement {up['thread_engagement']:.1f}, lower hole depth {lp['top_hole_depth']:.1f})")


if __name__ == "__main__":
    main()
