"""Study: rear hub carrier with a fork on a tongue of the rear wishbone (design concept E of the owner).

The rear wishbone ends in one tube (tongue) on the outer hinge pin instead of 2 outer lugs; the rear hub carrier has
2 lugs (fork) that straddle the tongue instead of one tube between 2 spacers 3x7x3. Shims 3x6x0.5 between the tongue
and the lugs set the position of the hub carrier along the outer hinge pin and with it the wheelbase. The pin is fixed
in the front lug with the grub screw M3x4 (as in the build) and turns in the tongue (bore 3.2).

Taken unchanged from the build: the rear wishbone up to the end of its shock plate (inner hinge pin, rails, web,
shock plate, hole of the sway ball stud, droop bosses), the hub carrier above the pin (bearing tube, web, top tab,
camber stud bore), the axle group and the outer hinge pin 3x26. In the middle position of the shims (3 on each side)
the axle has the position of the build. The parts of the build and the assembly are not changed.

Checks: interference of the study parts with the other parts of the assembly, swing of the hub carrier on the pin
relative to the wishbone, both end positions of the shims (wheelbase range) against the parts around the rear corner.

Usage (from the root directory of the repository, after generate_speedrun_assembly.py):
    python cad/studies/rear_fork_carrier/generate_rear_fork_carrier_study.py

Outputs in cad/studies/rear_fork_carrier: STEP and STL files of the study wishbone (arm coordinates, as the build
wishbones) and of the study hub carrier (right side, chassis plate coordinates, as the running gear), STEP file of
all study parts of both sides, pictures.

Requires the packages cadquery and matplotlib.
"""
import os
import sys

import numpy as np
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "cad"))
import generate_running_gear as G  # noqa: E402
import generate_wishbones as W  # noqa: E402
import technical_drawing as TD  # noqa: E402
import palette as P  # noqa: E402
from generate_bulkhead_lower import box, cyl_x, cyl_y, cyl_z, load_params  # noqa: E402
from generate_assembly_drawing import read_named_solids, bbox, hub_face_point  # noqa: E402
from mesh_views import subdivide, draw_mesh, iso_basis  # noqa: E402

ASSEMBLY = "cad/assembly/speedrun_chassis_T410R.step"
# parts of the build that the study replaces (End B, both sides)
REPLACED = ("rear_wishbone_End_B", "running_gear_hub_carrier_End_B", "running_gear_spacers_3x7x3_End_B",
            "running_gear_outer_hinge_pin_3x26_End_B")
AXLE_GROUP = ("running_gear_axle_with_joint_cup_End_B", "running_gear_hex_hub_12_End_B",
              "running_gear_wheel_bearings_5x10x4_End_B", "running_gear_axle_pin_2x10_End_B")
FOLLOW = ("running_gear_CVD_drive_shaft_End_B", "camber_link_End_B")    # follow the hub carrier (shim positions)

# design values of the study
TONGUE = 7.0             # length of the tongue along the outer hinge pin (tube 7.2 as the lugs of the build)
SHIM = (3.1, 6.0, 0.5)   # shim 3x6x0.5: bore (model with clearance), outer diameter, thickness
N_SHIMS = 6              # 3 on each side in the middle position
LUG = 6.0                # length of one lug of the fork (the boss 6.0 of the grub screw lies under the front lug)
BRIDGE = 1.0             # radial clearance of the bridge of the fork above the tongue
TAPER_X0 = 44.5          # wishbone: start of the taper toward the tongue (end of the shock plate)
NECK = 0.6               # wishbone: radial clearance of the taper to the lugs of the fork
SWING = np.arange(-25.0, 25.1, 2.5)    # rotation of the hub carrier on the pin relative to the wishbone (degrees)
DENSITY_PA12 = 1.01
OUT_ARM = os.path.join(HERE, "rear_wishbone_tongue_study")
OUT_CARRIER = os.path.join(HERE, "rear_hub_carrier_fork_study")
OUT_PARTS = os.path.join(HERE, "rear_fork_carrier_study_parts.step")
PIC = os.path.join(HERE, "rear_fork_carrier_study.png")
PIC_SECTION = os.path.join(HERE, "rear_fork_carrier_study_section.png")


def gap_half():
    """Inner faces of the lugs from the middle of the tongue (middle position of the shims)."""
    return TONGUE / 2 + N_SHIMS * SHIM[2] / 2


