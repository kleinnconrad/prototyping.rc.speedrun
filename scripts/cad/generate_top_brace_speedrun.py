"""Generate the speedrun top brace: new design that matches the new bulkheads.

The holes are taken unchanged from the geometry data of the top brace
(cad/chassis/top_brace/top_brace_geometry.json), except the holes in the middle part that are
not screwed to the bulkheads (B05, B06): they are closed. The two slots in the middle part are
closed as well. The obround cutout at the end with B07 to B15 is kept unchanged.

Design (in the style of the bulkheads): straight lines and radii only.
* End sections as wide as the bulkheads (body_half_width of the lower bulkhead), flush with
  their sides, end corners with radius 4 mm. The flat ends replace the notches of the original
  top brace, which clear the raised rib on top of the stock upper bulkhead. The upper bulkhead
  of this project has a flat contact face there.
* Solid bar of the original width (15.09 mm) between the end sections.
* Transitions at 30 degrees to the y axis on both ends, fillets 3 mm.
* Rectangular window instead of the hexagon cutout (it contains the hexagon).

Outputs in cad/chassis/top_brace_speedrun: geometry data, STEP, STL, DXF, hole table, 1:1
templates (100 % and 97 %) and two test print halves with a dovetail. Image: drawing with the
outline of the original top brace. The assembly with the chassis plate and the bulkheads is
generated with generate_speedrun_assembly.py.

Checks: the new outline lies within the outline of the original top brace; position of the
holes relative to the bulkhead screws (top brace screws, access holes for the M3x10 screws);
the ends of the top brace on the contact faces of both upper bulkheads; no interference.

Usage (from the root directory of the repository, after the bulkhead scripts):
    python scripts/cad/generate_top_brace_speedrun.py

Requires the packages cadquery, ezdxf, matplotlib and reportlab.
"""
import csv
import json
import math
import os
import sys

import numpy as np
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_solid import plate_solid, wire_from_prims  # noqa: E402
from generate_dxf import build_dxf  # noqa: E402
from generate_drawing import contour_points  # noqa: E402
from generate_bulkhead_lower import load_params  # noqa: E402
from generate_bulkhead_upper import bulkhead_upper  # noqa: E402

CAD = "cad/chassis"
ORIG = f"{CAD}/top_brace/top_brace_geometry.json"
OUT = f"{CAD}/top_brace_speedrun"
STEM = f"{OUT}/top_brace_T410R_speedrun"
GEOM = f"{OUT}/top_brace_speedrun_geometry.json"
LOWER = "cad/bulkhead/bulkhead_lower_parameters.json"
UPPER = "cad/bulkhead/bulkhead_upper_parameters.json"
BULKHEAD_Y = {"front": 287.36, "rear": 21.53}     # centres of H28 to H31 and H03 to H06 (chassis plate)

DESIGN = {
    "bar_half_width": 7.545,       # original bar width 15.09 (caliper)
    "end_corner_r": 4.0,           # wall around B01/B02 and B14/B15 approx. 1.7 to 2.0 mm
    "fillet_r": 3.0,
    "chamfer_deg": 30.0,           # angle of the transitions to the y axis
    "front_bar_start": 29.6,       # end of the transition at the end with B01 to B04
    "rear_bar_end": 196.6,         # start of the transition at the end with B07 to B15
    "window": (4.5, 12.8, 30.05, 2.0),   # half width, y0, y1, corner radius (contains the hexagon)
    "closed_holes": ("B05", "B06"),
    "split_y": 121.65,             # test print halves
}
DENSITY = {"carbon": 1.6, "7075": 2.81, "PLA": 1.24}


