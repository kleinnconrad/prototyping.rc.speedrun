"""Generate the speedrun battery tray for the LiPo Absima GreenHorn V2 3S 5000 mAh (hardcase).

Speedrun part, designed in this project. MJF 3D print in nylon PA12 (owner).

* Floor on the top face of the chassis plate on the left side of the car, fixed with 4 countersunk screws M3x6 from
  below through H11, H12, H22 and H23 (owner) into blind holes in the end stops.
* The battery (138 x 46 x 35, spec_battery.yaml) lies on the floor between 2 end stops and 2 low side walls. It
  stands beside the top brace (the brace is lower than the top of the battery), behind the steering and beside the
  drive line.
* 2 velcro straps 20 mm (owner) hold the battery from left to right: each strap runs over the battery, down through a
  slot beside the battery on each side and through a channel under the floor (wraps battery and floor). The slots
  and channels are wider than the strap, so it can be threaded easily.

All values with their source: cad/speedrun_parts/battery_tray/battery_tray_parameters.json.

Usage (from the root directory of the repository):
    python scripts/cad/generate_battery_tray.py [--no-check]

Outputs (chassis plate coordinates):
* cad/speedrun_parts/battery_tray/battery_tray_speedrun.step and .stl (position in the car)
* photos/cad_battery_tray_drawing.png: tray alone, tray with battery and straps in the car (top brace, steering,
  drive line), section across the car at a strap

Checks: overlap of the tray, the battery and the straps with all parts of the assembly
(cad/assembly/speedrun_chassis_T410R.step); steering on the left side (bellcrank, bridge with its sleeves, washers
and screws, servo link) turned and moved over the full angle of the bellcranks; smallest distances to the top brace, the
servo mount, the steering and the drive line.

Requires the packages cadquery and numpy.
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_bulkhead_lower import box, cyl_z, load_params  # noqa: E402
import edge_treatment as ET  # noqa: E402

PARAMS = "cad/speedrun_parts/battery_tray/battery_tray_parameters.json"
PLATE_GEOM = "cad/speedrun_parts/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_speedrun_wide_motor10_geometry.json"
ASSEMBLY = "cad/assembly/speedrun_chassis_T410R.step"
OUT = "cad/speedrun_parts/battery_tray/battery_tray_speedrun"
DRAWING = "photos/cad_battery_tray_drawing.png"
PLATE_T = 2.0


def holes(p):
    d = json.load(open(PLATE_GEOM))
    h = {q["id"]: (q["x"], q["y"]) for q in d["holes"]}
    return [h[k] for k in p["mount_holes"]]


def fillet_z(solid, r):
    """Fillet of the vertical edges (no change if the fillet fails)."""
    try:
        out = cq.Workplane().add(solid).edges("|Z").fillet(r).val()
        sols = out.Solids()
        return sols[0] if len(sols) == 1 and sols[0].isValid() else solid
    except Exception:  # noqa: BLE001
        return solid


def layout(p):
    """Main coordinates of the tray: pocket of the battery, end stops, straps."""
    L, W, H, _ = p["battery"]
    cl = p["clearance"]
    hs = holes(p)
    y_r = (hs[0][1] + hs[1][1]) / 2                                          # rear holes (H11, H12)
    y_f = (hs[2][1] + hs[3][1]) / 2                                          # front holes (H22, H23)
    ym = (y_r + y_f) / 2
    x_in = p["battery_x_inner"]
    x_out = x_in - W
    py0, py1 = ym - L / 2 - cl, ym + L / 2 + cl                              # pocket along the car
    px0, px1 = x_out - cl, x_in + cl                                         # pocket across the car
    wt, wh = p["wall"]
    sw, sl, sx, cd, sd, st = p["strap"]
    ys = (ym - sd / 2, ym + sd / 2)                                          # straps
    z0 = PLATE_T
    zf = z0 + p["floor_t"]                                                   # top of the floor
    return dict(L=L, W=W, H=H, hs=hs, y_r=y_r, y_f=y_f, ym=ym, x_in=x_in, x_out=x_out, py0=py0, py1=py1, px0=px0,
                px1=px1, wt=wt, wh=wh, sw=sw, sl=sl, sx=sx, cd=cd, ys=ys, st=st, z0=z0, zf=zf,
                ty0=y_r - p["stop_margin"], ty1=y_f + p["stop_margin"], xa=px0 - wt, xb=px1 + wt)


def tray_solid(p):
    g = layout(p)
    fl = p["slot_flange"]
    # slots across the car: from 0.5 inside the battery outline outward
    slot_in = (g["x_in"] - 0.5, g["x_in"] - 0.5 + g["sx"])
    slot_out = (g["x_out"] + 0.5 - g["sx"], g["x_out"] + 0.5)
    # floor with ears at the slots
    floor = box(g["xa"], g["xb"], g["ty0"], g["ty1"], g["z0"], g["zf"])
    for y in g["ys"]:
        floor = floor.fuse(box(slot_out[0] - fl, slot_in[1] + fl, y - g["sl"] / 2 - fl, y + g["sl"] / 2 + fl, g["z0"], g["zf"]))
    floor = fillet_z(floor.clean(), 1.0)
    s = floor
    # end stops (with the blind holes) and side walls (interrupted at the straps)
    zs = g["zf"] + p["stop_h"]
    s = s.fuse(box(g["xa"], g["xb"], g["ty0"], g["py0"], g["zf"] - 0.01, zs))
    s = s.fuse(box(g["xa"], g["xb"], g["py1"], g["ty1"], g["zf"] - 0.01, zs))
    gap = g["sl"] / 2 + 1.0
    cuts_y = [g["py0"]] + [v for y in g["ys"] for v in (y - gap, y + gap)] + [g["py1"]]
    for k in range(0, len(cuts_y), 2):
        ya, yb = cuts_y[k], cuts_y[k + 1]
        for xa, xb in ((g["xa"], g["px0"]), (g["px1"], g["xb"])):
            s = s.fuse(box(xa, xb, ya - 0.01, yb + 0.01, g["zf"] - 0.01, g["zf"] + g["wh"]))
    # strap slots through the floor, channels under the floor, chamfers at the top of the slots
    for y in g["ys"]:
        y0, y1 = y - g["sl"] / 2, y + g["sl"] / 2
        for xa, xb in (slot_in, slot_out):
            s = s.cut(box(xa, xb, y0, y1, g["z0"] - 1, g["zf"] + 1))
            # chamfer 0.8 x 45 deg at the top of the slot (easy threading): frustum of a pyramid
            s = s.cut(cq.Workplane("XY").workplane(offset=g["zf"] - 0.8).center((xa + xb) / 2, (y0 + y1) / 2)
                      .rect(xb - xa, y1 - y0).workplane(offset=0.81).rect(xb - xa + 1.62, y1 - y0 + 1.62).loft().val())
        s = s.cut(box(slot_out[0], slot_in[1], y0, y1, g["z0"] - 1, g["z0"] + g["cd"]))
    # windows in the floor (mass)
    mx, my, rw = p["windows"]
    wx0, wx1 = g["px0"] + mx, g["px1"] - mx
    edges = [g["py0"] + my, g["ys"][0] - g["sl"] / 2 - my, g["ys"][0] + g["sl"] / 2 + my,
             g["ys"][1] - g["sl"] / 2 - my, g["ys"][1] + g["sl"] / 2 + my, g["py1"] - my]
    for k in range(0, 6, 2):
        if edges[k + 1] - edges[k] > 2 * rw + 1:
            s = s.cut(fillet_z(box(wx0, wx1, edges[k], edges[k + 1], g["z0"] - 1, g["zf"] + 1), rw))
    # blind holes from below for the countersunk screws M3x6
    d, depth = p["screw_hole"]
    for hx, hy in g["hs"]:
        s = s.cut(cyl_z(d / 2, g["z0"] - 1, g["z0"] + depth, hx, hy))
    # chamfer on each sharp outer edge (owner, 2026-11-22: chamfers only)
    ch, ang = p["edge_chamfer"]
    s, tray_solid.edges = ET.treat(s.clean(), ch, None, (), ang)
    return s


def battery_solid(p):
    g = layout(p)
    r = p["battery"][3]
    b = box(g["x_out"], g["x_in"], g["ym"] - g["L"] / 2, g["ym"] + g["L"] / 2, g["zf"], g["zf"] + g["H"])
    return fillet_z(b, r)


def straps_solid(p):
    """The 2 velcro straps as closed bands: over the battery, down beside it, through the channel under the floor."""
    g = layout(p)
    t, zt = g["st"], g["zf"] + g["H"]
    out = []
    for y in g["ys"]:
        y0, y1 = y - g["sw"] / 2, y + g["sw"] / 2
        band = box(g["x_out"] - t, g["x_in"] + t, y0, y1, zt, zt + t)                       # over the battery
        band = band.fuse(box(g["x_in"], g["x_in"] + t, y0, y1, g["z0"] + t, zt + 0.01))       # inner side
        band = band.fuse(box(g["x_out"] - t, g["x_out"], y0, y1, g["z0"] + t, zt + 0.01))     # outer side
        band = band.fuse(box(g["x_out"] - t, g["x_in"] + t, y0, y1, g["z0"], g["z0"] + t + 0.01))  # in the channel
        out.append(band.clean())
    return cq.Compound.makeCompound(out)


def car_parts_in_plate(p=None):
    """Battery tray, battery and straps in chassis plate coordinates: list of (name, kind, solid)."""
    p = p or load_params(PARAMS)
    return [("speedrun battery tray", "battery_tray", tray_solid(p)),
            ("battery Absima GreenHorn 3S 5000 (hardcase)", "battery", battery_solid(p)),
            ("velcro straps 20 mm of the battery", "strap", straps_solid(p))]


# ------------------------------------------------------------------ checks
def distance(a, b):
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value()


def check(own):
    """Overlap with the assembly, smallest distances to the neighbours, left steering over the full angle."""
    sys.path.insert(0, "cad/studies/dual_motor")
    from generate_dual_motor_study import read_assembly
    import generate_running_gear as G
    own_names = ("speedrun_battery_tray", "battery_Absima", "velcro_straps")                  # the tray itself in the assembly
    asm = [(nm, s) for nm, s, _ in read_assembly(ASSEMBLY) if not nm.startswith(own_names)]
    own_c = cq.Compound.makeCompound([s for _, _, s in own])
    ob = own_c.BoundingBox()
    bad = []
    for nm, s in asm:
        b = s.BoundingBox()
        if b.xmin > ob.xmax or ob.xmin > b.xmax or b.ymin > ob.ymax or ob.ymin > b.ymax or b.zmin > ob.zmax or ob.zmin > b.zmax:
            continue
        for on, _, o in own:
            v = o.intersect(s).Volume()
            if v > 1e-4:
                bad.append((round(v, 4), on, nm))
    print(f"  overlap with the {len(asm)} parts of the assembly:", bad if bad else "none")
    names = dict(asm)
    for key in ("speedrun_top_brace", "running_gear_servo_mount_top_plate", "centre_driveshaft", "cup_joint_End_B",
                "motor_mount", "running_gear_steering_bridge", "running_gear_bridge_washers,_screws_M3x16_and_lock_nuts",
                "running_gear_servo_link_rod_ends", "running_gear_bellcrank_left"):
        if key in names:
            print(f"  distance to {key}: " + ", ".join(f"{on.split()[0]} {distance(o, names[key]):.2f}" for on, _, o in own))
    # left steering: bellcrank (with ball and screw) turned about the left post, bridge group moved (parallelogram)
    p = G.load_params(G.PARAMS)
    c = G.corners(p, G.load_params(G.LOWER))
    _, _, kb = G.front_corner(p, G.load_params(G.DRIVE), c["front"])
    parts = {n: s for n, _, s in G.steering(p, G.load_params(G.CL.PARAMS), c, kb)}
    info = G.steering.info
    ang = info["ackermann"]["bellcrank 25"] + 3.0
    PL = np.array([-21.7, 242.69])
    BL = np.array([-21.7, 242.69 - p["bellcrank"][4]])
    ring = G.sphere(5.0, info["bridge ball"])                                 # rod end of the servo link on the bridge
    turning = [parts["bellcrank left"], parts["bellcrank ball left"], parts["bellcrank ball screw M3x10 left"]]
    moving = [parts["steering bridge"], parts["bridge guide sleeves"], parts["bridge washers, screws M3x16 and lock nuts"],
              parts["ball stud of the bridge"], ring]
    worst, dmin = 0.0, 1e9
    for a in np.linspace(-ang, ang, 15):
        t = math.radians(a)
        v = BL - PL
        d = np.array([math.cos(t) * v[0] - math.sin(t) * v[1], math.sin(t) * v[0] + math.cos(t) * v[1]]) - v
        group = [s.rotate(cq.Vector(PL[0], PL[1], 0), cq.Vector(PL[0], PL[1], 1), a) for s in turning]
        group += [s.translate(cq.Vector(d[0], d[1], 0)) for s in moving]
        gc = cq.Compound.makeCompound(group)
        worst = max(worst, gc.intersect(own_c).Volume())
        dmin = min(dmin, distance(gc, own_c))
    print(f"  left steering turned by +-{ang:.1f} deg: largest overlap {worst:.4f} mm3, smallest distance {dmin:.2f}")
    return bad, worst, dmin


def drawing(own, path=DRAWING):
    """Tray alone (3D), tray with battery and straps in the car with the neighbouring parts (3D), section across the
    car through the rear strap with the top brace."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mesh_views import subdivide, draw_mesh, iso_basis
    sys.path.insert(0, "cad/studies/dual_motor")
    from generate_dual_motor_study import read_assembly
    p = load_params(PARAMS)
    g = layout(p)
    keep = ("chassis_plate", "speedrun_top_brace", "centre_driveshaft", "cup_joint_End_B", "motor_mount", "spur_gear",
            "rear_pinion_shaft", "running_gear_steering_bridge", "running_gear_bellcrank_left", "running_gear_steering_post_left",
            "running_gear_servo_link", "running_gear_ball_stud_of_the_bridge", "running_gear_bridge", "running_gear_servo",
            "lower_bulkhead_End_A", "upper_bulkhead_End_A")
    srgb = lambda c: tuple(float(v) ** (1 / 2.2) for v in c[:3]) if c is not None else (0.6, 0.6, 0.62)  # noqa: E731
    asm = [(nm, s, srgb(c)) for nm, s, c in read_assembly(ASSEMBLY) if nm.startswith(keep)]
    import palette as P                                      # colour scheme of the CAD pictures: blue and grey
    col = {k: P.rgb(k) for k in ("battery_tray", "battery", "strap")}

    def tess(s, me=1.5):
        v, idx = s.tessellate(0.03, 0.2)
        return subdivide(np.array([[q.x, q.y, q.z] for q in v])[np.array(idx)], me)

    def mesh(items, region=None):
        tris, cols = [], []
        box_r = cq.Solid.makeBox(region[3] - region[0], region[4] - region[1], region[5] - region[2],
                                 cq.Vector(*region[:3])) if region else None
        for s, c in items:
            if box_r is not None:
                s = s.intersect(box_r)
                if s.Volume() < 1e-3:
                    continue
            t = tess(s)
            tris.append(t)
            cols.append(np.tile(c, (len(t), 1)))
        return np.concatenate(tris), np.concatenate(cols)

    fig = plt.figure(figsize=(16, 10.5))
    fig.suptitle("Speedrun battery tray (MJF PA12) for the LiPo Absima GreenHorn 3S 5000 (hardcase), on H11, H12, H22 and H23",
                 fontsize=13, y=0.995)
    ax = fig.add_axes([0.01, 0.5, 0.42, 0.38])
    t, c = mesh([(own[0][2], col["battery_tray"])])
    draw_mesh(ax, t, iso_basis(-130, 35), tri_colors=c, depth_cue=0.2)
    ax.set_title("Tray alone (from the front right): floor with windows, end stops with the blind holes M3,\n"
                 "side walls, slots 24 x 4.5 and channels 24 x 2.5 under the floor for the 2 straps", fontsize=10, loc="left")
    ax.set_aspect("equal")
    ax.axis("off")
    ax = fig.add_axes([0.45, 0.42, 0.54, 0.46])
    region = (-75, 40, -1, 40, 262, 50)
    items = [(s, tuple(cc)) for nm, s, cc in asm] + [(s, col[k]) for _, k, s in own]
    t, c = mesh(items, region)
    draw_mesh(ax, t, iso_basis(-160, 16), tri_colors=c, depth_cue=0.25)
    ax.set_title("In the car (from the left): battery beside the top brace, behind the steering and beside the drive line;\n"
                 "straps over the battery, through the slots and under the floor", fontsize=10, loc="left")
    ax.set_aspect("equal")
    ax.axis("off")
    ax = fig.add_axes([0.03, 0.05, 0.6, 0.36])
    y = g["ys"][0]
    cut = cq.Solid.makeBox(140, 0.6, 60, cq.Vector(-100, y - 0.3, -1))
    front = (np.array([0, 1.0, 0]), np.array([-1.0, 0, 0]), np.array([0, 0, 1.0]))
    items = [(s.intersect(cut), tuple(cc)) for nm, s, cc in asm if nm.startswith(("chassis_plate", "speedrun_top_brace", "centre_driveshaft"))]
    items += [(s.intersect(cut), col[k]) for _, k, s in own]
    t, c = mesh([q for q in items if q[0].Volume() > 1e-4])
    draw_mesh(ax, t, front, tri_colors=c, depth_cue=0.0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"Section across the car at the rear strap (y = {y:.1f}), seen from the rear: battery top {g['zf'] + g['H']:.1f} above the "
                 f"bottom face of the chassis plate, beside the top brace (lower face 34.6)", fontsize=10, loc="left")
    notes = [f"Battery {g['L']:g} x {g['W']:g} x {g['H']:g} (spec), x = {g['x_out']:.1f} to {g['x_in']:.1f}, y = {g['ym'] - g['L'] / 2:.1f} to "
             f"{g['ym'] + g['L'] / 2:.1f}; 0.5 to the walls and the end stops.",
             f"Floor {p['floor_t']:g} on the chassis plate, end stops {p['stop_h']:g} and side walls {p['wall'][1]:g} high; countersunk "
             f"screws M3x6 from below into blind holes Ø{p['screw_hole'][0]:g} x {p['screw_hole'][1]:g} (4.0 of thread).",
             f"Straps 20 mm at y = {g['ys'][0]:.1f} and {g['ys'][1]:.1f}: slots 24 x 4.5 with chamfers, channels 24 x 2.5 under the floor "
             "(lay the straps into the channels before the tray is screwed on, or push them through).",
             "Checks: no overlap with the parts of the assembly; left steering turned over the full angle of the bellcranks: no contact; "
             "clearance to the top brace approx. 3 (battery and straps)."]
    fig.text(0.65, 0.36, "\n\n".join(notes), fontsize=9, va="top", wrap=True)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Generate the speedrun battery tray.")
    parser.add_argument("--no-check", action="store_true")
    args = parser.parse_args()
    p = load_params(PARAMS)
    own = car_parts_in_plate(p)
    tray = own[0][2]
    g = layout(p)
    print(f"tray: valid {tray.isValid()}, volume {tray.Volume() / 1000:.2f} cm3 ({tray.Volume() / 1000 * 1.01:.0f} g in PA12), "
          f"bounding box {[round(v, 2) for v in (tray.BoundingBox().xmin, tray.BoundingBox().xmax, tray.BoundingBox().ymin, tray.BoundingBox().ymax, tray.BoundingBox().zmin, tray.BoundingBox().zmax)]}")
    print("edge treatment:", getattr(tray_solid, "edges", None))
    print(f"battery x {g['x_out']:.2f}..{g['x_in']:.2f}, y {g['ym'] - g['L'] / 2:.2f}..{g['ym'] + g['L'] / 2:.2f}, "
          f"z {g['zf']:.2f}..{g['zf'] + g['H']:.2f}; straps at y = {g['ys'][0]:.2f} and {g['ys'][1]:.2f}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    cq.exporters.export(cq.Workplane().add(tray), f"{OUT}.step")
    cq.exporters.export(cq.Workplane().add(tray), f"{OUT}.stl", tolerance=0.01, angularTolerance=0.1)
    print(f"wrote {OUT}.step and .stl")
    if not args.no_check:
        check(own)
    drawing(own)
    print(f"wrote {DRAWING}")


if __name__ == "__main__":
    main()
