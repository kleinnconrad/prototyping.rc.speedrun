"""Technical drawings of the verified parts (green), the wishbones and the C-hub (the bulkheads: see
generate_bulkhead_technical_drawings.py).

The views and sections are projected from the STEP files with hidden line removal; the holes are read from the STEP
files (cylinders and countersinks along any axis). The scale and the layout follow from the size of each part. The
STEP file is the master geometry: dimensions that are not shown are taken from the model. Parts that are stored in the
coordinates of the chassis plate (C-hub, steering knuckle, front splitter) are drawn in a local frame (see the notes).

Each part gets 2 sheets A3 (landscape, first angle projection):
    sheet 1: views (3D parts: front view, top view, side view, isometric view; flat parts: view from above and an edge
             view), main dimensions, labels of the holes
    sheet 2: sections (if any), hole table, notes

Usage (from the root directory of the repository):
    python scripts/cad/generate_technical_drawings.py [--part KEY]

Outputs: <part>_technical_drawing.pdf and <part>_technical_drawing_sheet_1.png / _sheet_2.png in the directory of
each part, and a readme.md per directory that shows the sheets.

Requires the packages cadquery and matplotlib.
"""
import argparse
import csv
import datetime
import json
import os
import sys
import textwrap

import numpy as np
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import technical_drawing as TD  # noqa: E402
from technical_drawing import A3, View, text, linear, leader, centre_line, centre_mark, view_label  # noqa: E402

SCALES = (5.0, 2.0, 1.0, 0.5)
X_LEFT = 52.0                   # left edge of the views (room for the vertical dimensions)
Y_TOP = 262.0                   # top edge of the upper views (room for the dimensions and the label)


def scale_text(s):
    return f"{s:g}:1" if s >= 1 else f"1:{1 / s:g}"


# ------------------------------------------------------------------ part frames
def running_gear_frames():
    """Frames of the C-hub (origin on the axis of the outer hinge pin in the middle of the lug) and of the steering
    knuckle (kingpin frame: origin in the centre of the outer CVD joint)."""
    import generate_running_gear as G
    from generate_bulkhead_lower import load_params
    p = load_params(G.PARAMS)
    c = G.corners(p, load_params(G.LOWER))["front"]
    R, J = G.kingpin_frame(p, c)
    return {"c_hub": (np.eye(3), np.asarray(c["O"], float), p), "knuckle": (np.asarray(R, float), np.asarray(J, float), p)}


def csv_names(path, z=0.0):
    with open(path, encoding="utf-8") as f:
        return [(r["id"], (float(r["x_mm"]), float(r["y_mm"]), z)) for r in csv.DictReader(f)]


def chassis_names():
    d = json.load(open("cad/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_speedrun_wide_motor10_geometry.json"))
    return [(h["id"], (h["x"], h["y"], 0.0)) for h in d["holes"]]


# ------------------------------------------------------------------ part definitions
GENERAL_CNC = "ISO 2768-mK"
EDGES_BREAK = "break 0.1 to 0.2"