# ---------------------------------------------------------------- geometry
def filleted_polygon(points, radii):
    """Closed contour of lines and arcs (geometry data format) with a fillet at each vertex."""
    n = len(points)
    P = [np.asarray(p, float) for p in points]
    corners = []
    for i in range(n):
        v, a, b = P[i], P[i - 1], P[(i + 1) % n]
        r = radii[i]
        u1, u2 = (a - v) / np.linalg.norm(a - v), (b - v) / np.linalg.norm(b - v)
        half = math.acos(max(-1.0, min(1.0, float(u1 @ u2)))) / 2
        if r <= 0:
            corners.append((v, v, None))
            continue
        t = r / math.tan(half)
        bis = (u1 + u2) / np.linalg.norm(u1 + u2)
        c = v + bis * r / math.sin(half)
        corners.append((v + u1 * t, v + u2 * t, (c, c - bis * r, r)))
    prims = []
    for i in range(n):
        t1, t2, arc = corners[i]
        if arc is not None:
            c, m, r = arc
            prims.append({"type": "arc", "start": list(t1), "mid": list(m), "end": list(t2),
                          "center": list(c), "r": r})
        nxt = corners[(i + 1) % n][0]
        if np.linalg.norm(nxt - t2) > 1e-9:
            prims.append({"type": "line", "start": list(t2), "end": list(nxt)})
    for q in prims:                                  # plain floats, rounded for the JSON file
        for k in ("start", "mid", "end", "center"):
            if k in q:
                q[k] = [round(float(v), 6) for v in q[k]]
        if "r" in q:
            q["r"] = round(float(q["r"]), 6)
    return prims


def build_geometry(orig, half_width):
    d = DESIGN
    w, W, L = d["bar_half_width"], half_width, max(p[1] for p in contour_points(orig["outline"], 400))
    k = math.tan(math.radians(d["chamfer_deg"]))           # dx per dy of the transitions
    ya = d["front_bar_start"] - (W - w) / k
    yc = d["rear_bar_end"] + (W - w) / k
    rc, rf = d["end_corner_r"], d["fillet_r"]
    pts = [(-W, 0), (W, 0), (W, ya), (w, d["front_bar_start"]), (w, d["rear_bar_end"]), (W, yc), (W, L),
           (-W, L), (-W, yc), (-w, d["rear_bar_end"]), (-w, d["front_bar_start"]), (-W, ya)]
    radii = [rc, rc, rf, rf, rf, rf, rc, rc, rf, rf, rf, rf]
    hw, y0, y1, rw = d["window"]
    window = filleted_polygon([(-hw, y0), (hw, y0), (hw, y1), (-hw, y1)], [rw] * 4)
    return {
        "units": "mm",
        "thickness": orig["thickness"],
        "hole_d": orig["hole_d"],
        "csk_d": 0.0,
        "csk_angle": orig["csk_angle"],
        "csk_side": "none",
        "basis": "speedrun top brace: holes from top_brace_geometry.json without B05 and B06, outline and "
                 "window new (generate_top_brace_speedrun.py), obround unchanged",
        "outline": filleted_polygon(pts, radii),
        "cutouts": {"window": window, "obround": orig["cutouts"]["obround"]},
        "holes": [h for h in orig["holes"] if h["id"] not in d["closed_holes"]],
    }


# ---------------------------------------------------------------- checks
def outline_solid(prims, t=1.0):
    return wire_from_prims(prims).extrude(t).val()


def check_outline(g, orig, faces):
    """Area of the new outline outside the original outline: in total, and outside the contact
    faces of the bulkheads (faces: list of (y0, y1, half width) in top brace coordinates)."""
    new, old = outline_solid(g["outline"]), outline_solid(orig["outline"])
    outside = new.cut(old)
    print(f"  area of the new outline outside the original outline: {outside.Volume():.1f} mm2 "
          f"(closed end notches and wider ends)")
    for y0, y1, hw in faces:
        outside = outside.cut(cq.Solid.makeBox(2 * hw, y1 - y0, 3, cq.Vector(-hw, y0, -1)))
    print(f"  of which outside the contact faces of the bulkheads: {outside.Volume():.3f} mm2")
    for name in orig["cutouts"]:
        if name == "hexagon":
            hexa = outline_solid(orig["cutouts"]["hexagon"])
            print(f"  hexagon of the original outside the new window: {hexa.cut(outline_solid(g['cutouts']['window'])).Volume():.3f} mm2")
    return outside


def holes(g):
    return {h["id"]: (h["x"], h["y"]) for h in g["holes"]}


def brace_offset(g, d):
    """Offset c of the top brace on the car (plate y = c - brace y), from the screw positions at both
    ends and the distance d of the top brace screws from the bulkhead centre."""
    h = holes(g)
    c_front = BULKHEAD_Y["front"] - d + (h["B01"][1] + h["B02"][1]) / 2
    c_rear = BULKHEAD_Y["rear"] + d + (h["B14"][1] + h["B15"][1]) / 2
    return c_front, c_rear


