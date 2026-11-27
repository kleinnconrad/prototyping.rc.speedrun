"""Generate the running gear of the speedrun chassis (own design, partly based on the Carten T410R).

The running gear completes the build: wheel suspension (front C-hubs with steering knuckles, rear
hub carriers), axles with hex hubs, CVD drive shafts, steering (posts, bellcranks joined by a
rigid bridge, steering links, servo link), servo across the car with the horn facing forward in
the floating servo mount, dampers and sway bars (trapezoid with ball ends and drop links as the T410R). The design
follows the principle of the T410R and deviates from it where the function requires. All values
with their source: cad/generic_parts/running_gear_parameters.json.

Placement (chassis plate coordinates): ride height 10 mm front (setup sheet 4); rear axle height from the hub carrier
with the wishbones horizontal (ride height 10.3 mm in the model, setup sheet 4: 15 mm), rear
wheel centres as the original car at +-80.5 mm (overall width 187 mm over tyres of 26 mm), front 2 mm further out
(front wishbone 51.7 mm for the front CVD drive shafts, owner), caster 10 degrees front, rear toe from the pivot blocks.
The wishbones are horizontal. The parts of the right side are built and
mirrored to the left side.

Usage (from the root directory of the repository):
    python scripts/cad/generate_running_gear.py

The script writes the STEP and STL files of the own parts to manufacture (one file per part, right
side, in the assembly position: chassis plate coordinates; one folder per group, see FOLDERS), the drawing
photos/cad_running_gear_drawing.png, the free steering angle of the front knuckles and checks all
new parts against each other and against the parts of the assembly (overlap).

Requires the packages cadquery and matplotlib.
"""
import argparse
import itertools
import math
import os
import sys

import numpy as np
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_bulkhead_lower import box, cyl_x, cyl_y, cyl_z, load_params  # noqa: E402
from generate_top_brace_speedrun import BULKHEAD_Y  # noqa: E402
import generate_camber_links as CL  # noqa: E402
import generate_wishbones as W  # noqa: E402
import edge_treatment as ET  # noqa: E402
import palette as P  # noqa: E402

PARAMS = "cad/generic_parts/running_gear_parameters.json"
DRIVE = "cad/generic_parts/driveshaft/driveshaft_parameters.json"
LOWER = "cad/speedrun_parts/bulkhead/bulkhead_lower_parameters.json"
UPPER = "cad/speedrun_parts/bulkhead/bulkhead_upper_parameters.json"
OUT = "cad/generic_parts"
DRAWING = "photos/cad_running_gear_drawing.png"
PLATE_T = 2.0
TAP = 2.5                                                    # tap drill M3
AXIS_Z = PLATE_T + 17.2                                      # diff axes
XA_END = 4.5                                                 # end of the upper arm of the C-hub beyond the kingpin axis
EDGE_REPORT = {}                                             # edge treatment of the printed parts (name -> report)


def grub_boss_depth(p):
    """Depth of the boss of the grub screw below the axis of the hinge pin: pin radius + screw length + recess, so
    the grub screw M3x4 lies fully in the thread with its tip on the pin (owner)."""
    length, recess, _ = p["grub_screw_boss"]
    return 1.5 + length + recess


# ------------------------------------------------------------------ helpers
def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def frame(xdir, zdir):
    """Rotation matrix with the columns x', y', z' (x' made perpendicular to z')."""
    z = unit(zdir)
    x = np.asarray(xdir, float)
    x = unit(x - np.dot(x, z) * z)
    return np.column_stack([x, np.cross(z, x), z])


def place(solid, R, t):
    """Rigid transformation: rotation matrix R (columns = new axes), translation t."""
    from OCP.gp import gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    tr = gp_Trsf()
    R = np.asarray(R, float)
    tr.SetValues(*[float(v) for v in (R[0, 0], R[0, 1], R[0, 2], t[0], R[1, 0], R[1, 1], R[1, 2], t[1],
                                      R[2, 0], R[2, 1], R[2, 2], t[2])])
    return cq.Shape.cast(BRepBuilderAPI_Transform(solid.wrapped, tr, True).Shape())


def cyl_between(r, a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    return cq.Solid.makeCylinder(r, float(np.linalg.norm(d)), cq.Vector(*a), cq.Vector(*unit(d)))


def sphere(r, c):
    return cq.Solid.makeSphere(r, cq.Vector(*c), angleDegrees1=-90, angleDegrees2=90)


def fuse(*solids):
    s = solids[0]
    for o in solids[1:]:
        s = s.fuse(o)
    return s.clean()


def hex_z(af, z0, z1, x=0.0, y=0.0):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).polygon(6, af / math.cos(math.pi / 6)) \
        .extrude(z1 - z0).val()


def hex_x(af, x0, x1, y=0.0, z=0.0):
    return cq.Workplane("YZ").workplane(offset=x0).center(y, z).polygon(6, af / math.cos(math.pi / 6)) \
        .extrude(x1 - x0).val()


def prism_z(pts, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0).val()


def mirror_x(solid):
    return solid.mirror("YZ")


# ------------------------------------------------------------------ ball joints
def rod_end_canon(e, bore_d, bore_depth, cl):
    """Rod end (ball cup) in canonical coordinates: ball centre at the origin, body toward +x, socket
    axis z, opening toward +z (snap fit on the ball, see camber link parameters)."""
    _, ring_d, ring_w, af, _ = cl["rod_end"]
    c = cl["socket_closed"]
    clear, d_open = cl["socket_fit"]
    rb = cl["ball"][0] / 2 + clear
    ring = cyl_z(ring_d / 2, -c, ring_w - c, 0, 0)
    body = hex_x(af, ring_d / 2 - 1.5, e)
    cavity = sphere(rb, (0, 0, 0)).fuse(cyl_z(d_open / 2, 0, ring_w - c + 1, 0, 0))
    s = ring.fuse(body).cut(cavity)
    if bore_d:
        s = s.cut(cyl_x(bore_d / 2, e - bore_depth, e + 1, 0, 0))
    return s.clean()


def rod_end_at(ball, opening, body_dir, e, cl, bore_d=3.0, bore_depth=7.0):
    """Rod end on a ball: body exactly along body_dir (the link), socket axis as close as possible to
    the opening direction (the cup tilts on the ball)."""
    u = unit(body_dir)
    o = np.asarray(opening, float)
    o = unit(o - np.dot(o, u) * u)
    R = np.column_stack([u, np.cross(o, u), o])
    return place(rod_end_canon(e, bore_d, bore_depth, cl), R, np.asarray(ball, float))


def stud(ball, out, free, thread, ball_d=4.8):
    """Ball stud: ball, neck 3.0 (free length from the face of the part to the ball centre), thread M3
    into the part (modelled with the core diameter 2.5 in the tap hole 2.5)."""
    ball, out = np.asarray(ball, float), unit(out)
    face = ball - out * free
    return fuse(sphere(ball_d / 2, ball), cyl_between(1.5, ball, face), cyl_between(TAP / 2 - 0.001, face,
                                                                                    face - out * thread))