# ------------------------------------------------------------------ parts (local frames)
def tongue_arm(ap):
    """Rear wishbone of the study in arm coordinates: the build wishbone up to the end of the shock plate, then a
    plate as high as the rails that tapers to the tongue (one tube on the outer hinge pin, bore 3.2)."""
    length, half = ap["rear_arm_length"], ap["inner_width"] / 2
    yo = ap["rear_rail_y"][1]
    h = ap["rail_h"] / 2
    r = ap["outer_lug_d"] / 2
    zp = ap["outer_pin_z"]
    s = W.arm_solid(ap, "rear").cut(box(TAPER_X0, length + 10, -half - 1, half + 1, -20, 20))
    xt = length - r - NECK                                      # end of the taper: clear of the lugs of the fork
    taper = W.prism([(TAPER_X0 - 0.01, -yo), (TAPER_X0 - 0.01, yo), (xt, TONGUE / 2), (length, TONGUE / 2),
                     (length, -TONGUE / 2), (xt, -TONGUE / 2)], -h, h)
    s = s.fuse(taper).fuse(cyl_y(r, -TONGUE / 2, TONGUE / 2, length, zp))
    s = s.cut(cyl_y(ap["pin_bore_d"] / 2, -half - 1, half + 1, length, zp))
    return s.clean()


def fork_carrier(p):
    """Rear hub carrier of the study in the frame of the outer hinge pin (x along the arm, y along the pin, z up):
    2 lugs straddle the tongue, a bridge above the tongue joins them to the column under the bearing tube; above the
    column the part is the hub carrier of the build. Grub screw M3x4 from below in the front lug (+y)."""
    t_len, t_d, w_web = p["rear_carrier"][:3]
    pin_bore, lip_h, _ = p["rear_carrier_bores"]
    lay = G.rear_carrier_layout(p)
    r, x1, x0, zt, xc, za = lay["r_lug"], lay["x1"], lay["x0"], lay["zt"], lay["stud_x"], lay["za"]
    rt, rb, wb = t_d / 2, 5.0, 4.0
    g = gap_half()
    yl = g + LUG                                               # outer faces of the lugs
    zb = r + BRIDGE                                            # lower face of the bridge above the tongue
    zc = za - 5.0                                              # top of the column (in the bearing tube), as the build
    yoke = (cq.Workplane("YZ").polyline([(-yl, 0), (-g, 0), (-g, zb), (g, zb), (g, 0), (yl, 0), (yl, zb + 1.0),
                                         (4.0, zc), (-4.0, zc), (-yl, zb + 1.0)]).close().extrude(6.0).val()
            .translate(cq.Vector(-3.0, 0, 0)))
    xs = min(xc - 3.5, x0)
    car = G.fuse(cyl_y(r, g, yl, 0, 0), cyl_y(r, -yl, -g, 0, 0), yoke, cyl_x(rt, x0, x1, 0, za),
                 box(x0, x0 + w_web, -4.0, 4.0, za, zt), box(xs, x0 + w_web, -4.0, 4.0, zt - 3.5, zt))
    if xs < x0:                                                # sloped arm to the seat of the camber stud (build)
        arm = [(x0 + 1.0, za + rt - 1.0), (x0 + w_web, za + rt - 1.0), (x0 + w_web, zt - 3.4), (xs, zt - 3.4)]
        car = G.fuse(car, cq.Workplane("XZ").polyline(arm).close().extrude(4.0, both=True).val())
    zg = G.grub_boss_depth(p)
    yg = (g + yl) / 2                                          # middle of the front lug
    car = G.fuse(car, cyl_z(p["grub_screw_boss"][2] / 2, -zg, -1.0, 0, yg))
    car = car.cut(cyl_y(pin_bore / 2, -yl - 1, yl + 1, 0, 0))                            # bore of the hinge pin
    car = car.cut(cyl_x(rb, x0 - 1, x0 + wb, 0, za)).cut(cyl_x(rb, x1 - wb, x1 + 1, 0, za))     # bearing seats
    car = car.cut(cyl_x(rb - lip_h, x0 - 1, x1 + 1, 0, za))                              # lip between them
    car = car.cut(cyl_z(G.TAP / 2, zt - 4.5, zt + 1, xc, 0))                             # thread M3, camber stud
    car = car.cut(cyl_z(G.TAP / 2, -zg - 1, 0, 0, yg))                                   # thread M3, grub screw
    return car.clean()


