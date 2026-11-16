"""Generate the speedrun front splitter set (End A): body post mount, front splitter and splitter holder plate.

Speedrun parts, designed in this project for the speedruns. The car runs without the front foam bumper: the front
splitter takes its place and shows below the front edge of the body. The body post mount follows the original mount
of the T410R (photos and measurements of the owner), the holder plate follows the carbon plate on top of the original
foam bumper (photo of the owner).

* Body post mount (plastic, 3D print) on the holes H34, H35 and H36 at the front end of the speedrun chassis plate:
  deck on the top face of the chassis plate with a pocket in the form of the front end of the plate (the overhang
  around the plate holds the part against turning); in front of the plate the part is cranked down by the thickness of
  the plate, a ramp on the top face follows the front contour of the plate. Screwed to the chassis plate with
  countersunk screws M3x6 from below through H34, H35 and H36 (H36 without a boss). Bosses on H34/H35: a base that
  carries the splitter and a pin through the splitter, tapped M3 for the screw from below and the screw from above;
  their height follows from the screws (stack_screws). Raised ears with a hexagon recess: press fit of the body
  posts, each held by a countersunk screw M3x6 from below.
* Front splitter (carbon sheet 2.0) on the bases of the bosses and on the ears; the pins pass through its holes,
  hexagon holes fit over the body posts. Front end 90 mm ahead of the axis H34-H35 (owner). Outer form (owner): the
  form of the lower front edge of the body, moved forward to this front end, from tip to tip; the body sits on the
  splitter, which shows 15 to 20 mm ahead of the body. Full width only at the front, where the splitter closes the
  space between the chassis front and the body: concave rear edges, deeper beside the mount and narrower toward the
  tips (variant C of the design suggestions, owner), clear of the front tyres at full steering lock.
* Splitter holder plate (carbon sheet 2.0): outline as the mount, on top of the splitter, round holes around the body
  posts. Screws M3x6 from above through the holder plate into the pins clamp the splitter.

All values with their source: cad/front_splitter/front_splitter_parameters.json. Most dimensions of the mount
are estimates from the photos, the front edge of the body is an assumption; the measurement sheet lists them
(scripts/cad/generate_front_splitter_measurement_sheet.py).

Usage (from the root directory of the repository):
    python scripts/cad/generate_front_splitter.py [--no-check]

Outputs (chassis plate coordinates):
* cad/front_splitter/body_post_mount_end_a.step and .stl
* cad/front_splitter/front_splitter_end_a.step and .stl (position in the car: on the bosses of the mount), .dxf
  and _geometry.json (geometry data in the format of the chassis plates: z = 0 is the bottom face)
* cad/front_splitter/front_splitter_end_a_test_print.stl: middle part of the splitter over the mount for a test print
  of the fit (bottom face at z = 0)
* cad/front_splitter/front_splitter_holder_plate_end_a.step and .stl (on the splitter), .dxf and _geometry.json
* photos/cad_front_splitter_drawing.png
* alternative version, the body post mount enlarged to the splitter (one part, no separate splitter, no holder
  plate): cad/front_splitter/front_splitter_one_piece_end_a.step and .stl (position in the car), _test_print.stl
  (middle part, bottom face on the print bed), photos/cad_front_splitter_one_piece_drawing.png

Checks: holes of the mount and of the splitter against the holes of the chassis plate, overlap of the mount with the
chassis plate, clearance of the splitter and the mount to the front tyres over the steering angle (static ride
height and with droop), overlap with the parts of the assembly at End A (cad/assembly/speedrun_chassis_T410R.step).
The option --no-check skips the tyre check and the assembly check.

Requires the packages cadquery, ezdxf and matplotlib.
"""
import argparse
import json
import math
import os
import sys
import textwrap

import numpy as np
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_bulkhead_lower import cyl_z, load_params  # noqa: E402
from generate_dxf import build_dxf  # noqa: E402
from generate_solid import plate_solid, wire_from_prims  # noqa: E402

PARAMS = "cad/front_splitter/front_splitter_parameters.json"
PLATE_GEOM = "cad/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_speedrun_wide_motor10_geometry.json"
PLATE_STEP = "cad/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_T410R_speedrun_wide_motor10.step"
ASSEMBLY = "cad/assembly/speedrun_chassis_T410R.step"
OUT = "cad/front_splitter"
MOUNT_STEM = f"{OUT}/body_post_mount_end_a"
SPLITTER_STEM = f"{OUT}/front_splitter_end_a"
HOLDER_STEM = f"{OUT}/front_splitter_holder_plate_end_a"
DRAWING = "photos/cad_front_splitter_drawing.png"
ONE_PIECE_STEM = f"{OUT}/front_splitter_one_piece_end_a"
ONE_PIECE_DRAWING = "photos/cad_front_splitter_one_piece_drawing.png"
PLATE_T = 2.0
OWN_PREFIXES = ("speedrun_front_body_post_mount", "body_post", "speedrun_front_splitter",
                "speedrun_splitter_holder_plate")                             # names of these parts in the assembly


# ------------------------------------------------------------------ helpers
def plate_geometry():
    with open(PLATE_GEOM, encoding="utf-8") as f:
        return json.load(f)


def plate_holes(geom=None):
    geom = geom or plate_geometry()
    return {h["id"]: (h["x"], h["y"]) for h in geom["holes"]}


def hex_z(af, z0, z1, x, y):
    """Hexagon prism along z (across flats af, two flats parallel to x)."""
    rc = af / math.sqrt(3)
    pts = [cq.Vector(x + rc * math.cos(math.radians(a)), y + rc * math.sin(math.radians(a)), z0)
           for a in range(0, 360, 60)]
    return cq.Solid.extrudeLinear(cq.Wire.makePolygon(pts, close=True), [], cq.Vector(0, 0, z1 - z0))


def poly_wire(P, z):
    return cq.Wire.makePolygon([cq.Vector(float(x), float(y), z) for x, y in P], close=True)


def prism(P, z0, z1):
    return cq.Solid.extrudeLinear(poly_wire(P, z0), [], cq.Vector(0, 0, z1 - z0))


def arc_samples(prim, step=0.5):
    """Points of an arc primitive from the start (end excluded)."""
    c = np.array(prim["center"])
    a0, am, a1 = (math.atan2(q[1] - c[1], q[0] - c[0]) for q in (prim["start"], prim["mid"], prim["end"]))
    ccw = (am - a0) % (2 * math.pi) < (a1 - a0) % (2 * math.pi)
    sweep = (a1 - a0) % (2 * math.pi) if ccw else -((a0 - a1) % (2 * math.pi))
    n = max(2, int(math.ceil(abs(sweep) * prim["r"] / step)))
    return [c + prim["r"] * np.array([math.cos(a0 + sweep * k / n), math.sin(a0 + sweep * k / n)]) for k in range(n)]


def area(P):
    return 0.5 * float(np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]))


