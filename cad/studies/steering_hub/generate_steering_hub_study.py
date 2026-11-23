"""Study: steering hub (C-hub and steering knuckle in one part) with a foot under an A-shaped front wishbone
(owner, 2026-11-23, option 2).

The knuckle becomes the steering hub: bearing ring and steering arm as now, no C-hub, no outer hinge pin, no kingpin
screws, sleeves and washers. The hub is held by 2 ball joints on the current kingpin axis, so the steering axis, the
caster of 10 deg, the wheel position, the track and the Ackermann stay as they are:
* top: the ball 4.8 of the camber link, screwed directly into the hub (upper boss 4.5 longer, ball at the same place);
* bottom: a standard ball stud 4.8 (as the camber links: neck 3.0, ball centre 4.0 above the face, thread M3) is
  screwed into a foot of the hub from above. The foot sits under the end of the wishbone and is carried by a web on the
  wheel side. The ball points up and is pressed into the wishbone from below (PA12, owner): the road pushes the hub up,
  so the foot pushes the ball into the closed top of the seat; the snap-in lip below only holds the ball when the
  wheel hangs. One screw.
* The end of the wishbone rises to the seat; the seat is a boss along the steering axis (tilted 10 deg, owner). The
  verified wishbone is kept up to x = X_CUT (inner lugs, shock plate, sway bar ball, droop bosses).
* Wheel: the solid tyre model (cylinder 64 x 30) contains the parts inside the rim, so the study uses an envelope: a
  ring from the free radius inside the rim (RIM_R, as the verified wishbone end uses now) to the tyre radius.
Checks: hub, foot and ball stud to the wheel envelope (they steer together); new and verified wishbone to the wheel
turned about the steering axis over the free angles; hub turned against the wishbone (steering) and tilted against it
about the ball (suspension travel); distances to the CVD drive shaft, the axle and the chassis plate.
The study is not part of the build: the parts of the build and the assembly are not changed.

Usage (from the root directory of the repository, after scripts/cad/generate_speedrun_assembly.py):
    python cad/studies/steering_hub/generate_steering_hub_study.py
Outputs in the directory of this script: STEP and STL files of the steering hub and of the wishbone (front right,
chassis plate coordinates), results, sketch and render.
Requires the packages cadquery and matplotlib.
"""
import json
import os
import sys
import textwrap

import numpy as np
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "cad"))
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import generate_running_gear as G  # noqa: E402
import technical_drawing as TD  # noqa: E402
import palette as P  # noqa: E402
from generate_bulkhead_lower import box, cyl_z  # noqa: E402
from generate_assembly_drawing import read_named_solids  # noqa: E402
from mesh_views import subdivide, draw_mesh, iso_basis  # noqa: E402

ASSEMBLY = "cad/assembly/speedrun_chassis_T410R.step"
STEM = os.path.join(HERE, "steering_hub_study")
# design values of the study (kingpin frame: x toward the wheel along the axle, z along the steering axis, origin on the
# axis at the height of the axle)
BALL_D = 4.8           # standard ball stud (as the camber links): ball 4.8, neck 3.0, ball centre 4.0 above the face
BALL_OFF = 4.0
NECK_D = 3.0
RING_R = 7.05          # bearing ring of the knuckle
GAP_RING = 1.5         # end of the wishbone below the bearing ring
SEAT_WALL = 1.5        # closed top of the seat above the ball (carries the wheel load)
LIP = 1.6              # snap-in lip below the ball centre
OPEN_D = 4.4           # opening of the lip for the ball 4.8 (0.4 smaller), 2 cross slots
SLOT_W = 0.7
BOSS_R = 6.0           # end of the wishbone around the seat
GAP_WEB = 1.5          # radial gap between the end of the wishbone and the web of the hub
WEB_T = 2.5            # web of the hub on the wheel side (x), width 2 x HALF_W (y)
HALF_W = 3.0
FOOT_T = 4.0           # foot under the end of the wishbone: thread M3 for the ball stud
RIM_R = 22.0           # free radius inside the rim (the verified wishbone end reaches 22.0 from the axle in the wheel)
TYRE_IN, TYRE_W, TYRE_R = 67.5, 30.0, 32.0
X_CUT = 57.0           # the verified wishbone is kept up to this x
STEER = (-35.0, 45.0)  # free angles of the knuckle (right side)
TILT = (-16.0, 16.0)   # tilt of the hub against the wishbone about the ball (suspension travel), checked
COL_STUD, TXT, ANN = (0.85, 0.45, 0.2), "#1f2933", "#c2410c"


