"""Study: speedrun chassis plate closed between the tyres.

Owner (2026-11-21): the open space between the tyres is closed with the chassis plate, without touching the tyres or
getting too close to them. The study keeps the speedrun chassis plate (wide, longer motor window: holes, windows,
countersinks, thickness) and only adds material to its outline:

* New material only between the rear axle and the front end of the diagonal edges of the current outline (y = 258.24)
  (owner: none in front of the front tyres and behind the rear tyres, no spike beside the front wishbones); there the
  full width of the current plate (x = +-99.99).
* Keep-out zones, each enlarged by the clearance CLEAR (3.0, as the tyre check of the front splitter):
  * tyres (cylinder radius wheel_r, width TYRE_W = 30 as setup sheet 4) cut at the height of the plate (z = 0 to
    the top face plus CLEAR); front: turned about the kingpin axis over the free angles of the knuckle (45 deg with
    the steering arm toward the outside, 35 deg toward the middle), static and with droop up to DROOP; rear: static and
    with droop;
  * the parts that move with the suspension (wishbones, C-hubs, knuckles, kingpins, guide sleeves, kingpin washers,
    hub carriers, spacers, hinge pins, axles, hex hubs, bearings, ball studs on the wishbones), turned about the inner
    hinge pin from the static position to the droop DROOP at the wheel centre: where they come lower than Z_CLEAR above
    the top face of the plate.
* Outline = largest outline minus the keep-out zones, inside corners closed with the radius R_INNER (end mill), then
  united with the current outline (the study never removes material of the current plate).

Checks: distances of the new plate to the tyres (all positions) and to the moving parts (droop positions), overlap
with all parts of the assembly in the static position, mass (aluminium 6082).

Usage (from the root directory of the repository, after generate_speedrun_assembly.py; approx. 12 min):
    python cad/studies/chassis_plate_closed/generate_chassis_plate_closed_study.py [--pictures]
The option --pictures renders only the pictures from the written geometry data and STEP file.

Outputs in cad/studies/chassis_plate_closed: geometry data, STEP, STL, DXF of the plate, top view with the keep-out
zones, picture of the assembly with the new plate. Requires cadquery, ezdxf and matplotlib.
"""
import json
import math
import os
import sys

import numpy as np
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "cad"))
import generate_assembly_drawing as AD  # noqa: E402
import generate_wishbones as W  # noqa: E402
import palette as P  # noqa: E402
from generate_solid import plate_solid  # noqa: E402
from generate_dxf import build_dxf  # noqa: E402
from mesh_views import draw_mesh, iso_basis, subdivide  # noqa: E402

PLATE = "cad/speedrun_parts/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_speedrun_wide_motor10_geometry.json"
ASSEMBLY = "cad/assembly/speedrun_chassis_T410R.step"
STEM = os.path.join(HERE, "chassis_plate_closed_study")
TOP_VIEW = os.path.join(HERE, "chassis_plate_closed_study_top_view.png")
PICTURE = os.path.join(HERE, "chassis_plate_closed_study_assembly.png")

TYRE_W = 30.0            # tyre width (setup sheet 4, as the tyre check of the front splitter)
CLEAR = 3.0              # clearance to the tyres and to the moving parts (as the tyre check of the front splitter)
DROOP = 4.0              # droop of the wheel centre below the static ride height (assumption, as the front splitter)
Z_CLEAR = 1.0            # moving parts lower than this above the top face of the plate keep the plate away
R_INNER = 2.0            # radius of the inside corners of the outline (end mill 4 mm)
STATIC_CLEAR = 1.0       # gap to parts that do not move and reach down to the height of the plate (front splitter)
STEER = {"right": (-35.0, 45.0), "left": (-45.0, 35.0)}   # free angles of the knuckle about the kingpin axis
MOVING = ("wishbone", "C-hub", "steering_knuckle", "kingpins", "guide_sleeves", "kingpin_washers", "outer_hinge_pin",
          "axle_with_joint_cup", "axle_pin", "hex_hub", "wheel_bearings", "hub_carrier", "spacers", "sway_ball_stud",
          "damper_ball_studs")