def parts():
    rg = running_gear_frames()
    Rc, Oc, rgp = rg["c_hub"]
    Rk, Jk, _ = rg["knuckle"]
    ca, sa = np.cos(np.radians(rgp["caster"])), np.sin(np.radians(rgp["caster"]))
    kd = np.array([0.0, -sa, ca])                                      # kingpin axis (C-hub frame)
    kn = np.array([0.0, ca, sa])                                       # square to it in the y-z plane
    Jc = np.array([rgp["kingpin_x"] - Oc[0], -rgp["kingpin_y"], rgp["wheel_r"] - rgp["ride_height"][0] - Oc[2]])
    kx = rgp["kingpin_x"] - Oc[0]
    return [
        dict(key="chassis_plate", folder="cad/chassis/chassis_plate_speedrun_wide_motor10",
             step="chassis_plate_T410R_speedrun_wide_motor10.step", stem="chassis_plate_T410R_speedrun_wide_motor10",
             title="Speedrun chassis plate (wide) with longer motor window", number="CP", flat=True, rotate=True,
             material="EN AW-6082-T6, plate 2.0 mm", density=2.70, density_txt="6082", quantity="1", tol=GENERAL_CNC,
             edges="edges broken 0.1 to 0.2", status="ordered as CNC part (6082)", names=chassis_names(), label_names=True,
             end_labels=("End B (rear)", "End A (front)"),
             notes=["Countersinks Ø6.2 x 90 deg on the bottom face for countersunk screws M3 (ISO 10642).",
                    "Outline, windows and holes as in the DXF file chassis_plate_T410R_speedrun_wide_motor10.dxf.",
                    "Hole names as in the geometry data of the plate (H01 to H36)."]),
        dict(key="top_brace", folder="cad/chassis/top_brace_speedrun", step="top_brace_T410R_speedrun.step",
             stem="top_brace_T410R_speedrun", title="Speedrun top brace", number="TB", flat=True, rotate=True,
             material="Carbon plate 2.0 mm or EN AW-7075-T6", density=1.6, density_txt="carbon", quantity="1",
             tol=GENERAL_CNC, edges="chamfers 0.5 x 45 deg (outline), 0.3 (holes)", status="verified",
             names=csv_names("cad/chassis/top_brace_speedrun/top_brace_speedrun_hole_table.csv"), label_names=True,
             end_labels=("End with B01 to B04 (End A)", "End with B07 to B15 (End B)"),
             details=[dict(title="Detail X (end with B01 to B04)", box=(-18.5, 18.5, -1.5, 30.0), scale=2.0),
                      dict(title="Detail Y (end with B07 to B15)", box=(-18.5, 18.5, 198.0, 244.8), scale=2.0)],
             notes=["Laser or waterjet cutting from the DXF file top_brace_T410R_speedrun.dxf; edge chamfers 0.5 x 45 deg "
                    "on both faces of the outline and the obround, 0.3 x 45 deg on the holes (second machining step).",
                    "Hole names as in the hole table of the top brace (B01 to B15; B05 and B06 are closed)."]),
        dict(key="shock_tower_front", folder="cad/shock_tower", step="shock_tower_front_T410R_speedrun.step",
             stem="shock_tower_front_T410R_speedrun", title="Speedrun front shock tower", number="ST-F", flat=True,
             edge_view=True, material="Carbon plate 3.0 mm or EN AW-7075-T6", density=1.6, density_txt="carbon",
             quantity="1", tol=GENERAL_CNC, edges="chamfers 0.5 x 45 deg (outline), 0.3 (holes)", status="verified",
             names=csv_names("cad/shock_tower/shock_tower_front_hole_table.csv"), label_names=True,
             notes=["Laser or waterjet cutting from the DXF file shock_tower_front_T410R_speedrun.dxf; edge chamfers and "
                    "the relief on the back face (clearance to the root radius of the wall of the upper bulkhead) as in "
                    "the STEP file (second machining step).", "Hole names as in the hole table of the shock tower."]),
        dict(key="shock_tower_rear", folder="cad/shock_tower", step="shock_tower_rear_T410R_speedrun.step",
             stem="shock_tower_rear_T410R_speedrun", title="Speedrun rear shock tower", number="ST-R", flat=True,
             edge_view=True, material="Carbon plate 3.0 mm or EN AW-7075-T6", density=1.6, density_txt="carbon",
             quantity="1", tol=GENERAL_CNC, edges="chamfers 0.5 x 45 deg (outline), 0.3 (holes)", status="verified",
             names=csv_names("cad/shock_tower/shock_tower_rear_hole_table.csv"), label_names=True,
             notes=["Laser or waterjet cutting from the DXF file shock_tower_rear_T410R_speedrun.dxf; edge chamfers and "
                    "the relief on the back face as in the STEP file (second machining step).",
                    "Hole names as in the hole table of the shock tower."]),
        dict(key="pivot_block_long", folder="cad/parts/pivot_block", step="pivot_block_long_T410R.step",
             stem="pivot_block_long_T410R", title="Pivot block, long (End B, outer)", number="PB-L",
             dims=[("F", (-22.3, 0, 4.6), (22.3, 0, 4.6), "h", "below", None), ("T", (-15.91, 0, 0), (15.91, 0, 0), "h", "below", None)],
             material="To be defined (e.g. 7075-T6)", quantity="1", tol=GENERAL_CNC, edges=EDGES_BREAK,
             status="verified", sections=[dict(label="B", point=(0, 0, 0), d=(0, -1, 0), x=(1, 0, 0),
                                                  title="Section B-B (axes of the bores)",
                                                  callouts=[((-22.3, 0, 4.6 + 2.5), "Ø5.0, depth 4.7 (2x)", (-14, 12))])],
             notes=["Bores Ø5.0 for the inserts of the hinge pin (verified with the 3D printed prototype); fit to be "
                    "confirmed with the inserts.", "Threads M3 for the countersunk screws from below through the chassis plate."]),
        dict(key="pivot_block_short", folder="cad/parts/pivot_block", step="pivot_block_short_T410R.step",
             stem="pivot_block_short_T410R", title="Pivot block, short (End B inner, End A inner and outer)",
             dims=[("F", (-20.7, 0, 4.6), (20.7, 0, 4.6), "h", "below", None), ("T", (-14.56, 0, 0), (14.56, 0, 0), "h", "below", None)],
             number="PB-S", material="To be defined (e.g. 7075-T6)", quantity="3", tol=GENERAL_CNC,
             edges=EDGES_BREAK, status="verified",
             sections=[dict(label="B", point=(0, 0, 0), d=(0, -1, 0), x=(1, 0, 0), title="Section B-B (axes of the bores)",
                            callouts=[((-20.7, 0, 4.6 + 2.5), "Ø5.0, depth 4.7 (2x)", (-14, 12))])],
             notes=["Bores Ø5.0 for the inserts of the hinge pin (verified with the 3D printed prototype); fit to be "
                    "confirmed with the inserts.", "Threads M3 for the countersunk screws from below through the chassis plate."]),
        dict(key="motor_mount", folder="cad/parts/motor_mount", step="motor_mount_T410R.step", stem="motor_mount_T410R",
             title="Motor mount", number="MM", material="EN AW-7075-T6", density=2.81, density_txt="7075", quantity="1", tol=GENERAL_CNC,
             edges=EDGES_BREAK, status="verified (test print)",
             view_callouts=[("F", (0.0, 0.0, 17.2 - 5.3), "U-notch 10.6 (bearing 5x10x4)", (2, 46.2)),
                            ("F", (23.8, 0.0, 17.2 + 6.5), "long hole 13.0 (motor shaft)", (16, 31.0)),
                            ("F", (25.0, 0.0, 28.4 + 1.6), "long holes 3.2 (motor screws)", (44, 10.5))],
             notes=["U-shaped notch 10.6 wide, open to the top, for the bearing 5x10x4 of the rear pinion shaft (as the "
                    "original part); lip 1.0 wide (opening Ø8.0) on the side toward End A. The set screw M3x3 in the cap "
                    "(part MM-C) presses on the outer ring of the bearing.",
                    "Threads M3 from below for the screws through the holes H09 and H10 of the chassis plate; threads M3 "
                    "from above for the 2 screws M3x18 through the top brace and the cap."]),
        dict(key="motor_mount_cap", folder="cad/parts/motor_mount", step="motor_mount_cap_T410R.step",
             stem="motor_mount_cap_T410R", title="Cap of the motor mount", number="MM-C", material="EN AW-7075-T6",
             density=2.81, density_txt="7075", quantity="1", tol=GENERAL_CNC, edges=EDGES_BREAK, status="verified (test print)",
             notes=["Notch 7.0 wide and 4.3 deep across the top face; thread M3 in its bottom for the set screw M3x3 that "
                    "presses on the outer ring of the bearing in the motor mount (part MM).",
                    "Through holes Ø3.2 for the 2 screws M3x18 from the top brace into the motor mount."]),
        dict(key="c_hub", folder="cad/running_gear/front_corner", step="c_hub_end_a.step", stem="c_hub_end_a",
             title="Front C-hub, right (left part mirrored)", number="CH", frame=(Rc, Oc),
             material="To be defined (3D print verification planned)", quantity="2 (right; left mirrored)", tol=GENERAL_CNC,
             edges=EDGES_BREAK, status="not verified",
             frame_note=f"Drawing frame: origin O on the axis of the outer hinge pin in the middle of the lug, axes as in the "
                        f"chassis plate coordinates (x across the car, y along the car, z up); the STEP file is in the "
                        f"assembly position: O = ({Oc[0]:.2f}, {Oc[1]:.3f}, {Oc[2]:.2f}).",
             sections=[dict(label="B", point=(kx, 0, 0), d=(1, 0, 0), x=(0, 1, 0),
                            title="Section B-B (plane of the kingpin axis, seen from the wheel)",
                            axes=[(Jc - kd * 17, Jc + kd * 16), (Jc - kn * 9, Jc + kn * 9)],
                            callouts=[(Jc + kd * 12.6 + kn * 2.5, "Ø5.0 H7 (2x), guide sleeves", (32, 6)),
                                      (Jc - kd * 16.5, f"kingpin axis, {rgp['caster']:g} deg to z (caster)", (36, -2)),
                                      (Jc - kd * 10.8 + kn * 3.5, "counterbore Ø7.0 x 0.55", (18, 4)),
                                      (Jc - kd * 15.4 - kn * 2.85, "pocket Ø5.7 (screw head)", (-16, -10)),
                                      (Jc, "O' (axle, CVD joint)", (44, -16))])],
             notes=[f"Kingpin bores Ø5.0 for the flanged guide sleeves Ø4.95 (fit without pressing): Ø5.0 H7 (proposal). "
                    f"Kingpin axis {rgp['caster']:g} deg to z (caster, top toward -y), x = {kx:.2f} from O; at the height of "
                    f"the axle ({rgp['wheel_r'] - rgp['ride_height'][0] - Oc[2]:.2f} above O) {rgp['kingpin_y']:.2f} toward -y from O.",
                    "Bore Ø3.0 for the outer hinge pin 3x26 (fixed with the grub screw M3 from below): Ø3.0 H7 (proposal).",
                    "Owner: the top guide sleeve is inserted from below (foot approx. 0.6 mm between the C-hub and the "
                    "knuckle); the model is changed after further measurements (open point)."]),
        dict(key="steering_knuckle", folder="cad/running_gear/front_corner", step="steering_knuckle_end_a.step",
             stem="steering_knuckle_end_a", title="Front steering knuckle, right (left part mirrored)", number="SK",
             frame=(Rk, Jk), material="To be defined (original part: plastic)", quantity="2 (right; left mirrored)",
             tol=GENERAL_CNC, edges=EDGES_BREAK, status="verified (3D print)",
             frame_note=f"Drawing frame: kingpin frame, origin O in the centre of the outer CVD joint (kingpin axis at the "
                        f"height of the axle), x along the axle (toward the wheel), z along the kingpin axis; the STEP file is "
                        f"in the assembly position (caster {rgp['caster']:g} deg): O = ({Jk[0]:.2f}, {Jk[1]:.3f}, {Jk[2]:.2f}).",
             sections=[dict(label="B", point=(0, 0, 0), d=(0, -1, 0), x=(1, 0, 0), title="Section B-B (axle and kingpin axis)",
                            callouts=[((4.0, 0, 5.0), "Ø10 K7 (2x), bearings 5x10x4", (10, 18)),
                                      ((8.4, 0, 4.0), "lip Ø8.0", (12, 9)),
                                      ((2.0, 0, -6.2), "entry bore Ø12.4", (12, -10))])],
             notes=["Bearing seats Ø10 for 2 bearings 5x10x4, pressed in from both ends against the lip: Ø10 K7 (proposal; "
                    "original part 9.98).", "Kingpin bores Ø2.7 in the bosses: thread formed by the set screws M3 (as the "
                    "original part).", "Threads M3 in the steering arm for the ball stud of the steering link."]),
        dict(key="front_splitter", folder="cad/front_splitter", step="front_splitter_one_piece_end_a.step",
             stem="front_splitter_one_piece_end_a", title="Speedrun front splitter (one part)", number="FS",
             frame=(np.eye(3), np.array([0.0, 317.982, 0.0])), material="Nylon PA12 (MJF 3D print)", density=1.01, density_txt="PA12",
             quantity="1", tol="process tolerance (MJF approx. ±0.3)", edges="as modelled",
             status="ordered as MJF 3D print (PA12)",
             frame_note="Drawing frame: origin O in the middle between the holes H34 and H35 of the chassis plate, on the "
                        "bottom face; axes as in the chassis plate coordinates (the STEP file is in the assembly position: "
                        "O = (0, 317.982, 0)).",
             sections=[dict(label="B", point=(16.677, 0, 0), d=(-1, 0, 0), x=(0, -1, 0), title="Section B-B (through H35)",
                            clip=(-24.0, 9.0, -1.5, 11.5), scale=5.0,
                            axes=[((16.677, 0, -2), (16.677, 0, 12))],
                            callouts=[((16.677, 3.15, 9.0), "boss Ø6.3, top at z = 10.0", (-24, 10)),
                                      ((16.677, -1.25, 5.0), "Ø2.5 (thread M3), depth 4.5", (40, 14)),
                                      ((16.677, -3.0, 1.0), "pocket for the chassis plate, 2.0 deep", (34, -14))])],
             details=[dict(title="Detail X (body post mount)", box=(-42.0, 42.0, -6.0, 22.0), scale=2.0, plane="T")],
             notes=["Blind holes Ø2.5 in the bosses on H34, H35 and H36: thread M3 cut by hand or formed by the screws "
                    "M3x6 (countersunk, from below through the chassis plate).", "Hexagon recesses 7.06 across the flats "
                    "in the ears: fit of the body posts.", "Orient the part in the printer for a flat bottom face."]),
        dict(key="wishbone_front", folder="cad/parts/wishbone", step="wishbone_front_T410R.step", stem="wishbone_front_T410R",
             title="Front wishbone (used on both sides)", number="WB-F",
             dims=[("T", (0, -16.5, 0), (49.7, -16.5, 0), "h", "below", "49.70 (axis to axis)")], material="To be defined (original part: plastic)",
             quantity="2", tol=GENERAL_CNC, edges=EDGES_BREAK, status="measures qualified",
             notes=["Bores Ø3.0 of the inner lugs for the inner hinge pin 3x42, bores Ø4.3 of the outer lugs for the outer "
                    "hinge pin (as the original part).", "Threads M3 for the ball studs of the damper (shock plate) and of the "
                    "sway bar drop link, threads M4 for the droop screws."]),
        dict(key="wishbone_rear", folder="cad/parts/wishbone", step="wishbone_rear_T410R.step", stem="wishbone_rear_T410R",
             title="Rear wishbone (used on both sides)", number="WB-R",
             dims=[("T", (0, -16.5, 0), (54.3, -16.5, 0), "h", "below", "54.30 (axis to axis)")], material="To be defined (original part: plastic)",
             quantity="2", tol=GENERAL_CNC, edges=EDGES_BREAK, status="measures qualified",
             notes=["Bores Ø3.0 of the inner lugs for the inner hinge pin 3x42, bores Ø4.3 of the outer lugs for the outer "
                    "hinge pin (as the original part).", "Threads M3 for the ball studs of the damper (shock plate) and of the "
                    "sway bar drop link, threads M4 for the droop screws."]),
    ]


