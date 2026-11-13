"""Assembly of the speedrun chassis: chassis plate, bulkheads, top brace and front shock tower.

Parts:
* speedrun chassis plate (wide) with the longer motor window
* lower and upper bulkhead at End B (centre of H03 to H06) and at End A (centre of H28 to H31,
  rotated by 180 degrees); the pinions point to the middle of the car
* speedrun top brace on both upper bulkheads (end with the obround at End B)
* speedrun front shock tower on the upper bulkhead at End A (End A is assumed to be the front)

Outputs:
* cad/assembly/speedrun_chassis_T410R.step: assembly (STEP AP214, one solid per part)
* photos/cad_speedrun_chassis_assembly.png: 3D view, side view and top view

The script checks all pairs of parts for interference and lists the volume and the mass of
each part.

Usage (from the root directory of the repository, after the scripts of the bulkheads, the
speedrun top brace and the front shock tower):
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
from generate_shock_tower_front import tower_in_bulkhead  # noqa: E402
from generate_top_brace_speedrun import BULKHEAD_Y, GEOM as BRACE_GEOM, brace_offset, brace_solid  # noqa: E402

PLATE_STEP = "cad/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_T410R_speedrun_wide_motor10.step"
LOWER = "cad/bulkhead/bulkhead_lower_parameters.json"
UPPER = "cad/bulkhead/bulkhead_upper_parameters.json"
OUT_STEP = "cad/assembly/speedrun_chassis_T410R.step"
OUT_PNG = "photos/cad_speedrun_chassis_assembly.png"
COLORS = {"plate": (0.26, 0.27, 0.29), "lower": (0.45, 0.5, 0.56), "upper": (0.8, 0.56, 0.3),
          "brace": (0.55, 0.62, 0.72), "tower": (0.2, 0.21, 0.23)}
# part key: (label, material options with density in g/cm3)
MATERIALS = {"plate": ("Speedrun chassis plate (wide, longer motor window)", {"6082": 2.70, "carbon": 1.6}),
             "lower": ("Lower bulkhead (2 pieces)", {"7075": 2.81}),
             "upper": ("Upper bulkhead (2 pieces)", {"7075": 2.81}),
             "brace": ("Speedrun top brace", {"carbon": 1.6, "7075": 2.81}),
             "tower": ("Speedrun front shock tower", {"carbon": 1.6, "7075": 2.81})}


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
    # front shock tower on the upper bulkhead at End A (assumed front), placed as that bulkhead
    tower = tower_in_bulkhead(lp, up).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180)
    parts.append(("speedrun front shock tower End A", "tower",
                  tower.translate(cq.Vector(0, BULKHEAD_Y["front"], plate_t))))
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
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle("Speedrun chassis of the Carten T410R: chassis plate, bulkheads, top brace and front shock tower", fontsize=13, y=0.98)
    views = [([0.0, 0.3, 0.68, 0.64], iso_basis(-35, 28), ""),
             ([0.0, 0.0, 0.68, 0.3], ((-1, 0, 0), (0, 1, 0), (0, 0, 1)), "Side view"),
             ([0.66, 0.02, 0.34, 0.88], ((0, 0, -1), (1, 0, 0), (0, 1, 0)), "Top view")]
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
    handles = [Patch(color=np.clip(np.asarray(COLORS[k]) + 0.08, 0, 1), label=MATERIALS[k][0]) for k in COLORS]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.01, 0.93), fontsize=9, frameon=False)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    os.makedirs(os.path.dirname(OUT_STEP), exist_ok=True)
    parts = build()
    assy = cq.Assembly(name="speedrun_chassis_T410R")
    for name, key, s in parts:
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