DENSITY_6082 = 2.70
CORNERS = [(e, s) for e in ("A", "B") for s in ("right", "left")]


# ------------------------------------------------------------------ data of the assembly
def load():
    parts = AD.read_named_solids(ASSEMBLY)
    v = AD.model_values(parts)
    with open(PLATE, encoding="utf-8") as f:
        geo = json.load(f)
    return parts, v, geo


def tyre(v, e, s, steer=0.0, droop=0.0):
    """Tyre as a cylinder on the wheel centre plane, turned about the kingpin axis (front) and lowered by the droop."""
    R = v["wheel_r"]
    Wc = v["W"][e][s] - np.array([0, 0, droop])
    d = v["out"][e][s]
    t = cq.Solid.makeCylinder(R, TYRE_W, cq.Vector(*(Wc - d * TYRE_W / 2)), cq.Vector(*d))
    if e == "A" and steer:
        K = v["K"][s] - np.array([0, 0, droop])
        t = t.rotate(cq.Vector(*K), cq.Vector(*(K + v["kdir"])), float(steer))
    return t


def tyre_poses(e, s):
    angles = np.arange(STEER[s][0], STEER[s][1] + 0.01, 2.5) if e == "A" else [0.0]
    return [(float(a), dr) for dr in (0.0, DROOP / 2, DROOP) for a in angles]


def hinge_axis(e, s):
    """Inner hinge pin of the corner: point and unit direction."""
    origin, d, _ = W.pin_lines()[("front" if e == "A" else "rear", 1 if s == "right" else -1)]
    d3 = np.array([d[0], d[1], 0.0])
    return np.array(origin, float), d3 / np.linalg.norm(d3)


def droop_angle(v, e, s):
    """Angle (deg) about the inner hinge pin that lowers the wheel centre by DROOP, with its sign."""
    o, d = hinge_axis(e, s)
    wc = v["W"][e][s]
    r = wc - o
    r -= (r @ d) * d
    ang = math.degrees(math.asin(DROOP / np.linalg.norm(r[:2]) if np.linalg.norm(r[:2]) else 0.0))
    test = cq.Vertex.makeVertex(*wc).rotate(cq.Vector(*o), cq.Vector(*(o + d)), ang)
    return ang if test.Z < wc[2] else -ang


def moving_parts(parts, e, s):
    tag = f"End_{e}_{s}"
    return [(n, sh) for n, sh in parts if n.endswith(tag) and any(k in n for k in MOVING)]


# ------------------------------------------------------------------ 2D keep-out zones
def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def hull(pts):
    """Convex hull of 2D points (monotone chain), counter-clockwise."""
    pts = sorted(set(map(tuple, np.round(pts, 6))))
    if len(pts) < 3:
        return np.array(pts)
    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and _cross(out[-2], out[-1], p) <= 0:
                out.pop()
            out.append(p)
        return out
    lo, hi = half(pts), half(pts[::-1])
    return np.array(lo[:-1] + hi[:-1])


def footprints(solid, z_top):
    """Convex outlines (2D) of the pieces of a solid below z_top (each piece separately)."""
    cut = solid.intersect(cq.Solid.makeBox(600, 800, z_top + 50, cq.Vector(-300, -200, -50)))
    out = []
    for piece in cut.Solids():
        pts = [e.positionAt(u).toTuple()[:2] for e in piece.Edges() for u in np.linspace(0, 1, 16)]
        if len(pts) >= 3:
            out.append(hull(np.array(pts)))
    return out


def clean_poly(poly, tol=0.05):
    """Convex polygon without points closer than tol to the previous one (counter-clockwise)."""
    out = []
    for q in poly:
        if not out or np.hypot(*(np.subtract(q, out[-1]))) > tol:
            out.append(tuple(q))
    while len(out) > 2 and np.hypot(*(np.subtract(out[0], out[-1]))) <= tol:
        out.pop()
    return np.array(out)