# ------------------------------------------------------------------ layout
def placed_view(d, xdir, bb, scale, left=None, top=None, right=None, bottom=None):
    """View whose paper bounding box touches the given left/top (or right/bottom) edges."""
    v = View(d, xdir, (0, 0), scale=scale)
    x0, y0, x1, y1 = TD.view_box(v, bb)
    dx = (left - x0) if left is not None else (right - x1)
    dy = (top - y1) if top is not None else (bottom - y0)
    return View(d, xdir, (dx, dy), scale=scale)


def layout_3d(bb):
    W, D, H = bb.xlen, bb.ylen, bb.zlen
    s = next((s for s in SCALES if (H + D) * s <= 200 and (W + D) * s <= 305), SCALES[-1])
    F = placed_view((0, -1, 0), (1, 0, 0), bb, s, left=X_LEFT, top=Y_TOP)
    fb = TD.view_box(F, bb)
    T = placed_view((0, 0, 1), (1, 0, 0), bb, s, left=X_LEFT, top=fb[1] - 30)
    S = placed_view((-1, 0, 0), (0, -1, 0), bb, s, left=fb[2] + 38, top=Y_TOP)
    tb = TD.view_box(T, bb)
    sb = TD.view_box(S, bb)
    regions = [(max(tb[2] + 36, 245.0), 74.0, 405.0, min(fb[1], sb[1]) - 22),     # right of the top view
               (max(sb[2] + 30, tb[2] + 36), 74.0, 405.0, 268.0),                 # right of the side view
               (X_LEFT, 26.0, 225.0, tb[1] - 20),                                  # below the top view
               (230.0, 74.0, 405.0, tb[1] - 20)]
    iso = max(regions, key=lambda r: min(r[2] - r[0], r[3] - r[1]))
    return s, {"F": F, "T": T, "S": S}, iso


