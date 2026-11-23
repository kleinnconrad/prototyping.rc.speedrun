"""Assembly of the speedrun chassis: chassis plate, bulkheads, top brace, shock towers, front splitter,
drive line, wishbones and running gear.

Parts (the parts besides the speedrun chassis are the owner's own design, partly based on the
T410R; they are not in the mass total):
* speedrun chassis plate (wide) with the longer motor window
* lower and upper bulkhead at End B (centre of H03 to H06) and at End A (centre of H28 to H31,
  rotated by 180 degrees); the pinions point to the middle of the car
* speedrun top brace on both upper bulkheads (end with the obround at End B)
* speedrun shock towers on the upper bulkheads: front tower at End A (assumed to be the front),
  rear tower at End B
* speedrun battery tray on H11, H12, H22 and H23 (scripts/cad/generate_battery_tray.py) with the
  battery Absima GreenHorn 3S 5000 (hardcase) and the 2 velcro straps (battery and straps: not in the
  mass total and not in the picture, owner: only the battery tray is part of the chassis; they stay in the
  STEP file for the checks)
* speedrun front splitter at End A (scripts/cad/generate_front_splitter.py): one part, the body
  post mount enlarged to the splitter, on H34 to H36; the body posts (stock parts) are not in the
  mass total
* pivot blocks of the wishbones: long block on H01/H02, short blocks on H07/H08, H26/H27 and
  H32/H33
* centre driveshaft with the fixed metal pins, cup joints, front and rear pinion shaft with the
  pinions, the spur gear and the bearings, motor mount with its cap, differential, spool and diff
  outdrives
* camber links (turnbuckles M3x37 with rod ends) on the ball studs of the shock towers
* lower wishbones (front arms at End A, rear arms at End B) with their inner hinge pins on the
  pivot blocks
* running gear (scripts/cad/generate_running_gear.py): C-hubs with caster, steering knuckles, rear
  hub carriers, axles, hex hubs, CVD drive shafts, steering, servo with the servo mount, dampers,
  sway bars

Outputs:
* cad/assembly/speedrun_chassis_T410R.step: assembly (STEP AP214, one solid per part)
* photos/cad_speedrun_chassis_assembly.png: 3D view, side view, top view, close-ups of both ends and of the drive line at End B
  (picture only: without the battery and the straps, with the visible screws, servo shaft lower; see picture_parts)

The script checks all pairs of parts for interference and lists the volume and the mass of
each part.

Usage (from the root directory of the repository, after the scripts of the bulkheads, the
speedrun top brace, the shock towers, the pivot blocks, the driveshaft and the wishbones):
    python scripts/cad/generate_speedrun_assembly.py

Requires the packages cadquery and matplotlib.
"""
import itertools
import json
import os
import sys

import numpy as np
import cadquery as cq
from cadquery.occ_impl.exporters.assembly import exportAssembly

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_bulkhead_lower import bulkhead_lower, load_params  # noqa: E402
from generate_bulkhead_upper import bulkhead_upper  # noqa: E402
from generate_driveshaft import parts_in_plate as driveshaft_in_plate  # noqa: E402
from generate_pivot_blocks import blocks_in_plate  # noqa: E402
from generate_shock_towers import tower_in_bulkhead  # noqa: E402
from generate_wishbones import arms_in_plate  # noqa: E402
from generate_camber_links import links_in_plate  # noqa: E402
from palette import PARTS  # noqa: E402
from generate_running_gear import build as running_gear  # noqa: E402
from generate_front_splitter import car_parts_in_plate as front_splitter_in_plate  # noqa: E402
from generate_battery_tray import car_parts_in_plate as battery_tray_in_plate  # noqa: E402
from generate_top_brace_speedrun import BULKHEAD_Y, GEOM as BRACE_GEOM, brace_offset, brace_solid  # noqa: E402