def plate_front_contour(geom, y_cut=300.0):
    """Closed polygon (counterclockwise) of the chassis plate for y >= y_cut (the front end at End A)."""
    pts = []
    for prim in geom["outline"]:
        pts += [np.array(prim["start"], float)] if prim["type"] == "line" else arc_samples(prim)
    P, out = np.array(pts), []
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        if a[1] >= y_cut:
            out.append(a)
        if (a[1] >= y_cut) != (b[1] >= y_cut):
            out.append(a + (y_cut - a[1]) / (b[1] - a[1]) * (b - a))
    Q = np.array(out)
    Q = Q[::-1] if area(Q) < 0 else Q
    keep = [Q[0]]
    for q in Q[1:]:
        if np.hypot(*(q - keep[-1])) > 1e-3:
            keep.append(q)
    if np.hypot(*(keep[0] - keep[-1])) < 1e-3:
        keep.pop()
    return np.array(keep)


def offset(P, d):
    """Offset of a counterclockwise polygon by d (outward for d > 0), mitred at the vertices."""
    out = []
    for i in range(len(P)):
        a, b, c = P[i - 1], P[i], P[(i + 1) % len(P)]
        n1 = np.array([b[1] - a[1], a[0] - b[0]]) / np.hypot(*(b - a))
        n2 = np.array([c[1] - b[1], b[0] - c[0]]) / np.hypot(*(c - b))
        m = (n1 + n2) / np.linalg.norm(n1 + n2)
        out.append(b + m * d / max(float(m @ n1), 0.2))
    return np.array(out)


def filleted_polygon(V, radii):
    """Outline primitives (lines and arcs, counterclockwise) of the polygon V with a fillet of radius radii[i] at
    each vertex, in the format of the geometry data of the chassis plates."""
    V = [np.asarray(v, float) for v in V]
    n = len(V)
    corners = []
    for i in range(n):
        a, b, c = V[i - 1], V[i], V[(i + 1) % n]
        din, dout = (b - a) / np.linalg.norm(b - a), (c - b) / np.linalg.norm(c - b)
        r = radii[i]
        theta = math.acos(max(-1.0, min(1.0, float(din @ dout))))
        t = r * math.tan(theta / 2)
        left = din[0] * dout[1] - din[1] * dout[0] > 0
        nrm = np.array([-din[1], din[0]]) if left else np.array([din[1], -din[0]])
        t1, t2 = b - din * t, b + dout * t
        centre = t1 + nrm * r
        mid = centre + r * (b - centre) / np.linalg.norm(b - centre) if r > 0 else b
        corners.append((t1, t2, centre, mid, r, t))
    prims = []
    for i in range(n):
        t1, t2, centre, mid, r, t = corners[i]
        nxt = corners[(i + 1) % n]
        if t + nxt[5] > np.linalg.norm(V[(i + 1) % n] - V[i]) + 1e-9:
            raise ValueError(f"radii at the vertices {i} and {(i + 1) % n} of the splitter outline do not fit on "
                             "the edge")
        if r > 0:
            prims.append({"type": "arc", "start": t1.round(4).tolist(), "mid": mid.round(4).tolist(),
                          "end": t2.round(4).tolist(), "center": centre.round(4).tolist(), "r": float(r)})
        prims.append({"type": "line", "start": t2.round(4).tolist(), "end": nxt[0].round(4).tolist()})
    return prims


# ------------------------------------------------------------------ parts
def mount_outline(p):
    """Closed outline (list of points) of the mount: straight rear edge, spline through the outline points."""
    half = [tuple(q) for q in p["mount_outline"]]
    return half + [(-x, y) for x, y in reversed(half[:-1])]


def mount_outline_wire(p, z=0.0):
    """Outline of the mount at the height z: straight rear edge and one spline per half (horizontal tangent on the
    centre line), symmetric to x = 0."""
    half = [cq.Vector(x, y, z) for x, y in p["mount_outline"]]
    t0 = (half[1] - half[0]).normalized()
    right = cq.Edge.makeSpline(half, tangents=[t0, cq.Vector(-1, 0, 0)], scale=False)     # unit tangents: no loops
    left = right.mirror("YZ")
    rear = cq.Edge.makeLine(cq.Vector(-half[0].x, half[0].y, z), half[0])
    return cq.Wire.assembleEdges([rear, right, left])


def mount_outline_points(p, step=0.5):
    """Points of the outline of the mount (for drawings)."""
    w = mount_outline_wire(p)
    n = int(w.Length() / step)
    return np.array([[q.x, q.y] for q in (w.positionAt(t) for t in np.linspace(0, 1, n, endpoint=False))])


def mount_solid(p, geom=None):
    """Body post mount in chassis plate coordinates (cadquery Solid)."""
    geom = geom or plate_geometry()
    holes = plate_holes(geom)
    cl, dt, ft, rw = p["pocket_clearance"], p["deck_t"], p["front_t"], p["ramp_w"]
    z_deck = PLATE_T + dt
    wire = mount_outline_wire(p)

    def outline(h):
        return cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, h))
    C = plate_front_contour(geom)
    # deck and ramp: the contour of the plate (with the clearance of the pocket) at the top of the deck, widened by
    # the width of the ramp at the top of the front part (tapered prism)
    ramp = cq.Solid.extrudeLinear(poly_wire(offset(C, cl + rw), ft), [], cq.Vector(0, 0, z_deck - ft),
                                  taper=math.degrees(math.atan(rw / (z_deck - ft))))
    body = outline(ft).fuse(ramp.intersect(outline(z_deck + 1)))
    body = body.cut(prism(offset(C, cl), -1.0, PLATE_T))                     # pocket: overhang around the plate
    d_pin, d_base = p["collar"]
    tap = p["stack_screws"][3] / 2
    zs = splitter_z(p)
    for hid in ("H34", "H35"):
        x, y = holes[hid]
        # boss: base from the deck to the bottom face of the splitter, pin through the splitter (0.1 below its top)
        body = body.fuse(cyl_z(d_base / 2, z_deck - 0.5, zs, x, y))
        body = body.fuse(cyl_z(d_pin / 2, zs - 0.5, zs + p["splitter_t"] - 0.1, x, y))
        body = body.cut(cyl_z(tap, -1, zs + p["splitter_t"] + 1, x, y))           # tapped M3: from below and above
    x, y = holes["H36"]
    body = body.cut(cyl_z(tap, -1, z_deck + 1, x, y))                           # H36: tapped M3, no boss
    ed, eh, eaf, edep = p["ear_boss"]
    ex, ey = p["ear_holes"]
    r, rc = p["screw_hole_d"] / 2, p["ear_csk"] / 2
    for sx in (1, -1):
        # ear boss up to the bottom face of the splitter; hexagon recess from the original bottom (eh - edep) to the top
        body = body.fuse(cyl_z(ed / 2, ft - 0.5, zs, sx * ex, ey))
        body = body.cut(hex_z(eaf, eh - edep, zs + 1, sx * ex, ey))
        body = body.cut(cyl_z(r, -1, zs + 1, sx * ex, ey))
        # countersink (90 degrees) on the bottom face for the screw M3x6 of the body post
        body = body.cut(cq.Solid.makeCone(rc + 0.5, r, rc - r + 0.5, cq.Vector(sx * ex, ey, -0.5), cq.Vector(0, 0, 1)))
    return body.clean()