def layout_flat(bb, rotate, edge_view):
    long_, short = (bb.ylen, bb.xlen) if rotate else (bb.xlen, bb.ylen)
    hmax = 168.0 if edge_view else 201.0
    s = next((s for s in SCALES if long_ * s <= 340 and short * s <= hmax), SCALES[-1])
    xdir = (0, 1, 0) if rotate else (1, 0, 0)
    h = short * s
    bottom = 74.0 + (hmax - h) / 2 if not edge_view else 80.0
    T = placed_view((0, 0, 1), xdir, bb, s, left=X_LEFT, bottom=bottom)
    views = {"T": T}
    if edge_view:
        tb = TD.view_box(T, bb)
        E = placed_view((1, 0, 0) if rotate else (0, -1, 0), xdir, bb, s, left=X_LEFT, bottom=tb[3] + 30)
        views["E"] = E
    return s, views


# ------------------------------------------------------------------ drawing
def title_rows(cfg, vol, scale, date):
    dens = cfg.get("density")
    mass = f"{vol * dens:.0f} g ({cfg.get('density_txt', 'material')}, {vol:.2f} cm³)" if dens else f"– ({vol:.2f} cm³)"
    return {"title": cfg["title"], "subtitle": f"{cfg['stem']}.step (master geometry), {cfg['folder']}", "grid": [
        [("Drawn", TD.AUTHOR), ("Date", date), ("Drawing number", f"RC-SR-{cfg['number']}, revision A")],
        [("Material", cfg["material"]), ("Quantity", cfg["quantity"]), ("Scale", f"{scale_text(scale)} (A3)")],
        [("General tolerances", cfg["tol"]), ("Mass", mass), ("Units", "mm")],
        [("Edges", cfg["edges"]), ("Threads", "ISO metric, 6H"), ("Projection", "first angle")],
        [("Surface", "Ra 3.2"), ("Model", "STEP = master geometry"), ("Status", cfg["status"])],
    ]}