# ------------------------------------------------------------------ geometry
def build(p, c, knuckle, old_arm):
    R, J = G.kingpin_frame(p, c["front"])
    R = np.asarray(R, float)
    kd = R[:, 2]
    L = lambda s: G.place(s, R, J)
    zt = -RING_R - GAP_RING                                      # top of the end of the wishbone
    zb = zt - SEAT_WALL - BALL_D / 2                             # ball centre
    za = zb - LIP                                                # bottom of the end of the wishbone (lip)
    zf = zb - BALL_OFF                                           # top face of the foot (face of the ball stud)
    zfb = zf - FOOT_T                                            # bottom face of the foot
    xw0 = BOSS_R + GAP_WEB                                       # web: x from xw0 to xw0 + WEB_T
    B_low = J + zb * kd
    B_top = np.array(G.front_camber_ball(p))
    # hub: knuckle without its lower boss, upper boss 4.5 longer, rib on top of the bearing ring, web and foot
    hub = knuckle.cut(L(cyl_z(4.3, zt - 3.0, -RING_R - 0.15, 0, 0)))
    for a in (L(cyl_z(3.5, 10.5, 15.05, 0, 0)), L(box(1.5, 12.0, -2.5, 2.5, 6.0, 9.6)),
              L(box(xw0, xw0 + WEB_T, -HALF_W, HALF_W, zfb, -RING_R + 1.5)),
              L(box(0.0, xw0 + WEB_T, -HALF_W, HALF_W, zfb, zf)), L(cyl_z(HALF_W, zfb, zf, 0, 0))):
        hub = hub.fuse(a)
    hub = hub.cut(L(cyl_z(1.25, zfb - 1, zf + 0.01, 0, 0))).clean()                   # thread M3 for the ball stud
    stud = cq.Solid.makeSphere(BALL_D / 2, cq.Vector(*B_low)).fuse(L(cyl_z(NECK_D / 2, zf, zb, 0, 0)))
    stud = stud.fuse(L(cyl_z(1.25, zf - 3.5, zf + 0.01, 0, 0)))
    top_stud = cq.Solid.makeSphere(2.4, cq.Vector(*B_top)).fuse(G.cyl_between(1.5, B_top, J + 15.05 * kd))
    # wishbone: the verified wishbone up to X_CUT, a neck to the seat, the end rises to the seat (boss along the axis)
    yb = B_low[1]
    arm = old_arm.intersect(box(0.0, X_CUT, 250.0, 320.0, -5.0, 30.0))
    neck = G.prism_z([(X_CUT - 4.0, 276.0), (X_CUT - 4.0, 297.0), (B_low[0], yb + BOSS_R - 1.0),
                      (B_low[0], yb - BOSS_R + 1.0)], 3.6, 9.6)
    boss = L(cyl_z(BOSS_R, za, zt, 0, 0))
    ramp = G.prism_z([(X_CUT - 6.0, yb + 4.5), (B_low[0], yb + 4.5), (B_low[0], yb - 4.5), (X_CUT - 6.0, yb - 4.5)],
                     6.0, boss.BoundingBox().zmin + 3.0)
    arm = arm.fuse(neck).fuse(ramp).fuse(boss)
    clear = [L(box(xw0 - 1.0, xw0 + WEB_T + 1.0, -HALF_W - 1.0, HALF_W + 1.0, zfb - 1.0, -RING_R + 1.0)),
             L(box(-1.0, xw0 + WEB_T + 1.0, -HALF_W - 1.0, HALF_W + 1.0, zfb - 1.0, zf + 2.5)),
             L(cyl_z(HALF_W + 2.5, zfb - 1.0, zf + 2.5, 0, 0))]                   # room for the foot and the web
    for ang in np.arange(STEER[0], STEER[1] + 0.1, 5.0):                          # over the steering angle
        for cl in clear:
            arm = arm.cut(cl.rotate(cq.Vector(*J), cq.Vector(*(J + kd)), float(ang)))
    arm = arm.cut(cq.Solid.makeSphere(BALL_D / 2 + 0.05, cq.Vector(*B_low)))          # seat, closed on top
    arm = arm.cut(L(cyl_z(OPEN_D / 2, za - 10.0, zb, 0, 0)))                           # snap-in opening below
    arm = arm.cut(cq.Solid.makeCone(OPEN_D / 2 + 1.5, OPEN_D / 2, 1.0, cq.Vector(*(J + (za - 0.01) * kd)),
                                    cq.Vector(*kd)))                                    # entry chamfer (tilt)
    for a, b in ((SLOT_W / 2, BOSS_R + 1), (BOSS_R + 1, SLOT_W / 2)):                    # 2 cross slots
        arm = arm.cut(L(box(-a, a, -b, b, za - 10.0, zb + 0.4)))
    arm = arm.clean()
    wheel = (cq.Solid.makeCylinder(TYRE_R, TYRE_W, cq.Vector(TYRE_IN, J[1], J[2]), cq.Vector(1, 0, 0))
             .cut(cq.Solid.makeCylinder(RIM_R, TYRE_W + 2, cq.Vector(TYRE_IN - 1, J[1], J[2]), cq.Vector(1, 0, 0))))
    return dict(R=R, J=J, kd=kd, zb=zb, B_low=B_low, B_top=B_top, hub=hub, stud=stud, top_stud=top_stud, arm=arm,
                wheel=wheel)