def stack(p):
    """Heights of the stack on H34/H35 from the screws (stack_screws): tip of the screw from below, bottom face of the
    splitter, top face of the holder plate, tip of the screw from above."""
    l_bot, l_top, gap, _ = p["stack_screws"]
    t_s, t_h = p["splitter_t"], p["holder_plate"][0]
    zs = max(PLATE_T + p["deck_t"], l_bot + gap + l_top - t_s - t_h)
    z_top = zs + t_s + t_h
    return {"tip_bottom": l_bot, "splitter": zs, "holder_top": z_top, "tip_top": z_top - l_top}


def yb_gap(p):
    """Distance of the front end of the splitter ahead of the lower front edge of the body (owner: 15 to 20)."""
    return float(np.mean(p["body_overhang"]))


def splitter_z(p):
    """Height of the bottom face of the splitter: on the bases of the bosses on H34/H35 and on the ears (stack)."""
    return stack(p)["splitter"]


def posts(p):
    """Body posts (stock parts) in the ears: hexagon section from the bottom of the recess (into the hexagon hole of
    the splitter), round post above it up to the given length above the splitter; list of (name, solid)."""
    ed, eh, eaf, edep = p["ear_boss"]
    ex, ey = p["ear_holes"]
    pd, hl, pl, pb = p["body_post"]
    z0 = eh - edep
    zt = splitter_z(p) + p["splitter_t"] + pl
    out = []
    for sx, side in ((1, "right"), (-1, "left")):
        x = sx * ex
        s = hex_z(eaf, z0, z0 + hl, x, ey).fuse(cyl_z(pd / 2, z0 + hl - 0.5, zt, x, ey))
        out.append((f"body post End A {side}", s.cut(cyl_z(pb / 2, z0 - 1, zt + 1, x, ey)).clean()))
    return out


def offset_open(line, d):
    """Offset of an open polyline (from left to right) by d to its left (toward the front for d > 0), mitred."""
    out = []
    for i in range(len(line)):
        segs = ([(line[i - 1], line[i])] if i > 0 else []) + ([(line[i], line[i + 1])] if i < len(line) - 1 else [])
        ns = []
        for a_, b_ in segs:
            t = (b_ - a_) / np.linalg.norm(b_ - a_)
            ns.append(np.array([-t[1], t[0]]))
        m = sum(ns) / np.linalg.norm(sum(ns))
        out.append(line[i] + m * d / float(m @ ns[0]))
    return np.array(out)


def front_form_line(p):
    """Form of the front edge (front_form, both halves, from the left to the right end)."""
    half = [tuple(q) for q in p["front_form"]]
    return np.array([(-x, y) for x, y in reversed(half[1:])] + half, float)


def outer_form(p):
    """Front edge of the splitter as a polyline (both halves): front_form offset by front_form_offset and moved
    forward, so that its centre lies splitter_front_distance ahead of the axis H34-H35."""
    shift = plate_holes()["H34"][1] + p["splitter_front_distance"] - (p["front_form"][0][1] + p["front_form_offset"])
    return offset_open(front_form_line(p), p["front_form_offset"]) + np.array([0.0, shift])


def splitter_vertices(p):
    """Vertices (counterclockwise) and fillet radii of the splitter outline. Outer form (owner): the form of the lower
    front edge of the body (front_form), offset outward and moved forward, so that the front end lies
    splitter_front_distance ahead of the axis H34-H35, from tip to tip. Rear edge: straight in the middle, then
    concave around the front corners of the tyres at full steering lock to the tips (splitter_rear_outline)."""
    off = outer_form(p)
    n_half = len(p["front_form"])
    front = [(float(x), float(y)) for x, y in off[n_half - 1:]]       # centre line to the right tip
    radii = list(reversed(p["splitter_front_radii"]))               # centre line to the tip
    rear = [(x, y, r) for x, y, r in p["splitter_rear_outline"]]
    right = rear + [(x, y, r) for (x, y), r in zip(reversed(front[1:]), reversed(radii[1:]))]
    V = [(x, y) for x, y, _ in right] + [front[0]] + [(-x, y) for x, y, _ in reversed(right)]
    R = [r for _, _, r in right] + [radii[0]] + [r for _, _, r in reversed(right)]
    return V, R


def body_edge(p, overhang=None):
    """Lower front edge of the body (both halves, from left to right, points every 0.5): the outer form of the
    splitter offset inward by the overhang (body_overhang, mean of 15 and 20: the body sits on the splitter)."""
    over = float(np.mean(p["body_overhang"])) if overhang is None else overhang
    line = offset_open(outer_form(p), -over)
    dense = [line[0]]
    for a_, b_ in zip(line[:-1], line[1:]):
        n = max(2, int(np.linalg.norm(b_ - a_) / 0.5))
        dense += [a_ + (b_ - a_) * k / n for k in range(1, n + 1)]
    return np.array(dense)


def circle_prims(x, y, r):
    return [{"type": "arc", "start": [x + r, y], "mid": [x, y + r], "end": [x - r, y], "center": [x, y], "r": r},
            {"type": "arc", "start": [x - r, y], "mid": [x, y - r], "end": [x + r, y], "center": [x, y], "r": r}]


def hex_prims(af, x, y):
    """Hexagon (across flats af, two flats parallel to x, as hex_z) as line primitives."""
    rc = af / math.sqrt(3)
    pts = [[round(x + rc * math.cos(math.radians(a)), 4), round(y + rc * math.sin(math.radians(a)), 4)]
           for a in range(0, 360, 60)]
    return [{"type": "line", "start": pts[i], "end": pts[(i + 1) % 6]} for i in range(6)]


def splitter_geometry(p, holes=None):
    """Geometry data of the splitter (format of the chassis plates; z = 0 bottom face of the splitter): outline, holes
    S1/S2 on H34/H35 over the collars of the mount, hexagon holes over the body posts (cutouts)."""
    holes = holes or plate_holes()
    V, R = splitter_vertices(p)
    ex, ey = p["ear_holes"]
    d_c, c_hex = p["splitter_holes"]
    return {"basis": "speedrun front splitter End A (generate_front_splitter.py): chassis plate coordinates x, y; "
                     "z = 0 bottom face of the splitter (in the car on the bosses and the ears of the body post "
                     f"mount, z = {splitter_z(p):g}). S1/S2 on H34/H35 over the pins of the bosses, hexagon holes over "
                     "the body posts in the ears.",
            "units": "mm", "thickness": p["splitter_t"], "hole_d": p["collar"][0] + d_c, "csk_d": 0.0,
            "csk_angle": 90.0, "csk_side": "none", "outline": filleted_polygon(V, R),
            "cutouts": {"post_right": hex_prims(p["ear_boss"][2] + c_hex, ex, ey),
                        "post_left": hex_prims(p["ear_boss"][2] + c_hex, -ex, ey)},
            "holes": [{"id": i, "x": round(float(x), 3), "y": round(float(y), 3)}
                      for i, (x, y) in (("S1", holes["H34"]), ("S2", holes["H35"]))]}