PLATE_STEP = "cad/speedrun_parts/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_T410R_speedrun_wide_motor10.step"
LOWER = "cad/speedrun_parts/bulkhead/bulkhead_lower_parameters.json"
UPPER = "cad/speedrun_parts/bulkhead/bulkhead_upper_parameters.json"
OUT_STEP = "cad/assembly/speedrun_chassis_T410R.step"
OUT_PNG = "photos/cad_speedrun_chassis_assembly.png"
COLORS = dict(PARTS)                       # colour scheme of the CAD pictures: blue and grey (palette.py)
COLORS.update(screw_brace=PARTS["screw"], screw_tower=PARTS["screw"])   # screws hidden with the top brace / the towers
PICTURE_ONLY = set()                       # keys of parts shown in the picture only (not in the STEP file)
NOT_IN_PICTURE = {"battery", "strap"}      # in the STEP file (checks), not in the picture: not part of the chassis (owner)
# servo output shaft in the picture (owner, 2026-11-23: in reality nearer the bottom of the servo): 7.0 lower than in the
# model (6.0 above the lower face of the case, 13.0 below its top face; 10 would put the clamp screw of the horn into
# the chassis plate). The model (STEP file, steering geometry) keeps the caliper value S3 of servo_position
PICTURE_SERVO_DZ = -7.0
# part key: (label, material options with density in g/cm3)
MATERIALS = {"plate": ("Speedrun chassis plate (wide, longer motor window)", {"6082": 2.70, "carbon": 1.6}),
             "lower": ("Lower bulkhead (2 pieces)", {"PA12": 1.01, "7075": 2.81}),
             "upper": ("Upper bulkhead (2 pieces)", {"PA12": 1.01, "7075": 2.81}),
             "brace": ("Speedrun top brace", {"carbon": 1.6, "7075": 2.81}),
             "tower_front": ("Speedrun front shock tower", {"carbon": 1.6, "7075": 2.81}),
             "tower_rear": ("Speedrun rear shock tower", {"carbon": 1.6, "7075": 2.81}),
             "onepiece": ("Speedrun front splitter (one piece)", {"PA12": 1.01, "PETG": 1.27}),
             "battery_tray": ("Speedrun battery tray", {"PA12": 1.01}),
             "battery": ("Battery Absima GreenHorn 3S 5000 (hardcase, 370 g)", {}),
             "strap": ("Velcro straps 20 mm", {}),
             "pivot": ("Pivot blocks (4 pieces)", {}),     # no mass
             "shaft": ("Centre driveshaft with fixed pins", {}),
             "cup": ("Cup joints, outdrives, inner hinge pins", {}),
             "drive": ("Pinion shafts, pinions, spur gear, bearings", {}),
             "mount": ("Motor mount with cap", {}),
             "arm": ("Wishbones (4 pieces)", {}),
             "diff": ("Differential case and spool (ring gear grey)", {}),
             "rodend": ("Rod ends", {}),
             "link": ("Turnbuckles, ball studs and nuts", {}),
             "upright": ("C-hubs (caster 10 deg), knuckles, hub carriers", {}),
             "axle": ("Axles, hex hubs, pins, wheel bearings", {}),
             "cvd": ("CVD drive shafts", {}),
             "steer": ("Steering, servo mount, sway bar holders", {}),
             "damper": ("Dampers (standard 1:10 on-road)", {}),
             "spring": ("Damper springs", {}),
             "servo": ("Servo (low profile)", {}),
             "swaybar": ("Sway bars 1.4", {}),
             "bodypost": ("Front body posts (stock)", {})}