def shims(s=0.0):
    """Shims on the pin, against the faces of the tongue (frame of the outer hinge pin): s is the shift of the hub
    carrier along the pin (+y: toward the front of the car). Returns the compound and the number in front and behind."""
    t = SHIM[2]
    n_f = int(round((gap_half() + s - TONGUE / 2) / t))
    n_r = N_SHIMS - n_f
    rings = [cyl_y(SHIM[1] / 2, y0, y0 + t, 0, 0).cut(cyl_y(SHIM[0] / 2, y0 - 1, y0 + t + 1, 0, 0))
             for y0 in [TONGUE / 2 + k * t for k in range(n_f)] + [-TONGUE / 2 - (k + 1) * t for k in range(n_r)]]
    return cq.Compound.makeCompound(rings), n_f, n_r


def pin(s=0.0):
    return cyl_y(1.5, -13.0 + s, 13.0 + s, 0, 0)


# ------------------------------------------------------------------ placement
class Corner:
    """Frame of the outer hinge pin of the rear right arm (origin on the pin in the middle of the arm)."""

    def __init__(self, p):
        c = G.corners(p, load_params(G.LOWER))["rear"]
        self.O, self.ex, self.ey = c["O"], c["ex"], c["ey"]
        self.R = np.column_stack([self.ex, self.ey, [0, 0, 1.0]])

    def world(self, solid, side=1):
        s = G.place(solid, self.R, self.O)
        return s if side > 0 else G.mirror_x(s)

    def local(self, solid):
        """Solid of the right side (chassis plate coordinates) in the frame of the outer hinge pin."""
        Ri = self.R.T
        return G.place(solid.translate(cq.Vector(*(-self.O))), Ri, np.zeros(3))


def study_parts(p, ap, k, s=0.0):
    """Study parts of both sides in chassis plate coordinates: list of (name, colour key, solid)."""
    arm = tongue_arm(ap)
    car = fork_carrier(p).translate(cq.Vector(0, s, 0))
    sh = shims(s)[0]
    out = []
    for side, sname in ((1, "right"), (-1, "left")):
        out += [(f"rear wishbone tongue study End B {sname}", "arm", W.place_arm(arm, "rear", side)),
                (f"rear hub carrier fork study End B {sname}", "upright", k.world(car, side)),
                (f"shims 3x6x0.5 End B {sname}", "spring", k.world(sh, side)),
                (f"outer hinge pin 3x26 End B {sname}", "cup", k.world(pin(s), side))]
    return out


# ------------------------------------------------------------------ checks
def overlaps(movers, others, tol=1e-3):
    """Interference of each part in movers with each part in others (bounding boxes first): list of
    (name a, name b, volume mm3)."""
    res = []
    for na, sa in movers:
        ba = bbox(sa)
        for nb, sb in others:
            bb = bbox(sb)
            if np.any(ba[:3] > bb[3:] + 0.01) or np.any(bb[:3] > ba[3:] + 0.01):
                continue
            v = sa.intersect(sb).Volume()
            if v > tol:
                res.append((na, nb, round(v, 3)))
    return res


def swing(car_w, arm_w, k):
    """Overlap volume and smallest distance of the hub carrier (right) and the wishbone (right) for each rotation of
    the hub carrier on the outer hinge pin."""
    a0, a1 = cq.Vector(*k.O), cq.Vector(*(k.O + k.ey))
    rows = []
    for th in SWING:
        c = car_w.rotate(a0, a1, float(th))
        rows.append((float(th), c.intersect(arm_w).Volume(), c.distance(arm_w)))
    return rows


def name_has(n, keys):
    return any(n.startswith(kk) for kk in keys)


