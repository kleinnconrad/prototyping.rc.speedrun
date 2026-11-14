"""Generate the lower wishbones of the Carten T410R (stock parts, not part of the speedrun design).

The wishbones (suspension arms NHA402, manual step 7 and parts list) are stock parts: they are
not part of the speedrun design and are not manufactured in this project. They are modelled for
the completeness of the build: the assembly of the speedrun chassis contains them, so that the
space beside the bulkheads can be checked.

* front arm: 2 pieces, End A, left and right (the same part, turned by 180 degrees about z)
* rear arm: 2 pieces, End B, left and right (the same part, turned by 180 degrees about z)
* inner hinge pin NHA423 3x42: 4 pieces, between the pivot blocks

The manual has no dimensions. The values come from the manual (screws and pins), from the
other parts of the model (pivot blocks, bulkheads), from photos of the owner or are assumptions;
each value has its source
in cad/stock_parts/wishbone/wishbone_parameters.json. The drawing names the measurements that
replace the assumptions with letters.

Arm coordinates: x from the axis of the inner hinge pin toward the wheel, y along the inner
hinge pin (y = 0 middle of the arm), z = 0 axis of the inner hinge pin.

Usage (from the root directory of the repository):
    python scripts/cad/generate_wishbones.py

The script writes the STEP and STL files of both arms and of the hinge pin and the drawing
photos/cad_wishbones_drawing.png. It checks the placed arms against the pivot blocks, the
bulkheads, the chassis plate and the diff outdrives, and the ends of the hinge pins against the
bores of the pivot blocks.

Requires the packages cadquery and matplotlib.
"""
import argparse
import math
import os
import sys

import numpy as np
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_bulkhead_lower import box, cyl_y, cyl_z, load_params  # noqa: E402
from generate_pivot_blocks import PARAMS as PIVOT, POSITIONS, PLATE_T, plate_holes  # noqa: E402
from generate_top_brace_speedrun import BULKHEAD_Y  # noqa: E402

PARAMS = "cad/stock_parts/wishbone/wishbone_parameters.json"
OUT = "cad/stock_parts/wishbone"
DRAWING = "photos/cad_wishbones_drawing.png"
PLATE_STEP = "cad/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_T410R_speedrun_wide_motor10.step"
KINDS = ("front", "rear")
END_OF = {"front": "front", "rear": "rear"}       # front arms at End A (front), rear arms at End B (rear)


def prism(pts, z0, z1):
    """Prism from a plan polygon (x, y) between z0 and z1."""
    return cq.Workplane("XY").polyline(pts).close().extrude(z1 - z0).val().translate(cq.Vector(0, 0, z0))


def prism_xz(pts, y0, y1):
    """Prism from a side view polygon (x, z) between y0 and y1."""
    s = cq.Workplane("XY").polyline(pts).close().extrude(y1 - y0).val()
    return s.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90).translate(cq.Vector(0, y1, 0))