def splitter_solid(p, geometry=None):
    """Splitter in chassis plate coordinates (on the bosses and the ears of the mount)."""
    geometry = geometry or splitter_geometry(p)
    return plate_solid(geometry).val().translate(cq.Vector(0, 0, splitter_z(p)))


def holder_z(p):
    """Height of the bottom face of the holder plate: on the top face of the splitter."""
    return splitter_z(p) + p["splitter_t"]


def holder_geometry(p, holes=None):
    """Geometry data of the splitter holder plate (format of the chassis plates; z = 0 bottom face): outline as the
    mount (spline as lines of 0.5 mm), holes 3.2 on H34/H35, round holes around the body posts."""
    holes = holes or plate_holes()
    P = mount_outline_points(p, 0.5)
    t, c_post = p["holder_plate"]
    ex, ey = p["ear_holes"]
    pts = [[round(float(x), 4), round(float(y), 4)] for x, y in P]
    return {"basis": "splitter holder plate End A (generate_front_splitter.py): chassis plate coordinates x, y; z = 0 "
                     f"bottom face (in the car on the splitter, z = {holder_z(p):g}). Outline as the body post mount. "
                     "U1/U2 on H34/H35 (screws M3 from above into the bosses), round holes around the body posts.",
            "units": "mm", "thickness": t, "hole_d": p["screw_hole_d"], "csk_d": 0.0, "csk_angle": 90.0,
            "csk_side": "none",
            "outline": [{"type": "line", "start": pts[i], "end": pts[(i + 1) % len(pts)]} for i in range(len(pts))],
            "cutouts": {"post_right": circle_prims(ex, ey, (p["body_post"][0] + c_post) / 2),
                        "post_left": circle_prims(-ex, ey, (p["body_post"][0] + c_post) / 2)},
            "holes": [{"id": i, "x": round(float(x), 3), "y": round(float(y), 3)}
                      for i, (x, y) in (("U1", holes["H34"]), ("U2", holes["H35"]))]}


def holder_solid(p, geometry=None):
    """Splitter holder plate in chassis plate coordinates (on the splitter)."""
    geometry = geometry or holder_geometry(p)
    return plate_solid(geometry).val().translate(cq.Vector(0, 0, holder_z(p)))


def splitter_test_print(p, splitter=None):
    """Test print of the splitter: the middle part over the mount (holes over the pins, hexagon holes over the body
    posts), cut out of the splitter with a rectangle (splitter_test_print), bottom face at z = 0 for the print bed."""
    splitter = splitter or splitter_solid(p)
    hw, y0, y1 = p["splitter_test_print"]
    zs = splitter_z(p)
    box = cq.Solid.makeBox(2 * hw, y1 - y0, p["splitter_t"] + 2, cq.Vector(-hw, y0, zs - 1))
    return splitter.intersect(box).translate(cq.Vector(0, 0, -zs))


def one_piece_solid(p, geom=None):
    """Alternative version: the body post mount is enlarged to the splitter, one part, no separate splitter and no
    holder plate. The mount as measured by the owner (deck on the chassis plate, pocket and side lips around its front
    end, ramp, front part 3.0 thick with its bottom face flush with the bottom face of the plate, ears with the hexagon
    recesses of the body posts); its front part is extended to the outline of the splitter (behind the rear edge of the
    mount only beside the chassis plate). Bosses on H34/H35 for the countersunk screws M3x6 from below (blind tapped
    holes), H36 tapped through the deck."""
    geom = geom or plate_geometry()
    holes = plate_holes(geom)
    cl, dt, ft, rw = p["pocket_clearance"], p["deck_t"], p["front_t"], p["ramp_w"]
    z_deck = PLATE_T + dt
    wire = mount_outline_wire(p)

    def mount_prism(h):
        return cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, h))
    C = plate_front_contour(geom)
    ramp = cq.Solid.extrudeLinear(poly_wire(offset(C, cl + rw), ft), [], cq.Vector(0, 0, z_deck - ft),
                                  taper=math.degrees(math.atan(rw / (z_deck - ft))))
    # front part of the mount enlarged to the outline of the splitter (not behind the rear edge of the mount)
    split = wire_from_prims(splitter_geometry(p, holes)["outline"]).extrude(ft).val()
    split = split.intersect(cq.Solid.makeBox(400, 200, ft + 2, cq.Vector(-200, p["mount_rear_y"], -1)))
    body = mount_prism(ft).fuse(split).fuse(ramp.intersect(mount_prism(z_deck + 1)))
    body = body.cut(prism(offset(C, cl), -1.0, PLATE_T))                     # pocket: overhang around the plate
    tap = p["stack_screws"][3] / 2
    depth, d_boss, z_boss = p["stack_screws"][0] + p["one_piece"][0], p["collar"][0], p["one_piece"][2]
    for hid in ("H34", "H35"):
        x, y = holes[hid]
        body = body.fuse(cyl_z(d_boss / 2, z_deck - 0.5, z_boss, x, y))        # boss for the screw M3x6 from below
        body = body.cut(cyl_z(tap, -1, depth, x, y))                           # blind tapped hole M3
    x, y = holes["H36"]
    body = body.cut(cyl_z(tap, -1, z_deck + 1, x, y))                           # H36: tapped M3, no boss
    ed, eh, eaf, edep = p["ear_boss"]
    ex, ey = p["ear_holes"]
    r, rc = p["screw_hole_d"] / 2, p["ear_csk"] / 2
    for sx in (1, -1):
        body = body.fuse(cyl_z(ed / 2, ft - 0.5, eh, sx * ex, ey))            # ear boss as the original part
        body = body.cut(hex_z(eaf, eh - edep, eh + 1, sx * ex, ey))
        body = body.cut(cyl_z(r, -1, eh + 1, sx * ex, ey))
        body = body.cut(cq.Solid.makeCone(rc + 0.5, r, rc - r + 0.5, cq.Vector(sx * ex, ey, -0.5), cq.Vector(0, 0, 1)))
    return body.clean()


def one_piece_posts(p):
    """Body posts in the ears of the one-piece version: hexagon section from the bottom of the recess (8 long), round
    post above it (assembly and drawing only)."""
    ed, eh, eaf, edep = p["ear_boss"]
    ex, ey = p["ear_holes"]
    pd, hl, pl, pb = p["body_post"]
    z0 = eh - edep
    out = []
    for sx in (1, -1):
        x = sx * ex
        s = hex_z(eaf, z0, z0 + hl, x, ey).fuse(cyl_z(pd / 2, z0 + hl - 0.5, z0 + hl + pl, x, ey))
        out.append(s.cut(cyl_z(pb / 2, z0 - 1, z0 + hl + pl + 1, x, ey)).clean())
    return out