def build_and_check():
    p = load_params(G.PARAMS)
    ap = load_params(W.PARAMS)
    k = Corner(p)
    assy = read_named_solids(ASSEMBLY)
    others = [(n, s) for n, s in assy if not name_has(n, REPLACED)]
    study = study_parts(p, ap, k)
    res = {}

    # volumes and masses (nylon PA12 as for the wishbones of the build; the material of the hub carrier is open)
    arm_b = W.arm_solid(ap, "rear")
    arm_s = tongue_arm(ap)
    car_b = next(s for n, s in assy if n == "running_gear_hub_carrier_End_B_right")
    car_s = fork_carrier(p)
    res["volumes"] = {"wishbone build": arm_b.Volume() / 1000, "wishbone study": arm_s.Volume() / 1000,
                      "hub carrier build": car_b.Volume() / 1000, "hub carrier study": car_s.Volume() / 1000}
    # frame check: the study hub carrier keeps the upper part of the build hub carrier
    car_s_w = k.world(car_s)
    upper = box(-30, 30, -30, 30, G.rear_carrier_layout(p)["za"] - 5.0, 60)
    res["upper part kept (mm3 different)"] = abs(car_s_w.intersect(k.world(upper)).Volume()
                                                 - car_b.intersect(k.world(upper)).Volume())

    # 1. interference in the middle position of the shims
    sns = [(n, s) for n, _, s in study]
    res["interference"] = overlaps(sns, others) + [(a, b, v) for a, b, v in overlaps(sns, sns) if a < b]

    # 2. swing of the hub carrier on the pin relative to the wishbone (right side)
    arm_w = W.place_arm(arm_s, "rear", 1)
    res["swing"] = swing(car_s_w, arm_w, k)

    # 3. end positions of the shims: hub carrier, pin and axle group moved along the pin; the CVD drive shaft and the
    # camber link follow the hub carrier and are left out of the check
    t = SHIM[2]
    span = N_SHIMS * t / 2
    hub_parts = [(n, s) for n, s in assy if name_has(n, AXLE_GROUP) and "End_B_right" in n]
    H0 = hub_face_point(next(s for n, s in hub_parts if n.startswith("running_gear_hex_hub_12")),
                        next(s for n, s in hub_parts if n.startswith("running_gear_axle_with_joint_cup")))
    lay = G.rear_carrier_layout(p)
    lp, d = load_params(G.LOWER), load_params(G.DRIVE)
    inner = np.array([lp["body_half_width"] + d["outdrive_gap"] + d["outdrive_length"] - 4.0,
                      G.BULKHEAD_Y["rear"] + lp["diff_axis_y"], G.AXIS_Z])
    joint0 = k.O + k.R @ np.array([lay["x0"] - 5.0, 0, lay["za"]])
    fixed = [(n, s) for n, s in others if not ("End_B_right" in n and name_has(n, AXLE_GROUP + FOLLOW))]
    fixed += [(n, s) for n, s in sns if n.endswith("right") and "wishbone" in n]
    res["shift"] = []
    for s in (-span, 0.0, span):
        mv = k.ey * s
        movers = [(f"rear hub carrier fork study (shift {s:+.1f})", k.world(fork_carrier(p).translate(cq.Vector(0, s, 0)))),
                  ("outer hinge pin 3x26", k.world(pin(s)))]
        movers += [(n, sh.translate(cq.Vector(*mv))) for n, sh in hub_parts]
        sh_s, n_f, n_r = shims(s)
        hits = overlaps(movers, fixed) + overlaps([("shims", k.world(sh_s))], fixed)
        joint = joint0 + mv
        L = float(np.linalg.norm(joint - inner))
        ang = float(np.degrees(np.arctan2(joint[1] - inner[1], joint[0] - inner[0])))
        res["shift"].append({"shift": s, "front": n_f, "rear": n_r, "axle y": float((H0 + mv)[1]), "hits": hits,
                             "cvd length": L, "cvd plan angle": ang})
    return p, ap, k, assy, study, res


# ------------------------------------------------------------------ pictures
def tess(shape, tol=0.03):
    verts, idx = shape.tessellate(tol, 0.2)
    v = np.array([[q.x, q.y, q.z] for q in verts])
    return v[np.array(idx)]


REGION = (40.0, 95.0, 5.0, 50.0, -3.0, 36.0)      # rear right corner (chassis plate coordinates)


def corner_mesh(parts):
    region = box(*REGION)
    tris, cols = [], []
    for _, key, s in parts:
        b = bbox(s)
        if b[3] < REGION[0] or b[0] > REGION[1] or b[4] < REGION[2] or b[1] > REGION[3]:
            continue
        cut = s.intersect(region)
        if cut.Volume() < 1e-3:
            continue
        t = subdivide(tess(cut), 1.2)
        tris.append(t)
        cols.append(np.tile(P.rgb(key), (len(t), 1)))
    return np.concatenate(tris), np.concatenate(cols)


