"""Generate the camber links of the speedrun chassis (own design, partly based on the T410R).

The camber links (upper links, manual page 05 step 4 "C front upper" and "D rear upper", mounted in
step 21) consist of a turnbuckle M3x37 with a rod end on each end. The inner rod end
sits on a ball stud in the camber link hole of the shock tower (behind the tower, wall side), the
outer rod end on a vertical ball stud of the C-hub (front) or of the hub carrier (rear). The two rod
ends are turned by 90 degrees about the link axis.

* front links (End A): the outer ball sits on the top kingpin of the knuckle (manual set up C: gap 24.0 mm)
* rear links (End B): the outer ball sits on the ball stud in the camber stud bore on top of the hub carrier,
  13.7 mm from the outer face of the bearing tube (owner; manual set up D: gap 25.8 mm)

The positions of the outer balls come from the running gear (generate_running_gear.py); the gaps between the
rod ends follow from them.

Usage (from the root directory of the repository):
    python scripts/cad/generate_camber_links.py

The camber links are purchased parts (owner, 2026-11-24): the script builds the simplified model in memory for the
assembly (links_in_plate) and the checks, writes no part files, draws photos/cad_camber_links_drawing.png and
checks the placed links against the shock towers, the bulkheads and the wishbones.

Requires the package cadquery.
"""
import argparse
import math
import os
import sys

import numpy as np
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_bulkhead_lower import box, cyl_x, cyl_y, cyl_z, load_params  # noqa: E402
from generate_top_brace_speedrun import BULKHEAD_Y  # noqa: E402

PARAMS = "cad/generic_parts/camber_link_parameters.json"
LOWER = "cad/speedrun_parts/bulkhead/bulkhead_lower_parameters.json"
UPPER = "cad/speedrun_parts/bulkhead/bulkhead_upper_parameters.json"
PLATE_T = 2.0


def hex_x(af, x0, x1):
    """Hexagon prism along x (width across flats af) from x0 to x1."""
    h = cq.Workplane("YZ").workplane(offset=x0).polygon(6, af / np.cos(np.pi / 6)).extrude(x1 - x0).val()
    return h


def rod_end(p, axis, open_dir):
    """Rod end (ball cup) in link coordinates: ball centre at the origin, body toward +x, socket axis 'y'
    or 'z', open on one side only (open_dir = +1 or -1 along the socket axis, toward the ball stud),
    closed by a cap on the other side. Spherical socket with a small clearance (the rod end turns on
    the ball), opening smaller than the ball: the lip wraps the ball beyond its equator, so the rod
    end clicks onto the ball and holds."""
    e, ring_d, ring_w, af, depth = p["rod_end"]
    c = p["socket_closed"]                                  # ball centre to the closed face
    clear, d_open = p["socket_fit"]
    rb = p["ball"][0] / 2 + clear                           # spherical socket: the rod end turns on the ball
    cyl = cyl_y if axis == "y" else cyl_z
    a, b = sorted((open_dir * (ring_w - c), -open_dir * c))
    ring = cyl(ring_d / 2, a, b, 0, 0)
    # opening smaller than the ball: the lip wraps the ball beyond its equator (snap fit)
    cavity = cq.Solid.makeSphere(rb, cq.Vector(0, 0, 0), angleDegrees1=-90, angleDegrees2=90).fuse(
        cyl(d_open / 2, *sorted((0.0, open_dir * (ring_w - c + 1))), 0, 0))
    body = hex_x(af, ring_d / 2 - 1.5, e)
    s = ring.fuse(body).cut(cavity).cut(cyl_x(p["turnbuckle"][1] / 2, e - depth, e + 1, 0, 0))
    return s.clean()


def link_parts(p, gap, inner_open=-1, outer_open=-1):
    """Link in link coordinates (inner ball at the origin, outer ball at x = L): rod ends, turnbuckle,
    length L between the ball centres. inner_open: side of the opening of the inner socket along y,
    outer_open: along z (-1: open toward the bottom)."""
    e = p["rod_end"][0]
    L = gap + 2 * e
    tl, td = p["turnbuckle"]
    haf, hl = p["turnbuckle_hex"]
    inner = rod_end(p, "y", inner_open)
    outer = rod_end(p, "z", outer_open).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180).translate(cq.Vector(L, 0, 0))
    tb = cyl_x(td / 2, L / 2 - tl / 2, L / 2 + tl / 2, 0, 0).fuse(hex_x(haf, L / 2 - hl / 2, L / 2 + hl / 2)).clean()
    return inner, outer, tb, L