def arm_solid(p, kind):
    """Solid of the front or rear arm in arm coordinates (cadquery Solid): frame without a floor."""
    length, half = p[f"{kind}_arm_length"], p["inner_width"] / 2
    yi, yo = p[f"{kind}_rail_y"]
    h = p["rail_h"] / 2
    gap, lo = p[f"{kind}_outer_gap"], p[f"{kind}_outer_lug_len"]
    b0, b1 = p[f"{kind}_inner_bar_x"]
    c0, c1 = p[f"{kind}_cross_x"]
    sx, ylug = p["shoulder_x"], half - p["inner_lug_len"]
    zd0, zd1 = p["droop_boss_z"]
    parts = []
    for sy in (1, -1):
        parts.append(cyl_y(p["inner_lug_d"] / 2, *sorted((sy * ylug, sy * half)), 0, 0))                # inner lug
        parts.append(prism([(0, sy * ylug), (0, sy * half), (sx, sy * yo), (sx, sy * yi)], -h, h))       # shoulder
        parts.append(box(sx - 0.01, length, *sorted((sy * yi, sy * yo)), -h, h))                         # side rail
        parts.append(cyl_y(p["outer_lug_d"] / 2, *sorted((sy * gap / 2, sy * (gap / 2 + lo))), length,
                           p["outer_pin_z"]))                                                            # outer lug
        parts.append(cyl_z(p["droop_boss_d"] / 2, zd0, zd1, p["droop_x"], sy * p[f"{kind}_droop_y"]))
    parts.append(box(b0, b1, -yi - 0.01, yi + 0.01, -h, h))                                              # inner cross bar
    parts.append(box(c0, c1, -yi - 0.01, yi + 0.01, -h, h))                                              # outer cross bar
    # X-shaped ribs in the open window between the cross bars
    rw = p["rib_w"] / 2
    for sy in (1, -1):
        ya, yb = sy * yi, -sy * yi
        ang = math.atan2(yb - ya, c0 - b1)
        dx, dy = -math.sin(ang) * rw, math.cos(ang) * rw
        parts.append(prism([(b1 + dx, ya + dy), (c0 + dx, yb + dy), (c0 - dx, yb - dy), (b1 - dx, ya - dy)],
                           -h, p["rib_top"]))
    # octagonal plate of the shock ball stud on side rail A (y < 0)
    q0, q1 = p[f"{kind}_shock_plate_x"]
    z0, z1 = p["shock_plate_z"]
    ch = p["shock_plate_chamfer"]
    parts.append(prism_xz([(q0 + ch, z0), (q1 - ch, z0), (q1, z0 + ch), (q1, z1 - ch), (q1 - ch, z1), (q0 + ch, z1),
                           (q0, z1 - ch), (q0, z0 + ch)], -yo, -yi))
    if kind == "front":
        # thin closed loop beyond the outer lugs
        l0, l1, ly, lh = p["front_loop"]
        zc = p["outer_pin_z"]
        for sy in (1, -1):
            parts.append(box(length, length + l1, *sorted((sy * (ly - 2.0), sy * ly)), zc - lh / 2, zc + lh / 2))
        parts.append(box(length + l0, length + l1, -ly, ly, zc - lh / 2, zc + lh / 2))
    s = None
    for part in parts:
        s = part if s is None else s.fuse(part)
    s = s.intersect(box(-10, length + 20, -half, half, -20, 20))           # nothing beyond the inner lugs in y
    # bores and holes
    s = s.cut(cyl_y(p["inner_pin_d"] / 2, -half - 1, half + 1, 0, 0))
    s = s.cut(cyl_y(p["outer_pin_d"] / 2, -half - 1, half + 1, length, p["outer_pin_z"]))
    for sy in (1, -1):
        s = s.cut(cyl_z(p["droop_tap_d"] / 2, zd0 - 1, zd1 + 1, p["droop_x"], sy * p[f"{kind}_droop_y"]))
    rb = p["ball_tap_d"] / 2
    for x, z in p[f"{kind}_shock_holes"]:
        s = s.cut(cyl_y(rb, -yo - 1, -yi + 0.01, x, z))
    for x, z in p[f"{kind}_sway_holes"]:
        s = s.cut(cyl_y(rb, yi - 0.01, yo + 1, x, z))
    return s.clean()


def pin_solid(p):
    """Inner hinge pin NHA423 along y, centred at y = 0 (arm coordinates)."""
    return cyl_y(p["inner_pin_d"] / 2, -p["inner_pin_length"] / 2, p["inner_pin_length"] / 2, 0, 0)