def build():
    """Parts in chassis plate coordinates: list of (name, key, solid)."""
    lp, up = load_params(LOWER), load_params(UPPER)
    plate_t = 2.0
    plate = cq.importers.importStep(PLATE_STEP).val()
    lower, upper = bulkhead_lower(lp).val(), bulkhead_upper(lp, up).val()
    with open(BRACE_GEOM, encoding="utf-8") as f:
        brace_g = json.load(f)
    brace = brace_solid(brace_g)
    parts = [("chassis plate", "plate", plate)]
    for end, yb in (("End B", BULKHEAD_Y["rear"]), ("End A", BULKHEAD_Y["front"])):
        for key, solid in (("lower", lower), ("upper", upper)):
            s = solid.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180) if end == "End A" else solid
            parts.append((f"{key} bulkhead {end}", key, s.translate(cq.Vector(0, yb, plate_t))))
    c = sum(brace_offset(brace_g, up["deck_screw_y"])) / 2
    zb = plate_t + lp["axis_z"] + up["deck_h"]
    parts.append(("speedrun top brace", "brace",
                  brace.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180).translate(cq.Vector(0, c, zb))))
    # shock towers on the upper bulkheads, placed as these bulkheads: front at End A (assumed front,
    # rotated by 180 degrees), rear at End B
    front = tower_in_bulkhead(lp, up, "front").rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180)
    parts.append(("speedrun front shock tower End A", "tower_front",
                  front.translate(cq.Vector(0, BULKHEAD_Y["front"], plate_t))))
    parts.append(("speedrun rear shock tower End B", "tower_rear",
                  tower_in_bulkhead(lp, up, "rear").translate(cq.Vector(0, BULKHEAD_Y["rear"], plate_t))))
    # pivot blocks of the wishbones on the holes of the chassis plate
    for name, _, s, _ in blocks_in_plate():
        parts.append((f"pivot block {name}", "pivot", s))
    # centre driveshaft with the fixed metal pins, cup joints, drive lines, motor mount with cap,
    # differential, spool and diff outdrives
    for name, kind, s in driveshaft_in_plate():
        parts.append((name, kind, s))
    # lower wishbones with the inner hinge pins on the pivot blocks
    for name, kind, s in arms_in_plate():
        parts.append((name, "arm" if kind == "arm" else "cup", s))
    # camber links: turnbuckles with rod ends on the ball studs of the shock towers
    parts += links_in_plate()
    # running gear: wheel suspension, axles, CVD drive shafts, steering, servo, dampers, sway bars
    rg, _ = running_gear()
    parts += [(f"running gear {name}", kind, s) for name, kind, s in rg]
    # speedrun front splitter (End A, one part) with the body posts
    parts += front_splitter_in_plate()
    # speedrun battery tray with the battery and the velcro straps
    parts += battery_tray_in_plate()
    return parts


def tess(shape, tol=0.05):
    verts, idx = shape.tessellate(tol, 0.2)
    v = np.array([[p.x, p.y, p.z] for p in verts])
    return v[np.array(idx)]


def screw(kind, length, head, tip_dir):
    """Simplified screw with a hexagon socket (picture only). kind: "button" (ISO 7380), "socket" (ISO 4762) or "grub"
    (ISO 4026); head: centre of the bearing face under the head (grub screw: centre of the end with the socket);
    tip_dir: direction from the head to the tip; length: length under the head."""
    dk, k, s, t = {"button": (5.7, 1.65, 2.0, 1.0), "socket": (5.5, 3.0, 2.5, 1.5), "grub": (3.0, 0.0, 1.5, 1.2)}[kind]
    sol = cq.Solid.makeCylinder(1.45 if kind != "grub" else 1.5, length, cq.Vector(0, 0, -length))
    if kind == "button":
        sol = sol.fuse(cq.Workplane().circle(dk / 2).extrude(k).edges(">Z").fillet(0.8).val())
    elif kind == "socket":
        sol = sol.fuse(cq.Workplane().circle(dk / 2).extrude(k).edges(">Z").chamfer(0.3).val())
    sol = sol.cut(cq.Workplane().polygon(6, s / np.cos(np.radians(30))).extrude(t).val().translate(cq.Vector(0, 0, k - t)))
    a, b = np.array([0, 0, -1.0]), np.asarray(tip_dir, float) / np.linalg.norm(tip_dir)
    axis = np.cross(a, b)
    if np.linalg.norm(axis) > 1e-9:
        sol = sol.rotate(cq.Vector(0, 0, 0), cq.Vector(*axis), float(np.degrees(np.arccos(np.clip(a @ b, -1, 1)))))
    elif a @ b < 0:
        sol = sol.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 180.0)
    return sol.translate(cq.Vector(*head))