# ------------------------------------------------------------------ checks
def checks(geo, parts):
    J, kd, B = geo["J"], geo["kd"], geo["B_low"]
    rot = lambda s, a: s.rotate(cq.Vector(*J), cq.Vector(*(J + kd)), float(a))
    out = {"ball centre (x, y, z)": [round(float(v), 2) for v in B],
           "caster deg": round(float(np.degrees(np.arctan2(B[1] - geo["B_top"][1], geo["B_top"][2] - B[2]))), 2),
           "lowest point of the hub (z)": round(geo["hub"].BoundingBox().zmin, 2),
           "hub, foot and ball stud to the wheel envelope mm": round(geo["hub"].fuse(geo["stud"]).distance(geo["wheel"]), 2)}
    for name, arm in (("new wishbone", geo["arm"]), ("verified wishbone", parts["front_wishbone_End_A_right"])):
        res = (1e9, 0.0, 0.0)
        for a in np.arange(STEER[0], STEER[1] + 0.1, 5.0):
            w = rot(geo["wheel"], a)
            d = arm.distance(w)
            ov = arm.intersect(w).Volume() if d < 1e-6 else 0.0
            if ov > res[2] or (res[2] == 0 and d < res[0]):
                res = (round(d, 2), float(a), round(ov, 2))
        out[f"{name} to the wheel envelope over the steering angle (distance mm, angle deg, overlap mm3)"] = list(res)
    worst = 0.0
    for a in np.arange(STEER[0], STEER[1] + 0.1, 5.0):
        worst = max(worst, rot(geo["hub"], a).intersect(geo["arm"]).Volume())
    out["hub against the wishbone over the steering angle: largest overlap mm3"] = round(worst, 3)
    worst = 0.0
    for t in np.linspace(TILT[0], TILT[1], 9):
        for a in (STEER[0], 0.0, STEER[1]):
            h = rot(geo["hub"], a).rotate(cq.Vector(*B), cq.Vector(*(B + np.array([0, 1.0, 0]))), float(t))
            worst = max(worst, h.intersect(geo["arm"]).Volume())
    out[f"hub tilted {TILT[0]:g} to {TILT[1]:g} deg against the wishbone: largest overlap mm3"] = round(worst, 3)
    out["ball stud in the seat: overlap mm3"] = round(geo["stud"].intersect(geo["arm"]).Volume(), 3)
    for n in ("running_gear_CVD_drive_shaft_End_A_right", "chassis_plate"):
        out[f"wishbone to {n} mm"] = round(geo["arm"].distance(parts[n]), 2)
        out[f"hub to {n} mm"] = round(geo["hub"].distance(parts[n]), 2)
    return out