def pin_lines(pp=None):
    """Hinge pin lines on the speedrun chassis plate from the pivot blocks, per end and side:
    {(end, side): (origin (x, y, z), direction (dx, dy), bore bottoms (y0, y1))}. origin: point of
    the pin axis in the middle between the faces of the two pivot blocks."""
    pp = pp or load_params(PIVOT)
    holes = plate_holes()
    w, depth = pp["width"], pp["pin_bore_depth"]
    out = {}
    for end in ("rear", "front"):
        blocks = []
        for _, kind, (ha, hb), e in POSITIONS:
            if e != end:
                continue
            (xa, ya), (xb, yb) = holes[ha], holes[hb]
            xm, ym = (xa + xb) / 2, (ya + yb) / 2
            toward = 1 if BULKHEAD_Y[end] > ym else -1                 # side of the open bore
            blocks.append((xm, ym, pp[f"{kind}_pin_spacing"] / 2, ym + toward * w / 2,
                           ym + toward * (w / 2 - depth)))
        blocks.sort(key=lambda b: b[1])
        (xa, ya, ca, fa, ba), (xb, yb, cb, fb, bb) = blocks
        y_mid = (fa + fb) / 2
        for side in (1, -1):
            pa, pb = np.array([xa + side * ca, ya]), np.array([xb + side * cb, yb])
            d = (pb - pa) / np.linalg.norm(pb - pa)
            x_mid = pa[0] + (pb[0] - pa[0]) * (y_mid - ya) / (yb - ya)
            out[(end, side)] = ((x_mid, y_mid, PLATE_T + pp["pin_h"]), tuple(d), (ba, bb))
    return out


def placement(origin, d, side):
    """Rotation angle (degrees about z) and translation of the arm coordinates for one side:
    arm x outward and perpendicular to the hinge pin."""
    dx, dy = d
    phi = math.atan2(-dx, dy) if side > 0 else math.atan2(dx, -dy)
    return math.degrees(phi), cq.Vector(*origin)


def arms_in_plate(p=None, pp=None):
    """Arms and hinge pins placed on the speedrun chassis plate (coordinates of the chassis plate):
    list of (name, kind, solid), kind "arm" or "pin"."""
    p = p or load_params(PARAMS)
    arms = {k: arm_solid(p, k) for k in KINDS}
    pin = pin_solid(p)
    out = []
    lines = pin_lines(pp)
    for kind in KINDS:
        end = END_OF[kind]
        label = "End A" if end == "front" else "End B"
        for side, sname in ((1, "right"), (-1, "left")):
            origin, d, _ = lines[(end, side)]
            phi, t = placement(origin, d, side)
            for name, k, s in ((f"stock {kind} wishbone {label} {sname}", "arm", arms[kind]),
                               (f"stock hinge pin {label} {sname}", "pin", pin)):
                out.append((name, k, s.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), phi).translate(t)))
    return out


def tess(shape, tol=0.02):
    verts, idx = shape.tessellate(tol, 0.2)
    v = np.array([[q.x, q.y, q.z] for q in verts])
    return v[np.array(idx)]