def grown_face(poly, c):
    """Face of a convex polygon (counter-clockwise) enlarged by the clearance c: each edge moved out by c, an arc of
    radius c around each corner (Minkowski sum with a circle)."""
    q = clean_poly(poly)
    if len(q) < 3:
        ctr = q.mean(axis=0) if len(q) else np.zeros(2)
        rad = c + (max(np.hypot(*(p - ctr)) for p in q) if len(q) else 0.0)
        return cq.Face.makeFromWires(cq.Wire.makeCircle(rad, cq.Vector(ctr[0], ctr[1], 0), cq.Vector(0, 0, 1)))
    n = len(q)
    normals = []
    for i in range(n):
        d = q[(i + 1) % n] - q[i]
        normals.append(np.array([d[1], -d[0]]) / np.linalg.norm(d))       # outward for counter-clockwise
    # corners with a turn of less than 0.5 deg get no arc: the two moved edges are joined at their mean point
    pts, arcs = [], []
    for i in range(n):
        n0, n1 = normals[i - 1], normals[i]
        turn = math.atan2(n0[0] * n1[1] - n0[1] * n1[0], n0 @ n1)
        if abs(turn) < math.radians(0.5):
            pts.append([q[i] + c * (n0 + n1) / np.linalg.norm(n0 + n1)] * 2)
            arcs.append(None)
        else:
            m = (n0 + n1) / np.linalg.norm(n0 + n1)
            pts.append([q[i] + c * n0, q[i] + c * n1])
            arcs.append(q[i] + c * m)
    V = lambda a: cq.Vector(float(a[0]), float(a[1]), 0.0)
    edges = []
    for i in range(n):
        if arcs[i] is not None:
            edges.append(cq.Edge.makeThreePointArc(V(pts[i][0]), V(arcs[i]), V(pts[i][1])))
        a0, a1 = pts[i][1], pts[(i + 1) % n][0]
        if np.hypot(*(np.subtract(a1, a0))) > 1e-6:
            edges.append(cq.Edge.makeLine(V(a0), V(a1)))
    return cq.Face.makeFromWires(cq.Wire.assembleEdges(edges))


def sections(solid, z):
    """Exact cross-sections (2D faces) of a solid at the height z, enlarged by STATIC_CLEAR."""
    slab = solid.intersect(cq.Solid.makeBox(600, 800, 0.02, cq.Vector(-300, -200, z - 0.01)))
    out = []
    for f in slab.Faces():
        if f.normalAt().z > 0.99:
            f0 = f.translate(cq.Vector(0, 0, -f.Center().z))
            try:
                out.append(cq.Face.makeFromWires(f0.outerWire().offset2D(STATIC_CLEAR, "arc")[0]))
            except Exception:
                pts = [e.positionAt(u).toTuple()[:2] for e in f0.Edges() for u in np.linspace(0, 1, 16)]
                out.append(grown_face(hull(np.array(pts)), STATIC_CLEAR))
    return out


def keep_out(parts, v, t):
    """Keep-out polygons (2D, convex, before the clearance):
    tyres: per corner the hull over all positions, extended to the outside of the car (no plate beside the tyres);
    moving parts: each piece below Z_CLEAR above the top face, per part and droop position;
    static parts: each piece below the top face of the plate (parts that stand on the plate do not count)."""
    zones = {"tyres": [], "moving parts": [], "static parts": []}
    for e, s in CORNERS:
        pts = [p for steer, dr in tyre_poses(e, s) for poly in footprints(tyre(v, e, s, steer, dr), t + CLEAR) for p in poly]
        if pts:
            pts = np.array(pts)
            side = np.sign(v["W"][e][s][0])
            far = [[side * 400, pts[:, 1].min()], [side * 400, pts[:, 1].max()]]
            zones["tyres"].append(hull(np.vstack([pts, far])))
        o, d = hinge_axis(e, s)
        a_max = droop_angle(v, e, s)
        for _, sh in moving_parts(parts, e, s):
            for f in np.linspace(0.0, 1.0, 5):
                moved = sh.rotate(cq.Vector(*o), cq.Vector(*(o + d)), float(f * a_max)) if f else sh
                zones["moving parts"] += footprints(moved, t + Z_CLEAR)
    moving = {n for e, s in CORNERS for n, _ in moving_parts(parts, e, s)}
    zones["static faces"] = []
    for n, sh in parts:
        if n.startswith("chassis_plate") or n in moving or sh.BoundingBox().zmin > t - 0.01:
            continue
        zones["static faces"] += sections(sh, t / 2)
    for k in ("tyres", "moving parts"):               # drop duplicates (parts that do not move between positions)
        seen, keep = set(), []
        for q in zones[k]:
            key = tuple(np.round(q, 1).ravel())
            if key not in seen and len(q) >= 3:
                seen.add(key)
                keep.append(q)
        zones[k] = keep
    return zones


