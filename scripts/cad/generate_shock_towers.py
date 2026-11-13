"""Generate the front and the rear shock tower of the speedrun chassis (Carten T410R).

Both towers are new designs for the speedrun upper bulkhead: flat 3 mm plates on the contact face
of the shock tower wall, fixed with 4 screws M3x8 in the tapped holes of the wall. The damper holes
(and the body post holes of the rear tower) are in the positions of the stock shock towers
(measurements of the owner), the camber link holes (wheel mounts) as well. The wall of the upper
bulkhead is narrowed (wall_half_width), so that the rod ends behind the tower have space beside it.

Outline: a chain of straight edges and radii around the holes (round lobes around the camber link
holes, round ends around the damper holes of the front tower and around the body post holes of the
rear tower), a straight bottom edge above the block in front of the wall and inside corners with a
radius. Edges: chamfer on both faces; on the back face, the chamfer increases along the bottom edge
to the relief of the root radius of the wall. Holes with small chamfers.

Plate coordinates: x across the car (x = 0 centre line), y height above the parting face of the
bulkheads, z = 0 back face (contact face on the wall), z = thickness front face (damper side).

Usage (from the root directory of the repository):
    python scripts/cad/generate_shock_towers.py              (both towers)
    python scripts/cad/generate_shock_towers.py --tower rear

Output per tower (directory cad/shock_tower): geometry data, STEP and STL file (plate coordinates),
DXF file, hole table, 1:1 templates (A4, 100 % and 97 %) and a drawing in photos/. Checks: holes
against the tapped holes of the bulkhead, interference with both bulkheads, space for the rod ends,
gap above the block, contact face on the wall, edge distances, thin slits.

Requires the packages cadquery, ezdxf, matplotlib and reportlab.
"""
import argparse
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
OUT = "cad/shock_tower"
TOWERS = {
    "front": {"params": f"{OUT}/shock_tower_front_parameters.json", "stem": f"{OUT}/shock_tower_front_T410R_speedrun",
              "geom": f"{OUT}/shock_tower_front_geometry.json", "table": f"{OUT}/shock_tower_front_hole_table.csv",
              "drawing": "photos/cad_shock_tower_front_drawing.png", "status": "verified"},
    "rear": {"params": f"{OUT}/shock_tower_rear_parameters.json", "stem": f"{OUT}/shock_tower_rear_T410R_speedrun",
             "geom": f"{OUT}/shock_tower_rear_geometry.json", "table": f"{OUT}/shock_tower_rear_hole_table.csv",
             "drawing": "photos/cad_shock_tower_rear_drawing.png", "status": "verified"},
}
HOLE_USE = {"T": "mounting screw M3x8 (tapped hole of the upper bulkhead)", "C": "camber link ball stud (wheel mount)",
            "D": "damper ball stud", "B": "body post", "S": "screw of the body post mount"}
DENSITY = {"carbon": 1.6, "7075": 2.81, "PLA": 1.24}


# ---------------------------------------------------------------- layout and outline
def layout(tp, lp, up):
    """Hole centres in the plane of the tower (x, y above the parting face), right side (x > 0)."""
    r = tp["stock_hole_d"] / 2
    xm, yl, yu = up["tower_hole_x"], up["tower_hole_h_lower"], up["tower_hole_h_upper"]
    cam_stock = (xm + tp["camber_dx"], yl + r + tp["camber_dy"])
    # camber link holes at the stock position: the wall of the upper bulkhead is narrowed so that the
    # rod ends behind the tower have space beside it (wall_half_width of the upper bulkhead)
    lay = {"mount": [(-xm, yl), (xm, yl), (-xm, yu), (xm, yu)], "camber": cam_stock,
           "damper": (xm + r + tp["damper_dx"], yu + tp["damper_dy"])}
    if "body_post_dx" in tp:
        xb = xm + r + tp["body_post_dx"]
        lay["body_post"] = (xb, yu + tp["body_post_d"] / 2)
        lay["body_post_screw"] = (xb, yu + tp["body_post_d"] + tp["body_post_gap"] + tp["body_post_screw_d"] / 2)
    return lay