def note_lines(cfg, has_threads):
    lines = ["The STEP file is the master geometry. Dimensions that are not shown are taken from the model."]
    if cfg.get("frame_note"):
        lines.append(cfg["frame_note"])
    lines.append(f"Material: {cfg['material']}. General tolerances: {cfg['tol']}.")
    if has_threads:
        lines.append("Threads ISO metric, tolerance 6H. The model shows the tap drill; thread depth as in the hole table "
                     "(drill depth minus 1.0 for blind holes).")
    lines += cfg.get("notes", [])
    lines.append("Values marked as proposal are confirmed before the order.")
    return lines


def notes_block(ax, cfg, P, has_threads):
    x, y = P
    text(ax, (x, y), "Notes", ha="left", va="top", fs=9, weight="bold")
    y -= 5.0
    for i, s in enumerate(note_lines(cfg, has_threads), 1):
        for j, part in enumerate(textwrap.wrap(s, 112)):
            text(ax, (x + (0 if j == 0 else 4), y), (f"{i}. " if j == 0 else "") + part, ha="left", va="top", fs=7.4)
            y -= 4.0
    return y


HOLE_COLS = [("Id", 10), ("x", 15), ("y", 16), ("z", 13), ("Direction", 40), ("Size", 31), ("Depth", 33), ("Note", 218)]


def section_scale(secs, bb):
    def size(q):
        bx = [TD.view_box(View(sec["d"], sec["x"], (0, 0), scale=q), bb) for sec in secs]
        return sum(b_[2] - b_[0] for b_ in bx) + 50 * (len(secs) - 1), max(b_[3] - b_[1] for b_ in bx)
    q = next((q for q in SCALES if size(q)[0] <= 350 and size(q)[1] <= 190), SCALES[-1])
    return q, size(q)[1]


