"""Generate the front shock tower of the speedrun chassis (Carten T410R).

The tower is a new design for the speedrun upper bulkhead: a flat 3 mm plate on the contact face
of the shock tower wall, fixed with 4 screws M3x8 in the tapped holes of the wall. The damper
holes are in the positions of the stock front shock tower (measurements of the owner). The camber
link holes have the height of the stock tower but are moved outward, so that the rod ends behind
the tower have space beside the wall of the bulkhead (the stock bulkhead has two narrow ears).

Outline: straight top edge, round ends around the damper holes, straight edges down to round
lobes around the camber link holes, straight bottom edge above the block in front of the wall,
inside corners with a radius. Edges: chamfer on both faces; on the back face, the chamfer increases
along the bottom edge to the relief of the root radius of the wall. Holes with small chamfers.

Plate coordinates: x across the car (x = 0 centre line), y height above the parting face of the
bulkheads, z = 0 back face (contact face on the wall), z = thickness front face (damper side).

Usage (from the root directory of the repository):
    python scripts/cad/generate_shock_tower_front.py

Output (directory cad/shock_tower): geometry data, STEP and STL file (plate coordinates), DXF file,
hole table, 1:1 templates (A4, 100 % and 97 %) and the drawing photos/cad_shock_tower_front_drawing.png.
Checks: holes against the tapped holes of the bulkhead, interference with both bulkheads, space
for the rod ends, gap above the block, contact face on the wall, edge distances, thin slits.

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
from generate_bulkhead_lower import bulkhead_lower, load_params, thin_gaps  # noqa: E402
from generate_bulkhead_upper import bulkhead_upper  # noqa: E402
from generate_drawing import contour_points  # noqa: E402
from generate_dxf import build_dxf  # noqa: E402
from generate_solid import edge_chamfer_tools, hole_chamfer_cones, wire_from_prims  # noqa: E402
from generate_top_brace_speedrun import filleted_polygon  # noqa: E402

LOWER = "cad/bulkhead/bulkhead_lower_parameters.json"
UPPER = "cad/bulkhead/bulkhead_upper_parameters.json"
PARAMS = "cad/shock_tower/shock_tower_front_parameters.json"
OUT = "cad/shock_tower"
STEM = f"{OUT}/shock_tower_front_T410R_speedrun"
GEOM = f"{OUT}/shock_tower_front_geometry.json"
DRAWING = "photos/cad_shock_tower_front_drawing.png"
DENSITY = {"carbon": 1.6, "7075": 2.81, "PLA": 1.24}


# ---------------------------------------------------------------- layout and outline
def layout(tp, lp, up):
    """Hole centres in the plane of the tower (x, y above the parting face)."""
    r = tp["stock_hole_d"] / 2
    xm, yl, yu = up["tower_hole_x"], up["tower_hole_h_lower"], up["tower_hole_h_upper"]
    cam_stock = (xm + tp["camber_dx"], yl + r + tp["camber_dy"])
    damper = (xm + r + tp["damper_dx"], yu + tp["damper_dy"])
    # rod end behind the tower: keep its radius clear of the side faces of the bulkhead
    cam = (max(cam_stock[0], lp["body_half_width"] + tp["rod_end_clearance_r"]), cam_stock[1])
    return {"mount": [(-xm, yl), (xm, yl), (-xm, yu), (xm, yu)], "camber": cam,
            "camber_stock": cam_stock, "damper": damper}


def _left(d):
    return np.array([-d[1], d[0]])


def _intersect(p1, d1, p2, d2):
    t, _ = np.linalg.solve(np.array([d1, -d2]).T, p2 - p1)
    return p1 + t * d1


def _tangent_dir(p, c, r):
    """Direction of the line from p that touches the circle (c, r), circle on the left."""
    d = c - p
    ang = math.atan2(d[1], d[0]) - math.asin(r / np.linalg.norm(d))
    return np.array([math.cos(ang), math.sin(ang)])


def build_geometry(tp, lp, up, lay):
    """Geometry data (format of the plate geometry files) of the tower."""
    yb = up["gear_block_h"] + tp["bottom_gap"]
    xs = lp["body_half_width"] + tp["side_gap"]
    cl, rl = np.array(lay["camber"], float), tp["lobe_r"]
    cd, rd = np.array(lay["damper"], float), tp["end_r"]
    if abs(rl - rd) > 1e-9:
        raise ValueError("lobe_r and end_r must be equal (common tangent parallel to the centre line)")
    yt = cd[1] + rd
    v1 = np.array([xs, yb])                                   # bottom corner (inside corner)
    da = _tangent_dir(v1, cl, rl)                             # down to the lobe
    db = (cd - cl) / np.linalg.norm(cd - cl)                  # lobe to damper end, below both circles
    pb = cl - _left(db) * rl
    v2 = _intersect(v1, da, pb, db)                           # corner with the lobe radius
    v3 = _intersect(pb, db, np.array([0.0, yt]), np.array([-1.0, 0.0]))   # corner with the end radius
    right = [v1, v2, v3]
    pts = right + [np.array([-p[0], p[1]]) for p in reversed(right)]
    radii = [tp["inside_r"], rl, rd, rd, rl, tp["inside_r"]]
    prims = filleted_polygon(pts, radii)
    holes = [{"id": f"T{i + 1}", "x": round(x, 4), "y": round(y, 4)} for i, (x, y) in enumerate(lay["mount"])]
    holes += [{"id": "C1", "x": -round(cl[0], 4), "y": round(cl[1], 4)},
              {"id": "C2", "x": round(cl[0], 4), "y": round(cl[1], 4)},
              {"id": "D1", "x": -round(cd[0], 4), "y": round(cd[1], 4)},
              {"id": "D2", "x": round(cd[0], 4), "y": round(cd[1], 4)}]
    return {"units": "mm", "thickness": tp["thickness"], "hole_d": tp["hole_d"], "csk_d": 0.0,
            "csk_angle": 90.0, "csk_side": "none",
            "basis": "speedrun front shock tower (generate_shock_tower_front.py): x across the car, y height above "
                     "the parting face of the bulkheads. T1 to T4: mounting holes (tapped holes of the upper "
                     "bulkhead), C1/C2: camber link ball studs, D1/D2: damper ball studs",
            "outline": prims, "cutouts": {}, "holes": holes}


# ---------------------------------------------------------------- solid
def tower_solid(g, tp, lp, up):
    """Solid of the tower in plate coordinates (cadquery Solid)."""
    t, e = g["thickness"], tp["edge_chamfer"]
    yb = up["gear_block_h"] + tp["bottom_gap"]
    relief = up["gear_block_h"] + up["wall_root_r"] + tp["root_clearance"] - yb
    xa = lp["body_half_width"] + 0.1                          # full relief over the width of the bulkhead
    xb = xa + 1.5                                             # run-out to the edge chamfer

    def back(q):
        if q[1] > yb + 1.0:
            return e
        w = min(max((xb - abs(q[0])) / (xb - xa), 0.0), 1.0)
        return e + (relief - e) * w

    s = wire_from_prims(g["outline"]).extrude(t).val()
    for tool in edge_chamfer_tools(g["outline"], 0.0, 1, back) + edge_chamfer_tools(g["outline"], t, -1, lambda q: e):
        s = s.cut(tool)
    r, c = g["hole_d"] / 2, tp["hole_chamfer"]
    for h in g["holes"]:
        s = s.cut(cq.Solid.makeCylinder(r, t + 2, cq.Vector(h["x"], h["y"], -1)))
        for cone in hole_chamfer_cones(h["x"], h["y"], r, c, t):   # chamfers on both faces
            s = s.cut(cone)
    return s.clean()


def to_bulkhead(solid, lp, up):
    """Tower from plate coordinates to the coordinates of the bulkheads (contact face on the wall)."""
    return solid.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90).translate(
        cq.Vector(0, up["tower_face_y"], lp["axis_z"]))


def tower_in_bulkhead(lp=None, up=None):
    """Tower solid in the coordinates of the bulkheads (for the assembly of the speedrun chassis)."""
    lp = lp or load_params(LOWER)
    up = up or load_params(UPPER)
    tp = load_params(PARAMS)
    g = build_geometry(tp, lp, up, layout(tp, lp, up))
    return to_bulkhead(tower_solid(g, tp, lp, up), lp, up)


# ---------------------------------------------------------------- outputs
def write_hole_table(g, path):
    names = {"T": "mounting screw M3x8 (tapped hole of the upper bulkhead)", "C": "camber link ball stud",
             "D": "damper ball stud"}
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["id", "x_mm", "y_mm", "through_d_mm", "use"])
        for h in g["holes"]:
            wr.writerow([h["id"], f"{h['x']:.2f}", f"{h['y']:.2f}", f"{g['hole_d']:g}", names[h["id"][0]]])


def template_a4(path, g, print_scale, info):
    """1:1 template of the tower on one A4 page (portrait)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from generate_chassis_templates import DARK, bar, canvas_for, draw_part, print_lines, write_notes
    k = mm / print_scale
    ph = A4[1] / k
    k_ = (0, 0, 0)
    lines = [("Carten T410R speedrun front shock tower - 1:1 template, A4", 3.0, True, k_), ("", 1.2, False, k_)] + \
        print_lines(print_scale) + [
        ("Check both 100 mm bars with a ruler before use.", 2.2, False, k_),
        ("", 1.2, False, k_),
        (f"Red: through holes Ø{g['hole_d']:g} mm with centre cross. Outline without the edge chamfers.", 2.2, False, k_),
    ] + [(t, 2.2, False, DARK) for t in info]
    c = canvas_for(path, A4, f"Speedrun front shock tower - 1:1 template ({print_scale * 100:g} %)",
                   "Carten T410R speedrun front shock tower, A4 portrait")
    c.saveState()
    c.scale(k, k)
    write_notes(c, 8, ph - 12, lines)
    bar(c, 12, 15, True, "100 mm (x)")
    bar(c, 190, 40, False, "100 mm (y)")
    c.translate(105, 120)
    draw_part(c, g)
    c.restoreState()
    c.showPage()
    c.save()