def elements(tp, lp, up, lay):
    """Chain of the outline, counterclockwise: (centre, radius, fillet). Radius 0: a corner point
    with the given fillet radius; radius > 0: a circle that the outline runs around."""
    yb = up["gear_block_h"] + tp["bottom_gap"]
    xs = up.get("wall_half_width", lp["body_half_width"]) + tp["side_gap"]
    cam = (np.array(lay["camber"]), tp["lobe_r"], 0.0)
    if "body_post" in lay:
        rb = tp["body_post_end_r"]
        y_top = up["tower_hole_h_upper"] + tp["hole_d"] / 2 + tp["top_margin"]
        right = [(np.array([xs, yb]), 0.0, tp["inside_r"]), cam,
                 (np.array(lay["body_post"]), rb, 0.0), (np.array(lay["body_post_screw"]), rb, 0.0),
                 (np.array([lp["body_half_width"], y_top]), 0.0, tp["top_corner_r"])]
    else:
        right = [(np.array([xs, yb]), 0.0, tp["inside_r"]), cam, (np.array(lay["damper"]), tp["end_r"], 0.0)]
    left = [(np.array([-c[0], c[1]]), r, f) for c, r, f in reversed(right)]
    return right + left


def _left(d):
    return np.array([-d[1], d[0]])


def _intersect(p1, d1, p2, d2):
    t, _ = np.linalg.solve(np.array([d1, -d2]).T, p2 - p1)
    return p1 + t * d1


def outline_from_elements(elems):
    """Outline (geometry data format) of a chain of points and circles: common tangents between
    consecutive elements (material on the left), corners filleted with the circle radii."""
    n = len(elems)
    lines = []
    for i in range(n):
        (c1, r1, _), (c2, r2, _) = elems[i], elems[(i + 1) % n]
        dv = c2 - c1
        L = np.linalg.norm(dv)
        a = math.asin((r2 - r1) / L)
        u = dv / L
        d = np.array([u[0] * math.cos(a) + u[1] * math.sin(a), -u[0] * math.sin(a) + u[1] * math.cos(a)])
        lines.append((c1 - _left(d) * r1, d))
    verts = [_intersect(*lines[i - 1], *lines[i]) for i in range(n)]
    return filleted_polygon(verts, [r if r > 0 else f for _, r, f in elems])


def build_geometry(name, tp, lp, up, lay):
    """Geometry data (format of the plate geometry files) of a tower. Holes with another diameter
    than hole_d carry their own diameter d."""
    holes = [{"id": f"T{i + 1}", "x": round(x, 4), "y": round(y, 4)} for i, (x, y) in enumerate(lay["mount"])]
    for key, hid, d in (("camber", "C", None), ("damper", "D", None), ("body_post", "B", tp.get("body_post_d")),
                        ("body_post_screw", "S", tp.get("body_post_screw_d"))):
        if key not in lay:
            continue
        x, y = lay[key]
        for k, sx in enumerate((-1, 1)):
            h = {"id": f"{hid}{k + 1}", "x": round(sx * x, 4), "y": round(y, 4)}
            if d is not None and abs(d - tp["hole_d"]) > 1e-9:
                h["d"] = d
            holes.append(h)
    return {"units": "mm", "thickness": tp["thickness"], "hole_d": tp["hole_d"], "csk_d": 0.0,
            "csk_angle": 90.0, "csk_side": "none",
            "basis": f"speedrun {name} shock tower (generate_shock_towers.py): x across the car, y height above "
                     "the parting face of the bulkheads. T1 to T4: mounting holes (tapped holes of the upper "
                     "bulkhead), C1/C2: camber link ball studs, D1/D2: damper ball studs"
                     + (", B1/B2: body posts, S1/S2: screws of the body post mounts" if "body_post" in lay else ""),
            "outline": outline_from_elements(elements(tp, lp, up, lay)), "cutouts": {}, "holes": holes}


def hole_d(g, h):
    return h.get("d", g["hole_d"])