def draw_sheet1(cfg, solid, bb, rows, tb, n_sheets):
    flat = cfg.get("flat", False)
    if flat:
        s, views = layout_flat(bb, cfg.get("rotate", False), cfg.get("edge_view", False))
        iso = None
    else:
        s, views, iso = layout_3d(bb)
    fig, ax = TD.sheet(tb, 1, n_sheets)
    for k, V in views.items():
        TD.draw_view(ax, solid, V)
    boxes = {k: TD.view_box(V, bb) for k, V in views.items()}
    names = {"F": "Front view (from -y)", "T": "Top view" if not flat else f"View from above (t = {bb.zlen:.1f})",
             "S": "Side view (from the left, -x)", "E": "Edge view"}
    for k, (x0, y0, x1, y1) in boxes.items():
        if k in ("F", "S", "E"):
            view_label(ax, ((x0 + x1) / 2, y1 + 16), names[k])
        else:
            text(ax, (24, y1 + 14 if y1 + 14 < 280 else y0 - 12), names[k], fs=TD.LABEL_FS, ha="left", weight="bold")
    if flat:
        T = views["T"]
        x0, y0, x1, y1 = boxes["T"]
        if cfg.get("rotate"):
            linear(ax, T.P((0, bb.ymin, 0)), T.P((0, bb.ymax, 0)), "h", y1 + 8, f"{bb.ylen:.2f}")
            linear(ax, T.P((bb.xmax, bb.ymin, 0)), T.P((bb.xmin, bb.ymin, 0)), "v", x0 - 9, f"{bb.xlen:.2f}")
        else:
            linear(ax, T.P((bb.xmin, bb.ymin, 0)), T.P((bb.xmax, bb.ymin, 0)), "h", y0 - 8, f"{bb.xlen:.2f}")
            linear(ax, T.P((bb.xmax, bb.ymin, 0)), T.P((bb.xmax, bb.ymax, 0)), "v", x1 + 9, f"{bb.ylen:.2f}", tside="r")
        if cfg.get("end_labels"):                       # below the view, or in its upper corners if there is no room
            ly, va = (y0 - 6, "top") if y0 - 16 > 74 else (y1 - 2, "top")
            text(ax, (x0 + (0 if va == "top" and ly < y0 else 2), ly), cfg["end_labels"][0], ha="left", va=va, fs=8, color="0.3")
            text(ax, (x1 - (0 if ly < y0 else 2), ly), cfg["end_labels"][1], ha="right", va=va, fs=8, color="0.3")
        if "E" in views:
            E = views["E"]
            ex0 = boxes["E"][0]
            linear(ax, E.P((bb.xmin, bb.ymin, bb.zmin)), E.P((bb.xmin, bb.ymin, bb.zmax)), "v", ex0 - 6, f"{bb.zlen:.2f}",
                   inside=False, shift=6)
    else:
        F, T, S = views["F"], views["T"], views["S"]
        fx0, fy0, fx1, fy1 = boxes["F"]
        linear(ax, F.P((bb.xmin, 0, bb.zmin)), F.P((bb.xmax, 0, bb.zmin)), "h", fy0 - 8, f"{bb.xlen:.2f}")
        linear(ax, F.P((bb.xmin, 0, bb.zmin)), F.P((bb.xmin, 0, bb.zmax)), "v", fx0 - 9, f"{bb.zlen:.2f}")
        tx0, ty0, tx1, ty1 = boxes["T"]
        linear(ax, T.P((bb.xmax, bb.ymin, 0)), T.P((bb.xmax, bb.ymax, 0)), "v", tx1 + 9, f"{bb.ylen:.2f}", tside="r")
        sy0 = boxes["S"][1]
        linear(ax, S.P((0, bb.ymax, bb.zmin)), S.P((0, bb.ymin, bb.zmin)), "h", sy0 - 8, f"{bb.ylen:.2f}")
        origin_P = T.P((0, 0, 0))
        if tx0 - 1 <= origin_P[0] <= tx1 + 1 and ty0 - 1 <= origin_P[1] <= ty1 + 1:
            TD.origin_mark(ax, origin_P)
    for k, V in views.items():                             # holes seen as circles: centre marks and labels
        items = []
        for r in rows:
            h = r["hole"]
            if abs(h["d"] @ V.d) > 0.99:
                Pc = V.P(r["P"])
                centre_mark(ax, Pc, h["dia"] / 2 * V.s)
                items.append((Pc, r["id"]))
        if not items:
            continue
        x0, y0, x1, y1 = boxes[k]
        if cfg.get("label_names"):
            for Pc, lab in items:
                text(ax, (Pc[0] + 1.6, Pc[1] + 1.4), lab, ha="left", va="bottom", fs=6.3, color="0.15")
        else:
            TD.place_balloons(ax, items, ((x0 + x1) / 2, (y0 + y1) / 2), dist=7.0, avoid=[P for P, _ in items])
    for r in rows:                                         # tilted holes: label in the view closest to their axis
        h = r["hole"]
        if all(abs(h["d"] @ V.d) <= 0.99 for V in views.values()) and not any(abs(abs(c) - 1) < 1e-3 for c in h["d"]):
            k = min(views, key=lambda q: abs(h["d"] @ views[q].d))
            TD.place_balloons(ax, [(views[k].P(r["P"]), r["id"])], ((boxes[k][0] + boxes[k][2]) / 2, boxes[k][3] + 20))
    used = {("F", "below"): 1, ("F", "left"): 1, ("T", "right"): 1, ("S", "below"): 1, ("T", "above"): 1,
            ("T", "left"): 1, ("T", "below"): 1 if (flat and not cfg.get("rotate")) else 0}
    for vk, p1, p2, axis, side, label in cfg.get("dims", []):
        V, (x0, y0, x1, y1) = views[vk], boxes[vk]
        n = used.get((vk, side), 0)
        at = {"below": y0 - 8 * (n + 1), "above": y1 + 8 * (n + 1), "left": x0 - 9 * (n + 1), "right": x1 + 9 * (n + 1)}[side]
        used[(vk, side)] = n + 1
        val = label or f"{np.linalg.norm(np.asarray(p2, float) - np.asarray(p1, float)):.2f}"
        linear(ax, V.P(p1), V.P(p2), axis, at, val, tside="r" if side == "right" else "l")
    for vk, p3, label, off in cfg.get("view_callouts", []):
        Pf = views[vk].P(p3)
        leader(ax, Pf, Pf + np.asarray(off, float), label, ha="left" if off[0] >= 0 else "right")
    if iso and (iso[2] - iso[0]) > 60 and (iso[3] - iso[1]) > 50:
        TD.iso_inset_solid(fig, solid, [iso[0] / A3[0], iso[1] / A3[1], (iso[2] - iso[0]) / A3[0], (iso[3] - iso[1]) / A3[1]],
                           cfg.get("iso_azim", -55))
        text(ax, ((iso[0] + iso[2]) / 2, iso[1] - 4), "Isometric view (not to scale)", fs=8, color="0.3")
    text(ax, (24, 14), "Dimensions in mm. Dimensions that are not shown are taken from the STEP model. Hole sizes, threads "
         f"and depths: hole table on sheet {n_sheets}.", ha="left", va="bottom", fs=7.5)
    return fig, s


def draw_detail(fig, solid, rows, det, xdir, left, top, label_names):
    """Detail view (enlarged region of the view from above): its own axes clip the drawing to the region."""
    xa, xb, ya, yb = det["box"]
    q = det["scale"]
    V = View((0, 0, 1), xdir, (0, 0), scale=q)
    cs = np.array([V.P((x, y, 0)) for x in (xa, xb) for y in (ya, yb)])
    w, h = np.ptp(cs[:, 0]), np.ptp(cs[:, 1])
    V = View((0, 0, 1), xdir, (left - cs[:, 0].min(), top - h - cs[:, 1].min()), scale=q)
    axd = fig.add_axes([left / A3[0], (top - h) / A3[1], w / A3[0], h / A3[1]])
    axd.set_xlim(left, left + w)
    axd.set_ylim(top - h, top)
    axd.set_aspect("equal")
    axd.axis("off")
    TD.draw_view(axd, solid, V)
    for r in rows:
        if abs(r["hole"]["d"] @ V.d) > 0.99:
            Pc = V.P(r["P"])
            if left <= Pc[0] <= left + w and top - h <= Pc[1] <= top:
                centre_mark(axd, Pc, r["hole"]["dia"] / 2 * q)
                text(axd, (Pc[0] + 1.8, Pc[1] + 1.6), r["id"], ha="left", va="bottom", fs=7.2, color="0.15")
    return (left, top - h, left + w, top)