def picture_parts(parts):
    """Parts of the picture: without the battery and the straps (owner: only the battery tray is part of the chassis),
    the servo output shaft with the horn and the servo link PICTURE_SERVO_DZ lower, and the screws that can be seen
    from above and from the ends (simplified, hex socket; not in the STEP file): top brace on the upper bulkheads
    (button head M3x8), upper bulkheads on the lower bulkheads (button head M3x8 on the outer side, M3x10 in the
    counterbores on the pinion side), shock towers on the upper bulkheads (button head M3x8), cap of the motor mount
    (socket head M3x18 through the top brace, set screw M3x3 in the notch), servo mount (button head M3x6: top plate on
    the posts, servo ears with washers on the posts) and the clamp screw of the servo horn (socket head M3x8)."""
    import technical_drawing as TD
    import generate_running_gear as G
    p = G.load_params(G.PARAMS)
    out = [q for q in parts if q[1] not in NOT_IN_PICTURE]
    by = {n: s for n, _, s in out}
    holes = lambda n: TD.find_holes(by[n], 6.5)                                                    # noqa: E731
    ends = lambda h: (h["p"] + h["d"] * h["t0"], h["p"] + h["d"] * h["t1"])                       # noqa: E731
    zb_top = by["speedrun top brace"].BoundingBox().zmax                                          # top face of the brace
    new = []
    for end in ("A", "B"):
        tower = by["speedrun front shock tower End A" if end == "A" else "speedrun rear shock tower End B"]
        tb = tower.BoundingBox()
        for h in holes(f"upper bulkhead End {end}"):
            a, b = ends(h)
            if abs(h["d"][2]) > 0.99 and h["dia"] > 3.0:                                          # to the lower bulkhead
                cb = [e for e in h.get("extras", []) if e["d"] > 6.0]
                z = h["main"]["t1"] if cb else b[2]
                new.append(("screw", screw("button", 10.0 if cb else 8.0, (a[0], a[1], z), (0, 0, -1))))
            elif abs(h["d"][2]) > 0.99:                                                           # top brace screws
                new.append(("screw_brace", screw("button", 8.0, (a[0], a[1], zb_top), (0, 0, -1))))
            elif abs(h["d"][1]) > 0.99:                                                           # shock tower screws
                out_y = tb.ymax if end == "A" else tb.ymin
                new.append(("screw_tower", screw("button", 8.0, (a[0], out_y, a[2]), (0, -1 if end == "A" else 1, 0))))
    for h in holes("cap of the motor mount"):
        a, b = ends(h)
        if h["dia"] > 3.0:
            new.append(("screw_brace", screw("socket", 18.0, (a[0], a[1], zb_top), (0, 0, -1))))  # through the top brace
        else:
            new.append(("screw", screw("grub", 3.0, b, (0, 0, -1))))                              # set screw in the notch
    zp = by["running gear servo mount top plate"].BoundingBox().zmax
    ear_t = p["servo"][4]
    for n in ("running gear servo mount fixed post", "running gear servo mount floating post"):
        for h in holes(n):
            a, b = ends(h)
            if abs(h["d"][2]) > 0.99 and b[2] > zp - 3.0:                                         # top plate
                new.append(("screw", screw("button", 6.0, (a[0], a[1], zp), (0, 0, -1))))
            elif abs(h["d"][1]) > 0.99:                                                           # servo ears, washers
                y_e = b[1] + ear_t
                new.append(("screw", cq.Solid.makeCylinder(3.5, 0.5, cq.Vector(b[0], y_e, b[2]), cq.Vector(0, 1, 0)).cut(
                    cq.Solid.makeCylinder(1.6, 0.5, cq.Vector(b[0], y_e, b[2]), cq.Vector(0, 1, 0)))))
                new.append(("screw", screw("button", 6.0, (b[0], y_e + 0.5, b[2]), (0, -1, 0))))
    # servo: output shaft, horn, ball stud and servo link lower (picture only)
    dz = PICTURE_SERVO_DZ
    hl, _, _, hf = p["servo_horn"]
    hb = np.asarray(G.steering.info["horn"], float)
    xs, ycf, zs = hb[0], hb[1] - p["ball_offset"] - hf, hb[2] - hl                               # shaft, case front face
    mv = lambda s: s.translate(cq.Vector(0, 0, dz))                                               # noqa: E731
    horn = mv(by["running gear servo horn (aluminium clamp)"])
    for h in TD.find_holes(horn, 6.5):
        a, b = ends(h)
        if abs(h["d"][0]) > 0.99:
            new.append(("screw", screw("socket", 8.0, b, (-1, 0, 0))))                            # clamp screw
    rods, tbk, _ = G.link(hb + (0, 0, dz), np.array([0, -1.0, 0]), G.steering.info["bridge ball"], np.array([0, 1.0, 0]),
                          9.0, G.load_params(G.CL.PARAMS))
    spline = lambda z: cq.Solid.makeCylinder(2.95, 3.5, cq.Vector(xs, ycf - 0.1, z), cq.Vector(0, 1, 0))  # noqa: E731
    repl = {"running gear servo": by["running gear servo"].cut(spline(zs).translate(cq.Vector(0, 0.1, 0))).fuse(spline(zs + dz)),
            "running gear servo horn (aluminium clamp)": horn,
            "running gear servo horn ball stud": mv(by["running gear servo horn ball stud"]),
            "running gear servo link rod ends": rods, "running gear servo link turnbuckle": tbk}
    out = [(n, k, repl.get(n, s)) for n, k, s in out]
    return out + [(f"screw {i}", k, s) for i, (k, s) in enumerate(new)]