def check_bulkheads(g, lp, up):
    """Positions of the holes of the top brace relative to the screws of both upper bulkheads."""
    h = holes(g)
    d = up["deck_screw_y"]
    c_front, c_rear = brace_offset(g, d)
    c = (c_front + c_rear) / 2
    L = max(p[1] for p in contour_points(g["outline"], 400))
    print(f"  top brace screw position along y required by the top brace holes: "
          f"{(BULKHEAD_Y['front'] - BULKHEAD_Y['rear'] - (h['B14'][1] - h['B01'][1])) / 2:.2f} mm from the "
          f"bulkhead centre (upper bulkhead: {d:.2f})")
    rows = []
    for end, ids, access, yb, sign in (("front", ("B01", "B02"), ("B03", "B04"), BULKHEAD_Y["front"], -1),
                                       ("rear", ("B14", "B15"), ("B12", "B13"), BULKHEAD_Y["rear"], 1)):
        for hid in ids + access:
            bx, by = h[hid]
            px, py = -bx, c - by                                  # chassis plate coordinates
            ux, uy = sign * px, sign * (py - yb)                  # bulkhead coordinates
            if hid in ids:
                tx, ty = math.copysign(up["deck_screw_x"], ux), d
                kind = "top brace screw (tapped hole)"
            else:
                tx, ty = math.copysign(lp["top_boss_x_pinion"], ux), lp["top_boss_y_pinion"]
                kind = "access to the M3x10 screw"
            rows.append((end, hid, kind, ux - tx, uy - ty))
        end_y = sign * ((c - (0.0 if end == "front" else L)) - yb)
        rows.append((end, "end", f"end of the top brace at y = {end_y:.2f} (gear block ends at "
                     f"{up['deck_end_y'] - 0.5:.2f}, contact face ends at {lp['body_y_pinion_end']:.2f})", 0, 0))
    for end, hid, kind, dx, dy in rows:
        if hid == "end":
            print(f"    {end:5s} {kind}")
        else:
            print(f"    {end:5s} {hid}: {kind:30s} offset x {dx:+.2f}, y {dy:+.2f} mm")
    return c


# ---------------------------------------------------------------- outputs
def write_hole_table(g, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["id", "x_mm", "y_mm", "through_d_mm"])
        for h in g["holes"]:
            wr.writerow([h["id"], f"{h['x']:.2f}", f"{h['y']:.2f}", f"{g['hole_d']:g}"])


def test_print_halves(solid, t, ys, stem):
    """Two halves with one dovetail (neck 5 mm, tip 7 mm, length 5 mm, gap 0.1 mm per side)."""
    def trapezoid(off):
        pts = [(-2.5 - off, ys), (2.5 + off, ys), (3.5 + off, ys + 5 + off), (-3.5 - off, ys + 5 + off)]
        return cq.Workplane("XY").workplane(offset=-1).polyline(pts).close().extrude(t + 2).val()
    big = 400
    male = trapezoid(0.0).intersect(cq.Solid.makeBox(big, big, t, cq.Vector(-big / 2, 0, 0)))
    a = solid.intersect(cq.Solid.makeBox(big, ys + big, t + 2, cq.Vector(-big / 2, -big, -1))).fuse(male)
    b = solid.intersect(cq.Solid.makeBox(big, big, t + 2, cq.Vector(-big / 2, ys, -1))).cut(trapezoid(0.1))
    out = []
    for name, part in (("halfA", a), ("halfB", b)):
        path = f"{stem}_{name}.stl"
        cq.exporters.export(cq.Workplane().add(part), path, tolerance=0.01, angularTolerance=0.1)
        bb = part.BoundingBox()
        out.append((path, bb.xlen, bb.ylen))
    return out