def draw_sections(fig, ax, solid, bb, rows, cfg, secs, ss):
    """Sections and detail views, left to right in rows from the top of the sheet; returns the lowest paper y."""
    items = [("sec", s_) for s_ in secs] + [("det", d_) for d_ in cfg.get("details", [])]
    xcur, ytop, y_low = 40.0, 262.0, 262.0
    xdir = (0, 1, 0) if cfg.get("rotate") else (1, 0, 0)
    for kind, it in items:
        if kind == "sec" and it.get("clip"):
            w = (it["clip"][1] - it["clip"][0]) * it["scale"]
        elif kind == "sec":
            V0 = View(it["d"], it["x"], (0, 0), scale=ss)
            bx = TD.view_box(V0, bb)
            w = bx[2] - bx[0]
        else:
            V0 = View((0, 0, 1), xdir, (0, 0), scale=it["scale"])
            cs = np.array([V0.P((x, y, 0)) for x in it["box"][:2] for y in it["box"][2:]])
            w = np.ptp(cs[:, 0])
        if xcur + w > 405 and xcur > 40:
            xcur, ytop = 40.0, y_low - 24
        if kind == "sec" and it.get("clip"):              # partial section: own axes clip it to the region
            ua, ub, va, vb = it["clip"]
            q = it["scale"]
            V = View(it["d"], it["x"], (xcur - q * ua, ytop - q * vb), scale=q)
            x0, y0, x1, y1 = xcur, ytop - (vb - va) * q, xcur + (ub - ua) * q, ytop
            axd = fig.add_axes([x0 / A3[0], y0 / A3[1], (x1 - x0) / A3[0], (y1 - y0) / A3[1]])
            axd.set_xlim(x0, x1)
            axd.set_ylim(y0, y1)
            axd.set_aspect("equal")
            axd.axis("off")
            TD.draw_section(axd, solid, V, np.asarray(it["point"], float))
            ax.add_patch(TD.plt.Rectangle((x0 - 2, y0 - 2), x1 - x0 + 4, y1 - y0 + 4, fill=False, lw=TD.THIN, ls="--", zorder=8))
            view_label(ax, ((x0 + x1) / 2, y1 + 6), it["title"] + f" ({scale_text(q)})")
        elif kind == "sec":
            V = placed_view(it["d"], it["x"], bb, ss, left=xcur, top=ytop)
            TD.draw_section(ax, solid, V, np.asarray(it["point"], float))
            x0, y0, x1, y1 = TD.view_box(V, bb)
            view_label(ax, ((x0 + x1) / 2, y1 + 8), it["title"] + f" ({scale_text(ss)})")
        if kind == "sec":
            for p0, p1 in it.get("axes", []):
                centre_line(ax, V.P(p0), V.P(p1))
            for p3, txt, off in it.get("callouts", []):
                Pf = V.P(p3)
                leader(ax, Pf, Pf + np.asarray(off, float), txt, ha="left" if off[0] >= 0 else "right")
        else:
            x0, y0, x1, y1 = draw_detail(fig, solid, rows, it, xdir, xcur, ytop, cfg.get("label_names"))
            ax.add_patch(TD.plt.Rectangle((x0 - 2, y0 - 2), x1 - x0 + 4, y1 - y0 + 4, fill=False, lw=TD.THIN, ls="--", zorder=8))
            view_label(ax, ((x0 + x1) / 2, y1 + 5), it["title"] + f" ({scale_text(it['scale'])})")
        xcur = x1 + 45
        y_low = min(y_low, y0)
    return y_low


def draw_part(cfg, date):
    solid = cq.importers.importStep(f"{cfg['folder']}/{cfg['step']}").val()
    if cfg.get("frame") is not None:
        solid = TD.to_frame(solid, *cfg["frame"])
    bb = solid.BoundingBox()
    vol = solid.Volume() / 1000
    holes = TD.find_holes(solid)
    table, rows = TD.hole_rows_generic(holes, names=cfg.get("names"), centroid=np.array(solid.Center().toTuple()))
    has_threads = any(r[5].startswith("M") for r in table)
    secs = cfg.get("sections", [])
    dets = cfg.get("details", [])
    table_h = (len(table) + 1) * 4.6 + 14
    notes_h = 4.0 * sum(len(textwrap.wrap(s, 112)) for s in note_lines(cfg, has_threads)) + 16
    full = [s_ for s_ in secs if not s_.get("clip")]
    ss, sec_h = section_scale(full, bb) if full else (2.0, 0.0)
    for s_ in secs:
        if s_.get("clip"):
            sec_h = max(sec_h, (s_["clip"][3] - s_["clip"][2]) * s_["scale"])
    for d_ in dets:
        sec_h = max(sec_h, (d_["box"][1] - d_["box"][0] if cfg.get("rotate") else d_["box"][3] - d_["box"][2]) * d_["scale"])
    if secs and dets:
        sec_h += 24 + max((d_["box"][1] - d_["box"][0] if cfg.get("rotate") else d_["box"][3] - d_["box"][2]) * d_["scale"]
                          for d_ in dets)
    n_sheets = 3 if (secs or dets) and sec_h + 30 + table_h + notes_h > 255 else 2
    s = layout_flat(bb, cfg.get("rotate", False), cfg.get("edge_view", False))[0] if cfg.get("flat") else layout_3d(bb)[0]
    tb = title_rows(cfg, vol, s, date)
    fig1, s = draw_sheet1(cfg, solid, bb, rows, tb, n_sheets)
    figs = [fig1]
    fig, ax = TD.sheet(tb, 2, n_sheets)
    figs.append(fig)
    y_table = 275.0
    if secs or dets:
        y_low = draw_sections(fig, ax, solid, bb, rows, cfg, secs, ss)
        if n_sheets == 3:
            fig, ax = TD.sheet(tb, 3, n_sheets)
            figs.append(fig)
        else:
            y_table = y_low - 16
    text(ax, (24, y_table + 3), "Holes (x, y, z of the start point in the drawing frame; O: origin of the drawing frame)",
         ha="left", fs=8, weight="bold")
    y_end = TD.hole_table(ax, 24, y_table, table, cols=HOLE_COLS) if table else y_table - 6
    notes_block(ax, cfg, (24, min(y_end - 10, max(150.0, 14 + notes_h))), has_threads)
    pdf = f"{cfg['folder']}/{cfg['stem']}_technical_drawing.pdf"
    TD.save(figs, pdf, f"{cfg['folder']}/{cfg['stem']}_technical_drawing")
    return pdf, s, table, n_sheets