def build_corner(assy):
    """Parts of the rear right corner of the build with their colour keys."""
    keys = {"rear_wishbone": "arm", "running_gear_hub_carrier": "upright", "running_gear_spacers": "axle",
            "running_gear_outer_hinge_pin": "cup", "running_gear_axle_with": "axle", "running_gear_hex_hub": "axle",
            "running_gear_wheel_bearings": "bearing", "running_gear_axle_pin": "cup", "running_gear_CVD": "cvd"}
    out = []
    for n, s in assy:
        if not n.endswith("End_B_right"):
            continue
        for kk, col in keys.items():
            if n.startswith(kk):
                out.append((n, col, s))
    return out


def picture(assy, study):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    build = build_corner(assy)
    rest = [(n, c, s) for n, c, s in build if not name_has(n, REPLACED)]
    st = [(n, c, s) for n, c, s in study if n.endswith("right")] + rest
    fig = plt.figure(figsize=(16, 6.4))
    views = [(build, iso_basis(-40, 28), "Build: hub carrier with one tube between 2 spacers 3x7x3,\n"
              "2 outer lugs on the wishbone (view from outside and above)"),
             (st, iso_basis(-40, 28), "Study: fork on the hub carrier, tongue on the wishbone,\n"
              "shims 3x6x0.5 (light blue) set the wheelbase (view from outside and above)"),
             (st, iso_basis(-15, -30), "Study from outside and below: tongue between the lugs,\n"
              "shims on both sides, grub screw boss under the front lug")]
    for i, (parts, basis_, title) in enumerate(views):
        tris, cols = corner_mesh(parts)
        ax = fig.add_axes([i / 3, 0.0, 1 / 3, 0.86])
        lo, hi = draw_mesh(ax, tris, basis_, tri_colors=cols, depth_cue=0.3)
        ax.set_xlim(lo[0] - 2, hi[0] + 2)
        ax.set_ylim(lo[1] - 2, hi[1] + 2)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=10, loc="left")
    fig.suptitle("Study: rear hub carrier with a fork on a tongue of the rear wishbone (rear right corner)",
                 fontsize=12, y=0.985)
    fig.savefig(PIC, dpi=110)
    plt.close(fig)