def drawing(g, orig, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from generate_chassis_templates import draw_png_part, dim_arrows, extent, width_at
    fig, ax = plt.subplots(figsize=(6.4, 14.93))
    draw_png_part(ax, g)
    ref = contour_points(orig["outline"])
    ref = np.vstack([ref, ref[:1]])
    ax.plot(ref[:, 0], ref[:, 1], color="#9a9a9a", lw=0.9, ls=(0, (5, 4)), zorder=4,
            label="Outline of the original top brace")
    x0, x1, y0, y1 = extent(g)
    wb = width_at(g, 120.0)
    dim_arrows(ax, -wb / 2, wb / 2, -10, f"{wb:.2f} bar, {x1 - x0:.2f} ends", x1 + 6, y0, y1)
    ax.text(0, -24, f"Plain Ø{g['hole_d']:g} holes · t = {g['thickness']:.1f}", ha="center", va="top", fontsize=8.5)
    ax.set_xlim(-24, 32)
    ax.set_ylim(-34, 262)
    ax.set_title("Speedrun top brace - top view")
    ax.legend(loc="upper right", fontsize=7.5, framealpha=0.95)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    from generate_chassis_templates import brace_a4
    lp, up = load_params(LOWER), load_params(UPPER)
    with open(ORIG, encoding="utf-8") as f:
        orig = json.load(f)
    os.makedirs(OUT, exist_ok=True)
    g = build_geometry(orig, lp["body_half_width"])
    with open(GEOM, "w", encoding="utf-8") as f:
        json.dump(g, f, indent=1)
    solid = plate_solid(g).val()
    cq.exporters.export(cq.Workplane().add(solid), STEM + ".step")
    cq.exporters.export(cq.Workplane().add(solid), STEM + ".stl", tolerance=0.01, angularTolerance=0.1)
    build_dxf(g).saveas(STEM + ".dxf")
    write_hole_table(g, f"{OUT}/top_brace_speedrun_hole_table.csv")
    info = ["New design for the bulkheads of this project: ends as wide as the bulkheads, solid bar.",
            "Origin: x = 0 centre line, y = 0 end edge with B01 to B04 (same as the original top brace)."]
    for scale, suffix in ((1.0, ""), (0.97, "_print97")):
        brace_a4(f"{STEM}_1to1_A4{suffix}.pdf", g, scale, name="speedrun top brace", info=info)
    halves = test_print_halves(solid, g["thickness"], DESIGN["split_y"], f"{OUT}/testprint_top_brace_speedrun")
    drawing(g, orig, "photos/cad_top_brace_speedrun_drawing.png")

    vol, vol0 = solid.Volume(), plate_solid(orig).val().Volume()
    print(f"Wrote {GEOM}, {STEM}.step/.stl/.dxf, hole table, templates, test print halves, drawing")
    print(f"  solid valid: {solid.isValid()}, holes: {len(g['holes'])} (closed: {', '.join(DESIGN['closed_holes'])})")
    print(f"  volume {vol / 1000:.2f} cm3 (original {vol0 / 1000:.2f} cm3), mass: "
          + ", ".join(f"{m} {vol / 1000 * rho:.1f} g" for m, rho in DENSITY.items()))
    for path, w, l in halves:
        print(f"  {path}: {w:.1f} x {l:.1f} mm")
    print("Checks")
    c = check_bulkheads(g, lp, up)
    L = max(p[1] for p in contour_points(g["outline"], 400))
    y0, y1, hw = up["deck_end_y"] - 0.5, lp["body_y_pinion_end"], lp["body_half_width"]
    faces = [(y0 - (BULKHEAD_Y["front"] - c), y1 - (BULKHEAD_Y["front"] - c), hw),      # front end
             (c - BULKHEAD_Y["rear"] - y1, c - BULKHEAD_Y["rear"] - y0, hw)]          # rear end
    faces = [(min(a, b) - 0.01, max(a, b) + 0.01, h + 0.01) for a, b, h in faces]
    print(f"  contact faces of the bulkheads in top brace coordinates: y {faces[0][0]:.2f} to {faces[0][1]:.2f} "
          f"and {faces[1][0]:.2f} to {faces[1][1]:.2f}")
    check_outline(g, orig, faces)
    print(f"  top brace on the contact faces: end with B01 to B04 {faces[0][1] - 0.01:.2f} mm long, "
          f"end with B07 to B15 {L - faces[1][0] - 0.01:.2f} mm long")
    upper = bulkhead_upper(lp, up)
    zbrace = lp["axis_z"] + up["deck_h"]
    inter = 0.0
    for end, yb in BULKHEAD_Y.items():
        rot = 180 if end == "front" else 0
        # top brace in the coordinates of this bulkhead
        b = solid.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180).translate(cq.Vector(0, c - yb, zbrace))
        if rot:
            b = b.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180)
        inter += b.intersect(upper.val()).Volume()
    print(f"  interference of the top brace with both upper bulkheads: {inter:.4f} mm3")


if __name__ == "__main__":
    main()