# ---------------------------------------------------------------- solid
def tower_solid(g, tp, lp, up):
    """Solid of a tower in plate coordinates (cadquery Solid)."""
    t, e = g["thickness"], tp["edge_chamfer"]
    yb = up["gear_block_h"] + tp["bottom_gap"]
    relief = up["gear_block_h"] + up["wall_root_r"] + tp["root_clearance"] - yb
    xa = up.get("wall_half_width", lp["body_half_width"]) + 0.1   # full relief over the width of the wall
    xb = xa + 1.5                                             # run-out to the edge chamfer

    def back(q):
        if q[1] > yb + 1.0:
            return e
        w = min(max((xb - abs(q[0])) / (xb - xa), 0.0), 1.0)
        return e + (relief - e) * w

    s = wire_from_prims(g["outline"]).extrude(t).val()
    for tool in edge_chamfer_tools(g["outline"], 0.0, 1, back) + edge_chamfer_tools(g["outline"], t, -1, lambda q: e):
        s = s.cut(tool)
    c = tp["hole_chamfer"]
    for h in g["holes"]:
        r = hole_d(g, h) / 2
        s = s.cut(cq.Solid.makeCylinder(r, t + 2, cq.Vector(h["x"], h["y"], -1)))
        for cone in hole_chamfer_cones(h["x"], h["y"], r, c, t):   # chamfers on both faces
            s = s.cut(cone)
    return s.clean()


def to_bulkhead(solid, lp, up):
    """Tower from plate coordinates to the coordinates of the bulkheads (contact face on the wall)."""
    return solid.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90).translate(
        cq.Vector(0, up["tower_face_y"], lp["axis_z"]))


def tower_in_bulkhead(lp=None, up=None, name="front"):
    """Tower solid in the coordinates of the bulkheads (for the assembly of the speedrun chassis)."""
    lp = lp or load_params(LOWER)
    up = up or load_params(UPPER)
    tp = load_params(TOWERS[name]["params"])
    g = build_geometry(name, tp, lp, up, layout(tp, lp, up))
    return to_bulkhead(tower_solid(g, tp, lp, up), lp, up)


# ---------------------------------------------------------------- outputs
def write_hole_table(g, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["id", "x_mm", "y_mm", "through_d_mm", "use"])
        for h in g["holes"]:
            wr.writerow([h["id"], f"{h['x']:.2f}", f"{h['y']:.2f}", f"{hole_d(g, h):g}", HOLE_USE[h["id"][0]]])


def write_dxf(g, path):
    """DXF with the layers OUTLINE and HOLE_THROUGH (holes with their own diameter)."""
    doc = build_dxf(dict(g, holes=[h for h in g["holes"] if "d" not in h]))
    for h in g["holes"]:
        if "d" in h:
            doc.modelspace().add_circle((h["x"], h["y"]), h["d"] / 2, dxfattribs={"layer": "HOLE_THROUGH"})
    doc.saveas(path)