def drawing(path, p, solids):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mesh_views import draw_mesh, iso_basis, subdivide

    def dim(ax, a, b, text, off=(0, 0), fs=8, color="#b42318"):
        ax.annotate("", a, b, arrowprops=dict(arrowstyle="<->", lw=0.8, color=color, shrinkA=0, shrinkB=0))
        ax.text((a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1], text, ha="center", va="center", fontsize=fs,
                color=color, fontweight="bold", bbox=dict(fc="white", ec="none", pad=0.4))

    def tag(ax, xy, text, to, color="#b42318"):
        ax.annotate(text, xy, to, fontsize=8, color=color, fontweight="bold", ha="center", va="center",
                    arrowprops=dict(arrowstyle="-", lw=0.6, color=color), bbox=dict(fc="white", ec="none", pad=0.4))

    fig = plt.figure(figsize=(16, 15.5))
    fig.suptitle("Carten T410R lower wishbones NHA402 with hinge pin NHA423: stock parts, not part of the speedrun "
                 "design (not verified, work in progress)", fontsize=12, y=0.992)
    half, h = p["inner_width"] / 2, p["rail_h"] / 2
    z0, z1 = p["shock_plate_z"]
    for row, kind in enumerate(KINDS):
        s = solids[kind]
        length = p[f"{kind}_arm_length"]
        yi, yo = p[f"{kind}_rail_y"]
        b0, b1 = p[f"{kind}_inner_bar_x"]
        c0, c1 = p[f"{kind}_cross_x"]
        q0, q1 = p[f"{kind}_shock_plate_x"]
        dx, dy = p["droop_x"], p[f"{kind}_droop_y"]
        t = subdivide(tess(s), 1.0)
        y0 = 0.655 - 0.365 * row
        n = "2 pieces: End A left and right" if kind == "front" else "2 pieces: End B left and right"
        # plan view
        ax = fig.add_axes([0.03, y0, 0.45, 0.29])
        draw_mesh(ax, t, "top", color=(0.5, 0.52, 0.58), depth_cue=0.35)
        gap, lo_len = p[f"{kind}_outer_gap"], p[f"{kind}_outer_lug_len"]
        dim(ax, (-6, -half), (-6, half), "A", off=(-1.6, 0))
        dim(ax, (-2.5, half - p["inner_lug_len"]), (-2.5, half), "B", off=(-1.6, 0))
        dim(ax, (0, -half - 4), (length, -half - 4), "J", off=(0, -1.6))
        dim(ax, (0, 1.2), (b0, 1.2), "G", off=(0, 1.3))
        dim(ax, (0, half + 3), (c0, half + 3), "P", off=(0, 1.4))
        dim(ax, (length - 9, -yo), (length - 9, yo), "E", off=(1.6, 3.0))
        dim(ax, ((b1 + c0) / 2, yi), ((b1 + c0) / 2, yo), "F", off=(1.6, 0))
        dim(ax, (length + 9, -gap / 2), (length + 9, gap / 2), "O", off=(1.8, 0))
        dim(ax, (length + 4, gap / 2), (length + 4, gap / 2 + lo_len), "M", off=(1.8, 0))
        dim(ax, (dx, 0), (dx, -dy), "I", off=(1.6, 0))
        dim(ax, (0, -half - 1.8), (dx, -half - 1.8), "H", off=(-4.5, 0))
        ax.plot([dx] * 2, [-dy, -half - 1.8], color="#b42318", lw=0.5)
        tag(ax, ((q0 + q1) / 2, -(yi + yo) / 2), "Q", ((q0 + q1) / 2, -half - 8.5))
        sx = p[f"{kind}_sway_holes"][0][0]
        tag(ax, (sx, (yi + yo) / 2), "S", (sx, half + 8.5))
        if kind == "front":
            l0, l1, ly, _ = p["front_loop"]
            dim(ax, (length, -1.5), (length + l1, -1.5), "T", off=(0, -1.4))
        ax.plot([-3, length + 8], [0, 0], color="#888888", lw=0.5, ls="-.")
        ax.set_xlim(-12, 70)
        ax.set_ylim(-half - 11, half + 11)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{kind.capitalize()} arm ({n}):\nplan view from above, inner hinge pin on the left", fontsize=10,
                     loc="left")
        # side view (along y): heights
        ax2 = fig.add_axes([0.5, y0 + 0.155, 0.48, 0.135])
        draw_mesh(ax2, t, "end_outer", color=(0.5, 0.52, 0.58), depth_cue=0.35)
        dim(ax2, (-5, -h), (-5, h), "D", off=(-1.6, 0))
        tag(ax2, (0, p["inner_lug_d"] / 2), "C", (2.5, z1 + 2.5))
        tag(ax2, (length, p["outer_pin_z"] + p["outer_lug_d"] / 2), "L", (length - 4, z1 + 2.5))
        tag(ax2, (length, p["outer_pin_z"]), "K", (length + 9, p["outer_pin_z"] + 3))
        tag(ax2, (length + p["outer_lug_d"] / 2, p["outer_pin_z"]), "N", (length + 9, p["outer_pin_z"] - 3))
        dim(ax2, (q0 - 2, z0), (q0 - 2, z1), "Q", off=(-1.8, 0))
        for x, z in p[f"{kind}_shock_holes"]:
            ax2.plot(x, z, "+", color="#b42318", ms=6, mew=0.8)
        tag(ax2, p[f"{kind}_shock_holes"][0], "R", (q1 + 4, z1 + 1.5))
        ax2.plot([-8, length + 8], [0, 0], color="#888888", lw=0.5, ls="-.")
        ax2.set_xlim(-12, 70)
        ax2.set_ylim(z0 - 2, z1 + 4.5)
        ax2.set_aspect("equal")
        ax2.axis("off")
        ax2.set_title("View along the hinge pin (heights; z = 0 axis of the inner hinge pin, dash-dot)", fontsize=10,
                      loc="left")
        # axonometric view
        ax3 = fig.add_axes([0.53, y0 - 0.005, 0.42, 0.16])
        draw_mesh(ax3, t, iso_basis(-120, 32), color=(0.5, 0.52, 0.58), depth_cue=0.35)
        ax3.set_aspect("equal")
        ax3.autoscale_view()
        ax3.axis("off")
    # list of the measurements
    rows = [("A", "Length along the inner hinge pin over the outer faces of the inner lugs", "inner_width"),
            ("B", "Length of one inner lug along the hinge pin", "inner_lug_len"),
            ("C", "Outer diameter of the inner lugs", "inner_lug_d"),
            ("D", "Height of the side rails (and of the cross bars)", "rail_h"),
            ("E", "Width over the outer faces of the side rails", "{k}_rail_y:E"),
            ("F", "Width of one side rail", "{k}_rail_y:F"),
            ("G", "Inner hinge pin to the inner cross bar at the end of the notch between the inner lugs (start, end)",
             "{k}_inner_bar_x"),
            ("H", "Droop screw bosses: distance of the axis from the axis of the inner hinge pin", "droop_x"),
            ("I", "Droop screw bosses: distance of the axis from the middle of the arm", "{k}_droop_y"),
            ("J", "Inner hinge pin to outer hinge pin, axis to axis (outer edges of the bores minus 1 bore diameter)",
             "{k}_arm_length"),
            ("K", "Diameter of the outer hinge pin", "outer_pin_d"),
            ("L", "Outer diameter of the outer lugs", "outer_lug_d"),
            ("M", "Length of one outer lug along the outer hinge pin", "{k}_outer_lug_len"),
            ("N", "Height of the outer hinge pin above the inner hinge pin (arm on a flat surface)", "outer_pin_z"),
            ("O", "Gap between the outer lugs (front: C-hub, rear: hub carrier)", "{k}_outer_gap"),
            ("P", "Inner hinge pin to the outer cross bar (start, end)", "{k}_cross_x"),
            ("Q", "Octagonal plate of the shock ball stud: start, end (x); bottom, top (z)", "{k}_shock_plate_x:Q"),
            ("R", "Holes of the shock ball stud (x, z of each hole)", "{k}_shock_holes"),
            ("S", "Holes of the sway bar ball stud (x, z of each hole)", "{k}_sway_holes"),
            ("T", "Front arm, loop beyond the outer lugs: end bar from, to (beyond the outer pin), half width, height",
             "front_loop")]

    def fmt(v):
        if isinstance(v, list):
            return "/".join(fmt(x) for x in v) if not isinstance(v[0], list) else "  ".join(f"({fmt(x)})" for x in v)
        return f"{v:g}"
    def value(key, k):
        key, _, mode = key.partition(":")
        v = p[key.format(k=k)]
        if mode == "E":
            return fmt(2 * v[1])
        if mode == "F":
            return fmt(v[1] - v[0])
        if mode == "Q":
            return fmt(v) + "; " + fmt(p["shock_plate_z"])
        return fmt(v)
    lines = []
    for letter, text, key in rows:
        if "{k}" in key:
            val = f"front {value(key, 'front')}; rear {value(key, 'rear')}"
        else:
            val = value(key, "")
        lines.append(f"{letter}   {text}:  {val}")
    fig.text(0.03, 0.005, "Measurements for the caliper (current value in mm in the model: estimates from the photos "
             "or assumptions, except A and C, which follow from the pivot blocks and the bulkhead):\n" + "\n".join(lines),
             fontsize=8.5, va="bottom", family="DejaVu Sans", linespacing=1.45)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Generate the wishbones of the T410R (stock parts, not part of the speedrun design).")
    parser.parse_args()
    p, pp = load_params(PARAMS), load_params(PIVOT)
    solids = {k: arm_solid(p, k) for k in KINDS}
    files = [(f"wishbone_{k}_T410R", solids[k]) for k in KINDS] + [("hinge_pin_3x42_NHA423", pin_solid(p))]
    for stem, s in files:
        valid, bb, vol = s.isValid(), s.BoundingBox(), s.Volume()
        cq.exporters.export(cq.Workplane().add(s), f"{OUT}/{stem}.step")
        cq.exporters.export(cq.Workplane().add(s), f"{OUT}/{stem}.stl", tolerance=0.01, angularTolerance=0.1)
        print(f"{stem}: wrote {OUT}/{stem}.step/.stl, solid valid: {valid}, {len(s.Solids())} solid(s), size "
              f"{bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm, volume {vol / 1000:.2f} cm3")
    drawing(DRAWING, p, solids)
    print(f"Wrote {DRAWING}")

    # checks on the speedrun chassis plate
    from generate_pivot_blocks import blocks_in_plate, bulkheads_at
    from generate_driveshaft import parts_in_plate as drive_parts
    lp, up = load_params("cad/bulkhead/bulkhead_lower_parameters.json"), load_params("cad/bulkhead/bulkhead_upper_parameters.json")
    plate = cq.importers.importStep(PLATE_STEP).val()
    others = {"rear": [], "front": []}
    for name, _, s, _ in blocks_in_plate(pp):
        others["rear" if "End B" in name else "front"].append((f"pivot block {name}", s))
    for end in ("rear", "front"):
        for label, s in zip(("lower bulkhead", "upper bulkhead"), bulkheads_at(lp, up, end)):
            others[end].append((label, s))
    for name, kind, s in drive_parts():
        if "outdrive" in name:
            others["rear" if s.BoundingBox().ymin < 150 else "front"].append((name, s))
    lines = pin_lines(pp)
    print("checks (arms on the speedrun chassis plate)")
    for name, kind, s in arms_in_plate(p, pp):
        end = "front" if "End A" in name else "rear"
        res = []
        for label, o in others[end] + [("chassis plate", plate)]:
            if s.BoundingBox().xmax < o.BoundingBox().xmin - 5 or s.BoundingBox().xmin > o.BoundingBox().xmax + 5:
                continue
            inter = s.intersect(o).Volume()
            dist = s.distance(o)
            dist = dist[0] if isinstance(dist, tuple) else dist
            res.append((dist, f"{label}: overlap {inter:.4f} mm3, distance {dist:.2f}"))
        res.sort()
        print(f"  {name}: " + "; ".join(r for _, r in res[:3]))
    for (end, side), (origin, d, (b0, b1)) in sorted(lines.items()):
        half = p["inner_pin_length"] / 2
        e0 = (origin[1] - b0) / d[1] - half                  # pivot blocks sorted by y, d[1] > 0
        e1 = (b1 - origin[1]) / d[1] - half
        toe = math.degrees(math.atan2(abs(d[0]), d[1]))
        print(f"  hinge pin {end} {'right' if side > 0 else 'left'}: axis at x = {origin[0]:.2f}, y = {origin[1]:.2f}, "
              f"z = {origin[2]:.2f}; angle to the car axis {toe:.2f} deg; play of the ends to the bottoms of the "
              f"bores {e0:.2f} / {e1:.2f} mm")


if __name__ == "__main__":
    main()