def section_picture(p, ap, assy, k):
    """Sections through the axis of the outer hinge pin, seen from above (front of the car up, outer end right):
    build and study, scale 4:1, with the widths along the pin."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    s4 = 4.0
    W_, H_ = 330.0, 175.0
    fig = plt.figure(figsize=(W_ / 25.4, H_ / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_)
    ax.set_ylim(0, H_)
    ax.set_aspect("equal")
    ax.axis("off")
    clip = box(-15.0, 8.0, -16.0, 16.0, -10.0, 40.0)            # region around the pin (frame of the pin)
    arm_b = W.arm_solid(ap, "rear").translate(cq.Vector(-ap["rear_arm_length"], 0, 0))
    arm_s = tongue_arm(ap).translate(cq.Vector(-ap["rear_arm_length"], 0, 0))
    car_b = k.local(next(s for n, s in assy if n == "running_gear_hub_carrier_End_B_right"))
    spacers = k.local(next(s for n, s in assy if n == "running_gear_spacers_3x7x3_End_B_right"))
    g, yl, t = gap_half(), gap_half() + LUG, SHIM[2]
    lug_b, gap_b = ap["rear_outer_lug_len"], ap["rear_outer_gap"]
    sets = [("Build", 20.0, [arm_b, car_b, spacers, pin()]),
            ("Study", 185.0, [arm_s, fork_carrier(p), shims()[0], pin()])]
    for title, x_left, solids in sets:
        comp = cq.Compound.makeCompound([s.intersect(clip) for s in solids])
        V = TD.View((0, 0, 1), (1, 0, 0), (x_left + 15.0 * s4 + 10, 92.0), scale=s4)    # pin axis at paper x
        TD.draw_section(ax, comp, V, (0, 0, -0.001))
        TD.centre_line(ax, V.P((0, -15.5, 0)), V.P((0, 15.5, 0)))
        TD.text(ax, (x_left, 168.0), f"{title}: section at the axis of the outer hinge pin, from above "
                f"(4:1, front up)", ha="left", fs=9, weight="bold")
        xd = V.P((8.0, 0, 0))[0]
        if title == "Build":
            ys = [-gap_b / 2 - lug_b, -gap_b / 2, -4.6, 4.6, gap_b / 2, gap_b / 2 + lug_b]
            labs = [f"{lug_b:.1f}", None, "9.2", None, f"{lug_b:.1f}"]
            notes = ["2 lugs on the wishbone, 5.5 each", "hub carrier: one tube 9.2 on the pin",
                     "spacers 3x7x3 beside the tube", "grub screw M3x4 under the tube"]
        else:
            ys = [-yl, -g, -TONGUE / 2, TONGUE / 2, g, yl]
            labs = [f"{LUG:.1f}", f"{g - TONGUE / 2:.1f}", f"{TONGUE:.1f}", f"{g - TONGUE / 2:.1f}", f"{LUG:.1f}"]
            notes = [f"tongue of the wishbone, {TONGUE:.1f} on the pin", f"fork of the hub carrier: 2 lugs {LUG:.1f}",
                     f"shims 3x6x{t:g}: {N_SHIMS // 2} in front, {N_SHIMS // 2} behind",
                     "grub screw M3x4 under the front lug"]
        for i, lab in enumerate(labs):
            if lab:
                short = abs(ys[i + 1] - ys[i]) * s4 < 10
                TD.linear(ax, V.P((3.6, ys[i], 0)), V.P((3.6, ys[i + 1], 0)), "v", xd + 6, lab, inside=not short,
                          tside="r")
        TD.linear(ax, V.P((3.6, ys[0], 0)), V.P((3.6, ys[-1], 0)), "v", xd + 18, f"{ys[-1] - ys[0]:.1f}", tside="r")
        TD.linear(ax, V.P((1.5, -13.0, 0)), V.P((1.5, 13.0, 0)), "v", xd + 30, "26.0 (pin)", tside="r")
        for j, nt in enumerate(notes):
            TD.text(ax, (x_left, 24.0 - 4.6 * j), nt, ha="left", fs=8)
    TD.text(ax, (W_ - 8, 6.0), "Hatched: cut faces at the axis of the pin. Outer end of the car (wheel) to the right.",
            ha="right", fs=7.5)
    fig.savefig(PIC_SECTION, dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------ main
def export(parts, path):
    assy = cq.Assembly(name="rear_fork_carrier_study")
    for i, (nm, key, s) in enumerate(parts):
        assy.add(s, name=nm.replace(" ", "_"), color=cq.Color(*[c ** 2.2 for c in P.rgb(key)]))
    from cadquery.occ_impl.exporters.assembly import exportAssembly
    exportAssembly(assy, path)


def main():
    p, ap, k, assy, study, res = build_and_check()
    v = res["volumes"]
    print("volumes (cm3): " + ", ".join(f"{kk} {vv:.2f} ({vv * DENSITY_PA12:.1f} g PA12)" for kk, vv in v.items()))
    print(f"upper part of the hub carrier kept: difference {res['upper part kept (mm3 different)']:.4f} mm3")
    print("interference in the middle position:", res["interference"] or "none")
    free = [th for th, vol, dist in res["swing"] if vol < 1e-3]
    print(f"swing of the hub carrier relative to the wishbone: free from {min(free):+.1f} to {max(free):+.1f} deg")
    for th, vol, dist in res["swing"]:
        print(f"  {th:+5.1f} deg: overlap {vol:.3f} mm3, distance {dist:.2f} mm")
    for r in res["shift"]:
        print(f"shift {r['shift']:+.1f} mm (shims {r['front']} in front, {r['rear']} behind): face of the hex hub y = "
              f"{r['axle y']:.2f}, CVD {r['cvd length']:.2f} mm at {r['cvd plan angle']:.2f} deg in the top view, "
              f"interference: {r['hits'] or 'none'}")
    for path, solid in ((OUT_ARM, tongue_arm(ap)), (OUT_CARRIER, k.world(fork_carrier(p)))):
        cq.exporters.export(solid, path + ".step")
        cq.exporters.export(solid, path + ".stl", tolerance=0.01, angularTolerance=0.1)
    export(study, OUT_PARTS)
    picture(assy, study)
    section_picture(p, ap, assy, k)
    print("wrote the STEP and STL files and", PIC, PIC_SECTION)


if __name__ == "__main__":
    main()