def template_a4(path, name, g, print_scale, info):
    """1:1 template of a tower on one A4 page (portrait)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from generate_chassis_templates import DARK, bar, canvas_for, draw_part, print_lines, write_notes
    from generate_print_template import RED, text
    k = mm / print_scale
    ph = A4[1] / k
    k_ = (0, 0, 0)
    sizes = sorted({hole_d(g, h) for h in g["holes"]})
    lines = [(f"Carten T410R speedrun {name} shock tower - 1:1 template, A4", 3.0, True, k_), ("", 1.2, False, k_)] + \
        print_lines(print_scale) + [
        ("Check both 100 mm bars with a ruler before use.", 2.2, False, k_),
        ("", 1.2, False, k_),
        ("Red: through holes Ø" + " / Ø".join(f"{d:g}" for d in sizes) + " mm with centre cross. "
         "Outline without the edge chamfers.", 2.2, False, k_),
    ] + [(t, 2.2, False, DARK) for t in info]
    c = canvas_for(path, A4, f"Speedrun {name} shock tower - 1:1 template ({print_scale * 100:g} %)",
                   f"Carten T410R speedrun {name} shock tower, A4 portrait")
    c.saveState()
    c.scale(k, k)
    write_notes(c, 8, ph - 12, lines)
    bar(c, 12, 15, True, "100 mm (x)")
    bar(c, 190, 40, False, "100 mm (y)")
    c.translate(105, 120)
    draw_part(c, dict(g, holes=[h for h in g["holes"] if "d" not in h]))
    for h in g["holes"]:
        if "d" in h:
            x, y = h["x"], h["y"]
            c.setDash()
            c.setLineWidth(0.2)
            c.setStrokeColorRGB(*RED)
            c.circle(x, y, h["d"] / 2, stroke=1, fill=0)
            c.setLineWidth(0.1)
            c.setStrokeColorRGB(0, 0, 0)
            c.line(x - 3.4, y, x + 3.4, y)
            c.line(x, y - 3.4, x, y + 3.4)
            text(c, x + 2.8, y + 2.8, h["id"], 1.9, (0.2, 0.2, 0.2))
    c.restoreState()
    c.showPage()
    c.save()


def drawing(path, name, g, lay, tp, lp, up, tower_b, upper, lower):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon as MPoly, Rectangle
    from mesh_views import draw_mesh, iso_basis, subdivide
    from OCP.BRepTools import BRepTools_WireExplorer

    fig = plt.figure(figsize=(15, 10.5))
    fig.suptitle(f"Carten T410R speedrun {name} shock tower for the speedrun upper bulkhead "
                 f"({TOWERS[name]['status']})",
                 fontsize=12, y=0.985)
    pts = contour_points(g["outline"], 80)
    x_max, y_min, y_max = max(pts[:, 0]), min(pts[:, 1]), max(pts[:, 1])
    # front view with the bulkhead behind it
    ax = fig.add_axes([0.03, 0.47, 0.6, 0.47])
    hw, xw = lp["body_half_width"], up.get("wall_half_width", lp["body_half_width"])
    zg, zr, zw = up["gear_block_h"], up["gear_block_h"] + up["wall_root_r"], up["wall_top_h"]
    zs = up.get("side_step_h", zg)
    ax.add_patch(MPoly([(-hw, zs - 2), (hw, zs - 2), (hw, zs), (xw, zs), (xw, zg), (-xw, zg), (-xw, zs), (-hw, zs)],
                       closed=True, fc="#f1e2cf", ec="#b08a5a", lw=0.8, ls="--", zorder=1))
    ax.add_patch(Rectangle((-xw, zg), 2 * xw, zw - zg, fc="#f6ead9", ec="#b08a5a", lw=0.8, ls="--", zorder=1))
    ax.plot([-xw, xw], [zr, zr], color="#b08a5a", lw=0.6, ls=":", zorder=1)
    ax.text(-hw - 0.8, zs - 1.0, f"block in front of the wall {zg:g}\nside steps {zs:g}", fontsize=7.5,
            color="#8a6a40", ha="right", va="center")
    ax.add_patch(MPoly(pts, closed=True, fc="#3b4048", ec="#1d2025", lw=1.0, alpha=0.88, zorder=2))
    for h in g["holes"]:
        ax.add_patch(Circle((h["x"], h["y"]), hole_d(g, h) / 2, fc="white", ec="#1d2025", lw=0.6, zorder=4))
        off = 4 + 5 * (hole_d(g, h) - g["hole_d"]) / 2           # labels of larger holes further outward
        ax.annotate(h["id"], (h["x"], h["y"]), xytext=(off, off), textcoords="offset points", fontsize=7.5,
                    color="white" if h["id"][0] in "TDBS" else "#1d2025", zorder=5)
    cam = lay["camber"]
    for sx in (-1, 1):
        ax.add_patch(Circle((sx * cam[0], cam[1]), tp["rod_end_clearance_r"], fill=False, ec="#c0392b", lw=0.9,
                            ls="--", zorder=5))
    ax.text(cam[0] + tp["rod_end_clearance_r"] + 0.8, cam[1] - tp["rod_end_clearance_r"] - 1.0,
            f"space for the rod end behind the tower\n(radius {tp['rod_end_clearance_r']:g}, beside the wall)",
            fontsize=7.5, color="#c0392b", ha="left", va="center")
    dims = [up["tower_hole_x"], lay["camber"][0], lay["damper"][0]] + ([lay["body_post"][0]] if "body_post" in lay else [])
    y_dim = y_min - 4.5
    for k, xd in enumerate(dims):
        yy = y_dim - 3.2 * k
        ax.annotate("", (-xd, yy), (xd, yy), arrowprops=dict(arrowstyle="<->", lw=0.8))
        ax.text(0, yy + 0.3, f"{2 * xd:.2f}", ha="center", va="bottom", fontsize=8)
    xr = x_max + 3
    heights = sorted({round(v, 2) for v in [up["tower_hole_h_lower"], up["tower_hole_h_upper"], lay["camber"][1],
                                             lay["damper"][1]] + [lay[k][1] for k in ("body_post", "body_post_screw")
                                                                  if k in lay]})
    labels = []                                             # label heights at least 1.8 mm apart
    for yy in heights:
        labels.append(max(yy, labels[-1] + 1.8) if labels else yy)
    for yy, yt in zip(heights, labels):
        ax.plot([xr - 1, xr + 1, xr + 1.6], [yy, yy, yt], color="k", lw=0.7)
        ax.text(xr + 2.0, yt, f"{yy:.2f}", va="center", fontsize=8)
    ax.text(xr - 1, y_max + 1.2, "height above the\nparting face", fontsize=7.5, va="bottom")
    y_bottom = y_dim - 3.2 * len(dims) - 3
    ax.set_xlim(-x_max - 6, x_max + 15)
    ax.set_ylim(y_bottom, y_max + 7)
    ax.set_aspect("equal")
    ax.set_title("Front view (damper side), upper bulkhead dashed", fontsize=10)
    ax.set_xlabel("x [mm]")
    ax.grid(True, color="#eeeeee", lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.text(-x_max - 5, y_bottom + 1.0, f"t = {g['thickness']:g} mm carbon · holes with 0.3 chamfers · "
            f"edge chamfers {tp['edge_chamfer']:g} mm · screws M3x8 (T1 to T4)", fontsize=8)

    # section x = 0: wall, root radius and the relief on the back face of the tower
    ax2 = fig.add_axes([0.66, 0.5, 0.32, 0.42])
    plane = cq.Face.makePlane(400, 400, cq.Vector(0, 0, 0), cq.Vector(1, 0, 0))
    for solid, fc in ((upper, "#d9a35f"), (tower_b, "#3b4048")):
        for f in solid.intersect(plane).Faces():
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
    return {h["id"]: wire.distance(cq.Vertex.makeVertex(h["x"], h["y"], 0.0)) - hole_d(g, h) / 2
            for h in g["holes"]}


def generate(name, lp, up, upper, lower):
    cfg = TOWERS[name]
    tp = load_params(cfg["params"])
    lay = layout(tp, lp, up)
    g = build_geometry(name, tp, lp, up, lay)
    with open(cfg["geom"], "w", encoding="utf-8") as f:
        json.dump(g, f, indent=1)
    solid = tower_solid(g, tp, lp, up)
    # checks of the solid before the export: meshing for the STL file changes edge tolerances
    valid, pieces, bb, vol = solid.isValid(), len(solid.Solids()), solid.BoundingBox(), solid.Volume()
    stem = cfg["stem"]
    cq.exporters.export(cq.Workplane().add(solid), stem + ".step")
    cq.exporters.export(cq.Workplane().add(solid), stem + ".stl", tolerance=0.01, angularTolerance=0.1)
    write_dxf(g, stem + ".dxf")
    write_hole_table(g, cfg["table"])
    cam = lay["camber"]
    info = ["Origin: x = 0 centre line, y = 0 parting face of the bulkheads (height above it).",
            "Lay the template on the back face (wall side). T1 to T4: mounting holes, C1/C2: camber links,",
            "D1/D2: dampers" + (", B1/B2 and S1/S2: body post mounts." if "body_post" in lay else ".")
            + " All holes are at the positions of the stock tower."]
    for scale, suffix in ((1.0, ""), (0.97, "_print97")):
        template_a4(f"{stem}_1to1_A4{suffix}.pdf", name, g, scale, info)
    tower_b = to_bulkhead(solid, lp, up)
    drawing(cfg["drawing"], name, g, lay, tp, lp, up, tower_b, upper, lower)

    print(f"{name} shock tower: wrote {cfg['geom']}, {stem}.step/.stl/.dxf, hole table, templates, {cfg['drawing']}")
    print(f"  solid valid: {valid}, pieces: {pieces}, size {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm, "
          f"volume {vol / 1000:.2f} cm3, mass: " + ", ".join(f"{m} {vol / 1000 * rho:.1f} g" for m, rho in DENSITY.items()))
    dmp = lay["damper"]
    print(f"  damper holes: x +-{dmp[0]:.2f}, {dmp[1]:.2f} above the parting face (stock position)")
    if "body_post" in lay:
        bp, bs = lay["body_post"], lay["body_post_screw"]
        print(f"  body post bores: x +-{bp[0]:.2f}, {bp[1]:.2f} (Ø{tp['body_post_d']:g}) and {bs[1]:.2f} "
              f"(Ø{tp['body_post_screw_d']:g}) above the parting face (stock position)")
    print(f"  camber link holes: x +-{cam[0]:.2f}, {cam[1]:.2f} above the parting face "
          f"(stock position)")
    print("  checks")
    off = max(math.hypot(h["x"] - x, h["y"] - y) for h, (x, y) in zip(g["holes"][:4], lay["mount"]))
    print(f"    mounting holes T1 to T4 on the tapped holes of the upper bulkhead: largest offset {off:.4f} mm")
    print(f"    interference with the upper bulkhead: {tower_b.intersect(upper).Volume():.4f} mm3, "
          f"with the lower bulkhead: {tower_b.intersect(lower).Volume():.4f} mm3")
    contact = tower_b.translate(cq.Vector(0, 0.05, 0)).intersect(upper).Volume() / 0.05
    print(f"    contact area on the wall of the bulkhead: {contact:.0f} mm2")
    lo_, hi_ = 0.0, 2.0                                     # vertical gap above the block (bisection)
    for _ in range(12):
        mid = (lo_ + hi_) / 2
        if tower_b.translate(cq.Vector(0, 0, -mid)).intersect(upper).Volume() > 1e-6:
            hi_ = mid
        else:
            lo_ = mid
    print(f"    gap below the tower (block and root radius of the bulkhead): {lo_:.2f} mm")
    rod = 0.0
    for sx in (-1, 1):
        env = cq.Solid.makeCylinder(tp["rod_end_clearance_r"], tp["rod_end_depth"],
                                    cq.Vector(sx * cam[0], up["tower_face_y"], lp["axis_z"] + cam[1]), cq.Vector(0, 1, 0))
        rod += env.intersect(upper).Volume() + env.intersect(lower).Volume()
    print(f"    space for the rod ends behind the tower (radius {tp['rod_end_clearance_r']:g}, length "
          f"{tp['rod_end_depth']:g}): overlap with the bulkheads {rod:.4f} mm3")
    ed = edge_distances(g)
    print("    edge distance of the holes (outline without chamfers): "
          + ", ".join(f"{k} {v:.2f}" for k, v in ed.items() if k[1] == "1") + " mm")
    gaps = thin_gaps(solid)
    print(f"    check for thin slits and walls (faces closer than 0.25 mm): "
          f"{sum(1 for k in gaps if k[0] != 'narrow face')} slits or walls, "
          f"{sum(1 for k in gaps if k[0] == 'narrow face')} narrow faces")


def main():
    parser = argparse.ArgumentParser(description="Generate the speedrun shock towers of the T410R.")
    parser.add_argument("--tower", choices=["front", "rear", "all"], default="all")
    args = parser.parse_args()
    lp, up = load_params(LOWER), load_params(UPPER)
    os.makedirs(OUT, exist_ok=True)
    upper, lower = bulkhead_upper(lp, up).val(), bulkhead_lower(lp).val()
    for name in (["front", "rear"] if args.tower == "all" else [args.tower]):
        generate(name, lp, up, upper, lower)


if __name__ == "__main__":
    main()
