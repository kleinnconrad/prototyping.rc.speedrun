"""Assembly of the speedrun chassis: chassis plate, bulkheads, top brace and shock towers.

Parts:
* speedrun chassis plate (wide) with the longer motor window
* lower and upper bulkhead at End B (centre of H03 to H06) and at End A (centre of H28 to H31,
  rotated by 180 degrees); the pinions point to the middle of the car
* speedrun top brace on both upper bulkheads (end with the obround at End B)
* speedrun shock towers on the upper bulkheads: front tower at End A (assumed to be the front),
  rear tower at End B
* stock pivot blocks of the wishbones (not part of the speedrun design, modelled for the
  completeness of the build, not in the mass total): long block on H01/H02, short blocks on
  H07/H08, H26/H27 and H32/H33
* stock centre driveshaft with the fixed metal pins (not part of the speedrun design, modelled for
  the completeness of the build, not in the mass total)
* stock cup joints, rear pinion shaft with the spur gear and the bearing, motor mount with its cap
  and diff outdrives (not part of the speedrun design, not in the mass total)
* stock lower wishbones (front arms at End A, rear arms at End B) with their inner hinge pins on
  the pivot blocks (not part of the speedrun design, not in the mass total)

Outputs:
* cad/assembly/speedrun_chassis_T410R.step: assembly (STEP AP214, one solid per part)
* photos/cad_speedrun_chassis_assembly.png: 3D view, side view, top view, close-ups of both ends and of the drive line at End B

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
from generate_top_brace_speedrun import BULKHEAD_Y, GEOM as BRACE_GEOM, brace_offset, brace_solid  # noqa: E402

PLATE_STEP = "cad/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_T410R_speedrun_wide_motor10.step"
LOWER = "cad/bulkhead/bulkhead_lower_parameters.json"
UPPER = "cad/bulkhead/bulkhead_upper_parameters.json"
OUT_STEP = "cad/assembly/speedrun_chassis_T410R.step"
OUT_PNG = "photos/cad_speedrun_chassis_assembly.png"
COLORS = {"plate": (0.26, 0.27, 0.29), "lower": (0.45, 0.5, 0.56), "upper": (0.8, 0.56, 0.3),
          "brace": (0.55, 0.62, 0.72), "tower_front": (0.2, 0.21, 0.23), "tower_rear": (0.2, 0.21, 0.23),
          "pivot": (0.1, 0.1, 0.11), "shaft": (0.72, 0.2, 0.16), "cup": (0.72, 0.74, 0.77),
          "drive": (0.45, 0.47, 0.5), "mount": (0.6, 0.63, 0.68), "arm": (0.4, 0.34, 0.52),
          "diff": (0.16, 0.16, 0.18)}
PICTURE_ONLY = set()                       # keys of parts shown in the picture only (not in the STEP file)
# part key: (label, material options with density in g/cm3)
MATERIALS = {"plate": ("Speedrun chassis plate (wide, longer motor window)", {"6082": 2.70, "carbon": 1.6}),
             "lower": ("Lower bulkhead (2 pieces)", {"7075": 2.81}),
             "upper": ("Upper bulkhead (2 pieces)", {"7075": 2.81}),
             "brace": ("Speedrun top brace", {"carbon": 1.6, "7075": 2.81}),
             "tower_front": ("Speedrun front shock tower", {"carbon": 1.6, "7075": 2.81}),
             "tower_rear": ("Speedrun rear shock tower", {"carbon": 1.6, "7075": 2.81}),
             "pivot": ("Stock pivot blocks (4 pieces)", {}),     # no mass
             "shaft": ("Stock centre driveshaft with fixed pins", {}),
             "cup": ("Stock cup joints, diff outdrives, hinge pins", {}),
             "drive": ("Stock pinion shafts, pinions, spur gear, bearings", {}),
             "mount": ("Stock motor mount with cap", {}),
             "arm": ("Stock wishbones (4 pieces)", {}),
             "diff": ("Stock differential case and spool (ring gear grey)", {})}


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
    # stock pivot blocks of the wishbones on the holes of the chassis plate (not part of the speedrun
    # design, modelled for the completeness of the build)
    for name, _, s, _ in blocks_in_plate():
        parts.append((f"stock pivot block {name}", "pivot", s))
    # stock centre driveshaft with the fixed metal pins, cup joints, rear drive line, motor mount with
    # cap and diff outdrives (not part of the speedrun design)
    for name, kind, s in driveshaft_in_plate():
        parts.append((f"stock {name}" if kind == "shaft" else name, kind, s))
    # stock lower wishbones with the inner hinge pins on the pivot blocks (not part of the speedrun design)
    for name, kind, s in arms_in_plate():
        parts.append((name, "arm" if kind == "arm" else "cup", s))
    return parts


def tess(shape, tol=0.05):
    verts, idx = shape.tessellate(tol, 0.2)
    v = np.array([[p.x, p.y, p.z] for p in verts])
    return v[np.array(idx)]


def image(parts, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from mesh_views import subdivide, draw_mesh, iso_basis
    tris, cols = [], []
    for _, key, s in parts:
        t = subdivide(tess(s), 6.0 if key == "plate" else 2.0)
        tris.append(t)
        cols.append(np.tile(COLORS[key], (len(t), 1)))
    tris, cols = np.concatenate(tris), np.concatenate(cols)
    fig = plt.figure(figsize=(16, 15))
    fig.suptitle("Speedrun chassis of the Carten T410R: chassis plate, bulkheads, top brace and shock towers", fontsize=13, y=0.987)
    top = 1 / 3                                             # overview in the upper 2/3, close-ups below

    def upper(rect):
        return [rect[0], top + rect[1] * (1 - top), rect[2], rect[3] * (1 - top)]
    views = [(upper([0.0, 0.3, 0.68, 0.64]), iso_basis(-35, 28), ""),
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
    closeups = (("End A (front): front shock tower on the bulkheads,\nview from the outer end",
                 (-62, BULKHEAD_Y["front"] - 32, -5, 124, 64, 90), (), 55, 22),
                ("End B (rear): rear shock tower on the bulkheads,\nview from the outer end",
                 (-62, BULKHEAD_Y["rear"] - 32, -5, 124, 64, 90), (), -125, 22),
                ("End B: stock drive line (spur gear, motor mount with cap, cup joint),\n"
                 "view from the middle of the car, top brace and shock tower not shown",
                 (-38, -8, -5, 105, 110, 65), ("brace", "tower_front", "tower_rear"), 125, 28))
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
    # picture in picture: section through the differential at End B (stock part) with the pinion
    yd = BULKHEAD_Y["rear"] + load_params(LOWER)["diff_axis_y"]
    keep = cq.Solid.makeBox(80, 40, 80, cq.Vector(-40, yd - 40, -20))        # half on the side away from the pinion
    tris_d, cols_d = [], []
    inset_cols = (("bearing", (0.45, 0.65, 0.85)), ("shim", (0.85, 0.8, 0.55)), ("pin", (0.8, 0.8, 0.82)),
                  ("outdrive", (0.3, 0.3, 0.33)), ("side gear", (0.62, 0.63, 0.66)), ("spider gear", (0.62, 0.63, 0.66)),
                  ("ring gear", (0.66, 0.6, 0.5)), ("case", (0.17, 0.17, 0.19)))      # first match counts
    for name, key, s in parts:
        if not ("End B" in name and (name.startswith("diff") or name.startswith("ring gear"))):
            continue
        s = s.intersect(keep)
        if s.Volume() < 1e-6:
            continue
        t = subdivide(tess(s, 0.015), 0.7)
        tris_d.append(t)
        col = next((c for w, c in inset_cols if w in name), (0.62, 0.63, 0.66))   # inner gears: steel
        cols_d.append(np.tile(col, (len(t), 1)))
    ax = fig.add_axes([0.4, 0.53, 0.255, 0.175])
    lo, hi = draw_mesh(ax, np.concatenate(tris_d), iso_basis(75, 20), tri_colors=np.concatenate(cols_d), depth_cue=0.2)
    ax.set_xlim(lo[0] - 2, hi[0] + 2)
    ax.set_ylim(lo[1] - 2, hi[1] + 9)
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_facecolor("white")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("#6b7078")
        sp.set_linewidth(0.8)
    ax.text(0.02, 0.97, "Differential End B in section (stock part): ring gear 42T,\nside gears 14T, spider gears 9T on the "
            "cross pin,\nshims (yellow), bearings (blue), outdrives. End A: spool", transform=ax.transAxes, va="top",
            fontsize=7.5)
    handles = [Patch(color=np.clip(np.asarray(COLORS[k]) + 0.08, 0, 1), label=MATERIALS[k][0]) for k in COLORS]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.01, top + 0.95 * (1 - top)), fontsize=9,
               frameon=False, ncol=2, columnspacing=1.5)
    fig.text(0.013, top + 0.95 * (1 - top) - 0.122, "Stock parts: not part of the speedrun design, not verified, work in progress, "
             "not in the mass total", fontsize=8.5, color="#4a4f57")
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
            note = "simple bodies, picture only" if key in PICTURE_ONLY else "stock parts"
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
    for (na, _, a), (nb, _, b) in itertools.combinations(parts, 2):
        v = a.intersect(b).Volume()
        worst = max(worst, v)
        if v > 1e-4:
            print(f"  interference {na} / {nb}: {v:.4f} mm3")
    print(f"  interference check of all {len(parts)} parts: largest overlap {worst:.4f} mm3")


if __name__ == "__main__":
    main()