# ------------------------------------------------------------------ outline
def outline_solid(geo, zones, v):
    """Plate without holes and windows: new material only between the front and the rear axle (owner: none in front
    of the front tyres and behind the rear tyres), there the full width minus the keep-out zones (prisms, one after the
    other), united with the current plate (the study never removes material), inside corners rounded with R_INNER."""
    import edge_treatment as ET
    t = geo["thickness"]
    cur = _wire(geo["outline"])
    cur = cq.Solid.extrudeLinear(cq.Face.makeFromWires(cur), cq.Vector(0, 0, t))
    bb = cur.BoundingBox()
    # rear axle to the front end of the diagonal edges of the current outline (owner: no spike beside the droop bosses
    # of the front wishbones; the current outline turns into the narrow front end there)
    y0 = v["W"]["B"]["right"][1]
    y1 = min(v["W"]["A"]["right"][1], max(max(q["start"][1], q["end"][1]) for q in geo["outline"]
                                          if q["type"] == "line" and abs(q["end"][0] - q["start"][0]) > 20
                                          and min(q["start"][1], q["end"][1]) > 150))
    s = cq.Solid.makeBox(bb.xlen, y1 - y0, t, cq.Vector(bb.xmin, y0, 0))
    tools = [grown_face(q, CLEAR) for k in ("tyres", "moving parts") for q in zones[k]] + zones["static faces"]
    for tool in tools:
        prism = cq.Solid.extrudeLinear(tool.translate(cq.Vector(0, 0, -1)), cq.Vector(0, 0, t + 2))
        r = s.cut(prism)
        if r.Solids():
            s = max(r.Solids(), key=lambda q: q.Volume())
    u = s.fuse(cur).clean()
    s = max(u.Solids(), key=lambda q: q.Volume())
    s, done, left = ET._apply(s, "inner", [R_INNER, 1.0, 0.5], (), 175.0)       # inside corners (vertical edges)
    print(f"  inside corners rounded: {done}, left sharp: {len(left)}")
    return s


def top_face(solid):
    """Largest face looking up (the top face of the plate: its outer wire is the outline, counter-clockwise)."""
    return max([f for f in solid.Faces() if f.normalAt().z > 0.99], key=lambda q: q.Area())


def finished_plate(outline, geo):
    """Windows, through holes and countersinks of the current plate cut into the outline solid."""
    from generate_solid import wire_from_prims
    t = geo["thickness"]
    body = cq.Workplane().add(outline)
    for contour in geo["cutouts"].values():
        body = body.cut(wire_from_prims(contour, -1).extrude(t + 2))
    rh, rc = geo["hole_d"] / 2, geo.get("csk_d", 0) / 2
    k = np.tan(np.radians(geo.get("csk_angle", 90.0) / 2))
    cutter = None
    for h in geo["holes"]:
        c = cq.Solid.makeCylinder(rh, t + 2, cq.Vector(h["x"], h["y"], -1))
        if rc > rh:
            ext = 0.5
            c = c.fuse(cq.Solid.makeCone(rc + ext * k, rh, (rc - rh) / k + ext, cq.Vector(h["x"], h["y"], -ext),
                                         cq.Vector(0, 0, 1)))
        cutter = c if cutter is None else cutter.fuse(c)
    return body.cut(cq.Workplane().add(cutter)).val()


def _wire(prims):
    from generate_solid import wire_from_prims
    return wire_from_prims(prims).val()