def link(a, open_a, b, open_b, e, cl, hex_af=4.0):
    """Turnbuckle link between the balls a and b: 2 rod ends and the turnbuckle (M3, 5 mm in each rod
    end). Returns (rod ends, turnbuckle, gap between the rod ends)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    u = unit(b - a)
    L = np.linalg.norm(b - a)
    rods = cq.Compound.makeCompound([rod_end_at(a, open_a, u, e, cl), rod_end_at(b, open_b, -u, e, cl)])
    t0, t1 = a + u * (e - 5.0), b - u * (e - 5.0)
    tb = cyl_between(1.5, t0, t1)
    mid = (a + b) / 2
    if L - 2 * e > 6:
        R = frame(np.cross(u, [0, 0, 1]) if abs(u[2]) < 0.9 else [1, 0, 0], u)
        tb = tb.fuse(place(hex_z(hex_af, -2, 2), R, mid)).clean()
    return rods, tb, L - 2 * e


# ------------------------------------------------------------------ geometry of the car
def outer_pin_frame(end, lines=None, ap=None):
    """Frame of the outer hinge pin of the right arm: origin O on the outer hinge pin in the middle of the arm,
    ex along the arm (horizontal, toe), ey along the outer hinge pin."""
    lines = lines or W.pin_lines()
    ap = ap or W.load_params(W.PARAMS)
    J = ap[f"{end}_arm_length"]
    O = W.arm_point(end, 1, (J, 0, 0), lines)
    ex = unit(W.arm_point(end, 1, (J + 1, 0, 0), lines) - O)              # along the arm (horizontal)
    ey = np.array([-ex[1], ex[0], 0.0])                                  # along the outer hinge pin
    return O, ex, ey


def rear_carrier_layout(p):
    """Main positions of the rear hub carrier in the frame of the rear arm (origin on the outer hinge pin, x along
    the arm, z up), from the values of the owner: radius of the tube on the hinge pin, outer and inner end of the
    bearing tube, axle (za), top face, x of the camber stud bore (centred on the middle plane of the part, y = 0)."""
    t_len, t_d, _, height, stud, tube_low = p["rear_carrier"]
    r_lug = p["rear_carrier_bores"][2]
    x1 = r_lug                                                   # outer end of the tube, flush with the tube on the pin
    return {"r_lug": r_lug, "x1": x1, "x0": x1 - t_len, "za": tube_low - r_lug + t_d / 2, "zt": height - r_lug,
            "stud_x": x1 - stud}


def rear_camber_ball(p, side=1):
    """Centre of the outer ball of the rear camber link (chassis coordinates): the ball stud is screwed vertically
    into the camber stud bore on top of the hub carrier (13.7 from the outer face of the bearing tube, owner); the ball lies
    the neck of the stud above the top face. side: 1 right, -1 left."""
    O, ex, ey = outer_pin_frame("rear")
    lay = rear_carrier_layout(p)
    R = np.column_stack([ex, ey, [0, 0, 1.0]])
    ball = O + R @ np.array([lay["stud_x"], 0.0, lay["zt"] + CL.load_params(CL.PARAMS)["outer_neck"]])
    return ball * np.array([side, 1.0, 1.0])


def corners(p, lp):
    """Points of the right side: outer hinge pins, axle heights, damper and sway ball positions."""
    lines = W.pin_lines()
    ap = W.load_params(W.PARAMS)
    links = CL.link_points()
    faces = CL.tower_faces()
    import generate_shock_towers as T
    rf, rr = p["ride_height"]
    out = {}
    for end, kind, ride in (("front", "front", rf), ("rear", "rear", rr)):
        yi, yo = ap[f"{kind}_rail_y"]
        O, ex, ey = outer_pin_frame(end, lines, ap)
        tp = load_params(T.TOWERS[end]["params"])
        dx_t, dz_t = T.layout(tp, lp, load_params(UPPER))["damper"]
        yb, sign, _, _, tt = faces[end]
        y_front = yb - sign * tt                                         # damper side of the tower
        outw = -sign                                                     # toward the outer end of the car
        # damper in the plane 8.3 in front of the tower (collar 15); lower ball on a stud along the hole of the shock
        # plate given by damper_hole_z (height above the bottom face of the chassis plate)
        y_d = y_front + outw * p["damper_plane"]
        faces_a = [(W.arm_point(end, 1, (hx, -yo, hz), lines), W.arm_point(end, 1, (hx, -yo - 1, hz), lines))
                   for hx, hz in ap[f"{kind}_shock_holes"]]
        z_hole = p["damper_hole_z"][0 if end == "front" else 1]
        fa, fa1 = min(faces_a, key=lambda f: abs(f[0][2] - z_hole))
        n_a = unit(fa1 - fa)
        t_a = (y_d - fa[1]) / n_a[1]
        bot = fa + n_a * t_a
        top = np.array([dx_t, y_d, PLATE_T + lp["axis_z"] + dz_t])
        sx, sz = ap[f"{kind}_sway_holes"][0]
        fb = W.arm_point(end, 1, (sx, yo, sz), lines)
        n_b = unit(W.arm_point(end, 1, (sx, yo + 1, sz), lines) - fb)
        sway = fb + n_b * p["ball_offset"]
        # front: axle height from the ride height (wishbones horizontal); rear: from the hub carrier with the
        # wishbones horizontal (owner), the rear ride height follows from it
        axle_z = p["wheel_r"] - ride if end == "front" else O[2] + rear_carrier_layout(p)["za"]
        out[end] = {"O": O, "ex": ex, "ey": ey, "axle_z": axle_z, "camber": links[(end, 1)][1],
                    "damper_top": top, "damper_bot": bot, "tower_front": y_front, "outw": outw, "sway": sway,
                    "n_a": n_a, "t_a": t_a, "n_b": n_b,
                    "plate_face": W.arm_point(end, 1, (ap[f"{kind}_shock_holes"][0][0], -yo, 0), lines)[1],
                    "rail_b_face": W.arm_point(end, 1, (sx, yo, 0), lines)[1], "tt": tt, "yo": yo}
    return out


# ------------------------------------------------------------------ front corner
def top_face(p):
    """Local z (kingpin frame) of the top face of the upper arm of the C-hub (square to the kingpin axis): face of the
    upper arm toward the boss (gap) plus its thickness; the top sleeve (on its washer on the boss) stands
    guide_sleeve_proud above it."""
    kz1, gap, t_up = p["knuckle"][1], p["front_c_hub"][3], p["front_c_hub"][4]
    return kz1 + gap + t_up


def kingpin_y(p, O, outw):
    """y of the front kingpin axis at the height of the axle: kingpin_y toward the middle of the car from the middle
    of the wishbone (O: outer hinge pin point in the middle of the wishbone)."""
    return O[1] - outw * p["kingpin_y"]


def front_camber_ball(p, side=1):
    """Centre of the outer ball of the front camber link (chassis coordinates): the camber ball stud is the top
    kingpin (as the original, manual step 15: ball stud 4.8x9 through the guide sleeve and the washer into the
    knuckle), so the ball sits on the kingpin axis above the upper end of the sleeve. side: 1 right, -1 left."""
    ap = W.load_params(W.PARAMS)
    O = W.arm_point("front", 1, (ap["front_arm_length"], 0, 0), W.pin_lines())
    a = math.radians(p["caster"])                                         # front: top toward the middle (outw = +1)
    zl = top_face(p) + p["guide_sleeve_proud"] + p["ball_offset"]                     # ball stud on the end of the sleeve
    ball = np.array([p["kingpin_x"], kingpin_y(p, O, 1) - math.sin(a) * zl,
                     -p["ride_height"][0] + p["wheel_r"] + math.cos(a) * zl])
    return ball * np.array([side, 1.0, 1.0])


def kingpin_frame(p, c):
    """Frame of the front kingpin: origin in the centre of the outer CVD joint (on the kingpin axis at the
    height of the axle, kingpin_y toward the middle of the car from the middle of the wishbone), x along the axle,
    z along the kingpin axis (caster: top toward the middle of the car). The knuckle is built in this frame; its
    faces toward the C-hub are square to the kingpin axis."""
    a = math.radians(p["caster"]) * c["outw"]
    R = np.array([[1.0, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    J = np.array([p["kingpin_x"], kingpin_y(p, c["O"], c["outw"]), c["axle_z"]])
    return R, J


def front_corner(p, d, c):
    """Front right corner (End A): C-hub with 10 degrees caster, knuckle, kingpins, outer hinge pin, axle,
    bearings, hex hub, pin; returns dict name -> (kind, solid), the joint centre and the steering ball."""
    O = c["O"]
    yc = O[1]                                                             # middle of the wishbone
    R, J = kingpin_frame(p, c)                                            # kingpin axis: kingpin_y toward the middle
    kd = R[:, 2]
    c["kd"], c["R_k"], c["J"] = kd, R, J
    K = lambda s: place(s, R, J)                                          # kingpin frame -> chassis
    bx0, bx1, r_pass, gap, t_up = p["front_c_hub"]
    w_low, w_back, w_arm, z_w = p["front_c_hub_width"]
    kz0, kz1, r_boss, r_ring, xr0, xr1, d_lip, r_cup = p["knuckle"]
    d_seat, t_seat, x_cup, d_kp = p["knuckle_bores"]
    xs0 = xr0 + x_cup                                                     # end of the entry bore (section of the joint cup)
    xl0 = xs0 + t_seat                                                    # lip: inner face (end of the inner seat)
    xl1 = xr1 - t_seat                                                    # lip: outer face (end of the outer seat)
    xb = bx1 - J[0]                                                       # inner face of the back plate (local)
    zu = r_ring + 1.0                                                     # bottom of the upper arm: 1.0 above the ring
    rs = r_boss + 0.5                                                     # U-slot around the upper boss
    zf = top_face(p)                                                                      # top face of the upper arm
    # kingpin sleeves from standard parts (owner, 2026-11-22): on each knuckle boss a washer M3 DIN 125-A (thrust face
    # against the C-hub, in place of the flange of the Carten sleeve), then a plain brass spacer sleeve 4.8 x 3.2 x 4.0
    # in the bore of the C-hub; the screw (bottom) and the ball stud (top) clamp sleeve and washer to the knuckle
    d_sl, d_sl_in, l_sl, d_w, t_w, h_d, h_h, d_bore = p["guide_sleeve"]
    proud = p["guide_sleeve_proud"]                                                       # sleeves proud of the C-hub
    r_b = d_bore / 2                                                                      # bores of the sleeves
    zst = kz1 + t_w + l_sl                                                                # upper end of the top sleeve
    zl1 = kz0 - t_w                                                                       # lower washer: zl1 .. kz0
    zl0 = zl1 - l_sl                                                                      # lower end of the lower sleeve
    assert abs(zf - (zst - proud)) < 1e-9 and abs(gap - t_w - 0.05) < 1e-9, "front_c_hub does not match the sleeves"
    # C-hub in 2 frames (owner: the caster lies between the bore of the outer hinge pin and the kingpin bores):
    # the lug on the outer hinge pin, the lower arm and the narrow back plate lie between the rails of the
    # wishbone (chassis coordinates, centred on the middle of the wishbone); the wide back plate (horizontal bottom
    # face at z_w) and the upper arm are built in the frame of the kingpin axis (parallel to the axis and centred on
    # it; top face square to the axis). The upper arm is solid down to 1.0 above the ring of the knuckle, with a
    # U-slot around the upper boss (open toward the wheel: the knuckle slides in); space of the knuckle and U-slot
    # square to the kingpin. Bottom face of the lower arm and of the narrow back plate square to the kingpin axis
    # (caster angle), 0.1 above the lower end of the lower guide sleeve: the sleeve stands 0.1 proud, so the head of
    # the screw bears only on the sleeve (owner); the tube on the outer hinge pin stays complete. The top face of the
    # upper arm (zf) lies 0.1 below the upper end of the top sleeve (owner) for the same reason (ball stud)
    # lower arm up to 3.0 beyond the axis of the outer hinge pin: its end face meets the tube at 146 deg and is at
    # least 1.5 high below the face toward the lower boss (no sliver face for the edge treatment)
    body = fuse(box(bx0, O[0] + 3.0, yc - w_low / 2, yc + w_low / 2, O[2] - 6.0, J[2] - 5.0),
                box(bx0, bx1, yc - w_low / 2, yc + w_low / 2, O[2] - 6.0, z_w + 0.5),
                K(box(bx0 - J[0], bx1 - J[0], -w_back / 2, w_back / 2, -20.0, zf)).intersect(
                    box(bx0 - 1.0, bx1 + 1.0, yc - 30.0, yc + 30.0, z_w, J[2] + 30.0)),
                K(box(bx0 - J[0], XA_END, -w_arm / 2, w_arm / 2, 0.0, zf)))          # upper arm 4.5 beyond the axis
    z_bot = zl0 + proud                                                                   # bottom face (local z)
    body = body.cut(K(box(-60.0, 60.0, -60.0, 60.0, -80.0, z_bot)))                       # bottom face: caster angle
    lug = p["front_c_hub_lug"] / 2                                                     # tube on the outer hinge pin
    hub = fuse(cyl_y(3.6, yc - lug, yc + lug, O[0], O[2]), body)
    # space of the knuckle; it also trims the top of the tube on the hinge pin where the tube reaches above the face
    # toward the lower boss (up to approx. 0.2 at the inner end, the face is square to the kingpin axis): no sliver
    space = K(box(xb, 30, -30, 30, kz0 - gap, zu))
    hub = hub.cut(space)
    # shape (owner, 2026-11-23, after a study of a one-piece steering hub: the C-hub and the knuckle stay, the C-hub less
    # blocky and without sharp 90 degree corners): blends in the inner corners between the back plate and the arms on
    # the side of the knuckle (quarter ellipses, depth along x by height along the kingpin axis; upper: ends 0.1
    # outside the U-slot around the upper boss; lower: 0.5 from the washer 7.0 on the lower boss), corners of the end of
    # the upper arm rounded (r_end), top and bottom edge on the side of the chassis rounded (r_tb, r_bb), shoulders of
    # the wide back plate above the rails of the wishbone sloped at 45 degrees (the back plate narrows from w_back to
    # w_low without a notch). Faces toward the knuckle, bores, tube and passage are unchanged
    ax_t, az_t, ax_b, az_b, r_end, r_tb, r_bb = p["front_c_hub_rounds"]
    wa, xo, zlo = min(w_arm, w_back) / 2, bx0 - J[0], kz0 - gap

    def blend(x0, z0, dx, dz, y0, y1):
        """Quarter-ellipse blend in the kingpin frame: corner (x0, z0), depth dx along x, height dz along z (signs give
        the direction), from y0 to y1."""
        cx, cz = x0 + dx, z0 + dz
        q = box(min(x0, cx) - 0.01 * (dx < 0), max(x0, cx) + 0.01 * (dx < 0), y0, y1,
                min(z0, cz) - 0.01 * (dz > 0), max(z0, cz) + 0.01 * (dz < 0))
        ell = cq.Workplane("XZ", origin=(cx, y1 + 1, cz)).ellipse(abs(dx), abs(dz)).extrude(y1 - y0 + 2).val()
        return q.cut(ell)
    hub = fuse(hub, K(blend(xb, zu, ax_t, -az_t, -wa, wa)),
               K(blend(xb, zlo, ax_b, az_b, -30, 30)).intersect(box(bx0, bx1 + 10, yc - w_low / 2, yc + w_low / 2, -10, 60)))
    for sg_ in (-1, 1):                                                                   # corners of the arm end
        yr = sg_ * (wa - r_end)
        hub = hub.cut(K(box(XA_END - r_end, XA_END + 1, min(yr, sg_ * (wa + 1)), max(yr, sg_ * (wa + 1)), zu - 0.5, zf + 1)
                        .cut(cyl_z(r_end, zu - 1, zf + 2, XA_END - r_end, yr))))
    hub = hub.cut(K(box(xo - 1, xo + r_tb, -30, 30, zf - r_tb, zf + 1).cut(cyl_y(r_tb, -31, 31, xo + r_tb, zf - r_tb))))
    hub = hub.cut(K(box(xo - 1, xo + r_bb, -40, 40, z_bot - 1, z_bot + r_bb)
                    .cut(cyl_y(r_bb, -41, 41, xo + r_bb, z_bot + r_bb))))
    for sg_ in (-1, 1):                                                                   # shoulders at 45 degrees
        y_n = yc + sg_ * w_low / 2
        quad = [(y_n, z_w - 1.0), (y_n + sg_ * 25, z_w - 1.0), (y_n + sg_ * 25, z_w + 25), (y_n, z_w)]
        hub = hub.cut(cq.Workplane("YZ").workplane(offset=bx0 - 1).polyline(quad).close().extrude(bx1 - bx0 + 2).val())
    hub = hub.cut(K(fuse(cyl_z(rs, zu - 0.1, kz1 + gap, 0, 0), box(0, 30, -rs, rs, zu - 0.1, kz1 + gap))))  # U-slot
    zg = grub_boss_depth(p)                                                               # boss of the grub screw M3x4
    hub = fuse(hub, cyl_z(p["grub_screw_boss"][2] / 2, O[2] - zg, O[2] - 1.0, O[0], yc))
    hub = hub.cut(cyl_y(1.5, yc - 8, yc + 8, O[0], O[2]))                                  # outer hinge pin
    hub = hub.cut(cyl_x(r_pass, bx0 - 1, bx1 + 1, J[1], J[2]))                            # passage of the CVD
    # bores 4.9 through both arms for the sleeves (4.8: they turn with the knuckle, 0.1 clearance), no counterbores:
    # the washers lie in the gap of 0.55 between the boss and the arm (washer 0.5 + play 0.05) and slide on the arm
    # (thrust face); each sleeve stands 0.1 proud of the top face (under the ball stud) and of the bottom face (under
    # the head of the screw M3x8), both faces square to the kingpin axis (the outer hinge pin lies 6.75 beside the
    # kingpin axis: the bore and the head stay outside the tube on the pin)
    hub = hub.cut(K(cyl_z(r_b, kz1 + gap - 1.0, zf + 1.0, 0, 0)))                          # bore, top
    hub = hub.cut(K(cyl_z(r_b, zl0 - 1.0, kz0 - gap + 1.0, 0, 0)))                         # bore, bottom (through)
    hub = hub.cut(cyl_z(TAP / 2, O[2] - zg - 1, O[2], O[0], yc))                          # thread M3, grub screw
    # edge treatment (owner): chamfers on the sharp outer edges, radii in the sharp inner corners; the bores of the
    # sleeves get the entry chamfer on both ends (the washer, Ø7.0, covers the chamfer on the side of the knuckle)
    e_ch, e_r, e_ang = p["edge_treatment"]
    hub, EDGE_REPORT["C-hub"] = ET.treat(hub, e_ch, e_r, (), e_ang)
    # knuckle (kingpin frame) as the T410R knuckle (measured by the owner, manual step 15): ring for 2 bearings
    # 5x10x4 from the kingpin axis outward, pressed in from both ends against a lip; from the inner end a wider
    # bore around the joint cup up to the inner bearing; kingpin bosses above and below the inner end of the ring
    # with the bores for the kingpin set screws; flat steering arm in the middle plane of the axle: wide root along
    # the ring, diagonal to the end tab with 2 holes inboard of the kingpin axis; gussets between the arm and the
    # ring at the bosses; ball stud on top of the arm (as the original)
    sax, say, t_arm, t_web, d_hole2, z_arm, w_tab = p["steering_arm_ball"]
    wt = w_tab / 2
    sg = c["outw"]                                                        # toward the middle of the car along y: -sg
    kb_l = np.array([sax, say * sg, z_arm + t_arm / 2 + p["ball_offset"]])
    bx_, by_ = kb_l[0], kb_l[1]
    h2 = np.array([bx_, by_ + d_hole2 * sg])                              # second hole, toward the ring
    ay0, yt = -1.0 * sg, h2[1] + 3.0 * sg                                 # root inside the ring, start of the tab
    outline = [(xr0 + 0.3, ay0), (xr1 - 0.3, ay0), (bx_ + wt, yt), (bx_ + wt, by_), (bx_ - wt, by_), (bx_ - wt, yt),
               (xr0 + 0.6, -8.5 * sg)]                # inner edge straight back near the kingpin: clear of the C-hub
    a0, a1 = z_arm - t_arm / 2, z_arm + t_arm / 2
    arm = fuse(prism_z(outline, a0, a1), cyl_z(wt, a0, a1, bx_, by_))
    zw = min(t_web / 2, math.sqrt(r_ring ** 2 - 1.0) - 0.1)
    web = cq.Workplane("YZ").workplane(offset=xr0).polyline(
        [(ay0, z_arm - zw), (ay0, z_arm + zw), (-10.0 * sg, a1), (-10.0 * sg, a0)]).close().extrude(6.0).val()
    web = web.intersect(prism_z(outline, z_arm - t_web, z_arm + t_web))      # gussets at the bosses
    knu = fuse(cyl_x(r_ring, xr0, xr1, 0, 0), cyl_z(r_boss, kz0, kz1, 0, 0), arm, web)
    knu = knu.cut(cyl_x(r_cup, -10.0, xs0, 0, 0))                                        # entry bore around the joint cup
    knu = knu.cut(cyl_x(d_seat / 2, xs0 - 0.1, xl0, 0, 0))                               # seat of the inner bearing
    knu = knu.cut(cyl_x(d_lip / 2, xl0 - 0.1, xl1 + 0.1, 0, 0))                          # lip between the bearings
    knu = knu.cut(cyl_x(d_seat / 2, xl1, xr1 + 1.0, 0, 0))                               # seat of the outer bearing
    zb = r_cup - 0.5                                                                     # bores open into the entry bore
    knu = knu.cut(cyl_z(d_kp / 2, kz0 - 1, -zb, 0, 0)).cut(cyl_z(d_kp / 2, zb, kz1 + 1, 0, 0))   # kingpin set screws
    for hx, hy in ((bx_, by_), tuple(h2)):
        knu = knu.cut(cyl_z(TAP / 2, a0 - 1, a1 + 1, hx, hy))                            # threads M3, ball stud
    # kingpins, threaded into the bosses (bores 2.7, thread formed by the screw, as the original): top: the ball stud
    # 4.8x9 of the camber link (as the original, manual step 15) through the guide sleeve and the washer, which it
    # clamps to the boss (the ball sits on the kingpin axis); bottom: socket head screw M3x8 from below through the
    # second sleeve and the washer, which it clamps to the lower boss (the screw ends inside the boss, a longer screw
    # reaches into the entry bore). Knuckle, washers, sleeves and screws turn together in the bores 4.9 of the C-hub; threads
    # modelled with the core diameter in the bores 2.7
    zt0 = zst                                                                            # face of the ball stud
    pins = cq.Compound.makeCompound([K(fuse(cyl_z(d_kp / 2 - 0.001, zl0, zl0 + 8.0, 0, 0),
                                            cyl_z(h_d / 2, zl0 - h_h, zl0, 0, 0))),               # screw M3x8, bottom
                                     K(stud(np.array([0, 0, zt0 + p["ball_offset"]]), np.array([0, 0, 1.0]),
                                            p["ball_offset"], 9.0))])                            # ball stud 4.8x9, top
    c["camber_ball"] = J + R @ np.array([0, 0, zt0 + p["ball_offset"]])
    sleeves = cq.Compound.makeCompound([
        K(cyl_z(d_sl / 2, kz1 + t_w, zst, 0, 0).cut(cyl_z(d_sl_in / 2, kz1, zst + 1, 0, 0))),          # top
        K(cyl_z(d_sl / 2, zl0, zl1, 0, 0).cut(cyl_z(d_sl_in / 2, zl0 - 1, kz0, 0, 0)))])               # bottom
    washers = cq.Compound.makeCompound([
        K(cyl_z(d_w / 2, kz1, kz1 + t_w, 0, 0).cut(cyl_z(d_sl_in / 2, kz1 - 1, kz1 + 1, 0, 0))),       # top
        K(cyl_z(d_w / 2, zl1, kz0, 0, 0).cut(cyl_z(d_sl_in / 2, zl1 - 1, kz0 + 1, 0, 0)))])            # bottom
    # walls to the bore of the outer hinge pin (in the plane of the axle: kingpin axis to hinge pin axis along x)
    dk = O[0] - J[0]

    def walls(r, z0, z1):
        """Walls (front, rear) between a bore along the kingpin axis and the faces of the lower arm (yc +- w_low / 2),
        within the lower arm: above its bottom face (z = O[2]) and below its face toward the lower boss."""
        q = np.array([J + R @ np.array([r * math.cos(t), r * math.sin(t), z])
                      for z in np.arange(z0, min(z1, kz0 - gap) + 1e-9, 0.02) for t in np.linspace(0, 2 * math.pi, 181)])
        q = q[q[:, 2] >= O[2]]
        return round(float(yc + w_low / 2 - q[:, 1].max()), 2), round(float(q[:, 1].min() - (yc - w_low / 2)), 2)
    c["kingpin_layout"] = {"top face (local z)": zf, "upper end of the top sleeve": zst, "sleeve length": l_sl,
                           "lower washer": (zl1, kz0), "lower end": zl0,
                           f"bore {d_bore:g} to the tube on the hinge pin": round(dk - r_b - 3.6, 2),
                           "screw head to the tube on the hinge pin": round(dk - h_d / 2 - 3.6, 2),
                           "screw end (local z)": zl0 + 8.0,
                           "walls of the lower arm (front, rear)": {f"bore {d_bore:g}": walls(r_b, zl0 - 1.0, kz0)},
                           "bottom face (local z, square to the kingpin axis)": round(z_bot, 2),
                           "sleeve proud of the bottom face": round(z_bot - zl0, 2)}
    kb = J + R @ kb_l
    c["kb"] = kb
    hinge = cyl_y(1.5, yc - 13, yc + 13, O[0], O[2])
    parts = {"C-hub": ("upright", hub), "steering knuckle": ("upright", K(knu.clean())), "kingpins": ("axle", pins),
             "guide sleeves": ("axle", sleeves), "kingpin washers": ("axle", washers),
             "outer hinge pin 3x26": ("axle", hinge)}
    parts.update(axle_group(p, d, J, np.array([1.0, 0, 0]), (J[0] + xl0 - 4.0, J[0] + xl1), J[0] + xr1 + 0.5,
                            p["hex_hub"][1], shoulder=J[0] + xl0 - 4.1, cup_end=J[0] + xs0 - 0.2))    # bearings on the lip
    parts["ball stud of the steering arm"] = ("link", stud(kb, kd, p["ball_offset"], t_arm))            # on top
    return parts, J.copy(), kb


def steering_lock(p, c, parts, fixed):
    """Free steering angle of the front knuckle: the knuckle, the axle group and the steering ball stud turn
    about the kingpin axis; returns the largest angle (each direction, step 2.5 degrees) without overlap
    with the fixed parts (C-hub, CVD drive shaft, wishbone, hinge pin)."""
    turning = [parts[k][1] for k in ("steering knuckle", "ball stud of the steering arm", "hex hub 12", "wheel bearings 5x10x4")]
    kb, kd0 = c["kb"], c["kd"]
    turning.append(cyl_between(3.5, kb - kd0 * 3.0, kb + kd0 * 3.4))                         # rod end of the steering link
    axle = parts["axle with joint cup"][1]
    J, kd = c["J"], c["kd"]
    res = {}
    for sgn in (1, -1):
        free = 0.0
        for ang in np.arange(2.5, 45.1, 2.5):
            rot = lambda s: s.rotate(cq.Vector(*J), cq.Vector(*(J + kd)), sgn * ang)
            hit = False
            for s in turning + [axle]:
                rs = rot(s)
                for name, f in fixed:
                    if s is axle and name.startswith("CVD"):
                        continue                                                       # joint: ball and pin in the cup
                    if rs.intersect(f).Volume() > 1e-3:
                        hit = True
                        break
                if hit:
                    break
            if hit:
                break
            free = float(ang)
        res["steering arm toward the outside" if sgn > 0 else "steering arm toward the middle"] = free
    return res


def axle_group(p, d, joint, ax_dir, bearings, hub_x0, hub_w, shoulder=None, cup_end=None):
    """Axle with the joint cup, 2 bearings 5x10x4, hex hub with pin and grub screw thread, along ax_dir
    from the joint centre (positions as x along the axle relative to x = 0 of the front axle frame).
    shoulder: end of a shoulder 6.5 from the joint cup to the inner race of the inner bearing (front);
    cup_end: end of the joint cup (default 4.0 beyond the joint centre)."""
    ad, thr, cup_d, cup_l = p["axle"]
    hex_af = p["hex_hub"][0]
    pin_d = p["hex_hub"][3]
    j = joint[0]
    ce = j + 4.0 if cup_end is None else cup_end
    a = fuse(cyl_x(cup_d / 2, j - 4.5, ce, 0, 0), cyl_x(ad / 2, j + 3.9, hub_x0 + hub_w + 0.5, 0, 0),
             cyl_x(thr / 2, hub_x0 + hub_w + 0.4, hub_x0 + hub_w + 5.5, 0, 0))
    if shoulder is not None:
        a = fuse(a, cyl_x(3.25, ce - 0.1, shoulder, 0, 0))                                # shoulder on the inner race
    a = a.cut(cyl_x(3.3, j - 5, j + 3.3, 0, 0)).cut(box(j - 5, j + 3.3, -1.05, 1.05, -6, 6))   # bore and slots
    xp = hub_x0 + 2.0
    a = a.cut(cyl_z(pin_d / 2, -3, 3, xp, 0))
    hub = hex_x(hex_af, hub_x0, hub_x0 + hub_w).cut(cyl_x(ad / 2, hub_x0 - 1, hub_x0 + hub_w + 1, 0, 0))
    hub = hub.cut(box(hub_x0 - 1, xp + pin_d / 2 + 0.05, -1.05, 1.05, -7, 7))               # slot for the pin
    hub = hub.cut(cyl_y(TAP / 2, 0, 7, xp + 2.5, 0))                                      # thread M3, grub screw
    brg = cq.Compound.makeCompound([cyl_x(5.0, b0, b0 + 4, 0, 0).cut(cyl_x(2.5, b0 - 1, b0 + 5, 0, 0)) for b0 in bearings])
    pin = cyl_z(pin_d / 2 - 0.001, -5, 5, xp, 0)
    R = frame(ax_dir, (0, 0, 1))
    # parts built along x with the joint at x = joint[0]; place: rotate about the joint, translate to y, z
    T = lambda s: place(s.translate(cq.Vector(-j, 0, 0)), R, joint)
    return {"axle with joint cup": ("axle", T(a)), "hex hub 12": ("axle", T(hub)), "wheel bearings 5x10x4": ("axle", T(brg)),
            "axle pin 2x10": ("axle", T(pin))}


# ------------------------------------------------------------------ rear corner
def rear_corner(p, d, c):
    """Rear right corner (End B): hub carrier (values of the owner) in the frame of the rear arm (origin on the
    outer hinge pin, x along the arm, y along the pin: toe): tube on the outer hinge pin (bore 3.1 for the pin 3.0)
    between 2 spacers 3x7x3, the pin secured from below with a grub screw M3; bearing tube 10 long whose outer end is
    flush with the tube on the pin (outer end of the part), 2 bearings 5x10x4 in the ends of the tube, separated by
    a lip 1.0 high; lower end of the bearing tube 11.4 above the outer lower end of the tube on the pin; web on the
    inner end of the tube and a sloped arm up to the top tab, 30.4 above the outer lower end of the tube on the pin;
    camber stud bore 13.7 from the outer face of the bearing tube (the outer ball of the rear camber link sits on its
    stud); outer hinge pin, axle group."""
    O, ex, ey = c["O"], c["ex"], c["ey"]
    za = c["axle_z"] - O[2]
    t_len, t_d, w_web = p["rear_carrier"][:3]
    pin_bore, lip_h, _ = p["rear_carrier_bores"]
    lay = rear_carrier_layout(p)
    r_lug, x1, x0, zt, xc = lay["r_lug"], lay["x1"], lay["x0"], lay["zt"], lay["stud_x"]
    R = np.column_stack([ex, ey, [0, 0, 1.0]])
    rt = t_d / 2
    rb, wb = 5.0, 4.0                                                                   # bearings 5x10x4
    xs = min(xc - 3.5, x0)                                                              # inner end of the seat
    # along the pin, the column and the upper part (web, arm, top tab, gusset) are as wide as the tube on the pin
    # (owner: 9.2, flush with its ends); across, the column ends 1.0 inside the outer end of the bearing tube and
    # inside the tube on the pin (space for the edge treatment: radius 0.5 and chamfer 0.3 side by side)
    hw = 4.6
    car = fuse(cyl_y(r_lug, -hw, hw, 0, 0), box(-2.6, 2.6, -hw, hw, 0, za - 5.0), cyl_x(rt, x0, x1, 0, za),
               box(x0, x0 + w_web, -hw, hw, za, zt), box(xs, x0 + w_web, -hw, hw, zt - 3.5, zt))
    if xs < x0:                                                  # sloped arm from the inner end of the tube to the seat
        arm = [(x0 + 1.0, za + rt - 1.0), (x0 + w_web, za + rt - 1.0), (x0 + w_web, zt - 3.4), (xs, zt - 3.4)]
        car = fuse(car, cq.Workplane("XZ").polyline(arm).close().extrude(hw, both=True).val())
    # gusset (owner): triangle on the outer face of the web, as wide as the web, from the top face (no step) at 60 deg
    # down onto the bearing tube; it braces the web against the pull of the camber link on the top tab
    g_top, g_ang = p["rear_carrier_gusset"]
    xg, zg = x0 + w_web, zt - g_top
    xe = x1 - 1.0                                                # end inside the tube wall (below the tube surface)
    gus = [(xg - 0.5, za), (xg - 0.5, zg), (xg, zg), (xe, zg - (xe - xg) * math.tan(math.radians(g_ang))), (xe, za)]
    car = fuse(car, cq.Workplane("XZ").polyline(gus).close().extrude(hw, both=True).val())
    # shape (owner, 2026-11-23, as the C-hub: less blocky, no sharp 90 degree corners; function unchanged): inner end of
    # the top tab a half circle seen from above (about a point on the middle plane, as far inward as before), blend
    # between the column and the underside of the bearing tube on the side of the chassis (quarter ellipse revolved
    # about the axle: bx along the axle by bz down the column; the outer side keeps the 1.0 for the edge treatment)
    bx_, bz_ = p["rear_carrier_rounds"]
    xm = xs + hw
    car = car.cut(box(xs - 1, xm, -hw - 1, hw + 1, za, zt + 1).cut(cyl_z(hw, za - 1, zt + 2, xm, 0)))
    xa_, xb_ = -2.6 - bx_, -2.6
    ring = cyl_x(rt + bz_, xa_, xb_ + 0.01, 0, za).cut(cyl_x(rt - 0.01, xa_ - 1, xb_ + 1, 0, za))
    ell = (cq.Workplane("XY").moveTo(xa_, rt + bz_).ellipse(bx_, bz_).revolve(360, (0, 0, 0), (1, 0, 0)).val()
           .translate(cq.Vector(0, 0, za)))
    car = fuse(car, ring.cut(ell).intersect(box(xa_ - 1, xb_ + 0.01, -hw, hw, -10, za)))
    zg = grub_boss_depth(p)                                                               # boss of the grub screw M3x4
    car = fuse(car, cyl_z(p["grub_screw_boss"][2] / 2, -zg, -1.0, 0, 0))
    car = car.cut(cyl_y(pin_bore / 2, -6, 6, 0, 0))                                       # bore of the hinge pin
    car = car.cut(cyl_x(rb, x0 - 1, x0 + wb, 0, za)).cut(cyl_x(rb, x1 - wb, x1 + 1, 0, za))       # bearing seats
    car = car.cut(cyl_x(rb - lip_h, x0 - 1, x1 + 1, 0, za))                                       # lip between them
    car = car.cut(cyl_z(TAP / 2, zt - 6.0, zt + 1, xc, 0))                                 # thread M3, camber stud (through)
    car = car.cut(cyl_z(TAP / 2, -zg - 1, 0, 0, 0))                                       # thread M3, grub screw
    e_ch, e_r, e_ang = p["edge_treatment"]                                                # edge treatment (owner)
    keep = [cyl_x(rb + 0.05, x0 + 0.05, x1 - 0.05, 0, za)]                                # bearing seats and lip sharp
    car, EDGE_REPORT["hub carrier"] = ET.treat(car, e_ch, e_r, keep, e_ang)
    spacers = cq.Compound.makeCompound([cyl_y(3.5, s0, s0 + 3.0, 0, 0).cut(cyl_y(1.5, s0 - 1, s0 + 4, 0, 0))
                                        for s0 in (4.7, -7.7)])
    hinge = cyl_y(1.5, -13, 13, 0, 0)
    to_w = lambda s: place(s, R, O)
    parts = {"hub carrier": ("upright", to_w(car)), "spacers 3x7x3": ("axle", to_w(spacers)),
             "outer hinge pin 3x26": ("axle", to_w(hinge))}
    j = x0 - 5.0                                                     # joint cup 1.0 before the inner bearing
    ag = axle_group(p, d, np.array([j, 0, 0]), np.array([1.0, 0, 0]), (x0, x1 - 4.0), x1 + 0.5, p["hex_hub"][2])
    for k, (kind, s) in ag.items():
        parts[k] = (kind, to_w(s.translate(cq.Vector(0, 0, za))))
    rear_corner.hub_face = (O + R @ np.array([x1 + 0.5 + p["hex_hub"][2], 0, za]))[0]
    return parts, O + R @ np.array([j, 0, za])


# ------------------------------------------------------------------ CVD
def cvd(p, inner, outer):
    bone_d, ball_d, pin_d, pin_l = p["cvd"]
    s = fuse(cyl_between(bone_d / 2, inner, outer), sphere(ball_d / 2, inner), sphere(ball_d / 2, outer),
             cyl_between(pin_d / 2, inner - [0, 0, 5.5], inner + [0, 0, 5.5]),
             cyl_between(pin_d / 2, outer - [0, 0, pin_l / 2], outer + [0, 0, pin_l / 2]))
    return s


# ------------------------------------------------------------------ dampers
def spring(r_coil, wire_r, length, n):
    helix = cq.Wire.makeHelix(length / n, length, r_coil)                 # r_coil: centre line of the wire
    prof = cq.Wire.makeCircle(wire_r, helix.startPoint(), helix.tangentAt(0))
    return cq.Solid.sweep(prof, [], helix, isFrenet=True)


def damper(p, cl, top, bot, outw):
    """Standard 1:10 on-road damper between the ball studs top (tower) and bot (shock plate)."""
    bd, cd, sd, shd, bl, wire = p["damper"]
    e = 6.5
    a = unit(bot - top)
    L = float(np.linalg.norm(bot - top))
    R = frame([0, 1.0, 0], a)                       # z' along the damper axis, x' along y
    R = np.column_stack([R[:, 0], R[:, 1], R[:, 2]])
    ax = lambda s0, s1, r: place(cyl_z(r, s0, s1, 0, 0), R, top)
    opening = np.array([0, -outw * 1.0, 0])
    rods = cq.Compound.makeCompound([rod_end_at(top, opening, a, e, cl, bore_d=3.0, bore_depth=4.0),
                                     rod_end_at(bot, opening, -a, e, cl, bore_d=3.0, bore_depth=4.0)])
    body = fuse(ax(e, e + 3.0, cd / 2), ax(e + 3.0, e + 3.0 + bl, bd / 2), ax(e + 4.0, e + 6.0, sd / 2))
    shaft = ax(e + 3.0 + bl, L - e + 3.5, shd / 2)
    retainer = place(cyl_z(sd / 2 - 0.5, L - e - 1.0, L - e, 0, 0).cut(cyl_z(shd / 2 + 0.2, L - e - 2, L - e + 1, 0, 0)), R, top)
    sp_len = (L - e - 1.6) - (e + 6.6)
    try:
        spr = place(spring(sd / 2 - wire / 2, wire / 2, sp_len, 7).translate(cq.Vector(0, 0, e + 6.6)), R, top)
    except Exception:
        spr = place(cyl_z(sd / 2, e + 6.0, L - e - 1.0, 0, 0).cut(cyl_z(sd / 2 - wire, e + 5, L, 0, 0)), R, top)
    return {"damper rod ends": ("rodend", rods), "damper body with collar": ("damper", body),
            "damper shaft": ("axle", shaft), "damper spring": ("spring", spr), "spring retainer": ("damper", retainer)}, L


# ------------------------------------------------------------------ build
def build(p=None):
    """All parts of the running gear in chassis plate coordinates: list of (name, kind, solid)."""
    p = p or load_params(PARAMS)
    d = load_params(DRIVE)
    lp = load_params(LOWER)
    cl = load_params(CL.PARAMS)
    c = corners(p, lp)
    out = []

    def both(name, kind, solid, label):
        out.append((f"{name} {label} right", kind, solid))
        out.append((f"{name} {label} left", kind, mirror_x(solid)))

    xo_cup = lp["body_half_width"] + d["outdrive_gap"] + d["outdrive_length"] - 4.0       # inner pin of the CVD
    info = {}
    for end, label, yd in (("front", "End A", BULKHEAD_Y["front"] - lp["diff_axis_y"]),
                           ("rear", "End B", BULKHEAD_Y["rear"] + lp["diff_axis_y"])):
        cc = c[end]
        if end == "front":
            parts, joint, kb = front_corner(p, d, cc)
            info["kb"] = kb
            info["front kingpin"] = cc["kingpin_layout"]
        else:
            parts, joint = rear_corner(p, d, cc)
        for name, (kind, s) in parts.items():
            both(name, kind, s, label)
        inner = np.array([xo_cup, yd, AXIS_Z])
        both("CVD drive shaft", "cvd", cvd(p, inner, joint), label)
        info[end] = (inner, joint, float(np.linalg.norm(joint - inner)))
        # damper
        dparts, L = damper(p, cl, cc["damper_top"], cc["damper_bot"], cc["outw"])
        for name, (kind, s) in dparts.items():
            both(name, kind, s, label)
        info[f"damper {end}"] = L
        top, bot = cc["damper_top"], cc["damper_bot"]
        outw = np.array([0, cc["outw"] * 1.0, 0])
        tf = cc["tower_front"]
        st_top = fuse(sphere(2.4, top), cyl_between(1.5, top, np.array([top[0], tf - cc["outw"] * (cc["tt"] + 3.5), top[2]])))
        ny = tf - cc["outw"] * cc["tt"]
        nut = place(hex_z(5.5, 0, 2.4), frame([1, 0, 0], -outw), np.array([top[0], ny, top[2]])).cut(
            cyl_between(1.5, np.array([top[0], ny + 5 * cc["outw"], top[2]]), np.array([top[0], ny - 5 * cc["outw"], top[2]])))
        st_bot = stud(bot, cc["n_a"], cc["t_a"], 5.0)
        both("damper ball studs", "link", cq.Compound.makeCompound([st_top, st_bot]), label)
        both("nut M3 of the damper ball stud", "link", nut, label)
    # sway bars as the T410R (manual steps 22 and 23): plain trapezoid of wire, straight middle part in the holders
    # on the tabs of the lower bulkhead, a straight leg on each side to the ball end; vertical drop link from the
    # ball end down to the ball stud in rail B of the arm
    bar_d, z_bar, y_hold, x0 = p["sway_bar"]
    gap_l = p["sway_link"][0]
    be_d, be_neck, be_cd, be_cl, be_c0 = p["sway_ball_end"]
    e_rod = cl["rod_end"][0]
    for end, label in (("front", "End A"), ("rear", "End B")):
        cc = c[end]
        yb0 = BULKHEAD_Y[end]
        loc = (lambda x, y: (-x, yb0 - y)) if end == "front" else (lambda x, y: (x, yb0 + y))
        sw = cc["sway"]
        yb = loc(0, y_hold)[1]
        B = sw + np.array([0.0, 0.0, 2 * e_rod + gap_l])                                  # centre of the ball end
        M = np.array([x0, yb, z_bar])                                                   # end of the straight part
        u = unit(B - M)                                                                 # along the leg
        tip = B - u * 0.6                                                               # end of the bar in the ball end
        m = np.array([-1.0, 1.0, 1.0])
        segs = [cyl_between(bar_d / 2, M * m, M)]
        for s_ in (np.ones(3), m):
            segs += [cyl_between(bar_d / 2, M * s_, tip * s_), sphere(bar_d / 2, M * s_)]
        out.append((f"sway bar 1.4 {label}", "swaybar", fuse(*segs)))
        info[f"sway {end}"] = {"ball end": B.round(2), "leg": round(float(np.linalg.norm(B - M)), 1),
                               "rise of the leg (deg)": round(math.degrees(math.asin(u[2])), 1)}
        for sx in (1, -1):
            hx, hy = loc(sx * lp["swaybar_hole_x"], lp["swaybar_hole_y"])
            # holder from 4.3 outside to 2.7 inside the screw hole of the tab (y in the coordinates of the bulkhead)
            y0, y1 = sorted((loc(0, lp["swaybar_hole_y"] - 4.3)[1], loc(0, lp["swaybar_hole_y"] + 2.7)[1]))
            hold = box(hx - 3.2, hx + 3.2, y0, y1, AXIS_Z, AXIS_Z + 4.0)
            hold = hold.cut(cyl_z(1.6, AXIS_Z - 1, AXIS_Z + 5, hx, hy)).cut(cyl_x(bar_d / 2 + 0.05, hx - 4, hx + 4, yb, z_bar))
            out.append((f"sway bar holder {label} {'right' if sx > 0 else 'left'}", "steer", hold.clean()))
        # ball end on the bar: ball, neck, collar with the bore for the bar and the thread of the grub screw M3x3
        c0, c1 = B - u * be_c0, B - u * (be_c0 + be_cl)
        be = fuse(sphere(be_d / 2, B), cyl_between(be_neck / 2, B, c0 + u * 0.01), cyl_between(be_cd / 2, c0, c1))
        be = be.cut(cyl_between(bar_d / 2 + 0.05, c1 - u * 1.0, B + u * 0.3))
        up_ = unit(np.array([0.0, 0.0, 1.0]) - u * u[2])                                  # up, square to the bar
        cm = (c0 + c1) / 2
        be = be.cut(cyl_between(TAP / 2, cm, cm + up_ * (be_cd / 2 + 1.0)))
        both("sway bar ball end", "link", be, label)
        # drop link: rod end on the ball stud of the arm (opening toward the arm), rod end on the ball end
        # (opening toward the collar), set screw M3x12
        rods, screw, gap = link(sw, -cc["n_b"], B, -u, e_rod, cl)
        both("sway bar drop link rod ends", "rodend", rods, label)
        both("sway bar drop link set screw M3x12", "link", screw, label)
        both("sway ball stud", "link", stud(sw, cc["n_b"], p["ball_offset"], 5.0), label)
        info[f"sway {end}"]["gap of the drop link"] = round(float(gap), 2)
    # steering
    st = steering(p, cl, c, info["kb"])
    out += st
    return out, info


def plan_knuckle(Kp, K0, S, L):
    """Plan view: knuckle angle d (counterclockwise, rad) with |Kp + R(d)(K0 - Kp) - S| = L, nearest to 0."""
    v, w = K0 - Kp, S - Kp
    r, dw = np.linalg.norm(v), np.linalg.norm(w)
    cc = (r * r + dw * dw - L * L) / (2 * r * dw)
    if abs(cc) > 1:
        return None
    base, a0 = math.atan2(w[1], w[0]), math.atan2(v[1], v[0])
    sols = [((base + sg * math.acos(cc) - a0 + math.pi) % (2 * math.pi)) - math.pi for sg in (1, -1)]
    return min(sols, key=abs)


def ackermann(P, S, Kp, K, rear_axle_y):
    """Plan view of the steering (right side, the left side mirrored, both bellcranks turn by the same angle
    through the bridge): deviation of the steering link from the perpendicular to the knuckle arm and to the
    bellcrank arm, Ackermann percentage at 15, 20 and 25 degrees of the inner wheel and the bellcrank angle."""
    P, S, Kp, K = (np.asarray(q, float)[:2] for q in (P, S, Kp, K))
    L = np.linalg.norm(K - S)
    track, wb = 2 * Kp[0], Kp[1] - rear_axle_y
    ln = (K - S) / L
    dev_k = 90 - math.degrees(math.acos(abs(unit(K - Kp) @ ln)))
    dev_s = 90 - math.degrees(math.acos(abs(unit(S - P) @ ln)))
    m = np.array([-1.0, 1.0])
    rows = []
    for th in np.radians(np.arange(-45, 45.01, 0.1)):
        c_, s_ = math.cos(th), math.sin(th)
        Rm = np.array([[c_, -s_], [s_, c_]])
        dr = plan_knuckle(Kp, K, P + Rm @ (S - P), L)
        dl = plan_knuckle(Kp * m, K * m, P * m + Rm @ ((S - P) * m), L)
        if dr is not None and dl is not None:
            rows.append((math.degrees(th), math.degrees(dr), math.degrees(dl)))
    rows = np.array(rows)
    res = {"dev_k": round(dev_k, 1), "dev_s": round(dev_s, 1)}
    for inner in (15, 20, 25):
        th, dr, dl = rows[np.argmin(abs(rows[:, 2] - inner))]              # left turn: left wheel inside
        ideal = math.degrees(math.atan(1 / (1 / math.tan(math.radians(dl)) + track / wb)))
        res[f"ackermann {inner}"] = round((dl - dr) / (dl - ideal) * 100, 0)
        res[f"outer {inner}"] = round(dr, 1)
        res[f"bellcrank {inner}"] = round(abs(th), 1)
    return res


def steering(p, cl, c, kb):
    """Steering as the T410R (manual steps 10, 13, 14, 21): 2 symmetric bellcranks (straight levers, the same part on
    both sides, no front and rear) on the posts H24/H25 with 2 bearings 5x8x2.5 each: ball arm forward for the steering
    link, rear arm to a rigid bridge (parallelogram: both bellcranks turn by the same angle, the bridge moves across the
    car); steering links from the bellcranks to the steering arms of the knuckles; servo across the car on the floating
    servo mount (H17/H21) with the output shaft and the horn facing forward (End A), placed from the caliper values of
    the owner (S1 to S9, M1 to M5); servo link from the horn ball (up) to the ball of the bridge (inclined)."""
    out = []
    af, hpost, jd, h_post, d_sh, play = p["post"]
    bz0, bz1, r_s, a_s, r_b = p["bellcrank"]
    hub_d, end_d, seat_d, lip_t, lip_d, hole_d, ch = p["bellcrank_shape"]
    zb0, zb1, wb, d_tw, d_acc, w_bb = p["bridge"]
    g_bar = p["bridge_gusset"]                                     # stabilizing triangles beside the boss of the ball
    e_ch, _, e_ang = p["edge_treatment"]                           # chamfers of the bellcranks and the bridge (owner)
    d_sl, d_in, l_sl, d_w, t_w, _, _, d_bore = p["guide_sleeve"]          # bridge joint: the sleeve and washers of the C-hub
    j_play, l_scr = p["bridge_joint"]
    z_post = PLATE_T + h_post                                                                  # end of the journal
    assert abs(bz1 - z_post) < 1e-6 and abs(bz1 - bz0 - (5.0 + lip_t)) < 1e-6, "bearing stack on the post, journal flush"
    t_top = 6.0 - 0.5 - play                                     # full thread on top: screw M3x6 + washer 0.5 bottoms there
    P = np.array([21.7, 242.69])
    zt = bz1 + p["ball_offset"]
    K = kb
    pts = {}
    for side in (1, -1):
        Pp = np.array([side * P[0], P[1]])
        pts[side] = (Pp, Pp + np.array([side * a_s, r_s]), Pp + np.array([0.0, -r_b]))   # post, ball arm, bridge arm
    S = np.array([*pts[1][1], zt])

    def bellcrank(side):
        """Hull of the hub circle and the 2 end circles (full height); bearing seats from both faces with the lip
        between them; plain through holes at both ends."""
        Pp, Sp, Bp = pts[side]
        R, r = hub_d / 2, end_d / 2
        s = cyl_z(R, bz0, bz1, Pp[0], Pp[1])
        for q in (Sp, Bp):
            L = float(np.linalg.norm(q - Pp))
            u = (q - Pp) / L
            w = np.array([-u[1], u[0]])
            a = (R - r) / L                                                    # normal of the tangent along u
            n1, n2 = a * u + math.sqrt(1 - a * a) * w, a * u - math.sqrt(1 - a * a) * w
            poly = [tuple(Pp + R * n1), tuple(q + r * n1), tuple(q + r * n2), tuple(Pp + R * n2)]
            s = s.fuse(prism_z(poly, bz0, bz1)).fuse(cyl_z(r, bz0, bz1, q[0], q[1]))
        s = s.cut(cyl_z(lip_d / 2, bz0 - 1, bz1 + 1, Pp[0], Pp[1]))                         # opening of the lip
        for z0_, z1_ in ((bz0 - 1, bz0 + 2.5), (bz1 - 2.5, bz1 + 1)):                      # bearing seats
            s = s.cut(cyl_z(seat_d / 2, z0_, z1_, Pp[0], Pp[1]))
        for z_, d_ in ((bz0 - 1.0, 1.0), (bz1 + 1.0, -1.0)):                                # chamfers of the entries
            s = s.cut(cq.Solid.makeCone(seat_d / 2 + ch + 1.0, seat_d / 2, ch + 1.0, cq.Vector(Pp[0], Pp[1], z_),
                                        cq.Vector(0, 0, d_)))
        for q in (Sp, Bp):
            s = s.cut(cyl_z(hole_d / 2, bz0 - 1, bz1 + 1, q[0], q[1]))                     # through holes
        # chamfers on the sharp outer edges (owner, 2026-11-22: chamfers only); bearing seats and lip kept sharp
        keep = [cyl_z(seat_d / 2 + 0.05, bz0 + 0.05, bz1 - 0.05, Pp[0], Pp[1])]
        s, EDGE_REPORT["bellcrank"] = ET.treat(s.clean(), e_ch, None, keep, e_ang)
        return s
    # post: hexagon, shank up to the shoulder (collar) under the inner ring of the lower bearing, journal flush with the
    # bearing stack; blind thread M3 on top with a full thread of t_top: the screw M3x6 with washer bottoms at the end of the
    # thread and cannot be screwed in fully, the washer stays play above the journal (free bellcrank)
    post = fuse(hex_z(af, PLATE_T, PLATE_T + hpost, P[0], P[1]), cyl_z(d_sh / 2, PLATE_T + hpost - 0.1, bz0, P[0], P[1]),
                cyl_z(jd / 2, bz0 - 0.1, z_post, P[0], P[1]))
    post = post.cut(cyl_z(TAP / 2, PLATE_T - 1, PLATE_T + 6, P[0], P[1])).cut(cyl_z(TAP / 2, z_post - t_top - 1.0, z_post + 1, P[0], P[1]))
    brg = cq.Compound.makeCompound([cyl_z(4.0, z0, z0 + 2.5, P[0], P[1]).cut(cyl_z(2.5, z0 - 1, z0 + 4, P[0], P[1]))
                                    for z0 in (bz0, bz1 - 2.5)])
    zw = z_post + play                                                                           # washer at the stop
    washer = fuse(cyl_z(3.0, zw, zw + 0.5, P[0], P[1]).cut(cyl_z(1.6, zw - 1, zw + 1, P[0], P[1])),   # washer 3.2x6x0.5
                  cyl_z(2.85, zw + 0.5, zw + 2.15, P[0], P[1]),                                         # screw M3x6
                  cyl_z(TAP / 2 - 0.001, zw + 0.5 - 6.0, zw + 0.51, P[0], P[1]))
    up = np.array([0, 0, 1.0])
    ball0 = fuse(sphere(2.4, S), cyl_between(1.5, S, S - up * p["ball_offset"]))                # ball with internal thread
    bscrew = fuse(cyl_z(2.85, bz0 - 1.65, bz0, S[0], S[1]), cyl_z(1.45, bz0 - 0.01, bz1, S[0], S[1]))  # M3x10, head below
    for name, kind, sol in (("steering post", "steer", post), ("bellcrank bearings 5x8x2.5", "axle", brg),
                            ("washer and screw M3x6 of the post", "axle", washer), ("bellcrank ball", "link", ball0),
                            ("bellcrank ball screw M3x10", "link", bscrew)):
        out += [(f"{name} right", kind, sol), (f"{name} left", kind, mirror_x(sol))]
    bc = bellcrank(1)
    out += [("bellcrank right", "steer", bc), ("bellcrank left", "steer", mirror_x(bc))]
    # servo across the car from the caliper values of the owner (relative to H21 and the top face of the chassis plate)
    H17, H21 = (7.98, 174.15), (8.0, 199.15)
    s1, s2, s3, s4 = p["servo_position"]
    sv_l, sv_h, sv_d, sv_sh, ear_t, ear_l, ear_hx, ear_hz = p["servo"]
    hl, hw, ht, hf = p["servo_horn"]
    tp, m4, wp, m1, l_fix, dp, wf, dl, tf, dpf, dpr, zn, ha = p["servo_mount"]
    xs, zs = H21[0] + s2, PLATE_T + s3                                                         # output shaft
    ycf = H21[1] + s1                                                                            # front face of the case
    zs0 = PLATE_T + s4                                                                           # lower face of the case
    zs1 = zs0 + sv_h
    zm = (zs0 + zs1) / 2
    sx0 = xs - (sv_l - sv_sh)                                                                    # inner end of the case
    yfb = H21[1] + m1                                                                            # front faces of the posts
    zt1 = PLATE_T + m4                                                                           # top face of the top plate
    zt0 = zt1 - tp
    assert zs1 < zt0 and abs(yfb + ear_t - ycf) < 1e-6, "servo below the top plate, ears flush with the case"
    yh1 = ycf + hf                                                                               # front face of the horn
    yh0 = yh1 - ht
    horn_ball = np.array([xs, yh1 + p["ball_offset"], zs + hl])
    yball = horn_ball[1]
    # bridge behind the posts (owner: refined, PA12): beam across the car over the centre driveshaft with a tower at each
    # end; joint on the bellcrank arm with generic parts as the kingpins of the C-hub (owner, 2026-11-22): washer M3 DIN
    # 125-A on the arm, brass spacer sleeve in the bore of the tower, washer in the access bore, button head screw from
    # above, washer and lock nut M3 under the bellcrank arm; the screw clamps washer, sleeve and washer to the arm, the
    # tower turns on the sleeve and slides between the washers. Ball of the servo link in the middle of the rear face on
    # a grub screw M3x8, the boss reaches back to the y of the horn ball
    yb = P[1] - r_b                                                                              # axis of the bridge
    db = (yb - wb / 2) - (yball + p["ball_offset"])                                              # depth of the boss
    assert db > 1.0, f"boss of the bridge too short ({db:.2f})"
    zt_0 = bz1 + t_w                                                                             # bottom face of the towers
    z_st = zt_0 + l_sl                                                                           # upper end of the sleeve
    zt_1 = z_st - j_play                                                                         # floor of the access bore
    zh_s = z_st + t_w                                                                            # under the screw head
    zbb = (zb0 + zb1) / 2
    bball = np.array([0.0, yball, zbb])
    L_v = float(np.linalg.norm(horn_ball - bball))
    BL, BR = pts[-1][2], pts[1][2]
    assert zb0 > zt_0 - 1e-6, "bar of the bridge below the towers"
    assert zh_s + 1.65 < zb1 and d_acc > d_w + 0.5, "upper washer and screw head inside the access bore"
    assert zh_s - l_scr <= bz0 - 0.5 - 4.0 - 0.5, "screw too short for the lock nut under the arm"
    bridge = box(BL[0], BR[0], yb - wb / 2, yb + wb / 2, zb0, zb1)
    for q in (BL, BR):
        bridge = bridge.fuse(cyl_z(d_tw / 2, zt_0, zb1, q[0], q[1]))
    bridge = bridge.fuse(box(-w_bb / 2, w_bb / 2, yb - wb / 2 - db, yb, zb0, zb1))               # boss of the ball
    for sx in (1, -1):                       # stabilizing triangles (owner): corner of the bar face and the boss side
        xa, xg, yr, ye = sx * w_bb / 2, sx * (w_bb / 2 + g_bar), yb - wb / 2, yb - wb / 2 - db
        bridge = bridge.fuse(prism_z([(xa, ye), (xg, yr), (xg, yr + 0.5), (xa, yr + 0.5)], zb0, zb1))
    for q in (BL, BR):
        bridge = bridge.cut(cyl_z(d_bore / 2, zt_0 - 1, zt_1 + 0.01, q[0], q[1]))             # bore of the sleeve
        bridge = bridge.cut(cyl_z(d_acc / 2, zt_1, zb1 + 1, q[0], q[1]))                       # access bore for the screw
    bridge = bridge.cut(cyl_y(TAP / 2, yb - wb / 2 - db - 0.1, yb - wb / 2 - db + 5.5, 0.0, zbb))  # thread M3, grub screw
    bridge, EDGE_REPORT["steering bridge"] = ET.treat(bridge.clean(), e_ch, None, (), e_ang)       # chamfers (owner)
    joint = [cyl_z(d_sl / 2, zt_0, z_st, q[0], q[1]).cut(cyl_z(d_in / 2, zt_0 - 1, z_st + 1, q[0], q[1])) for q in (BL, BR)]
    hardware = []
    for q in (BL, BR):
        hole = cyl_z(d_in / 2, bz1 - 1, zh_s + 1, q[0], q[1])
        hardware += [cyl_z(d_w / 2, bz1, zt_0, q[0], q[1]).cut(hole), cyl_z(d_w / 2, z_st, zh_s, q[0], q[1]).cut(hole)]
        hardware.append(fuse(cyl_z(2.85, zh_s, zh_s + 1.65, q[0], q[1]),                          # button head screw
                             cyl_z(1.45, zh_s - l_scr, zh_s + 0.01, q[0], q[1])))
        hardware.append(cyl_z(3.5, bz0 - 0.5, bz0, q[0], q[1]).cut(cyl_z(1.6, bz0 - 1, bz0 + 1, q[0], q[1])))  # washer 3.2x7x0.5
        hardware.append(hex_z(5.5, bz0 - 4.5, bz0 - 0.5, q[0], q[1]).cut(cyl_z(1.5, bz0 - 6, bz0, q[0], q[1])))  # lock nut M3
    out += [("steering bridge", "steer", bridge),
            ("bridge guide sleeves", "axle", cq.Compound.makeCompound(joint)),
            ("bridge washers, screws M3x16 and lock nuts", "link", cq.Compound.makeCompound(hardware)),
            ("ball stud of the bridge", "link", stud(bball, (0, -1.0, 0), p["ball_offset"], 5.0))]
    rods, tb_, gap_a = link(S, -up, K, -c["front"]["kd"], 9.0, cl)                          # ball on top, along the kingpin
    out += [("steering link rod ends right", "rodend", rods), ("steering link turnbuckle right", "link", tb_),
            ("steering link rod ends left", "rodend", mirror_x(rods)), ("steering link turnbuckle left", "link", mirror_x(tb_))]
    rods, tb_, gap_v = link(horn_ball, np.array([0, -1.0, 0]), bball, np.array([0, 1.0, 0]), 9.0, cl)
    out += [("servo link rod ends", "rodend", rods), ("servo link turnbuckle", "link", tb_)]
    # servo: case, ears flush with the front face of the case, output spline
    xe = (sx0 - ear_hx, sx0 + sv_l + ear_hx)                                                     # ear holes (x)
    ear_holes = [(xx, zz) for xx in xe for zz in (zm - ear_hz / 2, zm + ear_hz / 2)]
    case = box(sx0, sx0 + sv_l, ycf - sv_d, ycf, zs0, zs1)
    ears = [box(sx0 - ear_l, sx0, yfb, ycf, zs0, zs1), box(sx0 + sv_l, sx0 + sv_l + ear_l, yfb, ycf, zs0, zs1)]
    servo = fuse(case, *ears, cyl_y(2.95, ycf - 0.1, ycf + 3.4, xs, zs))
    for xx, zz in ear_holes:
        servo = servo.cut(cyl_y(1.6, yfb - 1, ycf + 1, xx, zz))
    horn = fuse(cyl_y(5.5, yh0, yh1, xs, zs), box(xs - hw / 2, xs + hw / 2, yh0, yh1, zs, horn_ball[2]),
                cyl_y(hw / 2, yh0, yh1, xs, horn_ball[2]))
    horn = horn.cut(cyl_y(2.95, yh0 - 1, yh1 + 1, xs, zs)).cut(cyl_y(TAP / 2, yh0 - 1, yh1 + 1, xs, horn_ball[2]))
    horn = horn.cut(cyl_x(TAP / 2, xs - 6, xs + 6, (yh0 + yh1) / 2, zs - 3.8))                   # clamp screw M3
    # floating servo mount as the T410R (manual step 10): top plate on 2 posts. Only the fixed post at the inner end of
    # the servo is screwed onto the chassis plate (H17/H21, threads M3 from below); the floating post (L bracket) at the
    # output end hangs from the top plate. Servo ears on the front faces of the posts (threads M3 from the front), top
    # plate on the top faces (threads M3 from above; slots at the floating post)
    xac = (H21[0] + xe[0]) / 2                                                                   # fixed post: H21 and ear holes
    xa0, xa1 = xac - wp / 2, xac + wp / 2
    ya1, ya0 = yfb, yfb - l_fix
    yp0, yp1 = ya0 + dpr, ya1 - dpf                                                              # between the pillars
    rn, ra = 3.0, 2.0
    notch = fuse(box(xa0 - 1, xa1 + 1, yp0, yp1, PLATE_T + zn + rn, zt0 + 1),
                 box(xa0 - 1, xa1 + 1, yp0 + rn, yp1 - rn, PLATE_T + zn, zt0 + 1),
                 cyl_x(rn, xa0 - 1, xa1 + 1, yp0 + rn, PLATE_T + zn + rn), cyl_x(rn, xa0 - 1, xa1 + 1, yp1 - rn, PLATE_T + zn + rn))
    arch = fuse(box(xa0 - 1, xa1 + 1, yp0, yp1, PLATE_T - 1, PLATE_T + ha - ra),
                box(xa0 - 1, xa1 + 1, yp0 + ra, yp1 - ra, PLATE_T - 1, PLATE_T + ha),
                cyl_x(ra, xa0 - 1, xa1 + 1, yp0 + ra, PLATE_T + ha - ra), cyl_x(ra, xa0 - 1, xa1 + 1, yp1 - ra, PLATE_T + ha - ra))
    fixed = box(xa0, xa1, ya0, ya1, PLATE_T, zt0).cut(notch).cut(arch)
    for h in (H17, H21):
        fixed = fixed.cut(cyl_z(TAP / 2, PLATE_T - 1, PLATE_T + 5.0, *h))                       # threads M3 from below
    top_a = (ya1 - 6.5, ya0 + dpr / 2)                                                           # top screws (pillars)
    for hy in top_a:
        fixed = fixed.cut(cyl_z(TAP / 2, zt0 - 5.0, zt0 + 0.1, xac, hy))
    xbc = xe[1]                                                                                  # floating post
    xb0, xb1 = xbc - wf / 2, xbc + wf / 2
    assert xb0 > sx0 + sv_l + 0.2
    ymr = ya1 - dp                                                                               # rear edge of the main plate
    yl0, yfl0, fl_r = yfb - dl, ymr + 0.5, 6.0                                                   # leg, end of the flange
    floating = fuse(box(xb0, xb1, yl0, yfb, zs0, zt0), box(xb0, xb1, yfl0, yl0 + 0.01, zt0 - tf, zt0),
                    box(xb0, xb1, yl0 - fl_r, yl0 + 0.01, zt0 - tf - fl_r, zt0 - tf + 0.01).cut(
                        cyl_x(fl_r, xb0 - 1, xb1 + 1, yl0 - fl_r, zt0 - tf - fl_r)))
    top_b = (yfl0 + 3.5, yfl0 + 10.0)                                                            # screws in the flange
    for hy in top_b:
        floating = floating.cut(cyl_z(TAP / 2, zt0 - tf - 0.1, zt0 + 0.1, xbc, hy))
    for xx, zz in ear_holes:
        cut_ = cyl_y(TAP / 2, yfb - 4.0, yfb + 0.1, xx, zz)                                     # threads M3, servo ears
        fixed, floating = fixed.cut(cut_), floating.cut(cut_)
    cpl, cin = 2.0, 3.0                                                                          # chamfers of the top plate
    # top plate: front edge straight (flush with the front faces of the posts), main part dp deep over the servo and the
    # floating post; at the fixed post the plate reaches back to the rear face of the post (owner)
    xst = xa1 + 2.0                                                                              # step at the fixed post
    plate_top = prism_z([(xa0 + cpl, ya0), (xst - cpl, ya0), (xst, ya0 + cpl), (xst, ymr - cin), (xst + cin, ymr),
                         (xb1 - cpl, ymr), (xb1, ymr + cpl), (xb1, ya1 - cpl), (xb1 - cpl, ya1), (xa0 + cpl, ya1),
                         (xa0, ya1 - cpl), (xa0, ya0 + cpl)], zt0, zt1)
    for hy in top_a:
        plate_top = plate_top.cut(cyl_z(1.6, zt0 - 1, zt1 + 1, xac, hy))
    for hy in top_b:                                                                             # slots along x
        plate_top = plate_top.cut(fuse(cyl_z(1.6, zt0 - 1, zt1 + 1, xbc - 1.5, hy), cyl_z(1.6, zt0 - 1, zt1 + 1, xbc + 1.5, hy),
                                       box(xbc - 1.5, xbc + 1.5, hy - 1.6, hy + 1.6, zt0 - 1, zt1 + 1)))
    steering.mount = {"top plate": (zt0, zt1), "gap of the floating post": zs0 - PLATE_T,
                      "fixed post": (xa0, xa1, ya0, ya1), "floating post": (xb0, xb1, yfl0, yfb)}
    # chamfers on the sharp outer edges of the 3 parts of the servo mount (owner, 2026-11-22: chamfers only)
    plate_top, EDGE_REPORT["servo mount top plate"] = ET.treat(plate_top.clean(), e_ch, None, (), e_ang)
    fixed, EDGE_REPORT["servo mount fixed post"] = ET.treat(fixed.clean(), e_ch, None, (), e_ang)
    floating, EDGE_REPORT["servo mount floating post"] = ET.treat(floating.clean(), e_ch, None, (), e_ang)
    hstud = stud(horn_ball, (0, 1.0, 0), p["ball_offset"], 3.5)
    out += [("servo", "servo", servo.clean()), ("servo horn (aluminium clamp)", "steer", horn.clean()),
            ("servo mount top plate", "steer", plate_top), ("servo mount fixed post", "steer", fixed),
            ("servo mount floating post", "steer", floating), ("servo horn ball stud", "link", hstud)]
    ack = ackermann(P, S, c["front"]["J"], K, c["rear"]["O"][1])
    th = math.radians(ack["bellcrank 25"])
    travel = r_b * math.sin(th)
    steering.info = {"S": S, "K": K, "B": np.array([*BR, zb0]), "bridge ball": bball, "horn": horn_ball,
                     "gap steering link": gap_a, "gap servo link": gap_v, "ackermann": ack,
                     "bridge travel 25": round(travel, 2), "servo angle 25": round(math.degrees(math.asin(travel / hl)), 1),
                     "servo link inclination": round(math.degrees(math.asin((horn_ball[2] - zbb) / L_v)), 1),
                     "boss depth": round(db, 2)}
    return out


def steering_sweep(parts, others, angle):
    """Turns the right bellcrank with its ball stud and the rod end of the steering link about the post and
    moves the bridge with its sleeves, washers, screws and ball (parallelogram) by +-angle; returns the largest overlap with the other
    parts (bulkheads, cup joint, centre driveshaft, steering posts)."""
    st = steering.info
    P = np.array([21.7, 242.69, 0.0])
    S = st["S"]
    ring = cyl_between(3.5, S + np.array([0, 0, -3.0]), S + np.array([0, 0, 3.4]))
    turning = [parts["bellcrank right"], parts["bellcrank ball right"], parts["bellcrank ball screw M3x10 right"], ring]
    moving = [parts["steering bridge"], parts["bridge guide sleeves"], parts["ball stud of the bridge"],
              parts["bridge washers, screws M3x16 and lock nuts"]]
    B = st["B"]
    res = {}
    for sg in (1, -1):
        a = math.radians(sg * angle)
        v = np.array([B[0] - P[0], B[1] - P[1]])
        d = np.array([math.cos(a) * v[0] - math.sin(a) * v[1], math.sin(a) * v[0] + math.cos(a) * v[1]]) - v
        worst = (0.0, "")
        for s in turning + moving:
            s2 = s.rotate(cq.Vector(*P), cq.Vector(P[0], P[1], 1.0), sg * angle) if s in turning \
                else s.translate(cq.Vector(d[0], d[1], 0))
            bb = s2.BoundingBox()
            for n, o in others:
                ob = o.BoundingBox()
                if bb.xmin > ob.xmax or ob.xmin > bb.xmax or bb.ymin > ob.ymax or ob.ymin > bb.ymax or bb.zmin > ob.zmax \
                        or ob.zmin > bb.zmax:
                    continue
                v_ = s2.intersect(o).Volume()
                if v_ > worst[0]:
                    worst = (v_, n)
        res[f"{sg * angle:+.0f} deg"] = (round(worst[0], 4), worst[1])
    return res


def carrier_swing(c, car, arm, angles=np.arange(-25.0, 25.1, 2.5)):
    """Rear hub carrier turned on the outer hinge pin relative to the rear wishbone (the camber link holds the top of
    the carrier, so it turns on the pin when the suspension moves; +-25 deg covers the compression to the chassis at the
    ride height of 15): largest overlap and smallest distance with their angles."""
    O, ey = np.array(c["rear"]["O"]), np.array(c["rear"]["ey"])
    a0, a1 = cq.Vector(*O), cq.Vector(*(O + ey))
    rows = []
    for th in angles:
        r = car.rotate(a0, a1, float(th))
        rows.append((float(th), r.intersect(arm).Volume(), r.distance(arm)))
    v = max(rows, key=lambda q: q[1])
    d = min(rows, key=lambda q: q[2])
    return {"largest overlap": (round(v[1], 4), v[0]), "smallest distance": (round(d[2], 2), d[0])}


def check(parts, others):
    """Overlap of all pairs of the new parts and with the other parts of the assembly."""
    items = parts + others
    boxes = [s.BoundingBox() for _, _, s in items]
    n_new = len(parts)
    bad = []
    for i, j in itertools.combinations(range(len(items)), 2):
        if i >= n_new and j >= n_new:
            continue
        a, b = boxes[i], boxes[j]
        if a.xmin > b.xmax or b.xmin > a.xmax or a.ymin > b.ymax or b.ymin > a.ymax or a.zmin > b.zmax or b.zmin > a.zmax:
            continue
        v = items[i][2].intersect(items[j][2]).Volume()
        if v > 1e-4:
            bad.append((v, items[i][0], items[j][0]))
    return sorted(bad, reverse=True)


KIND_COLORS = {k: P.rgb(k) for k in ("upright", "axle", "cvd", "steer", "damper", "spring", "servo", "swaybar",
                                     "rodend", "link", "arm", "plate")}
KIND_COLORS["bulkhead"] = P.rgb("lower")                  # colour scheme of the CAD pictures (palette.py)
MADE = {"upright", "steer"}                                     # own parts to manufacture (files)
MADE_NAMES = ("axle with joint cup", "hex hub 12")
# purchased (owner, 2026-11-24): in the assembly only, no files; the steering links and the servo link (rod ends and
# turnbuckles) are no own parts either
PURCHASED = ("sway bar", "CVD drive shaft", "servo horn")
HANDED = ("C-hub",)              # parts without a plane of symmetry (caster): a left and a right part (mirror images)


FOLDERS = {"front_corner": ("c_hub_end_a_right", "c_hub_end_a_left", "steering_knuckle_end_a", "axle_with_joint_cup_end_a",
                            "hex_hub_12_end_a"),
           "rear_corner": ("hub_carrier_end_b", "axle_with_joint_cup_end_b", "hex_hub_12_end_b"),
           "steering": ("steering_post", "bellcrank", "steering_bridge"),
           "servo_mount": ("servo_mount_top_plate", "servo_mount_fixed_post", "servo_mount_floating_post")}


def write_files(parts):
    """STEP and STL of the own parts of the right side (assembly position, chassis plate coordinates), one folder per
    group of parts (FOLDERS). The other parts are the same on both sides; the handed parts (HANDED: no plane of
    symmetry) get a file for the right and one for the left side (mirror image). Purchased parts (PURCHASED: sway bars
    with holders and ball ends, CVD drive shafts, servo horn) are in the assembly only."""
    import re
    folder = {stem: name for name, stems_ in FOLDERS.items() for stem in stems_}
    stems = []
    for name, kind, s in parts:
        handed = name.startswith(HANDED)
        if (kind not in MADE and not name.startswith(MADE_NAMES)) or (name.endswith(" left") and not handed) \
                or name.startswith(PURCHASED):
            continue
        side = name.rsplit(" ", 1)[1] if name.endswith((" right", " left")) else ""
        base = name[:-len(side) - 1] if side else name
        stem = re.sub(r"[^a-z0-9]+", "_", base.lower().replace("1.4", "")).strip("_") + (f"_{side}" if handed else "")
        if stem not in folder:
            raise KeyError(f"no folder for the part file {stem} (FOLDERS)")
        path = f"{OUT}/{folder[stem]}/{stem}"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        cq.exporters.export(cq.Workplane().add(s), f"{path}.step")
        cq.exporters.export(cq.Workplane().add(s), f"{path}.stl", tolerance=0.01, angularTolerance=0.1)
        stems.append(f"{folder[stem]}/{stem}")
    return stems


def drawing(parts, info, lock, path=DRAWING):
    """Drawing of the running gear: front corner from the side (kingpin axis with caster), front corner from
    the outer end, steering from above, rear corner from the outer end, front corner in 3D, servo on the floating
    servo mount and front sway bar in 3D."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from mesh_views import subdivide, draw_mesh, iso_basis
    import generate_speedrun_assembly as A
    p = load_params(PARAMS)
    lp = load_params(LOWER)
    c = corners(p, lp)
    plate = [("chassis plate", "plate", cq.importers.importStep(A.PLATE_STEP).val())]
    arms = [(n, "arm", s) for n, k, s in W.arms_in_plate() if k == "arm"]
    allp = parts + arms + plate

    def tess(s, tol=0.03):
        v, idx = s.tessellate(tol, 0.2)
        v = np.array([[q.x, q.y, q.z] for q in v])
        return v[np.array(idx)]

    def panel(ax, region, view, keep=lambda n, k: True, max_edge=1.0, extra=()):
        box_r = cq.Solid.makeBox(region[3] - region[0], region[4] - region[1], region[5] - region[2],
                                 cq.Vector(*region[:3]))
        tris, cols = [], []
        for n, k, s in allp + list(extra):
            if not keep(n, k):
                continue
            bb = s.BoundingBox()
            if bb.xmin > region[3] or bb.xmax < region[0] or bb.ymin > region[4] or bb.ymax < region[1] \
                    or bb.zmin > region[5] or bb.zmax < region[2]:
                continue
            cut = s.intersect(box_r)
            if cut.Volume() < 1e-3:
                continue
            t = subdivide(tess(cut), 6.0 if k == "plate" else max_edge)
            tris.append(t)
            cols.append(np.tile(KIND_COLORS[k], (len(t), 1)))
        lo, hi = draw_mesh(ax, np.concatenate(tris), view, tri_colors=np.concatenate(cols), depth_cue=0.25)
        ax.set_xlim(lo[0] - 3, hi[0] + 3)
        ax.set_ylim(lo[1] - 3, hi[1] + 3)
        ax.set_aspect("equal")
        ax.axis("off")
        return view

    fig = plt.figure(figsize=(16, 19))
    fig.suptitle("Speedrun chassis: running gear (own design, partly based on the T410R)", fontsize=13, y=0.99)
    row = lambda r: [r[0], (r[1] * 13 + 6) / 19, r[2], r[3] * 13 / 19]          # upper two rows, third row below
    fp, J, kb = front_corner(p, load_params(DRIVE), c["front"])
    kd = c["front"]["kd"]
    yc = J[1]
    # 1: front right corner seen from the outside (view along -x): kingpin axis with the caster
    ax = fig.add_axes(row([0.01, 0.5, 0.36, 0.44]))
    side = (np.array([-1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0]))
    keep_f = lambda n, k: "End A" in n and ("right" in n or k in ("swaybar",)) and k not in ("damper", "spring", "swaybar")
    panel(ax, (40, yc - 22, 0, 75.5, yc + 16, 42), side,
          lambda n, k: keep_f(n, k) and (k != "axle" or n.startswith(("kingpins", "guide sleeves", "outer hinge"))))
    a, b = J - kd * 17, J + kd * 17
    ax.plot([a[1], b[1]], [a[2], b[2]], "-.", color="k", lw=1.2)
    ax.plot([J[1], J[1]], [J[2] - 17, J[2] + 17], ":", color="#555", lw=1.0)
    ax.text(J[1] + 1.0, J[2] + 17.5, f"kingpin axis, caster {p['caster']:g} deg (top toward the middle of the car),\n"
            "dotted: vertical", fontsize=8.5, ha="left", va="bottom")
    ax.set_ylim(ax.get_ylim()[0], J[2] + 23)
    ax.set_title("Front right corner (End A), view from the outside, section at x = 75.5 (hex hub not shown):\n"
                 "the C-hub carries the caster; faces between C-hub and knuckle square to the kingpin axis (gap 0.5)",
                 fontsize=9.5, loc="left")
    ax.text(J[1] - 21, 1, "<- middle of the car", fontsize=8)
    # 2: front right corner seen from the outer end (view along -y)
    ax = fig.add_axes(row([0.38, 0.5, 0.3, 0.44]))
    rear = (np.array([0, -1.0, 0]), np.array([-1.0, 0, 0]), np.array([0, 0, 1.0]))
    panel(ax, (15, yc - 30, -1, 100, yc + 30, 52), rear,
          lambda n, k: ("End A" in n and "left" not in n) or k in ("plate",))
    ax.set_title(f"Front corner, view from the front (End A): axle height {c['front']['axle_z']:g}\n"
                 f"(ride height {p['ride_height'][0]:g}), wheel centre x = {p['wheel_centre_x']:g}", fontsize=9.5, loc="left")
    # 3: steering from above
    ax = fig.add_axes(row([0.69, 0.3, 0.3, 0.64]))
    top = (np.array([0, 0, -1.0]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))
    panel(ax, (-95, 150, -1, 95, 300, 52), top,
          lambda n, k: k not in ("damper", "spring") and not n.startswith(("sway", "CVD")) and ("End B" not in n), 2.0)
    ax.set_title("Steering from above (End A at the top): symmetric bellcranks on H24/H25\njoined by the bridge (parallelogram), "
                 "servo across the car below the top plate\nof the floating servo mount (H17/H21), horn facing forward",
                 fontsize=9.5, loc="left")
    st = steering.info
    ak = st["ackermann"]
    ax.text(0, 146, f"gaps between the rod ends: steering links {st['gap steering link']:.1f}, servo link "
            f"{st['gap servo link']:.1f}\nAckermann {ak['ackermann 15']:.0f} / {ak['ackermann 20']:.0f} / "
            f"{ak['ackermann 25']:.0f} % at 15 / 20 / 25 deg of the inner wheel", fontsize=8, ha="center", va="top")
    ax.set_ylim(132, ax.get_ylim()[1])
    # 4: rear right corner seen from the outer end (view along +y)
    ax = fig.add_axes(row([0.01, 0.04, 0.36, 0.42]))
    back = (np.array([0, 1.0, 0]), np.array([1.0, 0, 0]), np.array([0, 0, 1.0]))
    yr = c["rear"]["O"][1]
    panel(ax, (15, yr - 35, -1, 100, yr + 25, 52), back,
          lambda n, k: ("End B" in n and "left" not in n) or k in ("plate",))
    ax.set_title(f"Rear right corner (End B), view from the rear: hub carrier on the outer hinge pin\n"
                 f"(axle height {c['rear']['axle_z']:.1f}, ride height {p['wheel_r'] - c['rear']['axle_z']:.1f}), damper, sway bar",
                 fontsize=9.5, loc="left")
    # 5: front corner, iso view
    ax = fig.add_axes(row([0.38, 0.04, 0.3, 0.42]))
    panel(ax, (45, yc - 20, 0, 100, yc + 14, 42), iso_basis(-60, 25), keep_f, 0.8)
    ax.set_title("Front right corner, 3D view: C-hub (blue), knuckle with steering arm,\n"
                 "guide sleeves and kingpin screws, axle, hex hub", fontsize=9.5, loc="left")
    # notes
    fmt = lambda v: f"{v:g} deg" + (" or more (limit of the check)" if v >= 45 else "")
    notes = [f"Free steering angle of the knuckle (check, step 2.5 deg): {fmt(lock['steering arm toward the middle'])} "
             f"(arm toward the middle), {fmt(lock['steering arm toward the outside'])} (arm toward the outside); "
             f"required {p['steering_lock']:g} deg. Bellcranks, bridge and rod ends at the full angle of the bellcranks: "
             f"largest overlap {max(v[0] for v in info.get('sweep', {'-': (0.0, '')}).values()):g} mm3",
             f"CVD drive shafts: front {info['front'][2]:.1f}, rear {info['rear'][2]:.1f} (centre to centre of the joints); "
             f"dampers {info['damper front']:.1f} front, {info['damper rear']:.1f} rear (centre to centre of the balls)",
             "Threads M3 (tap drill 2.5): C-hub (camber stud, grub screw of the hinge pin), knuckle (steering ball stud), "
             "hub carrier (camber stud, grub screw), hex hubs (grub screw), steering posts (both ends), bridge (ball stud), "
             "servo mount (fixed post: H17/H21 from below; both posts: top plate from above, servo ears from the front), "
             "servo horn (clamp, ball stud), sway bar ball ends (grub screw M3x3). Bellcranks: plain through holes 3.2 (bridge "
             "screw M3x16 through washer, brass sleeve and washer, washer and lock nut below the arm, ball screw M3x10 from below)"]
    fig.text(0.69, 0.555, "\n\n".join(notes), fontsize=8.3, va="top", wrap=True)
    labels = {"upright": "C-hubs, knuckles, hub carriers", "axle": "axles, hex hubs, pins, bearings",
              "cvd": "CVD drive shafts", "steer": "steering, servo mount, sway bar holders", "damper": "dampers",
              "spring": "springs", "servo": "servo", "swaybar": "sway bars", "rodend": "rod ends",
              "link": "turnbuckles, ball studs, ball ends", "arm": "wishbones", "plate": "chassis plate",
              "bulkhead": "lower bulkhead"}
    fig.legend(handles=[Patch(color=KIND_COLORS[k], label=v) for k, v in labels.items()], loc="lower right",
               bbox_to_anchor=(0.995, (0.01 * 13 + 6) / 19), fontsize=8.5, ncol=2, frameon=False)
    # 6: servo on the floating servo mount, 3D view from the front right
    ax = fig.add_axes([0.01, 0.01, 0.47, 0.285])
    mt = steering.mount
    panel(ax, (-2, 160, 0, 72, 232, 52), iso_basis(62, 20),
          lambda n, k: n.startswith(("servo", "steering post right")) or k == "plate", 0.8)
    ax.set_title("Servo on the floating servo mount (manual step 10, caliper values of the owner), 3D view from the front right:\n"
                 "top plate on 2 posts; only the fixed post (inner end) is screwed onto H17/H21, the floating post (L bracket) at the\n"
                 f"output end hangs from the top plate ({mt['gap of the floating post']:.1f} above the chassis plate); horn ball "
                 f"{steering.info['horn'][2] - PLATE_T:.1f} above the chassis plate",
                 fontsize=9.5, loc="left")
    # 7: front sway bar, 3D view from the front right
    ax = fig.add_axes([0.51, 0.01, 0.48, 0.285])
    from generate_bulkhead_lower import bulkhead_lower
    import generate_driveshaft as D
    lower = bulkhead_lower(lp).val().rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180).translate(
        cq.Vector(0, BULKHEAD_Y["front"], PLATE_T))
    panel(ax, (-62, 255, 0, 62, 326, 34), iso_basis(68, 38),
          lambda n, k: "End A" in n and (n.startswith("sway") or k in ("arm", "cvd", "bulkhead")) or k == "plate", 0.8,
          extra=[("lower bulkhead End A", "bulkhead", lower)] + [(n_, "cvd", s_) for n_, _, s_ in D.parts_in_plate()
                                                                if n_.startswith("diff outdrive End A")])
    sw = info["sway front"]
    ax.set_title("Front sway bar (manual steps 22 and 23), 3D view from the front right: straight middle part in the holders\n"
                 "on the tabs of the lower bulkhead, straight legs past the diff outdrives and over the CVD drive shafts to the\n"
                 "ball ends (grub screw), vertical drop links to the "
                 f"ball studs in rail B of the wishbones (ball centres {2 * load_params(CL.PARAMS)['rod_end'][0] + p['sway_link'][0]:g} apart);\n"
                 f"leg {sw['leg']:g} mm, rising {sw['rise of the leg (deg)']:g} deg", fontsize=9.5, loc="left")
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Generate the running gear of the speedrun chassis.")
    parser.add_argument("--no-check", action="store_true")
    args = parser.parse_args()
    parts, info = build()
    print(f"{len(parts)} parts")
    for k, v in info.items():
        print(" ", k, v if not isinstance(v, tuple) else f"inner {v[0].round(2)}, joint {v[1].round(2)}, length {v[2]:.2f}")
    print("  steering:", {k: (v.round(2) if hasattr(v, "round") else (v if isinstance(v, dict) else round(v, 2))) for k, v in steering.info.items()})
    invalid = [n for n, _, s in parts if not s.isValid()]
    print("  invalid solids:", invalid)
    for n, rep in EDGE_REPORT.items():
        print(f"  edge treatment {n}:", rep)
    stems = write_files(parts)
    print(f"  wrote {len(stems)} parts to {OUT}: " + ", ".join(stems))
    import generate_speedrun_assembly as A
    others = [q for q in A.build() if not q[0].startswith("running gear ")]
    names = {n: s for n, _, s in parts}
    p = load_params(PARAMS)
    c = corners(p, load_params(LOWER))
    fp, _, _ = front_corner(p, load_params(DRIVE), c["front"])
    fixed = [(n, names[n + " End A right"]) for n in ("C-hub", "kingpins", "outer hinge pin 3x26", "CVD drive shaft")]
    fixed += [(n, s) for n, _, s in others if "wishbone End A right" in n]
    lock = steering_lock(p, c["front"], fp, fixed)
    print("  free steering angle (front right knuckle):", lock)
    sweep_o = [(n, s) for n, _, s in others if n.startswith(("lower bulkhead End A", "upper bulkhead End A", "cup joint End A",
                                                                 "centre driveshaft", "front pinion shaft", "speedrun top brace"))]
    sweep_o += [(n, names[n]) for n in ("steering post right", "steering post left", "servo", "servo mount top plate",
                                         "servo mount fixed post", "servo mount floating post", "servo horn (aluminium clamp)")]
    ang = steering.info["ackermann"]["bellcrank 25"] + 3.0
    info["sweep"] = steering_sweep(names, sweep_o, ang)
    print(f"  bellcranks and bridge turned by +-{ang:.1f} deg (25 deg of the inner wheel plus 3):", info["sweep"])
    sw = carrier_swing(c, names["hub carrier End B right"], next(s for n, _, s in others if n == "rear wishbone End B right"))
    print("  rear hub carrier turned on the outer hinge pin against the rear wishbone (+-25 deg, mm3 / mm, deg):", sw)
    drawing(parts, info, lock)
    print(f"  wrote {DRAWING}")
    if args.no_check:
        return
    bad = check(parts, others)
    print(f"  overlaps: {len(bad)}")
    for v, a, b in bad[:60]:
        print(f"    {v:8.4f} mm3  {a} / {b}")


if __name__ == "__main__":
    main()