FOLDERS = {
    "cad/chassis/chassis_plate_speedrun_wide_motor10": ("Speedrun chassis plate (wide) with longer motor window: technical drawing",
                                                        "../../readme.md#longer-motor-window-for-a-3660-motor"),
    "cad/chassis/top_brace_speedrun": ("Speedrun top brace: technical drawing", "../../readme.md#speedrun-top-brace"),
    "cad/shock_tower": ("Speedrun shock towers: technical drawings", "../readme.md#speedrun-shock-towers"),
    "cad/parts/pivot_block": ("Pivot blocks: technical drawings", "../../readme.md#pivot-blocks"),
    "cad/parts/motor_mount": ("Motor mount and cap: technical drawings", "../../readme.md#centre-driveshaft-and-drive-line"),
    "cad/running_gear/front_corner": ("Front corner: technical drawings of the C-hub and the steering knuckle",
                                      "../../readme.md#running-gear"),
    "cad/front_splitter": ("Speedrun front splitter: technical drawing", "../readme.md#speedrun-front-splitter"),
    "cad/parts/wishbone": ("Wishbones: technical drawings", "../../readme.md#wishbones"),
}
SHEET_TEXT = {1: "views, main dimensions, labels of the holes",
              2: "sections and detail views, hole table and notes",
              3: "hole table and notes"}


def anchor(title):
    s = "".join(c for c in title.lower() if c.isalnum() or c in " -_")
    return s.replace(" ", "-")


def write_readmes(results):
    """readme.md per directory: the sheets of each part, generated from the part definitions."""
    for folder, (title, link) in FOLDERS.items():
        items = [(cfg, r) for cfg, r in results if cfg["folder"] == folder]
        if not items:
            continue
        lines = [f"# {title}", "", "## Table of contents", "* [Overview](#overview)"]
        lines += [f"* [{cfg['title']}](#{anchor(cfg['title'])})" for cfg, _ in items]
        lines += ["* [Files](#files)", "* [Generating the drawings](#generating-the-drawings)", "", "## Overview",
                  "* Technical drawings for manufacturing. The views and sections are projected from the STEP files (hidden "
                  "line removal); the hole table is read from the STEP files.",
                  "* The STEP file is the master geometry. Dimensions that are not shown on the drawing are taken from the model.",
                  "* Format: A3 landscape, first angle projection, scale per part (title block). The PDF files are for printing "
                  "and for the order, the PNG files show the sheets on this page.",
                  f"* Description, sources and status of the parts: [CAD readme]({link}).",
                  "* Values marked as proposal on the drawings (fits, materials to be defined) are confirmed before the order.",
                  "* This page is generated by `scripts/cad/generate_technical_drawings.py`."]
        for cfg, (pdf, s, table, n) in items:
            lines += ["", f"## {cfg['title']}",
                      f"Material: {cfg['material']}. Quantity: {cfg['quantity']}. Status: {cfg['status']}. Scale of the views: "
                      f"{scale_text(s)}. {len(table)} holes in the hole table."]
            extra = " and ".join(w for w, on in (("sections", cfg.get("sections")), ("detail views", cfg.get("details"))) if on)
            for k in range(1, n + 1):
                txt = SHEET_TEXT[3 if (k == 2 and n == 2 and not extra) else k]
                if k == 2 and extra:
                    txt = extra + ("" if n == 3 else ", hole table and notes")
                lines += ["", f"**Sheet {k}:** {txt}", "",
                          f"![{cfg['title']}, technical drawing, sheet {k}]({cfg['stem']}_technical_drawing_sheet_{k}.png)"]
        lines += ["", "## Files", "| File | Content |", "|:---|:---|"]
        for cfg, (pdf, s, table, n) in items:
            pngs = ", ".join(f"`{cfg['stem']}_technical_drawing_sheet_{k}.png`" for k in range(1, n + 1))
            lines += [f"| `{cfg['stem']}_technical_drawing.pdf` | {cfg['title']}: technical drawing, {n} sheets A3 |",
                      f"| {pngs} | The sheets as images (150 dpi) |",
                      f"| `{cfg['step']}` | Master geometry of the part |"]
        lines += ["", "## Generating the drawings",
                  "The drawings are generated from the STEP files (from the root directory of the repository; packages "
                  "cadquery and matplotlib). After a change of a part, its generator runs first, then:", "", "```bash",
                  "python scripts/cad/generate_technical_drawings.py", "```", "",
                  "The option `--part` generates the drawing of one part (keys: " +
                  ", ".join(f"`{cfg['key']}`" for cfg, _ in items) + "), the option `--date` sets the date in the title block."]
        with open(f"{folder}/readme.md", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Technical drawings of the verified parts, the wishbones and the C-hub.")
    parser.add_argument("--part", help="key of one part (default: all)")
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    args = parser.parse_args()
    results = []
    for cfg in parts():
        if args.part and cfg["key"] != args.part:
            continue
        res = draw_part(cfg, args.date)
        results.append((cfg, res))
        print(f"{cfg['key']}: scale {scale_text(res[1])}, {len(res[2])} holes, {res[3]} sheets -> {res[0]}")
    if not args.part:
        write_readmes(results)
        print("wrote the readme files of the part directories")


if __name__ == "__main__":
    main()