def prims_of(face):
    """Lines and arcs of the outer wire of a face in the order along the wire (format of the geometry data). The edges
    are chained by their end points: each edge starts where the previous one ends."""
    from OCP.BRepTools import BRepTools_WireExplorer
    edges = []
    exp = BRepTools_WireExplorer(face.outerWire().wrapped, face.wrapped)
    while exp.More():
        e = cq.Edge(exp.Current())
        if e.Length() > 1e-4:
            edges.append(e)
        exp.Next()
    ends = [(np.array(e.startPoint().toTuple()[:2]), np.array(e.endPoint().toTuple()[:2])) for e in edges]
    a0, b0 = ends[0]
    n0 = ends[1]
    cur = b0 if min(np.hypot(*(b0 - n0[0])), np.hypot(*(b0 - n0[1]))) < min(np.hypot(*(a0 - n0[0])),
                                                                          np.hypot(*(a0 - n0[1]))) else a0
    start = a0 if cur is b0 else b0
    out = []
    for e, (a, b) in zip(edges, ends):
        if out:
            start = np.array(out[-1]["end"])
            end = b if np.hypot(*(a - start)) <= np.hypot(*(b - start)) else a
        else:
            end = cur
        m = np.array(e.positionAt(0.5).toTuple()[:2])
        chord = end - start
        mv = m - start
        sag = abs(chord[0] * mv[1] - chord[1] * mv[0]) / max(np.linalg.norm(chord), 1e-9)
        if e.geomType() == "LINE" or sag < 1e-3:
            out.append({"type": "line", "start": list(start), "end": list(end)})
        elif e.geomType() == "CIRCLE":
            c = e.arcCenter()
            out.append({"type": "arc", "start": list(start), "mid": list(m), "end": list(end), "center": [c.x, c.y],
                        "r": e.radius()})
        else:                                                        # other curves: short lines
            us = np.linspace(0, 1, 9)
            q = [np.array(e.positionAt(u).toTuple()[:2]) for u in us]
            if np.hypot(*(q[0] - start)) > np.hypot(*(q[-1] - start)):
                q = q[::-1]
            for k in range(1, len(q)):
                out.append({"type": "line", "start": list(out[-1]["end"] if out else start), "end": list(q[k])})
    out[-1]["end"] = out[0]["start"]
    return [{k: ([float(x) for x in v] if isinstance(v, (list, np.ndarray)) else v) for k, v in p.items()} for p in out]


def checks(parts, v, plate, old_plate):
    res = {"tyres": {}, "moving parts": {}}
    for e, s in CORNERS:
        best = None
        for steer, dr in tyre_poses(e, s):
            d = plate.distance(tyre(v, e, s, steer, dr))
            if best is None or d < best[0]:
                best = (d, steer, dr)
        res["tyres"][f"End {e} {s}"] = best
        o, d3 = hinge_axis(e, s)
        a_max = droop_angle(v, e, s)
        worst = None
        for f in np.linspace(0.0, 1.0, 5):
            for n, sh in moving_parts(parts, e, s):
                moved = sh.rotate(cq.Vector(*o), cq.Vector(*(o + d3)), float(f * a_max)) if f else sh
                dist = plate.distance(moved)
                old = old_plate.distance(moved)
                if worst is None or dist < worst[0]:
                    worst = (dist, n, f * DROOP, old)
        res["moving parts"][f"End {e} {s}"] = worst
    static = []
    for n, sh in parts:
        if n.startswith("chassis_plate"):
            continue
        if sh.BoundingBox().zmin > 2.5:
            continue
        vol = plate.intersect(sh).Volume()
        if vol > 1e-3:
            static.append((n, vol, old_plate.intersect(sh).Volume()))
    res["static overlap"] = static
    return res