def one_piece_test_print(p, solid=None):
    """Test print of the one-piece version: the middle part over the chassis plate and the ears (splitter_test_print),
    bottom face on the print bed (the deck over the pocket is printed as a bridge)."""
    solid = solid or one_piece_solid(p)
    hw, y0, y1 = p["splitter_test_print"]
    return solid.intersect(cq.Solid.makeBox(2 * hw, y1 - y0, 30, cq.Vector(-hw, y0, -1)))


def one_piece_drawing(p, solid, plate, posts_, notes, path=ONE_PIECE_DRAWING):
    """Picture of the one-piece version: 3D views from above and from below, sections through H34 and the ear."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mesh_views import draw_mesh, iso_basis, subdivide

    def tris(s, tol=0.03, edge=1.0):
        v, idx = s.tessellate(tol, 0.2)
        return subdivide(np.array([[q.x, q.y, q.z] for q in v])[np.array(idx)], edge)
    grey, red, light = (0.55, 0.58, 0.63), (0.75, 0.3, 0.25), (0.86, 0.87, 0.89)
    holes = plate_holes()
    fig = plt.figure(figsize=(16, 11))
    fig.suptitle("Speedrun front splitter, alternative: the body post mount enlarged to the splitter, one part (End A)",
                 fontsize=13, y=0.985)
    views = [([0.0, 0.42, 0.5, 0.52], iso_basis(-60, 32), "From above (front left), body posts cut at z = 14",
              [(solid, grey)] + [(s.intersect(cq.Solid.makeBox(200, 100, 15, cq.Vector(-100, 280, -1))), red)
                                 for s in posts_]),
             ([0.5, 0.42, 0.5, 0.52], iso_basis(-120, -40), "From below: pocket for the front end of the chassis "
              "plate, tapped holes H34, H35, H36, countersinks of the post screws", [(solid, grey)])]
    for rect, basis, title, solids in views:
        ax = fig.add_axes(rect)
        t = [tris(s) for s, _ in solids]
        col = [np.tile(c, (len(q), 1)) for q, (_, c) in zip(t, solids)]
        lo, hi = draw_mesh(ax, np.concatenate(t), basis, tri_colors=np.concatenate(col), depth_cue=0.3)
        ax.set_xlim(lo[0] - 2, hi[0] + 2)
        ax.set_ylim(lo[1] - 2, hi[1] + 2)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=9.5, loc="left")
    side = tuple(np.array(v) for v in ((-1.0, 0, 0), (0, 1.0, 0), (0, 0, 1.0)))
    for k, (x, title) in enumerate(((holes["H34"][0], f"Section through H34 (x = {holes['H34'][0]:.2f})"),
                                    (p["ear_holes"][0], f"Section through the ear and the body post "
                                                        f"(x = {p['ear_holes'][0]:.2f})"))):
        ax = fig.add_axes([0.03 + 0.49 * k, 0.2, 0.46, 0.2])
        slab = cq.Solid.makeBox(0.3, 140, 60, cq.Vector(x - 0.15, 290, -20))
        t, col = [], []
        for s, c in [(plate, light), (solid, grey)] + [(q, red) for q in posts_]:
            cut = s.intersect(slab)
            if cut.Volume() > 1e-4:
                t.append(tris(cut, 0.02, 0.6))
                col.append(np.tile(c, (len(t[-1]), 1)))
        draw_mesh(ax, np.concatenate(t), side, tri_colors=np.concatenate(col), depth_cue=0.0)
        ax.set_xlim(300, 412)
        ax.set_ylim(-3, 16)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title + " (y horizontal, z vertical; chassis plate light, part grey, body post red)",
                     fontsize=9, loc="left")
    fig.text(0.03, 0.155, "Checks", fontsize=10, fontweight="bold", va="top")
    fig.text(0.03, 0.135, "\n".join("\n".join(textwrap.wrap(n, 190)) for n in notes), fontsize=8, va="top",
             linespacing=1.35)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def parts_in_plate(p=None):
    """Mount, body posts, splitter and holder plate in chassis plate coordinates: list of (name, kind, solid)."""
    p = p or load_params(PARAMS)
    out = [("speedrun front body post mount End A", "bodymount", mount_solid(p))]
    out += [(name, "bodypost", s) for name, s in posts(p)]
    out.append(("speedrun front splitter End A", "splitter", splitter_solid(p)))
    out.append(("speedrun splitter holder plate End A", "holder", holder_solid(p)))
    return out


# ------------------------------------------------------------------ checks
def kingpin():
    """Front right kingpin: point at the height of the axle and direction (running gear)."""
    import generate_running_gear as G
    rg = G.load_params(G.PARAMS)
    c = G.corners(rg, G.load_params(G.LOWER))["front"]
    R, J = G.kingpin_frame(rg, c)
    return rg, J, R[:, 2]


def tyre_clearance(p, solids):
    """Smallest distance of each solid to the front right tyre (cylinder) turned about the kingpin axis, at the
    static ride height and with droop: dict name -> (distance, angle, droop)."""
    rg, J, kd = kingpin()
    width, droop, _, a_max = p["tyre_check"]
    res = {}
    for dz in (0.0, droop):
        Jd = J - np.array([0, 0, dz])
        tyre = cq.Solid.makeCylinder(rg["wheel_r"], width, cq.Vector(rg["wheel_centre_x"] - width / 2, Jd[1], Jd[2]),
                                     cq.Vector(1, 0, 0))
        for ang in np.arange(-a_max, a_max + 0.01, 2.5):
            t = tyre.rotate(cq.Vector(*Jd), cq.Vector(*(Jd + kd)), float(ang))
            for name, s in solids:
                d = s.distance(t)
                if name not in res or d < res[name][0]:
                    res[name] = (d, float(ang), dz)
    return res, (rg, J, kd)


def assembly_front_parts(path=ASSEMBLY, y_min=295.0):
    """Parts of the assembly STEP file with their name (without the parts of this script) that reach y >= y_min."""
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TDocStd import TDocStd_Document
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from OCP.TDF import TDF_LabelSequence
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.ReadFile(path)
    reader.Transfer(doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    labels = TDF_LabelSequence()
    tool.GetFreeShapes(labels)
    out = []

    def walk(lab):
        if tool.IsAssembly_s(lab):
            comps = TDF_LabelSequence()
            tool.GetComponents_s(lab, comps)
            for i in range(1, comps.Length() + 1):
                walk(comps.Value(i))
            return
        name = TDataStd_Name()
        nm = name.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), name) else ""
        s = cq.Shape.cast(tool.GetShape_s(lab))
        if not nm.startswith(OWN_PREFIXES) and s.BoundingBox().ymax >= y_min:
            out.append((nm, s))
    for i in range(1, labels.Length() + 1):
        walk(labels.Value(i))
    return out


# ------------------------------------------------------------------ drawing
def drawing(p, parts, geometry, tyre, plate, notes, context=None, path=DRAWING):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon as MPoly
    from mesh_views import draw_mesh, iso_basis, subdivide

    def tris(s, tol=0.03, edge=1.0):
        v, idx = s.tessellate(tol, 0.2)
        return subdivide(np.array([[q.x, q.y, q.z] for q in v])[np.array(idx)], edge)
    geom = plate_geometry()
    holes = plate_holes(geom)
    named = {n: s for n, _, s in parts}
    mount, splitter = named["speedrun front body post mount End A"], named["speedrun front splitter End A"]
    holder = named["speedrun splitter holder plate End A"]
    fig = plt.figure(figsize=(16, 15.5))
    fig.suptitle("Speedrun front splitter set (End A): body post mount, front splitter and splitter holder plate",
                 fontsize=13, y=0.985)
    # top view
    ax = fig.add_axes([0.03, 0.43, 0.62, 0.52])
    contour = []
    for prim in geom["outline"]:
        contour += [np.array(prim["start"])] if prim["type"] == "line" else arc_samples(prim)
    ax.add_patch(MPoly(np.array(contour), closed=True, fc="#d9dce1", ec="#55595f", lw=0.8, zorder=1))
    spl = []
    for prim in geometry["outline"]:
        spl += [np.array(prim["start"])] if prim["type"] == "line" else arc_samples(prim, 0.3)
    spl = np.array(spl)
    mo = mount_outline_points(p)
    ax.add_patch(MPoly(mo, closed=True, fc="#8a8f99", ec="black", lw=0.8, zorder=2))
    ax.add_patch(MPoly(spl, closed=True, fc="#3a3d42", ec="black", lw=1.0, alpha=0.8, zorder=3))
    ax.plot(np.append(mo[:, 0], mo[0, 0]), np.append(mo[:, 1], mo[0, 1]), "--", color="#c9ccd2", lw=0.7, zorder=4)
    for name, prims in geometry["cutouts"].items():
        q = []
        for prim in prims:
            q += [np.array(prim["start"])] if prim["type"] == "line" else arc_samples(prim, 0.2)
        ax.add_patch(MPoly(np.array(q), closed=True, fc="white", ec="black", lw=0.6, zorder=5))
    ax.add_patch(MPoly(mo, closed=True, fc="#2b2d31", ec="black", lw=0.8, alpha=0.9, zorder=4))     # holder plate
    for hid in ("H32", "H33", "H34", "H35"):
        x, y = holes[hid]
        ax.add_patch(Circle((x, y), 1.6, fc="white", ec="black", lw=0.6, zorder=5))
        ax.text(x + 2.0, y - 2.6 if hid in ("H32", "H33") else y - 7.0, hid, fontsize=7, zorder=6)
    ex, ey = p["ear_holes"]
    for sx in (1, -1):
        ax.add_patch(Circle((sx * ex, ey), p["body_post"][0] / 2, fc="#b42318", ec="black", lw=0.6, zorder=6))
    # front tyres at the height of the splitter (chord of the tyre at z = -thickness .. 0), turned about the kingpin
    if tyre is not None:
        rg, J, kd = tyre
        width, droop = p["tyre_check"][:2]
        zt = splitter_z(p) + p["splitter_t"]                                   # top face of the splitter
        hz = J[2] - droop - zt
        half = math.sqrt(max(rg["wheel_r"] ** 2 - hz ** 2, 0))
        yk = J[1] - hz * kd[1] / kd[2]                                          # kingpin axis at z = zt
        xc = rg["wheel_centre_x"]
        rect = np.array([[xc - width / 2, J[1] - half], [xc + width / 2, J[1] - half],
                         [xc + width / 2, J[1] + half], [xc - width / 2, J[1] + half]])
        for side in (1, -1):
            for ang in np.arange(-p["tyre_check"][3], p["tyre_check"][3] + 0.1, 2.5):
                a = math.radians(ang)
                Rm = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
                q = (rect - [J[0], yk]) @ Rm.T + [J[0], yk]
                q[:, 0] *= side
                ax.add_patch(MPoly(q, closed=True, fc="#2f6db5", ec="none", alpha=0.035, zorder=2))
                if ang in (-25.0, 0.0, 25.0):
                    ax.add_patch(MPoly(q, closed=True, fill=False, ec="#2f6db5", lw=0.8 if ang == 0 else 0.5,
                                       ls="-" if ang == 0 else "--", zorder=2))
        ax.text(0, 258, f"Front tyre (width {p['tyre_check'][0]:g}) cut at the top face of the splitter, droop "
                f"{p['tyre_check'][1]:g}:\nstraight (solid), 25 deg (dashed), swept area up to "
                f"{p['tyre_check'][3]:g} deg (blue)", ha="center", fontsize=7.5, color="#2f6db5")
    be = body_edge(p)
    yb = float(be[np.argmin(np.abs(be[:, 0])), 1])
    for o in p["body_overhang"]:
        b2 = body_edge(p, o)
        ax.plot(b2[:, 0], b2[:, 1], "--", color="#e8833a", lw=1.0, zorder=7)
    yf = holes["H34"][1] + p["splitter_front_distance"]
    lo_, hi_ = p["body_overhang"]
    ax.text(0, yb - 27, f"dashed: lower front edge of the body, {lo_:g} and {hi_:g} behind the front edge of the "
            "splitter (owner: the body sits on the splitter)", ha="center", fontsize=8, color="#e8833a", zorder=7)
    ax.text(0, yf + 3, f"front end of the splitter {p['splitter_front_distance']:g} ahead of the axis H34-H35 "
            f"(y = {yf:.1f}); outer form: form of the body edge moved forward", ha="center", fontsize=8, zorder=7)
    ax.set_xlim(-100, 100)
    ax.set_ylim(255, 418)
    ax.set_aspect("equal")
    ax.grid(True, lw=0.25, color="#bbbbbb")
    ax.set_title("Top view (mm): chassis plate light grey, splitter dark grey on the mount (outline of the mount "
                 "dashed), holder plate black, body posts red", fontsize=9, loc="left")
    # section at x = 0: thin slab of each part, seen along the x axis (y to the right, z up)
    ax = fig.add_axes([0.03, 0.16, 0.62, 0.24])
    slab = cq.Solid.makeBox(0.4, 140, 60, cq.Vector(-0.2, 285, -20))
    t, col = [], []
    for s, c in ((plate, (0.85, 0.86, 0.88)), (mount, (0.55, 0.58, 0.63)), (splitter, (0.23, 0.24, 0.26)),
                 (holder, (0.08, 0.08, 0.09))):
        sec = s.intersect(slab)
        if sec.Volume() > 0:
            t.append(tris(sec, 0.02, 0.6))
            col.append(np.tile(c, (len(t[-1]), 1)))
    draw_mesh(ax, np.concatenate(t), tuple(np.array(v) for v in ((-1.0, 0, 0), (0, 1.0, 0), (0, 0, 1.0))),
              tri_colors=np.concatenate(col), depth_cue=0.0)
    ax.plot([288, 415], [-10, -10], color="#6b4f2a", lw=1.2)
    ax.text(289, -12.5, "ground at the ride height of 10 (setup sheet 4)", fontsize=8, color="#6b4f2a")
    zt = splitter_z(p) + p["splitter_t"]
    z0, z1 = p["ear_boss"][1] - p["ear_boss"][3], zt + p["body_post"][2]
    r = p["body_post"][0] / 2
    ax.plot([ey - r, ey - r, ey + r, ey + r], [z0, z1, z1, z0], color="#b42318", lw=0.8)
    ax.text(ey, z1 + 1, f"body post (at x = +-{ex:.1f})", ha="center", fontsize=8, color="#b42318")
    ax.plot([yb, yb], [-3, 25], "--", color="#c2410c", lw=0.9)
    ax.set_xlim(288, 415)
    ax.set_ylim(-14, 42)
    ax.set_aspect("equal")
    ax.grid(True, lw=0.25, color="#bbbbbb")
    ax.set_title("Section at x = 0 (y horizontal, z vertical, mm): chassis plate, mount, splitter, holder plate",
                 fontsize=9, loc="left")
    # shaded views: mount from above and from below, body posts with the parts of the assembly around them
    posts_ = [s for n, _, s in parts if n.startswith("body post")]
    grey, red = (0.55, 0.58, 0.63), (0.75, 0.3, 0.25)
    carbon = (0.25, 0.26, 0.28)
    cut_posts = [s.intersect(cq.Solid.makeBox(200, 100, 14, cq.Vector(-100, 280, -1))) for s in posts_]
    views = [(-60, 35, "Mount from above: collars on H34/H35, hexagon recesses of the posts", [(mount, grey)]),
             (-120, -40, "Mount from below: pocket for the front end of the plate, countersinks", [(mount, grey)])]
    views.append((-55, 30, "Mount, splitter, holder plate and body posts (posts cut at z = 13)",
                  [(mount, grey), (splitter, carbon), (holder, (0.08, 0.08, 0.09))] + [(s, red) for s in cut_posts]))
    for k, (az, el, title, solids) in enumerate(views):
        ax = fig.add_axes([0.67, 0.64 - 0.31 * k, 0.32, 0.3])
        t = [tris(s) for s, _ in solids]
        col = [np.tile(c, (len(q), 1)) for q, (_, c) in zip(t, solids)]
        lo, hi = draw_mesh(ax, np.concatenate(t), iso_basis(az, el), tri_colors=np.concatenate(col), depth_cue=0.3)
        ax.set_xlim(lo[0] - 2, hi[0] + 2)
        ax.set_ylim(lo[1] - 2, hi[1] + 2)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=9, loc="left")
    fig.text(0.04, 0.125, "Checks", fontsize=10, fontweight="bold", va="top")
    fig.text(0.04, 0.105, "\n".join("\n".join(textwrap.wrap(n, 125)) for n in notes), fontsize=8, va="top",
             linespacing=1.35)
    fig.savefig(path, dpi=100)
    plt.close(fig)


# ------------------------------------------------------------------ main
def main():
    parser = argparse.ArgumentParser(description="Generate the front body post mount and the speedrun front splitter.")
    parser.add_argument("--no-check", action="store_true", help="skip the tyre check and the assembly check")
    args = parser.parse_args()
    p = load_params(PARAMS)
    geom = plate_geometry()
    holes = plate_holes(geom)
    geometry = splitter_geometry(p, holes)
    parts = parts_in_plate(p)
    named = {n: s for n, _, s in parts}
    mount, splitter = named["speedrun front body post mount End A"], named["speedrun front splitter End A"]
    os.makedirs(OUT, exist_ok=True)
    holder = named["speedrun splitter holder plate End A"]
    st, st_l = stack(p), p["stack_screws"]
    print(f"  stack on H34/H35: screw M3x{st_l[0]:g} from below to z = {st['tip_bottom']:g}, splitter z = "
          f"{st['splitter']:g} to {st['splitter'] + p['splitter_t']:g}, holder plate to {st['holder_top']:g}, screw "
          f"M3x{st_l[1]:g} from above to z = {st['tip_top']:g} (gap {st['tip_top'] - st['tip_bottom']:.1f})")
    for stem, s in ((MOUNT_STEM, mount), (SPLITTER_STEM, splitter), (HOLDER_STEM, holder)):
        cq.exporters.export(cq.Workplane().add(s), stem + ".step")
        cq.exporters.export(cq.Workplane().add(s), stem + ".stl", tolerance=0.01, angularTolerance=0.1)
    for stem, g in ((SPLITTER_STEM, geometry), (HOLDER_STEM, holder_geometry(p, holes))):
        with open(stem + "_geometry.json", "w", encoding="utf-8") as f:
            json.dump(g, f, indent=1)
            f.write("\n")
        build_dxf(g).saveas(stem + ".dxf")
    test = splitter_test_print(p, splitter)
    cq.exporters.export(cq.Workplane().add(test), SPLITTER_STEM + "_test_print.stl", tolerance=0.01,
                        angularTolerance=0.1)
    tb = test.BoundingBox()
    v_test = test.translate(cq.Vector(0, 0, splitter_z(p))).intersect(mount).Volume()
    print(f"Wrote {MOUNT_STEM}.step/.stl, {SPLITTER_STEM}.step/.stl/.dxf/_geometry.json/_test_print.stl, "
          f"{HOLDER_STEM}.step/.stl/.dxf/_geometry.json")
    print(f"  test print of the splitter: {tb.xlen:.1f} x {tb.ylen:.1f} x {tb.zlen:.1f} mm (bottom face on the print "
          f"bed), overlap with the mount in its position: {v_test:.4f} mm3")
    hb = holder.BoundingBox()
    print(f"  holder plate: {hb.xlen:.1f} x {hb.ylen:.1f} x {p['holder_plate'][0]:g} mm, carbon 1.6 g/cm3: "
          f"{holder.Volume() / 1000 * 1.6:.1f} g")
    mb = mount.BoundingBox()
    mo = mount_outline_points(p, 0.1)
    print(f"  mount: width over the ears {mb.xlen:.2f} (M1), depth on the centre line "
          f"{mo[np.abs(mo[:, 0]) < 0.2, 1].max() - p['mount_rear_y']:.2f} (M5)")
    bb = splitter.BoundingBox()
    print(f"  mount: volume {mount.Volume() / 1000:.2f} cm3 (PETG 1.27 g/cm3: {mount.Volume() / 1000 * 1.27:.1f} g)")
    print(f"  splitter: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm (y {bb.ymin:.1f} to {bb.ymax:.1f}), volume "
          f"{splitter.Volume() / 1000:.2f} cm3 (carbon 1.6 g/cm3: {splitter.Volume() / 1000 * 1.6:.1f} g), "
          f"{bb.ymax - 325.62:.1f} ahead of the chassis plate, {yb_gap(p):.1f} ahead of the body edge")
    # holes: mount and splitter on the holes of the chassis plate
    dev = max(math.hypot(h["x"] - holes[k][0], h["y"] - holes[k][1]) for h, k in zip(geometry["holes"], ("H34", "H35")))
    print(f"  holes S1/S2 of the splitter on H34/H35: largest offset {dev:.3f}")
    plate = cq.importers.importStep(PLATE_STEP).val()
    print(f"  overlap mount / chassis plate: {mount.intersect(plate).Volume():.4f} mm3, splitter / chassis plate: "
          f"{splitter.intersect(plate).Volume():.4f} mm3")
    for name, _, s in parts:
        if name.startswith("body post"):
            print(f"  overlap {name} / mount: {s.intersect(mount).Volume():.4f} mm3, / splitter: "
                  f"{s.intersect(splitter).Volume():.4f} mm3, / holder plate: {s.intersect(holder).Volume():.4f} mm3")
    print(f"  overlap splitter / mount: {splitter.intersect(mount).Volume():.4f} mm3, holder plate / splitter: "
          f"{holder.intersect(splitter).Volume():.4f} mm3, holder plate / mount: {holder.intersect(mount).Volume():.4f}"
          " mm3")
    notes = [f"Splitter {bb.xlen:.0f} x {bb.ylen:.1f} x {p['splitter_t']:g} (carbon approx. "
             f"{splitter.Volume() / 1000 * 1.6:.0f} g), {bb.ymax - 325.62:.1f} ahead of the chassis plate, "
             f"{yb_gap(p):.1f} ahead of the lower front edge of the body; bottom face on the bosses of the mount "
             f"(z = {splitter_z(p):g}), {10 + splitter_z(p):g} above the ground at the ride height of 10.",
             f"Mount approx. {mount.Volume() / 1000 * 1.27:.1f} g (PETG). Holes S1/S2 on H34/H35: offset {dev:.3f}; "
             f"overlap mount / chassis plate {mount.intersect(plate).Volume():.3f} mm3, splitter / mount "
             f"{splitter.intersect(mount).Volume():.3f} mm3, holder plate / splitter "
             f"{holder.intersect(splitter).Volume():.3f} mm3.",
             f"Holder plate {hb.xlen:.1f} x {hb.ylen:.1f} x {p['holder_plate'][0]:g} (carbon approx. "
             f"{holder.Volume() / 1000 * 1.6:.0f} g) on the splitter. Screws on H34/H35: M3x{st_l[0]:g} countersunk "
             f"from below (tip at z = {st['tip_bottom']:g}), M3x{st_l[1]:g} from above (tip at z = "
             f"{st['tip_top']:g}): gap "
             f"{st['tip_top'] - st['tip_bottom']:.1f}; H36: M3x6 countersunk from below into the deck."]
    tyre, context = None, None
    if st["tip_top"] - st["tip_bottom"] < st_l[2] - 1e-6:
        raise ValueError("the screws from below and from above on H34/H35 touch (stack_screws)")
    if not args.no_check:
        res, tyre = tyre_clearance(p, [("splitter", splitter), ("mount", mount), ("holder plate", holder)])
        need = p["tyre_check"][2]
        for name, (d, ang, dz) in res.items():
            state = "ok" if d >= need else f"TOO SMALL (required {need:g})"
            line = (f"Clearance {name} / front tyre (steering -{p['tyre_check'][3]:g} to +{p['tyre_check'][3]:g} deg, "
                    f"droop 0 and {p['tyre_check'][1]:g}): {d:.2f} at {ang:+.1f} deg, droop {dz:g}: {state}")
            print("  " + line)
            notes.append(line + ".")
        if os.path.exists(ASSEMBLY):
            context = assembly_front_parts()
            worst = 0.0
            for name, _, s in parts:
                for on, o in context:
                    if on == "chassis_plate":
                        continue
                    v = s.intersect(o).Volume()
                    worst = max(worst, v)
                    if v > 1e-4:
                        line = f"Interference {name} / {on.replace('_', ' ')}: {v:.2f} mm3"
                        print("  " + line)
                        notes.append(line + ".")
            print(f"  overlap with {len(context)} parts of the assembly at End A: largest {worst:.4f} mm3")
            notes.append(f"Overlap of the mount, the body posts, the splitter and the holder plate with the "
                         f"{len(context)} parts of the assembly at End A (without the chassis plate): largest "
                         f"{worst:.3f} mm3.")
    else:
        tyre = kingpin()
        notes.append("Tyre check and assembly check skipped (--no-check).")
    drawing(p, parts, geometry, tyre, plate, notes, context)
    print(f"Wrote {DRAWING}")
    # alternative version: body post mount and front splitter in one piece
    one = one_piece_solid(p, geom)
    cq.exporters.export(cq.Workplane().add(one), ONE_PIECE_STEM + ".step")
    cq.exporters.export(cq.Workplane().add(one), ONE_PIECE_STEM + ".stl", tolerance=0.01, angularTolerance=0.1)
    one_test = one_piece_test_print(p, one)
    cq.exporters.export(cq.Workplane().add(one_test), ONE_PIECE_STEM + "_test_print.stl", tolerance=0.01,
                        angularTolerance=0.1)
    ob, tb = one.BoundingBox(), one_test.BoundingBox()
    posts_ = one_piece_posts(p)
    one_notes = [f"One piece {ob.xlen:.0f} x {ob.ylen:.1f} mm, volume {one.Volume() / 1000:.1f} cm3 (PETG approx. "
                 f"{one.Volume() / 1000 * p['one_piece'][1]:.0f} g): the mount enlarged to the outline of the splitter "
                 f"at the thickness of its front part (z = 0 to {p['front_t']:g}, bottom face flush with the chassis "
                 "plate, 10 above the ground at the ride height of 10); the body sits on it at z = "
                 f"{p['front_t']:g}.",
                 f"Overlap with the chassis plate {one.intersect(plate).Volume():.3f} mm3, with the body posts "
                 f"{max(s.intersect(one).Volume() for s in posts_):.3f} mm3. Screws M3x6 from below: tip at z = "
                 f"{p['stack_screws'][0]:g}, blind tapped holes on H34/H35 in bosses up to z = {p['one_piece'][2]:g}. "
                 f"Test print (middle part, bottom face on the bed): {tb.xlen:.0f} x {tb.ylen:.0f} mm."]
    if not args.no_check:
        d, ang, dz = tyre_clearance(p, [("one piece", one)])[0]["one piece"]
        one_notes.append(f"Clearance to the front tyres (steering -{p['tyre_check'][3]:g} to +{p['tyre_check'][3]:g} "
                         f"deg, droop 0 and {p['tyre_check'][1]:g}): {d:.2f} at {ang:+.1f} deg, droop {dz:g}.")
        if context:
            worst = max(one.intersect(o).Volume() for on, o in context if on != "chassis_plate")
            one_notes.append(f"Overlap with the {len(context)} parts of the assembly at End A (without the chassis "
                             f"plate): largest {worst:.3f} mm3.")
    for n in one_notes:
        print("  one piece: " + n)
    one_piece_drawing(p, one, plate, posts_, one_notes)
    print(f"Wrote {ONE_PIECE_STEM}.step/.stl/_test_print.stl, {ONE_PIECE_DRAWING}")


if __name__ == "__main__":
    main()