def image(parts, path):
    parts = picture_parts(parts)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mesh_views import subdivide, draw_mesh, iso_basis
    tris, cols = [], []
    for _, key, s in parts:
        t = subdivide(tess(s), 6.0 if key == "plate" else 2.0)
        tris.append(t)
        cols.append(np.tile(COLORS[key], (len(t), 1)))
    tris, cols = np.concatenate(tris), np.concatenate(cols)
    fig = plt.figure(figsize=(16, 15))
    fig.suptitle("Speedrun Chassis", fontsize=13, y=0.987)                                    # owner
    top = 1 / 3                                             # overview in the upper 2/3, close-ups below

    def upper(rect):
        return [rect[0], top + rect[1] * (1 - top), rect[2], rect[3] * (1 - top)]
    views = [(upper([0.0, 0.27, 0.68, 0.68]), iso_basis(-35, 28), ""),                  # no legend (owner)
             (upper([0.0, 0.0, 0.68, 0.3]), ((-1, 0, 0), (0, 1, 0), (0, 0, 1)), "Side view"),
             (upper([0.66, 0.02, 0.34, 0.88]), ((0, 0, -1), (1, 0, 0), (0, 1, 0)), "Top view")]
    for rect, view, title in views:
        ax = fig.add_axes(rect)
        if isinstance(view[0], tuple):
            d, r, u = (np.asarray(v, float) for v in view)
            view = (d, r, u)
        lo, hi = draw_mesh(ax, tris, view, tri_colors=cols, depth_cue=0.3)
        ax.set_xlim(lo[0] - 2, hi[0] + 2)
        ax.set_ylim(lo[1] - 2, hi[1] + 2)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=10, loc="left")
        if title == "Top view":
            ax.text(0, hi[1] + 1, "End A", ha="center", va="bottom", fontsize=9)
            ax.text(0, lo[1] - 1, "End B (motor, spur gear)", ha="center", va="top", fontsize=9)
            ax.set_ylim(lo[1] - 9, hi[1] + 9)
        elif title == "Side view":
            ax.text(lo[0], hi[1] + 1, "End B", ha="left", va="bottom", fontsize=9)
            ax.text(hi[0], hi[1] + 1, "End A", ha="right", va="bottom", fontsize=9)
            ax.set_ylim(lo[1] - 2, hi[1] + 8)
    # close-ups: both ends seen from the outer end (bulkheads, shock tower, end of the top brace) and the drive
    # line at End B seen from the middle of the car (top brace and shock towers left out, they hide the spur gear)
    closeups = (("End A (front): shock tower, C-hubs with knuckles, dampers,\nsway bar, view from the outer end "
                 "(front splitter not shown)",
                 (-92, BULKHEAD_Y["front"] - 32, -5, 184, 64, 90), ("onepiece", "bodypost"), 55,
                 22),
                ("End B (rear): shock tower, hub carriers, dampers, sway bar,\nview from the outer end",
                 (-92, BULKHEAD_Y["rear"] - 32, -5, 184, 64, 90), (), -125, 22),
                ("End B: drive line (spur gear, motor mount with cap, cup joint),\n"
                 "view from the middle of the car, top brace and shock tower not shown",
                 (-38, -8, -5, 105, 110, 65), ("brace", "tower_front", "tower_rear", "screw_brace", "screw_tower"), 125, 28))
    for k, (title, (x0, y0, z0, dx, dy, dz), hidden, azim, elev) in enumerate(closeups):
        region = cq.Solid.makeBox(dx, dy, dz, cq.Vector(x0, y0, z0))
        tris_e, cols_e = [], []
        for _, key, s in parts:
            bb = s.BoundingBox()
            if key in hidden or bb.ymin > y0 + dy or bb.ymax < y0:
                continue
            cut = s.intersect(region)
            if cut.Volume() < 1e-3:
                continue
            t = subdivide(tess(cut, 0.02), 4.0 if key == "plate" else 1.2)
            tris_e.append(t)
            cols_e.append(np.tile(COLORS[key], (len(t), 1)))
        ax = fig.add_axes([k / 3, 0.01, 1 / 3, 0.3])
        lo, hi = draw_mesh(ax, np.concatenate(tris_e), iso_basis(azim, elev), tri_colors=np.concatenate(cols_e),
                           depth_cue=0.3)
        ax.set_xlim(lo[0] - 2, hi[0] + 2)
        ax.set_ylim(lo[1] - 2, hi[1] + 2)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=10, loc="left")
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    os.makedirs(os.path.dirname(OUT_STEP), exist_ok=True)
    parts = build()
    assy = cq.Assembly(name="speedrun_chassis_T410R")
    for name, key, s in parts:
        if key not in PICTURE_ONLY:
            assy.add(s, name=name.replace(" ", "_"), color=cq.Color(*COLORS[key]))
    exportAssembly(assy, OUT_STEP)
    image(parts, OUT_PNG)
    print(f"Wrote {OUT_STEP} and {OUT_PNG}")
    total = {}
    seen = set()
    for name, key, s in parts:
        if key in seen:
            continue
        seen.add(key)
        n = sum(1 for p in parts if p[1] == key)
        label, mats = MATERIALS[key]
        if not mats:
            note = "simple bodies, picture only" if key in PICTURE_ONLY else "no material given"
            print(f"  {label}: {n} piece{'s' if n > 1 else ''}, {note}, not in the mass total")
            continue
        vol = s.Volume() / 1000
        masses = {m: vol * rho * n for m, rho in mats.items()}
        for m, v in masses.items():
            total.setdefault(key, {})[m] = v
        print(f"  {label}: {n} x {vol:.2f} cm3, " + ", ".join(f"{m} {v:.0f} g" for m, v in masses.items()))
    first = {k: list(v.values())[0] for k, v in total.items()}
    print(f"  total with the first material of each part: {sum(first.values()):.0f} g")
    worst = 0.0
    boxes = [s.BoundingBox() for _, _, s in parts]
    for (ia, (na, _, a)), (ib, (nb, _, b)) in itertools.combinations(enumerate(parts), 2):
        ba, bb = boxes[ia], boxes[ib]
        if ba.xmin > bb.xmax or bb.xmin > ba.xmax or ba.ymin > bb.ymax or bb.ymin > ba.ymax or ba.zmin > bb.zmax \
                or bb.zmin > ba.zmax:
            continue                                         # bounding boxes apart: no overlap possible
        v = a.intersect(b).Volume()
        worst = max(worst, v)
        if v > 1e-4:
            print(f"  interference {na} / {nb}: {v:.4f} mm3")
    print(f"  interference check of all {len(parts)} parts: largest overlap {worst:.4f} mm3")


if __name__ == "__main__":
    main()