# ------------------------------------------------------------------ pictures
def prim_points(prims, n=16):
    """Points along the lines and arcs of a contour, in order."""
    pts = []
    for p in prims:
        chord = np.subtract(p["end"], p["start"])
        mv = np.subtract(p.get("mid", p["start"]), p["start"])
        sag = abs(chord[0] * mv[1] - chord[1] * mv[0]) / max(np.linalg.norm(chord), 1e-9)
        if p["type"] == "line" or np.linalg.norm(chord) < 1e-6 or sag < 1e-4:
            pts += [p["start"], p["end"]]
        else:
            try:
                e = cq.Edge.makeThreePointArc(cq.Vector(*p["start"], 0), cq.Vector(*p["mid"], 0), cq.Vector(*p["end"], 0))
                pts += [e.positionAt(u).toTuple()[:2] for u in np.linspace(0, 1, n)]
            except Exception:                                # nearly straight or tiny: three points
                pts += [p["start"], p["mid"], p["end"]]
    return np.array(pts)



def top_view(geo, face, zones, path, outline=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    fig, ax = plt.subplots(figsize=(10, 15))
    for k, col in (("tyres", (0.55, 0.6, 0.66)), ("moving parts", (0.80, 0.84, 0.90))):
        ax.add_collection(PolyCollection([p for p in zones[k]], facecolors=[col], edgecolors=[col], lw=0.3, alpha=0.6))
    for f in zones["static faces"]:
        q = prim_points(prims_of(f))
        ax.fill(q[:, 0], q[:, 1], color=(0.93, 0.80, 0.62), alpha=0.6, lw=0)
    new = prim_points(outline or prims_of(face))
    ax.fill(new[:, 0], new[:, 1], color=P.rgb("plate"), alpha=0.35, lw=0)
    ax.plot(new[:, 0], new[:, 1], color=P.rgb("plate"), lw=1.6, label="new outline (study)")
    o = prim_points(geo["outline"])
    ax.plot(o[:, 0], o[:, 1], "k--", lw=0.9, label="current outline")
    for c in geo["cutouts"].values():                 # windows open (motor window, slot of the spur gear)
        q = prim_points(c)
        ax.fill(q[:, 0], q[:, 1], color="white", lw=0, zorder=3)
        ax.plot(q[:, 0], q[:, 1], "k", lw=0.6, zorder=4)
    for h in geo["holes"]:
        ax.add_patch(plt.Circle((h["x"], h["y"]), geo["hole_d"] / 2, fc="white", ec="k", lw=0.5, zorder=4))
    ax.plot([], [], "s", color=(0.55, 0.6, 0.66), label=f"tyres at the height of the plate (steering, droop 0 to {DROOP:g})")
    ax.plot([], [], "s", color=(0.80, 0.84, 0.90), label=f"moving parts lower than {Z_CLEAR:g} above the plate (droop 0 to {DROOP:g})")
    ax.plot([], [], "s", color=(0.93, 0.80, 0.62), label=f"static parts at the height of the plate (front splitter), enlarged by {STATIC_CLEAR:g}")
    ax.set_aspect("equal")
    ax.set_xlim(-125, 125)
    ax.set_ylim(-30, 350)
    ax.grid(alpha=0.25)
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm] (End A at the top)")
    ax.legend(loc="lower center", fontsize=8, bbox_to_anchor=(0.5, -0.12))
    ax.set_title(f"Study: chassis plate closed between the tyres (clearance {CLEAR:g}, inside corners R{R_INNER:g})",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def picture(parts, plate, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tris, cols = [], []
    for n, sh in [(n, sh) for n, sh in parts if not n.startswith("chassis_plate")] + [("plate", plate)]:
        key = "plate" if n == "plate" else ("damper" if "tyre" in n else "upright")
        vs, idx = sh.tessellate(0.1, 0.3)
        if not idx:
            continue
        pts = np.array([[q.x, q.y, q.z] for q in vs])
        t = subdivide(pts[np.array(idx)], 6.0 if key == "plate" else 3.0)
        tris.append(t)
        cols.append(np.tile(P.rgb("plate" if key == "plate" else "cup"), (len(t), 1)))
    fig = plt.figure(figsize=(14, 9))
    ax = fig.add_axes([0, 0, 1, 0.94])
    lo, hi = draw_mesh(ax, np.concatenate(tris), iso_basis(-40, 30), tri_colors=np.concatenate(cols), depth_cue=0.3)
    ax.set_xlim(lo[0] - 3, hi[0] + 3)
    ax.set_ylim(lo[1] - 3, hi[1] + 3)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.suptitle("Study: speedrun chassis with the chassis plate closed between the tyres", fontsize=11, y=0.985)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    parts, v, geo = load()
    zones = keep_out(parts, v, geo["thickness"])
    if "--outline" in sys.argv:                       # geometry data and DXF again from the written STEP file
        solid = cq.importers.importStep(STEM + ".step").val()
        new = json.load(open(STEM + "_geometry.json", encoding="utf-8"))
        new["outline"] = prims_of(top_face(solid))
        with open(STEM + "_geometry.json", "w", encoding="utf-8") as f:
            json.dump(new, f, indent=1)
        build_dxf(new).saveas(STEM + ".dxf")
        check = plate_solid(new).val()
        print(f"outline: {len(new['outline'])} lines and arcs; plate from the geometry data valid {check.isValid()}, "
              f"volume {check.Volume():.1f} (STEP {solid.Volume():.1f})")
    if "--pictures" in sys.argv or "--outline" in sys.argv:  # pictures only, from the geometry data and STEP file
        new = json.load(open(STEM + "_geometry.json", encoding="utf-8"))
        solid = cq.importers.importStep(STEM + ".step").val()
        top_view(geo, top_face(solid), zones, TOP_VIEW, new["outline"])
        picture(parts, solid, PICTURE)
        print(f"wrote {TOP_VIEW} and {PICTURE}")
        return
    outline = outline_solid(geo, zones, v)
    face = top_face(outline)
    new = dict(geo)
    new["basis"] = ("Study (not part of the build): speedrun chassis plate (wide, longer motor window) closed between "
                    f"the tyres; clearance {CLEAR:g} to the tyres and to the moving parts, see the readme of the study.")
    new["outline"] = prims_of(face)
    with open(STEM + "_geometry.json", "w", encoding="utf-8") as f:
        json.dump(new, f, indent=1)
    solid = finished_plate(outline, geo)
    old = plate_solid(geo).val()
    cq.exporters.export(solid, STEM + ".step")
    cq.exporters.export(solid, STEM + ".stl", tolerance=0.01, angularTolerance=0.1)
    build_dxf(new).saveas(STEM + ".dxf")
    print(f"wrote {STEM}_geometry.json, .step, .stl, .dxf; valid {solid.isValid()}, outline: {len(new['outline'])} "
          f"lines and arcs")
    print(f"  area of the outline: new {face.Area():.0f} mm2, current {cq.Face.makeFromWires(_wire(geo['outline'])).Area():.0f} mm2")
    print(f"  mass (6082): new {solid.Volume() * DENSITY_6082 / 1000:.0f} g, current {old.Volume() * DENSITY_6082 / 1000:.0f} g")
    res = checks(parts, v, solid, old)
    for k, (d, steer, dr) in res["tyres"].items():
        print(f"  tyre {k}: smallest distance {d:.2f} (steering {steer:+.1f} deg, droop {dr:g})")
    for k, (d, n, dr, old_d) in res["moving parts"].items():
        print(f"  moving parts {k}: smallest distance {d:.2f} ({n}, droop {dr:g}; current plate {old_d:.2f})")
    print("  static overlap with the parts of the assembly:", [(n, round(a, 3), round(b, 3)) for n, a, b in res["static overlap"]] or "none")
    with open(STEM + "_results.json", "w", encoding="utf-8") as f:
        json.dump({"tyres": res["tyres"], "moving parts": res["moving parts"],
                   "static overlap": res["static overlap"],
                   "mass_g": {"new": solid.Volume() * DENSITY_6082 / 1000, "current": old.Volume() * DENSITY_6082 / 1000},
                   "area_mm2": {"new": face.Area(), "current": cq.Face.makeFromWires(_wire(geo['outline'])).Area()}},
                  f, indent=1)
    top_view(geo, face, zones, TOP_VIEW, new["outline"])
    picture(parts, solid, PICTURE)
    print(f"wrote {TOP_VIEW} and {PICTURE}")


if __name__ == "__main__":
    main()