def ball_stud(p, neck_dir, neck_len, thread_len=0.0):
    """Ball stud: ball at the origin, neck (diameter of the set screw) along neck_dir (unit vector), then
    the thread M3 in a tapped hole (modelled with the core diameter 2.5)."""
    bd, _, nd = p["ball"]
    s = cq.Solid.makeSphere(bd / 2, cq.Vector(0, 0, 0), angleDegrees1=-90, angleDegrees2=90)
    neck = cq.Solid.makeCylinder(nd / 2, neck_len, cq.Vector(0, 0, 0), cq.Vector(*neck_dir))
    s = s.fuse(neck)
    if thread_len:
        start = cq.Vector(*neck_dir) * neck_len
        s = s.fuse(cq.Solid.makeCylinder(1.249, thread_len, start, cq.Vector(*neck_dir)))
    return s.clean()


def tower_faces():
    """Back faces (wall side) of the shock towers in chassis plate coordinates and the height of the
    camber link holes: {end: (y of the back face, sign toward the wall, z of the holes, x of the holes)}."""
    import generate_shock_towers as T
    lp, up = load_params(LOWER), load_params(UPPER)
    out = {}
    for end, name in (("rear", "rear"), ("front", "front")):
        tp = load_params(T.TOWERS[name]["params"])
        cx, ch = T.layout(tp, lp, up)["camber"]
        s = T.tower_in_bulkhead(lp, up, name)
        if end == "front":
            s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180)
        bb = s.translate(cq.Vector(0, BULKHEAD_Y[end], PLATE_T)).BoundingBox()
        sign = 1 if end == "rear" else -1                   # wall side: toward the middle of the car
        out[end] = (bb.ymax if end == "rear" else bb.ymin, sign, PLATE_T + lp["axis_z"] + ch, cx, tp["thickness"])
    return out


def front_outer_ball(side):
    """Front: the outer ball sits on the top kingpin of the steering knuckle (the ball stud 4.8x9 is the top
    kingpin, as the original); its position comes from the running gear."""
    import generate_running_gear as G
    return G.front_camber_ball(G.load_params(G.PARAMS), side)


def rear_outer_ball(side):
    """Rear: the outer ball sits on the ball stud in the camber stud bore on top of the hub carrier (13.7 from the
    outer face of the bearing tube, owner); its position comes from the running gear."""
    import generate_running_gear as G
    return G.rear_camber_ball(G.load_params(G.PARAMS), side)


def link_points(p=None):
    """Centres of the inner and outer balls of the camber links: {(end, side): (p1, p2)}. The outer ball sits on the
    camber stud of the hub carrier (rear) or on the top kingpin of the knuckle (front)."""
    p = p or load_params(PARAMS)
    faces = tower_faces()
    off = p["ball"][1]
    out = {}
    for end, outer_ball in (("rear", rear_outer_ball), ("front", front_outer_ball)):
        yf, sign, zc, cx, tt = faces[end]
        for side in (1, -1):
            p1 = np.array([side * cx, yf + sign * off, zc])
            out[(end, side)] = (p1, outer_ball(side))
    return out


def gaps(p):
    """Gap between the rod ends from the positions of the balls (front and rear)."""
    pts = link_points(p)
    return {end: float(np.linalg.norm(pts[(end, 1)][1] - pts[(end, 1)][0])) - 2 * p["rod_end"][0]
            for end in ("front", "rear")}