# ------------------------------------------------------------------ sketch (3 views and notes)
def sketch(geo, chk, parts, path):
    NEW, ARM, KEEP, GHOST, WHEEL = P.rgb("upright"), P.rgb("arm"), (0.35, 0.37, 0.40), (0.72, 0.74, 0.77), (0.55, 0.57, 0.6)
    B_low, B_top, kd, J, Rk = geo["B_low"], geo["B_top"], geo["kd"], geo["J"], geo["R"]
    lp = lambda x, y, z: J + Rk @ np.array([x, y, z])
    kept = [parts[n] for n in ("running_gear_axle_with_joint_cup_End_A_right", "running_gear_hex_hub_12_End_A_right",
                               "running_gear_CVD_drive_shaft_End_A_right",
                               "running_gear_ball_stud_of_the_steering_arm_End_A_right", "inner_hinge_pin_End_A_right")]
    removed = [parts[n] for n in ("running_gear_C-hub_End_A_right", "running_gear_outer_hinge_pin_3x26_End_A_right",
                                  "front_wishbone_End_A_right", "running_gear_guide_sleeves_End_A_right",
                                  "running_gear_kingpin_washers_End_A_right")]
    S_ball, K_ball, T_ball = np.array([21.7, 257.69, 26.3]), np.array([60.65, 259.13, 24.01]), np.array([18.05, 289.16, 38.3])
    views = {"rear": TD.View((0, -1, 0), (1, 0, 0), (0, 0), (0, 0, 0), 1.0),
             "side": TD.View((1, 0, 0), (0, 1, 0), (0, 0), (0, 0, 0), 1.0),
             "top": TD.View((0, 0, 1), (1, 0, 0), (0, 0), (0, 0, 0), 1.0)}

    def draw(ax, shape, view, color, lw, ls="-", z=2):
        vis, _ = TD.hlr(shape, view)
        for line in vis:
            q = np.array([view.uv2paper(a, b) for a, b in line])
            ax.plot(q[:, 0], q[:, 1], color=color, lw=lw, ls=ls, zorder=z, solid_capstyle="round")

    fig = plt.figure(figsize=(18, 12.5))
    fig.patch.set_facecolor("white")
    axes = {"rear": fig.add_axes([0.02, 0.50, 0.40, 0.40]), "side": fig.add_axes([0.43, 0.50, 0.30, 0.40]),
            "top": fig.add_axes([0.02, 0.03, 0.40, 0.44])}
    titles = {"rear": "View from behind (x outward to the right)", "side": "View from the outside (End A to the right)",
              "top": "Top view (End A up)"}
    lims = {"rear": ((12, 104), (-12, 52)), "side": ((246, 316), (-12, 52)), "top": ((12, 104), (250, 316))}
    for k, ax in axes.items():
        view = views[k]
        draw(ax, geo["wheel"], view, WHEEL, 0.8, ":", 1)
        for s in removed:
            draw(ax, s, view, GHOST, 0.7, "--", 1)
        for s in kept:
            draw(ax, s, view, KEEP, 0.7, "-", 3)
        draw(ax, geo["hub"], view, NEW, 1.4, "-", 5)
        draw(ax, geo["stud"], view, ANN, 1.4, "-", 6)
        draw(ax, geo["top_stud"], view, NEW, 1.4, "-", 5)
        draw(ax, geo["arm"], view, ARM, 1.4, "-", 4)
        a0, a1 = view.P(B_low - 12 * kd), view.P(B_top + 9 * kd)
        ax.plot([a0[0], a1[0]], [a0[1], a1[1]], color="k", lw=0.8, ls=(0, (8, 2, 2, 2)), zorder=7)
        for p0, p1, col in ((S_ball, K_ball, "#2f6f3e"), (T_ball, B_top, "#7a4fb0")):
            q0, q1 = view.P(p0), view.P(p1)
            ax.plot([q0[0], q1[0]], [q0[1], q1[1]], color=col, lw=2.2, alpha=0.8, zorder=6)
        (x0, x1), (y0, y1) = lims[k]
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(titles[k], fontsize=10.5, loc="left", color=TXT)
    lab = dict(fontsize=8.5, color=TXT, va="center", arrowprops=dict(arrowstyle="-", lw=0.6, color="0.3"))
    ann = dict(fontsize=8.5, color=ANN, va="center", fontweight="bold", arrowprops=dict(arrowstyle="-", lw=0.8, color=ANN))
    ax, view = axes["rear"], views["rear"]
    ax.annotate("ball stud 4.8 (standard, as the camber links): screwed into the\nfoot from above, ball pressed into the "
                f"wishbone from below\n(ball x = {B_low[0]:.2f}, z = {B_low[2]:.2f})", view.P(B_low), (14, -8), **ann)
    ax.annotate("foot and web of the hub\n(inside the rim, max. 22 mm from the axle)", view.P(lp(9, 0, -18)), (76, -6), **lab)
    ax.annotate("upper ball joint: ball 4.8 of the camber link,\nscrewed directly into the hub (boss 4.5 longer)",
                view.P(B_top), (14, 48), **ann)
    ax.annotate("steering axis = line through the 2 ball centres\n= current kingpin axis", view.P(J + 8 * kd), (60, 48), **lab)
    ax.annotate("wheel envelope (dotted)", (97.5, 26), (80, 19), **lab)
    ax.annotate("end of the wishbone rises\nto the seat (tilted 10°)", view.P(lp(-5, 0, -9)), (14, 36), **lab)
    ax, view = axes["side"], views["side"]
    caster = chk["caster deg"]
    ax.annotate(f"caster {caster:.1f}° unchanged", view.P(J + 12 * kd), (290, 46), **lab)
    ax.annotate("steering arm and steering link\nas now", view.P(K_ball), (248, 40), **lab)
    ax.annotate("seat along the steering axis,\nclosed on top, snap-in lip below", view.P(B_low), (292, -6), **ann)
    ax, view = axes["top"], views["top"]
    ax.annotate("verified wishbone kept up to x = 57\n(inner lugs, shock plate, sway bar ball)", (40, 300), (14, 313), **lab)
    ax.annotate("new neck and seat (6.75 inside the old outer hinge pin)", view.P(B_low), (58, 256), **ann)
    ax.annotate("old wishbone end (dashed)", (78, 300), (80, 309), **lab)
    txt = fig.add_axes([0.75, 0.01, 0.24, 0.89])
    txt.axis("off")
    k_new = [k for k in chk if k.startswith("new wishbone to the wheel")][0]
    k_old = [k for k in chk if k.startswith("verified wishbone to the wheel")][0]
    notes = [
        ("Concept (option 2)", [
            "The knuckle becomes the steering hub (bearing ring and steering arm as now, no C-hub, no kingpin screws). "
            "Its former lower boss is removed; a web on the wheel side carries a foot under the end of the wishbone.",
            "Lower joint: a standard ball stud 4.8 (as the camber links, neck 3.0, thread M3) is screwed into the foot "
            "from above; its ball points up and is pressed into the wishbone from below. One screw.",
            "Upper joint: the ball 4.8 of the camber link, screwed directly into the hub (upper boss 4.5 longer).",
            f"Steering axis through the 2 balls = current kingpin axis: caster {caster:.1f} deg, wheel position, track "
            "and Ackermann unchanged."]),
        ("Load and seat", [
            "The road pushes the hub up: the foot pushes the ball into the closed top of the seat (pressure on solid "
            "material). The snap-in lip below the ball only holds it when the wheel hangs.",
            f"Seat: wall {SEAT_WALL:g} above the ball, lip opening Ø{OPEN_D:g} for the ball Ø{BALL_D:g} with 2 cross "
            "slots (4 fingers), entry chamfer for the neck. Test coupons in MJF PA12 before the wishbone.",
            "The end of the wishbone rises to the seat (boss along the steering axis, tilted 10 deg); the verified "
            f"wishbone is kept up to x = {X_CUT:g} mm."]),
        ("Clearances (model)", [
            f"Hub, foot and ball stud to the wheel envelope: {chk['hub, foot and ball stud to the wheel envelope mm']} mm "
            f"(they steer together; free radius inside the rim {RIM_R:g} mm from the axle).",
            f"New wishbone to the wheel over {STEER[0]:g} to {STEER[1]:g} deg of steering: {chk[k_new][0]} mm (verified "
            f"wishbone in the same model: {chk[k_old][2]} mm3 overlap at {chk[k_old][1]:g} deg).",
            f"Hub against the wishbone: no contact over the steering angle and with the hub tilted {TILT[0]:g} to "
            f"{TILT[1]:g} deg against the wishbone (suspension travel).",
            f"Ball centre x = {B_low[0]:.2f}, y = {B_low[1]:.2f}, z = {B_low[2]:.2f}; lowest point of the foot z = "
            f"{chk['lowest point of the hub (z)']:.1f} (chassis plate bottom face z = 0)."]),
        ("Open points", [
            f"Wheel envelope from the model (tyre Ø64 x 30, free radius {RIM_R:g} inside the rim): measure the rim before "
            "a design.",
            "Lower pivot point 6.75 mm inward and 3.1 mm higher than the outer hinge pin: camber change and roll centre "
            "to be checked.",
            "Snap-in fit in MJF PA12, loads on the foot and the web, steering stops, CVD joint angle."]),
    ]
    y = 1.0
    for head, items in notes:
        txt.text(0.0, y, head, fontsize=10.5, fontweight="bold", color=TXT, va="top")
        y -= 0.027
        for it in items:
            w = textwrap.fill(it, 62)
            txt.text(0.0, y, "- " + w.replace("\n", "\n  "), fontsize=8.2, color=TXT, va="top")
            y -= 0.0172 * (w.count("\n") + 1) + 0.006
        y -= 0.008
    fig.text(0.02, 0.975, "Study: steering hub with a foot under the wishbone, standard ball stud 4.8 pressed into the "
             "wishbone from below", fontsize=14, fontweight="bold", color=TXT, va="top")
    fig.text(0.02, 0.945, "Front right corner, model geometry. Blue: steering hub. Orange: lower ball stud. Dark blue: "
             "wishbone. Dark grey: kept parts. Dashed light grey: removed parts and the current wishbone. Dotted: wheel "
             "envelope. Green: steering link, purple: camber link.", fontsize=9.5, color=TXT, va="top")
    fig.savefig(path, dpi=110)
    plt.close(fig)