def drawing(path, g, lay, tp, lp, up, tower_b, upper, lower):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon as MPoly, Rectangle
    from mesh_views import draw_mesh, iso_basis, subdivide

    fig = plt.figure(figsize=(15, 10.5))
    fig.suptitle("Carten T410R speedrun front shock tower for the speedrun upper bulkhead (not verified)",
                 fontsize=12, y=0.985)
    # front view with the bulkhead behind it
    ax = fig.add_axes([0.03, 0.47, 0.6, 0.47])
    hw = lp["body_half_width"]
    zg, zr, zw = up["gear_block_h"], up["gear_block_h"] + up["wall_root_r"], up["wall_top_h"]
    ax.add_patch(Rectangle((-hw, zg - 3), 2 * hw, 3, fc="#f1e2cf", ec="#b08a5a", lw=0.8, ls="--", zorder=1))
    ax.add_patch(Rectangle((-hw, zg), 2 * hw, zw - zg, fc="#f6ead9", ec="#b08a5a", lw=0.8, ls="--", zorder=1))
    ax.plot([-hw, hw], [zr, zr], color="#b08a5a", lw=0.6, ls=":", zorder=1)
    ax.text(-hw + 0.5, zw - 1.2, "upper bulkhead: wall (dashed)", fontsize=7.5, color="#8a6a40")
    ax.text(-hw + 0.5, zg - 2.4, "block in front of the wall, 17.8", fontsize=7.5, color="#8a6a40")
    pts = contour_points(g["outline"], 80)
    ax.add_patch(MPoly(pts, closed=True, fc="#3b4048", ec="#1d2025", lw=1.0, alpha=0.88, zorder=2))
    for h in g["holes"]:
        ax.add_patch(Circle((h["x"], h["y"]), g["hole_d"] / 2, fc="white", ec="#1d2025", lw=0.6, zorder=4))
        ax.annotate(h["id"], (h["x"], h["y"]), xytext=(4, 4), textcoords="offset points", fontsize=7.5,
                    color="white" if h["id"][0] == "T" else "#1d2025", zorder=5)
    cs = lay["camber_stock"]
    for sx in (-1, 1):
        ax.add_patch(Circle((sx * cs[0], cs[1]), tp["rod_end_clearance_r"] - 0.5, fill=False, ec="#c0392b", lw=0.9,
                            ls="--", zorder=5))
    ax.text(cs[0] + 0.5, cs[1] - 6.6, "stock camber link position\n(rod end would hit the wall)", fontsize=7.5,
            color="#c0392b", ha="center")
    xm, yl, yu = up["tower_hole_x"], up["tower_hole_h_lower"], up["tower_hole_h_upper"]
    cam, dmp = lay["camber"], lay["damper"]
    y_dim = min(pts[:, 1]) - 4.5
    for xa_, xb_, lab, yy in ((-xm, xm, f"{2 * xm:.1f}", y_dim), (-cam[0], cam[0], f"{2 * cam[0]:.2f}", y_dim - 3.2),
                              (-dmp[0], dmp[0], f"{2 * dmp[0]:.2f}", y_dim - 6.4)):
        ax.annotate("", (xa_, yy), (xb_, yy), arrowprops=dict(arrowstyle="<->", lw=0.8))
        ax.text(0, yy + 0.3, lab, ha="center", va="bottom", fontsize=8)
    xr = max(pts[:, 0]) + 3
    for k, (yy, lab) in enumerate(((yl, f"{yl:.1f}"), (yu, f"{yu:.1f}"), (cam[1], f"{cam[1]:.1f}"),
                                   (dmp[1], f"{dmp[1]:.1f}"))):
        ax.plot([xr - 1, xr + 1], [yy, yy], color="k", lw=0.7)
        ax.text(xr + 1.5, yy, lab, va="center", fontsize=8)
    ax.text(xr - 1, max(pts[:, 1]) + 2.2, "height above the\nparting face", fontsize=7.5, va="bottom")
    ax.set_xlim(-42, 50)
    ax.set_ylim(y_dim - 9, 40)
    ax.set_aspect("equal")
    ax.set_title("Front view (damper side)", fontsize=10)
    ax.set_xlabel("x [mm]")
    ax.grid(True, color="#eeeeee", lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.text(-41, y_dim - 7.5, f"t = {g['thickness']:g} mm carbon · holes Ø{g['hole_d']:g} with 0.3 chamfers · "
            f"edge chamfers {tp['edge_chamfer']:g} mm · screws M3x8 (T1 to T4)", fontsize=8)

    # section x = 0: wall, root radius and the relief on the back face of the tower
    ax2 = fig.add_axes([0.66, 0.5, 0.32, 0.42])
    plane = cq.Face.makePlane(400, 400, cq.Vector(0, 0, 0), cq.Vector(1, 0, 0))
    for solid, fc in ((upper, "#d9a35f"), (tower_b, "#3b4048")):
        for f in solid.intersect(plane).Faces():
            from OCP.BRepTools import BRepTools_WireExplorer
            ex = BRepTools_WireExplorer(f.outerWire().wrapped)
            poly = []
            while ex.More():
                ed = cq.Edge(ex.Current())
                n = 2 if ed.geomType() == "LINE" else 30
                seg = [(ed.positionAt(k / (n - 1)).y, ed.positionAt(k / (n - 1)).z - lp["axis_z"]) for k in range(n)]
                if poly and np.hypot(*(np.array(seg[0]) - poly[-1])) > np.hypot(*(np.array(seg[-1]) - poly[-1])):
                    seg = seg[::-1]
                poly += seg
                ex.Next()
            ax2.add_patch(MPoly(poly, closed=True, fc=fc, ec="#1d2025", lw=0.6, alpha=0.9))
    fy = up["tower_face_y"]
    ax2.set_xlim(fy - 7, fy + 6)
    ax2.set_ylim(zg - 2.5, zg + 9)
    ax2.set_aspect("equal")
    ax2.grid(True, color="#eeeeee", lw=0.6)
    ax2.set_title("Section x = 0: relief of the tower at the root radius", fontsize=10)
    ax2.set_xlabel("y [mm] (outer end to the left)")
    ax2.set_ylabel("height above the parting face [mm]")
    ax2.text(fy - 6.6, zg - 1.9, "tower", fontsize=8, color="#3b4048")
    ax2.text(fy + 0.6, zg - 1.9, "wall and block of the upper bulkhead", fontsize=8, color="#8a6a40")

    # assembly view
    ax3 = fig.add_axes([0.03, 0.02, 0.94, 0.4])
    tris, cols = [], []
    for solid, col in ((lower, (0.56, 0.62, 0.69)), (upper, (0.85, 0.62, 0.38)), (tower_b, (0.25, 0.27, 0.3))):
        vs, ts = solid.tessellate(0.02, 0.1)
        v = np.array([[p.x, p.y, p.z] for p in vs])
        t_ = subdivide(v[np.array(ts)], 1.2)
        tris.append(t_)
        cols.append(np.tile(col, (len(t_), 1)))
    lo, hi = draw_mesh(ax3, np.concatenate(tris), iso_basis(-125, 22), tri_colors=np.concatenate(cols))
    ax3.set_xlim(lo[0], hi[0])
    ax3.set_ylim(lo[1], hi[1])
    ax3.set_aspect("equal")
    ax3.axis("off")
    ax3.set_title("Tower on the speedrun bulkheads (view from the outer end)", fontsize=10)
    fig.savefig(path, dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- checks
def edge_distances(g):
    """Smallest distance from each hole edge to the outline (2D, without chamfers)."""
    wire = wire_from_prims(g["outline"]).val()
    return {h["id"]: wire.distance(cq.Vertex.makeVertex(h["x"], h["y"], 0.0)) - g["hole_d"] / 2
            for h in g["holes"]}


def main():
    lp, up, tp = load_params(LOWER), load_params(UPPER), load_params(PARAMS)
    os.makedirs(OUT, exist_ok=True)
    lay = layout(tp, lp, up)
    g = build_geometry(tp, lp, up, lay)
    with open(GEOM, "w", encoding="utf-8") as f:
        json.dump(g, f, indent=1)
    solid = tower_solid(g, tp, lp, up)
    cq.exporters.export(cq.Workplane().add(solid), STEM + ".step")
    cq.exporters.export(cq.Workplane().add(solid), STEM + ".stl", tolerance=0.01, angularTolerance=0.1)
    build_dxf(g).saveas(STEM + ".dxf")
    write_hole_table(g, f"{OUT}/shock_tower_front_hole_table.csv")
    info = ["Origin: x = 0 centre line, y = 0 parting face of the bulkheads (height above it).",
            "Lay the template on the back face (wall side). T1 to T4: mounting holes, C1/C2: camber links,",
            "D1/D2: dampers. The camber link holes are 3.19 mm further outward than on the stock tower."]
    for scale, suffix in ((1.0, ""), (0.97, "_print97")):
        template_a4(f"{STEM}_1to1_A4{suffix}.pdf", g, scale, info)

    upper, lower = bulkhead_upper(lp, up).val(), bulkhead_lower(lp).val()
    tower_b = to_bulkhead(solid, lp, up)
    drawing(DRAWING, g, lay, tp, lp, up, tower_b, upper, lower)

    vol = solid.Volume()
    bb = solid.BoundingBox()
    print(f"Wrote {GEOM}, {STEM}.step/.stl/.dxf, hole table, templates, {DRAWING}")
    print(f"  solid valid: {solid.isValid()}, size {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm, "
          f"volume {vol / 1000:.2f} cm3, mass: " + ", ".join(f"{m} {vol / 1000 * rho:.1f} g" for m, rho in DENSITY.items()))
    cs, cam, dmp = lay["camber_stock"], lay["camber"], lay["damper"]
    print(f"  damper holes: x +-{dmp[0]:.2f}, {dmp[1]:.2f} above the parting face (stock position)")
    print(f"  camber link holes: x +-{cam[0]:.2f}, {cam[1]:.2f} above the parting face "
          f"(stock: x +-{cs[0]:.2f}, moved {cam[0] - cs[0]:.2f} mm outward)")
    print("Checks")
    off = max(math.hypot(h["x"] - x, h["y"] - y) for h, (x, y) in zip(g["holes"][:4], lay["mount"]))
    print(f"  mounting holes T1 to T4 on the tapped holes of the upper bulkhead: largest offset {off:.4f} mm")
    print(f"  interference with the upper bulkhead: {tower_b.intersect(upper).Volume():.4f} mm3, "
          f"with the lower bulkhead: {tower_b.intersect(lower).Volume():.4f} mm3")
    # contact area on the wall: overlap after a shift of 0.05 mm toward the wall
    contact = tower_b.translate(cq.Vector(0, 0.05, 0)).intersect(upper).Volume() / 0.05
    print(f"  contact area on the wall of the bulkhead: {contact:.0f} mm2")
    lo_, hi_ = 0.0, 2.0                                     # vertical gap above the block (bisection)
    for _ in range(12):
        mid = (lo_ + hi_) / 2
        if tower_b.translate(cq.Vector(0, 0, -mid)).intersect(upper).Volume() > 1e-6:
            hi_ = mid
        else:
            lo_ = mid
    print(f"  gap below the tower (block and root radius of the bulkhead): {lo_:.2f} mm")
    rod = 0.0
    for sx in (-1, 1):
        env = cq.Solid.makeCylinder(tp["rod_end_clearance_r"], tp["rod_end_depth"],
                                    cq.Vector(sx * cam[0], up["tower_face_y"], lp["axis_z"] + cam[1]), cq.Vector(0, 1, 0))
        rod += env.intersect(upper).Volume() + env.intersect(lower).Volume()
    print(f"  space for the rod ends behind the tower (radius {tp['rod_end_clearance_r']:g}, length "
          f"{tp['rod_end_depth']:g}): overlap with the bulkheads {rod:.4f} mm3")
    ed = edge_distances(g)
    print("  edge distance of the holes (outline without chamfers): "
          + ", ".join(f"{k} {v:.2f}" for k, v in ed.items() if k in ("T1", "C1", "D1")) + " mm")
    gaps = thin_gaps(solid)
    print(f"  check for thin slits and walls (faces closer than 0.25 mm): "
          f"{sum(1 for k in gaps if k[0] != 'narrow face')} slits or walls, "
          f"{sum(1 for k in gaps if k[0] == 'narrow face')} narrow faces")


if __name__ == "__main__":
    main()