def links_in_plate(p=None):
    """Camber links on the speedrun chassis (chassis plate coordinates): list of (name, kind, solid),
    kind "rodend" (2 rod ends of a link), "link" (turnbuckle, ball studs)."""
    p = p or load_params(PARAMS)
    faces = tower_faces()
    bd, off, nd = p["ball"]
    out = []
    pts = link_points(p)
    for end, label in (("rear", "End B"), ("front", "End A")):
        yf, sign, zc, cx, tt = faces[end]
        for side, sname in ((1, "right"), (-1, "left")):
            p1, p2 = pts[(end, side)]
            L = float(np.linalg.norm(p2 - p1))
            gap = L - 2 * p["rod_end"][0]
            th = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
            pitch = math.degrees(math.atan2(p2[2] - p1[2], math.hypot(p2[0] - p1[0], p2[1] - p1[1])))
            # opening of the inner socket toward the tower (stud direction -sign along y in plate coordinates)
            inner_open = 1 if -sign * math.cos(math.radians(th)) > 0 else -1
            inner_r, outer_r, tb, _ = link_parts(p, gap, inner_open, -1)

            def place(sol):
                return (sol.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), -pitch)
                        .rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), th).translate(cq.Vector(*p1)))
            rods = cq.Compound.makeCompound([place(inner_r), place(outer_r)])
            st_in = ball_stud(p, (0, -sign, 0), off + tt + 1.0).translate(cq.Vector(*p1))
            # outer ball stud: rear vertical into the hub carrier; front: the top kingpin of the knuckle (running gear)
            st_out = ball_stud(p, (0, 0, -1), p["outer_neck"], 3.5).translate(cq.Vector(*p2)) if end == "rear" else None
            out.append((f"camber link {label} {sname}: rod ends", "rodend", rods))
            out.append((f"camber link {label} {sname}: turnbuckle M3x37", "link", place(tb)))
            out.append((f"camber link {label} {sname}: ball studs", "link",
                        cq.Compound.makeCompound([st_in] + ([st_out] if st_out is not None else []))))
    return out


DRAWING = "photos/cad_camber_links_drawing.png"