# ------------------------------------------------------------------ render (shaded views)
def render(geo, parts, path):
    J, B_low = geo["J"], geo["B_low"]
    col = dict(P.PARTS)
    col["new_stud"], col["wheel"] = COL_STUD, (0.80, 0.82, 0.85)
    clip = box(-2.0, 110.0, 240.0, 325.0, -5.0, 80.0)
    common = [("chassis_plate", "plate", True), ("speedrun_front_shock_tower_End_A", "tower_front", True),
              ("pivot_block_End_A,_inner", "pivot", True), ("pivot_block_End_A,_outer", "pivot", True),
              ("inner_hinge_pin_End_A_right", "cup", False), ("running_gear_axle_with_joint_cup_End_A_right", "axle", False),
              ("running_gear_hex_hub_12_End_A_right", "axle", False), ("running_gear_CVD_drive_shaft_End_A_right", "cvd", False),
              ("running_gear_ball_stud_of_the_steering_arm_End_A_right", "link", False),
              ("running_gear_steering_link_rod_ends_right", "rodend", False),
              ("running_gear_steering_link_turnbuckle_right", "link", False),
              ("camber_link_End_A_right:_rod_ends", "rodend", False), ("camber_link_End_A_right:_turnbuckle_M3x37", "link", False),
              ("running_gear_damper_rod_ends_End_A_right", "rodend", False),
              ("running_gear_damper_body_with_collar_End_A_right", "damper", False),
              ("running_gear_damper_shaft_End_A_right", "axle", False), ("running_gear_damper_spring_End_A_right", "spring", False),
              ("running_gear_spring_retainer_End_A_right", "damper", False),
              ("running_gear_damper_ball_studs_End_A_right", "link", False), ("running_gear_sway_ball_stud_End_A_right", "link", False)]
    current = [("front_wishbone_End_A_right", "arm"), ("running_gear_C-hub_End_A_right", "upright"),
               ("running_gear_steering_knuckle_End_A_right", "steer"), ("running_gear_outer_hinge_pin_3x26_End_A_right", "cup"),
               ("running_gear_kingpins_End_A_right", "link"), ("running_gear_guide_sleeves_End_A_right", "gear"),
               ("running_gear_kingpin_washers_End_A_right", "drive")]
    concept = [(geo["arm"], "arm"), (geo["hub"], "upright"), (geo["stud"], "new_stud"), (geo["top_stud"], "link")]
    half_wheel = geo["wheel"].cut(box(40.0, 120.0, J[1], 340.0, -20.0, 70.0))

    def tess(shape, tol=0.03):
        vs, idx = shape.tessellate(tol, 0.2)
        v = np.array([[q.x, q.y, q.z] for q in vs])
        return v[np.array(idx)]

    def scene(own, cut=None):
        tris, cols = [], []
        for s, k in [(parts[n].intersect(clip) if cl else parts[n], k) for n, k, cl in common] + own:
            if cut is not None:
                s = s.cut(cut)
            if s is None or len(s.Faces()) == 0:
                continue
            t = subdivide(tess(s), 1.5)
            tris.append(t)
            cols.append(np.tile(col[k], (len(t), 1)))
        return np.concatenate(tris), np.concatenate(cols)

    panels = [([0.00, 0.47, 0.50, 0.43], scene([(parts[n], k) for n, k in current]), iso_basis(40, 24),
               "Now: C-hub, knuckle, outer hinge pin, kingpins with sleeves", None),
              ([0.50, 0.47, 0.50, 0.43], scene(concept), iso_basis(40, 24),
               "Study: steering hub with a foot under the wishbone", None),
              ([0.00, 0.02, 0.50, 0.42], scene(concept + [(half_wheel, "wheel")]), iso_basis(-25, 14),
               "Study with the wheel envelope (cut at the axle), from behind", None),
              ([0.50, 0.02, 0.50, 0.42], scene(concept + [(geo["wheel"], "wheel")], box(-5.0, 120.0, B_low[1], 330.0, -20.0, 80.0)),
               iso_basis(75, 10), "Close-up, cut through the lower ball joint (seen from End A, wheel side on the left)", B_low)]
    fig = plt.figure(figsize=(18, 13))
    fig.patch.set_facecolor("white")
    for rect, (tris, cols), view, title, focus in panels:
        ax = fig.add_axes(rect)
        lo, hi = draw_mesh(ax, tris, view, tri_colors=cols, depth_cue=0.3)
        ax.set_xlim(lo[0] - 2, hi[0] + 2)
        ax.set_ylim(lo[1] - 2, hi[1] + 2)
        if focus is not None:
            _, r_, u_ = view
            fx, fy = float(np.dot(focus, r_)), float(np.dot(focus, u_))
            ax.set_xlim(fx - 24, fx + 24)
            ax.set_ylim(fy - 17, fy + 22)
            bg = dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.9)
            lab = dict(fontsize=10, color=TXT, bbox=bg, arrowprops=dict(arrowstyle="-", lw=0.7, color="0.3"))
            ax.annotate("ball stud 4.8 screwed into the foot,\nball pressed into the wishbone from below", (fx, fy - 3.5),
                        (fx + 3, fy - 14.5), fontsize=10, color=ANN, fontweight="bold", bbox=bg,
                        arrowprops=dict(arrowstyle="-", lw=0.9, color=ANN))
            ax.annotate("seat closed on top: the wheel load\npushes the ball into it", (fx, fy + 2.5), (fx + 6, fy + 17), **lab)
            ax.annotate("foot and web of the hub", (fx - 4.0, fy - 6.5), (fx - 23, fy - 14.5), **lab)
            ax.annotate("rim / tyre (envelope)", (fx - 19, fy - 4), (fx - 23, fy + 17), **lab)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=11.5, loc="left")
    fig.text(0.01, 0.985, "Study: steering hub (C-hub and knuckle in one part) with a foot under the A-shaped front "
             "wishbone (not built)", fontsize=14, fontweight="bold", va="top")
    fig.text(0.01, 0.958, "Blue: C-hub (now) / steering hub (study). Dark blue: wishbone. Orange: lower ball stud 4.8. "
             f"Light grey: wheel envelope (tyre Ø64 x 30, free radius {RIM_R:g} mm inside the rim). Plate and shock tower "
             "cut at the corner.", fontsize=10, va="top")
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    os.chdir(ROOT)
    parts = dict(read_named_solids(ASSEMBLY))
    p = G.load_params(G.PARAMS)
    c = G.corners(p, G.load_params(G.LOWER))
    geo = build(p, c, parts["running_gear_steering_knuckle_End_A_right"], parts["front_wishbone_End_A_right"])
    print("hub valid", geo["hub"].isValid(), "wishbone valid", geo["arm"].isValid())
    for key, name in (("hub", "steering_hub_study_hub_end_a_right"), ("arm", "front_wishbone_steering_hub_study_right")):
        base = os.path.join(HERE, name)
        cq.exporters.export(cq.Workplane().add(geo[key]), base + ".step")
        cq.exporters.export(cq.Workplane().add(geo[key]), base + ".stl", tolerance=0.01, angularTolerance=0.1)
    chk = checks(geo, parts)
    for k, v in chk.items():
        print(" ", k, v)
    with open(STEM + "_results.json", "w", encoding="utf-8") as f:
        json.dump(chk, f, indent=1)
    sketch(geo, chk, parts, STEM + "_sketch.png")
    render(geo, parts, STEM + "_render.png")
    print("wrote the files of the study to", HERE)


if __name__ == "__main__":
    main()