def drawing(p, path=DRAWING):
    """Side views of the front and the rear camber link with the gap between the rod ends."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mesh_views import basis, draw_mesh, iso_basis, subdivide

    def tess(sol):
        v, i = sol.tessellate(0.01, 0.1)
        v = np.array([[q.x, q.y, q.z] for q in v])
        return v[np.array(i)]
    fig = plt.figure(figsize=(14, 6.2))
    fig.suptitle("Camber links: turnbuckle M3x37 with 2 rod ends (own design, partly based on the T410R)",
                 fontsize=11, y=0.98)
    e = p["rod_end"][0]
    g = gaps(p)
    for row, (name, gap) in enumerate((("Front upper link (C), End A, 2 pieces", g["front"]),
                                       ("Rear upper link (D), End B, 2 pieces", g["rear"]))):
        inner, outer, tb, L = link_parts(p, gap)
        T, C = [], []
        for sol, col in ((inner, (0.15, 0.15, 0.16)), (outer, (0.15, 0.15, 0.16)), (tb, (0.75, 0.76, 0.8))):
            t = subdivide(tess(sol), 0.5)
            T.append(t)
            C.append(np.tile(col, (len(t), 1)))
        ax = fig.add_axes([0.04, 0.52 - 0.46 * row, 0.6, 0.36])
        lo, hi = draw_mesh(ax, np.concatenate(T), basis((0, 1, 0), (1, 0, 0), (0, 0, 1)),
                           tri_colors=np.concatenate(C), depth_cue=0.2)
        src = "ball on the hub carrier" if row == 1 else "ball on the top kingpin"
        for x0, x1, yy, txt in ((e, L - e, -6.0, f"{gap:.1f} (gap between the rod ends, {src})"),
                                (0, L, -9.5, f"{L:.1f} between the ball centres")):
            ax.annotate("", (x0, yy), (x1, yy), arrowprops=dict(arrowstyle="<->", lw=0.8, color="#b42318"))
            ax.text((x0 + x1) / 2, yy + 0.5, txt, ha="center", va="bottom", fontsize=8, color="#b42318")
        ax.plot([0, 0], [-10, 0], color="#b42318", lw=0.5)
        ax.plot([L, L], [-10, 0], color="#b42318", lw=0.5)
        ax.set_xlim(-6, L + 6)
        ax.set_ylim(-12, 6)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(name + ": inner rod end (left) on the shock tower,\nouter rod end on the C-hub or hub carrier, turned by "
                     "90 degrees", fontsize=9, loc="left")
        ax2 = fig.add_axes([0.68, 0.52 - 0.46 * row, 0.3, 0.36])
        if row == 0:
            draw_mesh(ax2, np.concatenate(T), iso_basis(-60, 25), tri_colors=np.concatenate(C), depth_cue=0.2)
            ax2.set_aspect("equal")
            ax2.autoscale_view()
            ax2.axis("off")
            continue
        # section through the inner socket on the ball stud (plane z = 0)
        stud = ball_stud(p, (0, -1, 0), p["ball"][1] + 2.0)
        cut = box(-6, 14, -8, 6, -6, 0)
        T2, C2 = [], []
        for sol, col in ((inner.intersect(cut), (0.15, 0.15, 0.16)), (stud.intersect(cut), (0.78, 0.79, 0.82))):
            t = subdivide(tess(sol), 0.3)
            T2.append(t)
            C2.append(np.tile(col, (len(t), 1)))
        lo2, hi2 = draw_mesh(ax2, np.concatenate(T2), basis((0, 0, -1), (1, 0, 0), (0, 1, 0)),
                             tri_colors=np.concatenate(C2), depth_cue=0.1)
        clear, d_open = p["socket_fit"]
        ax2.annotate(f"opening {d_open:g} < ball {p['ball'][0]:g}:\nthe lip holds the ball (click on)",
                     (d_open / 2, -(p["rod_end"][2] - p["socket_closed"])), (6.5, -6.5), fontsize=7.5,
                     arrowprops=dict(arrowstyle="-", lw=0.6, color="#b42318"), color="#b42318")
        ax2.annotate(f"spherical socket, {clear:g} clearance:\nturns on the ball", (-1.8, 1.7), (2.5, 4.6), fontsize=7.5,
                     arrowprops=dict(arrowstyle="-", lw=0.6, color="#b42318"), color="#b42318")
        ax2.set_xlim(-6, 14)
        ax2.set_ylim(-8.5, 6.5)
        ax2.set_aspect("equal")
        ax2.axis("off")
        ax2.set_title("Section through the inner rod end on the ball stud", fontsize=9, loc="left")
    fig.text(0.04, 0.01, "Rod ends: ball cups open on one side only (toward the ball stud), for RC standard ball studs; they click onto "
             "the balls (opening smaller than the ball) and turn on them. Dimensions assumed; threads not modelled.", fontsize=8.5)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Generate the camber links of the speedrun chassis.")
    parser.parse_args()
    p = load_params(PARAMS)
    g = gaps(p)                                        # purchased parts: model in memory only, no part files (owner)
    for name, gap in (("front", g["front"]), ("rear", g["rear"])):
        inner, outer, tb, L = link_parts(p, gap)
        s = cq.Compound.makeCompound([inner, outer, tb])
        print(f"camber link {name}: valid: {s.isValid()}, gap between the rod ends {gap:.1f} mm, ball centres {L:.1f} mm apart")

    drawing(p)
    print(f"Wrote {DRAWING}")

    # checks on the speedrun chassis
    import generate_speedrun_assembly as A
    others = [(n, s) for n, k, s in A.build() if not n.startswith("camber link")]
    print("checks (camber links on the speedrun chassis)")
    worst = 0.0
    for name, kind, s in links_in_plate(p):
        bb = s.BoundingBox()
        res = []
        for on, o in others:
            ob = o.BoundingBox()
            if ob.xmin > bb.xmax or ob.xmax < bb.xmin or ob.ymin > bb.ymax or ob.ymax < bb.ymin or ob.zmin > bb.zmax \
                    or ob.zmax < bb.zmin:
                continue
            v = s.intersect(o).Volume()
            worst = max(worst, v)
            d = s.distance(o)
            d = d[0] if isinstance(d, tuple) else d
            res.append((d, f"{on}: overlap {v:.4f} mm3, distance {d:.2f}"))
        res.sort()
        print(f"  {name}: " + ("; ".join(r for _, r in res[:2]) if res else "no part nearby"))
    print(f"largest overlap {worst:.4f} mm3")


if __name__ == "__main__":
    main()
