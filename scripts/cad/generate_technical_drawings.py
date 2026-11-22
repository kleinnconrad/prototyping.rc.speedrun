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


def steering_frames():
    """Frames of the bellcrank (origin on the hub axis on the bottom face) and of the servo mount parts (origin O at
    the hole H21 of the chassis plate: on its top face for the posts, on the lower face of the top plate for the plate)."""
    import generate_running_gear as G
    from generate_bulkhead_lower import load_params
    p = load_params(G.PARAMS)
    tp, m4 = p["servo_mount"][:2]
    t_w = p["guide_sleeve"][4]                                               # washer of the bridge joint on the bellcrank arm
    return {"bellcrank": np.array([21.7, 242.69, p["bellcrank"][0]]), "post": np.array([8.0, 199.15, G.PLATE_T]),
            "bridge": np.array([0.0, 242.69 - p["bellcrank"][4], p["bellcrank"][1] + t_w]),
            "steering_post": np.array([21.7, 242.69, G.PLATE_T]),
            "battery_tray": battery_tray_frame(),
            "plate": np.array([8.0, 199.15, G.PLATE_T + m4 - tp]), "p": p}


def battery_tray_frame():
    """Origin of the battery tray frame: middle between the 4 holes H11, H12, H22, H23 on the top face of the chassis plate."""
    import generate_battery_tray as BT
    hs = BT.holes(BT.load_params(BT.PARAMS))
    return np.array([np.mean([h[0] for h in hs]), np.mean([h[1] for h in hs]), BT.PLATE_T])


def battery_tray_layout():
    """Values of the battery tray in its drawing frame (x along the car, y = -x of the car, z up from the plate)."""
    import generate_battery_tray as BT
    p = BT.load_params(BT.PARAMS)
    g = BT.layout(p)
    o = battery_tray_frame()
    return p, g, (lambda xc: -(xc - o[0])), (lambda yc: yc - o[1])


def csv_names(path, z=0.0):
    with open(path, encoding="utf-8") as f:
        return [(r["id"], (float(r["x_mm"]), float(r["y_mm"]), z)) for r in csv.DictReader(f)]


def chassis_names(path="cad/speedrun_parts/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_speedrun_wide_motor10_geometry.json"):
    d = json.load(open(path))
    return [(h["id"], (h["x"], h["y"], 0.0)) for h in d["holes"]]


# ------------------------------------------------------------------ part definitions
GENERAL_CNC = "ISO 2768-mK"
EDGES_BREAK = "break 0.1 to 0.2"
EDGES_TREATED = "chamfer 0.3, radius 0.5 (modelled)"     # edge treatment of the C-hubs (printed)


def parts():
    rg = running_gear_frames()
    Rc, Oc, rgp = rg["c_hub"]
    Rk, Jk, _ = rg["knuckle"]
    ca, sa = np.cos(np.radians(rgp["caster"])), np.sin(np.radians(rgp["caster"]))
    kd = np.array([0.0, -sa, ca])                                      # kingpin axis (C-hub frame)
    kn = np.array([0.0, ca, sa])                                       # square to it in the y-z plane
    Jc = np.array([rgp["kingpin_x"] - Oc[0], -rgp["kingpin_y"], rgp["wheel_r"] - rgp["ride_height"][0] - Oc[2]])
    kx = rgp["kingpin_x"] - Oc[0]
    sf = steering_frames()
    sp = sf["p"]["servo_position"]
    bc, bs, sm, sv = sf["p"]["bellcrank"], sf["p"]["bellcrank_shape"], sf["p"]["servo_mount"], sf["p"]["servo"]
    xs = sp[1]                                                               # output shaft from H21 (x)
    x_ear = (xs - (sv[0] - sv[3]) - sv[6], xs + sv[3] + sv[6])               # ear holes from H21 (x)
    xfc, xlc = x_ear[0] / 2, x_ear[1]                                        # middle planes of the posts
    xf0, xpe = xfc - sm[2] / 2, xlc + sm[6] / 2                              # inner face of the fixed post, outer end
    ymid = sm[3] - sm[9] - (sm[4] - sm[9] - sm[10]) / 2                      # middle between the pillars
    btp, btg, bty, btx = battery_tray_layout()                               # battery tray: params, layout, frame maps
    bt_rs = btx(btg["ys"][0])                                                # rear strap (frame x)
    bt_h12 = bty(btg["hs"][1][0])                                            # line of H12 and H22 (frame y)
    bt_si0, bt_si1 = bty(btg["x_in"] - 0.5), bty(btg["x_in"] - 0.5 + btg["sx"])   # inner slot (frame y)
    bri, gsl, brj = sf["p"]["bridge"], sf["p"]["guide_sleeve"], sf["p"]["bridge_joint"]
    pst = sf["p"]["post"]
    z_shoulder = pst[3] - (5.0 + bs[3])                                      # shoulder of the post above the chassis plate
    t_top = 6.0 - 0.5 - pst[5]                                               # full thread on top (stop of the screw M3x6)
    xb_ = 21.7                                                               # axes of the towers (posts H24/H25)
    zbo = sf["bridge"][2]                                                    # bottom face of the towers (frame z = 0)
    zb_lo, zb_hi, zb_ball = bri[0] - zbo, bri[1] - zbo, (bri[0] + bri[1]) / 2 - zbo
    z_seat = gsl[2] - brj[0]                                                 # bore of the sleeve: sleeve length minus play
    y_horn_ball = 199.15 + sp[0] + sf["p"]["servo_horn"][3] + sf["p"]["ball_offset"]           # H21 + S1 + S5 + S8
    dboss = (242.69 - bc[4] - bri[2] / 2) - (y_horn_ball + sf["p"]["ball_offset"])             # depth of the ball boss

    def c_hub(side):
        """Front C-hub, right (side = 1) or left (side = -1). The C-hub has no plane of symmetry (caster, kingpin axis
        2.0 toward the middle of the car): the left part is the mirror image of the right part (x mirrored), it is
        drawn in the mirrored frame and the section is seen from its wheel."""
        m = np.array([side, 1.0, 1.0])
        name, other = ("right", "left") if side > 0 else ("left", "right")
        O_, J_ = Oc * m, Jc * m

        def off(dx, dy):                                    # paper offsets of the callouts (left: column right of the view)
            return (dx, dy)
        return dict(key="c_hub" if side > 0 else "c_hub_left", folder="cad/generic_parts/front_corner",
                    step=f"c_hub_end_a_{name}.step", stem=f"c_hub_end_a_{name}",
                    title=f"Front C-hub, {name}", number="CH-R" if side > 0 else "CH-L", frame=(Rc, O_),
                    material="To be defined (3D print verification planned)", quantity="1", tol=GENERAL_CNC,
                    edges=EDGES_TREATED, status="not verified",
                    frame_note=f"Drawing frame: origin O on the axis of the outer hinge pin in the middle of the lug, axes as "
                               f"in the chassis plate coordinates (x across the car, y along the car, z up); the STEP file is "
                               f"in the assembly position: O = ({O_[0]:.2f}, {O_[1]:.3f}, {O_[2]:.2f}).",
                    sections=[dict(label="B", point=(side * kx, 0, 0), d=(side, 0, 0), x=(0, side, 0), labels_right=side < 0,
                                   title="Section B-B (plane of the kingpin axis, seen from the wheel)",
                                   axes=[(J_ - kd * 17, J_ + kd * 16), (J_ - kn * 9, J_ + kn * 9)],
                                   callouts=[(J_ + kd * 12.6 + kn * 2.45, "Ø4.9 (2x), brass sleeves 4.8 x 3.2 x 4.0", off(32, 6)),
                                             (J_ - kd * 16.5, f"kingpin axis, {rgp['caster']:g} deg to z (caster)", off(36, -2)),
                                             (J_ - kd * 11.1 + kn * 3.5, "face toward the boss: washer M3 DIN 125-A, gap 0.55",
                                              off(18, 4)),
                                             (J_ + kd * 14.95 + kn * 4.5, "top face square to the kingpin axis, sleeve 0.1 proud",
                                              off(16, 6)),
                                             (J_ - kd * 14.95 + kn * 4.5, "bottom face square to the kingpin axis, sleeve 0.1 proud",
                                              off(12, -24)),
                                             (J_, "O' (axle, CVD joint)", off(44, -16))])],
                    notes=[f"{name.capitalize()} part. The C-hub has no plane of symmetry (caster, kingpin axis toward the middle "
                           f"of the car): the {other} part (CH-{other[0].upper()}) is its mirror image; the same part cannot "
                           f"be used on both sides.",
                           f"Kingpin bores Ø4.9 for the brass spacer sleeves Ø4.8 x 3.2 x 4.0 (they turn with the knuckle; ream if "
                           f"tight). "
                           f"Kingpin axis {rgp['caster']:g} deg to z (caster, top toward -y), x = {side * kx:.2f} from O; at the "
                           f"height of the axle ({rgp['wheel_r'] - rgp['ride_height'][0] - Oc[2]:.2f} above O) "
                           f"{rgp['kingpin_y']:.2f} toward -y from O.",
                           "Bore Ø3.0 for the outer hinge pin 3x26: Ø3.0 H7 (proposal). The pin is fixed with a grub screw M3x4 "
                           "from below in the boss Ø6.0 below the tube (thread M3 4.2 long, face 5.7 below the axis of the pin: "
                           "the screw lies fully in the thread with its tip on the pin).",
                           "Standard parts (owner): on each knuckle boss a washer M3 DIN 125-A (3.2 x 7 x 0.5) in the gap of 0.55 "
                           "between the boss and the arm, then the brass sleeve in the bore; the sleeves stand 0.1 proud of the "
                           "top face and of the bottom face (both square to the kingpin axis), so the ball stud and the screw "
                           "clamp sleeve and washer to the knuckle and the knuckle moves freely (owner).",
                           "Sleeve and washer turn with the knuckle: the sleeve in the bore (radial), the washer on the face of "
                           "the arm toward the boss (axial). No counterbores."])
    return [
        dict(key="chassis_plate", folder="cad/speedrun_parts/chassis/chassis_plate_speedrun_wide_motor10",
             step="chassis_plate_T410R_speedrun_wide_motor10.step", stem="chassis_plate_T410R_speedrun_wide_motor10",
             title="Speedrun chassis plate (wide) with longer motor window", number="CP", flat=True, rotate=True,
             material="EN AW-6082-T6, plate 2.0 mm", density=2.70, density_txt="6082", quantity="1", tol=GENERAL_CNC,
             edges="edges broken 0.1 to 0.2", status="ordered as CNC part (6082)", names=chassis_names(), label_names=True,
             end_labels=("End B (rear)", "End A (front)"),
             notes=["Countersinks Ø6.2 x 90 deg on the bottom face for countersunk screws M3 (ISO 10642).",
                    "Outline, windows and holes as in the DXF file chassis_plate_T410R_speedrun_wide_motor10.dxf.",
                    "Hole names as in the geometry data of the plate (H01 to H36)."]),
        dict(key="top_brace", folder="cad/speedrun_parts/chassis/top_brace_speedrun", step="top_brace_T410R_speedrun.step",
             stem="top_brace_T410R_speedrun", title="Speedrun top brace", number="TB", flat=True, rotate=True,
             material="Carbon plate 2.0 mm", density=1.6, density_txt="carbon", quantity="1",
             tol=GENERAL_CNC, edges="chamfers 0.5 x 45 deg (outline), 0.3 (holes)", status="ordered as carbon plate (2D milling)",
             names=csv_names("cad/speedrun_parts/chassis/top_brace_speedrun/top_brace_speedrun_hole_table.csv"), label_names=True,
             end_labels=("End with B01 to B04 (End A)", "End with B07 to B15 (End B)"),
             details=[dict(title="Detail X (end with B01 to B04)", box=(-18.5, 18.5, -1.5, 30.0), scale=2.0),
                      dict(title="Detail Y (end with B07 to B15)", box=(-18.5, 18.5, 198.0, 244.8), scale=2.0)],
             notes=["Ordered as carbon plate, 2D milling. Outline and holes from the DXF file top_brace_T410R_speedrun.dxf; edge chamfers 0.5 x 45 deg "
                    "on both faces of the outline and the obround, 0.3 x 45 deg on the holes (second machining step).",
                    "Hole names as in the hole table of the top brace (B01 to B15; B05 and B06 are closed)."]),
        dict(key="shock_tower_front", folder="cad/speedrun_parts/shock_tower", step="shock_tower_front_T410R_speedrun.step",
             stem="shock_tower_front_T410R_speedrun", title="Speedrun front shock tower", number="ST-F", flat=True,
             edge_view=True, material="Carbon plate 3.0 mm", density=1.6, density_txt="carbon",
             quantity="1", tol=GENERAL_CNC, edges="chamfers 0.5 x 45 deg (outline), 0.3 (holes)", status="ordered as carbon plate (2D milling)",
             names=csv_names("cad/speedrun_parts/shock_tower/shock_tower_front_hole_table.csv"), label_names=True,
             notes=["Ordered as carbon plate, 2D milling. Outline and holes from the DXF file shock_tower_front_T410R_speedrun.dxf; edge chamfers and "
                    "the relief on the back face (clearance to the root radius of the wall of the upper bulkhead) as in "
                    "the STEP file (second machining step).", "Hole names as in the hole table of the shock tower."]),
        dict(key="shock_tower_rear", folder="cad/speedrun_parts/shock_tower", step="shock_tower_rear_T410R_speedrun.step",
             stem="shock_tower_rear_T410R_speedrun", title="Speedrun rear shock tower", number="ST-R", flat=True,
             edge_view=True, material="Carbon plate 3.0 mm", density=1.6, density_txt="carbon",
             quantity="1", tol=GENERAL_CNC, edges="chamfers 0.5 x 45 deg (outline), 0.3 (holes)", status="ordered as carbon plate (2D milling)",
             names=csv_names("cad/speedrun_parts/shock_tower/shock_tower_rear_hole_table.csv"), label_names=True,
             notes=["Ordered as carbon plate, 2D milling. Outline and holes from the DXF file shock_tower_rear_T410R_speedrun.dxf; edge chamfers and "
                    "the relief on the back face as in the STEP file (second machining step).",
                    "Hole names as in the hole table of the shock tower."]),
        dict(key="pivot_block_long", folder="cad/generic_parts/pivot_block", step="pivot_block_long_T410R.step",
             stem="pivot_block_long_T410R", title="Pivot block, long (End B, outer)", number="PB-L",
             dims=[("F", (-22.3, 0, 4.6), (22.3, 0, 4.6), "h", "below", None), ("T", (-15.91, 0, 0), (15.91, 0, 0), "h", "below", None)],
             material="To be defined (e.g. 7075-T6)", quantity="1", tol=GENERAL_CNC, edges=EDGES_BREAK,
             status="verified", sections=[dict(label="B", point=(0, 0, 0), d=(0, -1, 0), x=(1, 0, 0),
                                                  title="Section B-B (axes of the bores)",
                                                  callouts=[((-22.3, 0, 4.6 + 2.5), "Ø5.0, depth 4.7 (2x)", (-14, 12))])],
             notes=["Bores Ø5.0 for the inserts of the hinge pin (verified with the 3D printed prototype); fit to be "
                    "confirmed with the inserts.", "Threads M3 for the countersunk screws from below through the chassis plate."]),
        dict(key="pivot_block_short", folder="cad/generic_parts/pivot_block", step="pivot_block_short_T410R.step",
             stem="pivot_block_short_T410R", title="Pivot block, short (End B inner, End A inner and outer)",
             dims=[("F", (-20.7, 0, 4.6), (20.7, 0, 4.6), "h", "below", None), ("T", (-14.56, 0, 0), (14.56, 0, 0), "h", "below", None)],
             number="PB-S", material="To be defined (e.g. 7075-T6)", quantity="3", tol=GENERAL_CNC,
             edges=EDGES_BREAK, status="verified",
             sections=[dict(label="B", point=(0, 0, 0), d=(0, -1, 0), x=(1, 0, 0), title="Section B-B (axes of the bores)",
                            callouts=[((-20.7, 0, 4.6 + 2.5), "Ø5.0, depth 4.7 (2x)", (-14, 12))])],
             notes=["Bores Ø5.0 for the inserts of the hinge pin (verified with the 3D printed prototype); fit to be "
                    "confirmed with the inserts.", "Threads M3 for the countersunk screws from below through the chassis plate."]),
        dict(key="motor_mount", folder="cad/generic_parts/motor_mount", step="motor_mount_T410R.step", stem="motor_mount_T410R",
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
        dict(key="motor_mount_cap", folder="cad/generic_parts/motor_mount", step="motor_mount_cap_T410R.step",
             stem="motor_mount_cap_T410R", title="Cap of the motor mount", number="MM-C", material="EN AW-7075-T6",
             density=2.81, density_txt="7075", quantity="1", tol=GENERAL_CNC, edges=EDGES_BREAK, status="verified (test print)",
             notes=["Notch 7.0 wide and 4.3 deep across the top face; thread M3 in its bottom for the set screw M3x3 that "
                    "presses on the outer ring of the bearing in the motor mount (part MM).",
                    "Through holes Ø3.2 for the 2 screws M3x18 from the top brace into the motor mount."]),
        c_hub(1),
        c_hub(-1),
        dict(key="steering_knuckle", folder="cad/generic_parts/front_corner", step="steering_knuckle_end_a.step",
             stem="steering_knuckle_end_a", title="Front steering knuckle (same part on both sides)", number="SK",
             frame=(Rk, Jk), material="To be defined (original part: plastic)", quantity="2 (the left one turned upside down)",
             tol=GENERAL_CNC, edges=EDGES_BREAK, status="verified (3D print)",
             frame_note=f"Drawing frame: kingpin frame, origin O in the centre of the outer CVD joint (kingpin axis at the "
                        f"height of the axle), x along the axle (toward the wheel), z along the kingpin axis; the STEP file is "
                        f"in the assembly position (caster {rgp['caster']:g} deg): O = ({Jk[0]:.2f}, {Jk[1]:.3f}, {Jk[2]:.2f}).",
             sections=[dict(label="B", point=(0, 0, 0), d=(0, -1, 0), x=(1, 0, 0), title="Section B-B (axle and kingpin axis)",
                            callouts=[((4.0, 0, 5.0), "Ø10 K7 (2x), bearings 5x10x4", (10, 18)),
                                      ((8.4, 0, 4.0), "lip Ø8.0", (12, 9)),
                                      ((2.0, 0, -6.2), "entry bore Ø12.4", (12, -10))])],
             notes=["The knuckle is symmetric to the plane through the axle square to the kingpin axis: the same part is "
                    "used on both sides (drawn: right side; on the left side it is turned upside down).",
                    "Bearing seats Ø10 for 2 bearings 5x10x4, pressed in from both ends against the lip: Ø10 K7 (proposal; "
                    "original part 9.98).", "Kingpin bores Ø2.7 in the bosses: thread formed by the set screws M3 (as the "
                    "original part).", "Threads M3 in the steering arm for the ball stud of the steering link."]),
        dict(key="front_splitter", folder="cad/speedrun_parts/front_splitter", step="front_splitter_one_piece_end_a.step",
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
        dict(key="dual_motor_mount", folder="cad/studies/dual_motor", step="dual_motor_mount_study.step",
             stem="dual_motor_mount_study", title="Dual motor mount (study)", number="DM-M", material="EN AW-7075-T6",
             density=2.81, density_txt="7075", quantity="1", tol=GENERAL_CNC, edges=EDGES_BREAK,
             status="study, not part of the build",
             view_callouts=[("F", (0.0, 0.0, 17.2 - 5.3), "U-notch 10.6 (bearing 5x10x4)", (2, 46.2)),
                            ("F", (23.8, 0.0, 17.2 + 6.5), "long holes 13.0 (motor shafts, 2x)", (16, 31.0)),
                            ("F", (25.0, 0.0, 28.4 + 1.6), "long holes 3.2 (motor screws, 4x)", (44, 10.5))],
             notes=["Study (not part of the build): the verified motor mount (drawing RC-SR-MM) with the tall part "
                    "mirrored to the left side instead of the hook beside the bearing seat; frame of the motor mount "
                    "(x = 0 pinion axis, y = 0 middle of the plate, z = 0 bottom face).",
                    "U-shaped notch 10.6 wide for the bearing 5x10x4 of the rear pinion shaft, lip 1.0 wide (opening Ø8.0); "
                    "cap (drawing RC-SR-MM-C) and its 2 screws M3x18 unchanged.",
                    "Threads M3 from below for the screws through the holes H09, H10 and H37 of the chassis plate (study)."]),
        dict(key="chassis_plate_dual_motor", folder="cad/studies/dual_motor", step="chassis_plate_dual_motor_study.step",
             stem="chassis_plate_dual_motor_study", title="Chassis plate for the dual motor setup (study)", number="CP-DM",
             flat=True, rotate=True, material="EN AW-6082-T6, plate 2.0 mm", density=2.70, density_txt="6082",
             quantity="1", tol=GENERAL_CNC, edges="edges broken 0.1 to 0.2", status="study, not part of the build",
             names=chassis_names("cad/studies/dual_motor/chassis_plate_dual_motor_study_geometry.json"), label_names=True,
             end_labels=("End B (rear)", "End A (front)"),
             notes=["Study (not part of the build): the speedrun chassis plate (wide) with the longer motor window "
                    "(drawing RC-SR-CP), with the right motor window mirrored to the left side (x = -40.06 to -16.59, "
                    "y = 65.63 to 128.90, corner radius 3.0) and the new hole H37 (H09 mirrored, x = -45.33).",
                    "The holes H11, H12, H14 and H15 are closed (H12 and H15 lie in the new window, the countersinks of "
                    "H11 and H14 would open into it).",
                    "Countersinks Ø6.2 x 90 deg on the bottom face for countersunk screws M3 (ISO 10642). Hole names as "
                    "in the geometry data of the plate (study)."]),
        dict(key="wishbone_front", folder="cad/generic_parts/wishbone", step="wishbone_front_T410R.step", stem="wishbone_front_T410R",
             title="Front wishbone (used on both sides)", number="WB-F",
             dims=[("T", (0, -16.5, 0), (51.7, -16.5, 0), "h", "below", "51.70 (axis to axis)")], material="Nylon PA12 (MJF 3D print)",
             density=1.01, density_txt="PA12", quantity="2", tol="process tolerance (MJF approx. ±0.3)", edges="chamfer 0.3 (modelled)",
             status="verified",
             notes=["Bores Ø3.2 of the inner lugs (inner hinge pin 3x42) and of the outer lugs (outer hinge pin 3x26): the metal "
                    "pins are exactly Ø3.0 (owner), 0.2 clearance so that the pins slide in without force and the arm turns "
                    "freely (owner: Ø3.1 was too tight on an FDM print; original part: outer lugs Ø4.3). If an MJF part is "
                    "tight, ream the bores with a drill Ø3.1 to Ø3.2 instead of pressing the pins in.",
                    "Closed plate as high as the rails from the tube on the inner hinge pin to the outer cross bar, with 3 "
                    "lightening holes Ø3.5 of the same size (design, owner; the original part has an open notch and "
                    "X-shaped ribs there).", "Threads M3 for the ball studs of the damper (shock plate) and of the "
                    "sway bar drop link, threads M4 for the droop screws."]),
        dict(key="wishbone_rear", folder="cad/generic_parts/wishbone", step="wishbone_rear_T410R.step", stem="wishbone_rear_T410R",
             title="Rear wishbone (used on both sides)", number="WB-R",
             dims=[("T", (0, -16.5, 0), (54.3, -16.5, 0), "h", "below", "54.30 (axis to axis)")], material="Nylon PA12 (MJF 3D print)",
             density=1.01, density_txt="PA12", quantity="2", tol="process tolerance (MJF approx. ±0.3)", edges="chamfer 0.3 (modelled)",
             status="verified",
             notes=["Bores Ø3.2 of the inner lugs (inner hinge pin 3x42) and of the outer lugs (outer hinge pin 3x26): the metal "
                    "pins are exactly Ø3.0 (owner), 0.2 clearance so that the pins slide in without force and the arm turns "
                    "freely (owner: Ø3.1 was too tight on an FDM print; original part: outer lugs Ø4.3). If an MJF part is "
                    "tight, ream the bores with a drill Ø3.1 to Ø3.2 instead of pressing the pins in.",
                    "Closed plate as high as the rails from the tube on the inner hinge pin to the outer cross bar, with 4 "
                    "lightening holes Ø5.0 of the same size (design, owner; the original part has an open notch and "
                    "X-shaped ribs there).", "Threads M3 for the ball studs of the damper (shock plate) and of the "
                    "sway bar drop link, threads M4 for the droop screws."]),
        dict(key="bellcrank", folder="cad/generic_parts/steering", step="bellcrank.step", stem="bellcrank",
             title="Bellcrank (same part on both sides)", number="BC", frame=(np.column_stack([(0, 1, 0), (-1, 0, 0), (0, 0, 1)]), sf["bellcrank"]),
             material="Nylon PA12 (MJF 3D print)", density=1.01, density_txt="PA12", quantity="2 (same part on both sides)",
             tol="process tolerance (MJF approx. ±0.3)", edges="as modelled", status="measures qualified, not printed",
             frame_note=f"Drawing frame: origin O on the axis of the hub on the bottom face; x along the arms (in the car "
                        f"+x toward End A), z up. The STEP file is in the assembly position of the right bellcrank: O = "
                        f"({sf['bellcrank'][0]:.2f}, {sf['bellcrank'][1]:.2f}, {sf['bellcrank'][2]:.2f}).",
             dims=[("T", (-bc[4], 0, 0), (bc[2], 0, 0), "h", "below", f"{bc[4] + bc[2]:.2f} (2 x {bc[2]:.2f})")],
             view_callouts=[("T", (0, bs[0] / 2, bc[1] - bc[0]), f"Ø{bs[0]:.1f} (hub)", (10, 12)),
                            ("T", (bc[2] + bs[1] / 2, 0, bc[1] - bc[0]), f"R{bs[1] / 2:.2f} (2x, ends)", (8, 12))],
             max_hole_d=8.5, section_gap=16,
             hole_note=lambda h: (None if abs(h["dia"] - bs[5]) < 0.05 else "bearing seats with the lip"),
             sections=[dict(label="B", point=(0, 0, 0), d=(0, -1, 0), x=(1, 0, 0), title="Section B-B (plane of the 3 axes)",
                            axes=[((q, 0, -1.5), (q, 0, bc[1] - bc[0] + 1.5)) for q in (-bc[4], 0.0, bc[2])],
                            callouts=[((-bs[2] / 2, 0, 0.6), f"Ø{bs[2]:.1f}, 2.5 deep (2x)", (-57.5, -15.5)),
                                      ((bs[4] / 2, 0, 2.5), f"lip {bs[3]:g}, opening Ø{bs[4]:.1f}", (8, -33)),
                                      ((bc[2] - bs[5] / 2, 0, 4.25), f"Ø{bs[5]:.1f} through (2x)", (10.5, 14.25))])],
             notes=["Symmetric part: the same part on both sides and at both ends (no front and rear). One end carries the "
                    "ball of the steering link, the other end the bridge.",
                    f"Bearing seats Ø{bs[2]:.1f} for 2 bearings 5x8x2.5, pressed in from both faces against the lip ({bs[3]:g} thick, "
                    f"opening Ø{bs[4]:.1f}: contact on the outer rings only). Chamfer {bs[6]:g} x 45 deg at the entries. Check the fit "
                    "after printing (MJF approx. ±0.3); ream to Ø8.0 if the bearings do not fit.",
                    f"Plain through holes Ø{bs[5]:.1f} at both ends (owner: no hex pockets). Bridge end: button head screw M3x16 "
                    "from above through washer, brass sleeve and washer of the bridge joint, washer 3.2x7x0.5 and lock nut M3 "
                    "(DIN 985) under the arm. Ball end: button "
                    "head screw M3x10 (ISO 7380) from below that holds the ball with internal thread.",
                    "Outline: hull of the hub and the 2 ends (tangent flanks), full height. Print flat on the bottom face."]),
        dict(key="servo_mount_top_plate", folder="cad/generic_parts/servo_mount", step="servo_mount_top_plate.step",
             stem="servo_mount_top_plate", title="Servo mount: top plate", number="SM-T", flat=True, edge_view=True,
             frame=(np.eye(3), sf["plate"]), material="To be defined (e.g. EN AW-7075-T6)", quantity="1", tol=GENERAL_CNC,
             dims=[("T", (xpe, sm[3] - sm[5], 0), (xpe, sm[3], 0), "v", "right", f"{sm[5]:.2f}"),
                   ("T", (xf0, sm[3] - sm[4], 0), (xf0 + sm[2] + 2.0, sm[3] - sm[4], 0), "h", "below", f"{sm[2] + 2.0:.2f}")],
             edges="chamfers as modelled, other edges broken 0.1 to 0.2", status="verified (owner)",
             frame_note=f"Drawing frame: origin O above the hole H21 of the chassis plate (front screw of the fixed post), on the "
                        f"lower face of the top plate; axes as the chassis plate coordinates (x across the car toward the servo "
                        f"output, y toward End A). The STEP file is in the assembly position: O = ({sf['plate'][0]:.2f}, "
                        f"{sf['plate'][1]:.2f}, {sf['plate'][2]:.2f}).",
             notes=[f"Plate {sm[0]:g} thick (M5), top face {sm[1]:g} above the chassis plate (M4). Front edge straight (flush "
                    f"with the front faces of the posts); {sm[5]:g} deep over the servo and the floating post; at the fixed post the "
                    "plate reaches back to the rear face of the post (owner, manual). Outer corners chamfered 2.0 x 45 deg, inner corner of the step 3.0 x 45 deg.",
                    "Holes Ø3.2 for the 2 screws M3x6 into the fixed post; slots 3.2 wide along x for the 2 screws M3x6 into the "
                    "floating post (other servo lengths)."]),
        dict(key="servo_mount_fixed_post", folder="cad/generic_parts/servo_mount", step="servo_mount_fixed_post.step",
             stem="servo_mount_fixed_post", title="Servo mount: fixed post", number="SM-F", frame=(np.eye(3), sf["post"]),
             material="To be defined (e.g. EN AW-7075-T6)", quantity="1", tol=GENERAL_CNC, edges=EDGES_BREAK,
             status="verified (owner)",
             frame_note=f"Drawing frame: origin O in the hole H21 of the chassis plate (front screw of the post) on the top "
                        f"face of the chassis plate; axes as the chassis plate coordinates (y toward End A). The STEP file is in "
                        f"the assembly position: O = ({sf['post'][0]:.2f}, {sf['post'][1]:.2f}, {sf['post'][2]:.2f}).",
             sections=[dict(label="B", point=(xfc, 0, 0), d=(-1, 0, 0), x=(0, -1, 0), title="Section B-B (middle plane of the post)",
                            callouts=[((xfc, sm[3] - sm[4] + sm[10] + 3.0 - 2.12, sm[11] + 3.0 - 2.12), "U-notch from the top, R3.0", (54, 29)),
                                      ((xfc, sm[3] - sm[4] + sm[10] + 2.0 - 1.41, sm[12] - 2.0 + 1.41), "arch from below, R2.0", (53, -8))],
                            dims=[((xfc, sm[3], 0), (xfc, sm[3] - sm[9], 0), "h", -8, f"{sm[9]:.2f}"),
                                  ((xfc, sm[3] - sm[9], 0), (xfc, sm[3] - sm[4] + sm[10], 0), "h", -8, f"{sm[4] - sm[9] - sm[10]:.2f}"),
                                  ((xfc, sm[3] - sm[4] + sm[10], 0), (xfc, sm[3] - sm[4], 0), "h", -8, f"{sm[10]:.2f}"),
                                  ((xfc, ymid, 0), (xfc, ymid, sm[12]), "v", 0, f"{sm[12]:.2f}"),
                                  ((xfc, ymid, sm[11]), (xfc, ymid, sm[1] - sm[0]), "v", 0, f"{sm[1] - sm[0] - sm[11]:.2f}")])],
             notes=["Before printing: check the holes for the servo ears (threads M3 for the screws M3x6 of the servo ears; positions assumed: spacing 49.5 between the ears, 10 between the holes of an ear) against the servo (owner).",
                    f"Front face {sm[3]:g} ahead of H21 (M1): contact face of the servo ear. Length {sm[4]:g} (measured part: "
                    "32.0; lengthened to the rear so that the thread of H17 has 2.25 of material behind it, owner). Width "
                    f"{sm[2]:g} (M3), height up to the lower face of the top plate.",
                    "Threads M3 from below for the screws through H17 and H21 of the chassis plate (depth 5), from above for the "
                    "screws M3x6 of the top plate (depth 5), from the front for the screws M3x6 of the servo ear (depth 4).",
                    "Side view: front and rear pillar joined by a web with a U-notch from the top and an arch from below (as "
                    "the part in the manual; heights assumed)."]),
        dict(key="servo_mount_floating_post", folder="cad/generic_parts/servo_mount", step="servo_mount_floating_post.step",
             stem="servo_mount_floating_post", title="Servo mount: floating post", number="SM-L", frame=(np.eye(3), sf["post"]),
             material="To be defined (e.g. EN AW-7075-T6)", quantity="1", tol=GENERAL_CNC, edges=EDGES_BREAK,
             status="verified (owner)", section_gap=14,
             frame_note=f"Drawing frame: origin O in the hole H21 of the chassis plate on its top face (as the fixed post); "
                        f"axes as the chassis plate coordinates. The STEP file is in the assembly position: O = "
                        f"({sf['post'][0]:.2f}, {sf['post'][1]:.2f}, {sf['post'][2]:.2f}).",
             sections=[dict(label="B", point=(xlc, 0, 0), d=(-1, 0, 0), x=(0, -1, 0), title="Section B-B (middle plane of the post)",
                            callouts=[((xlc, sm[3] - sm[7] - 1.76, sm[1] - sm[0] - sm[8] - 1.76), "gusset R6.0", (26, -22))],
                            dims=[((xlc, sm[3], sp[3]), (xlc, sm[3] - sm[7], sp[3]), "h", -8, f"{sm[7]:.2f}"),
                                  ((xlc, sm[3], sp[3]), (xlc, sm[3] - sm[5] + 0.5, sm[1] - sm[0] - sm[8]), "h", -16, f"{sm[5] - 0.5:.2f}"),
                                  ((xlc, sm[3] - sm[5] + 0.5, sm[1] - sm[0] - sm[8]), (xlc, sm[3] - sm[5] + 0.5, sm[1] - sm[0]), "v", 8,
                                   f"{sm[8]:.2f}"),
                                  ((xlc, sm[3], sp[3]), (xlc, sm[3], sm[1] - sm[0]), "v", -8, f"{sm[1] - sm[0] - sp[3]:.2f}")])],
             notes=["Before printing: check the holes for the servo ears (threads M3 for the screws M3x6 of the servo ears; positions assumed: spacing 49.5 between the ears, 10 between the holes of an ear) against the servo (owner).",
                    "L bracket: the leg carries the servo ear on its front face (contact face as the fixed post), the top "
                    "flange hangs from the top plate. The lower end of the leg is 2.0 above the chassis plate (floating).",
                    "Threads M3 from above in the flange for the screws M3x6 of the top plate (through the slots), from the "
                    "front for the screws M3x6 of the servo ear (depth 4)."]),
        dict(key="steering_bridge", folder="cad/generic_parts/steering", step="steering_bridge.step", stem="steering_bridge",
             title="Steering bridge", number="SB", frame=(np.eye(3), sf["bridge"]),
             material="Nylon PA12 (MJF 3D print)", density=1.01, density_txt="PA12", quantity="1",
             tol="process tolerance (MJF approx. ±0.3)", edges="as modelled", status="measures qualified, not printed",
             frame_note=f"Drawing frame: origin O in the middle between the axes of the towers on their bottom face; x across the "
                        f"car, y toward End A, z up. The STEP file is in the assembly position: O = ({sf['bridge'][0]:.2f}, "
                        f"{sf['bridge'][1]:.2f}, {sf['bridge'][2]:.2f}).",
             max_hole_d=8.5, sheets=3,
             hole_note=lambda h: (f"brass spacer sleeve {gsl[0]:g} x {gsl[1]:g} x {gsl[2]:g} (turns in the bore), washers M3 "
                                  f"DIN 125-A below and above; screw M3x{brj[1]:g} from above" if abs(h["dia"] - gsl[7]) < 0.05 else
                                  ("grub screw M3x8, ball of the servo link with internal thread" if abs(h["dia"] - 2.5) < 0.05 else None)),
             dims=[("T", (-xb_, 0, 0), (xb_, 0, 0), "h", "below", f"{2 * xb_:.2f} (axes of the towers)")],
             sections=[dict(label="B", point=(0, 0, 0), d=(0, -1, 0), x=(1, 0, 0), title="Section B-B (plane of the tower axes)",
                            axes=[((q, 0, -1.5), (q, 0, zb_hi + 1.5)) for q in (-xb_, xb_)],
                            callouts=[((xb_ + gsl[7] / 2, 0, z_seat / 2), f"Ø{gsl[7]:.1f} through (brass sleeve Ø{gsl[0]:g})", (28, -12)),
                                      ((xb_ + bri[4] / 2, 0, zb_hi - 1.0), f"Ø{bri[4]:.1f}, access bore for the washer and the screw head", (23, 10)),
                                      ((8.0, 0, zb_lo), f"bar {bri[2]:g} x {zb_hi - zb_lo:.2f}, 1.0 above the centre driveshaft", (22, -10))],
                            dims=[((xb_, 0, 0), (xb_, 0, z_seat), "v", 0, f"{z_seat:.2f}"),
                                  ((xb_, 0, z_seat), (xb_, 0, zb_hi), "v", 0, f"{zb_hi - z_seat:.2f}")]),
                       dict(label="C", point=(0, 0, 0), d=(-1, 0, 0), x=(0, -1, 0), title="Section C-C (ball of the servo link)",
                            clip=(-bri[2] / 2 - 1.5, bri[2] / 2 + 5.0, zb_lo - 3.0, zb_hi + 1.0), scale=5.0,
                            callouts=[((0, -bri[2] / 2 - 2.0, zb_ball + 1.25), "M3, depth 5.5 (grub screw M3x8)", (18, 16))],
                            dims=[((0, bri[2] / 2, zb_lo), (0, -bri[2] / 2, zb_lo), "h", -6, f"{bri[2]:.2f}"),
                                  ((0, -bri[2] / 2, zb_lo), (0, -bri[2] / 2 - dboss, zb_lo), "h", -6, f"{dboss:.2f}"),
                                  ((0, bri[2] / 2, zb_lo), (0, bri[2] / 2, zb_hi), "v", -6, f"{zb_hi - zb_lo:.2f}"),
                                  ((0, -bri[2] / 2 - dboss, zb_lo), (0, -bri[2] / 2 - dboss, zb_ball), "v", 6, f"{zb_ball - zb_lo:.2f}")])],
             notes=["Flat bar over the centre driveshaft (1.0 above it) with round ends (towers). The towers turn on the rear arms "
                    f"of the bellcranks with generic parts as the kingpins of the C-hub (owner): washer M3 DIN 125-A ({gsl[1]:g} x "
                    f"{gsl[3]:g} x {gsl[4]:g}) on the bellcrank arm, brass spacer sleeve Ø{gsl[0]:g} x Ø{gsl[1]:g} x {gsl[2]:g} in the "
                    f"bore of the tower, washer M3 DIN 125-A in the access bore, button head screw M3x{brj[1]:g} from above, washer "
                    "and lock nut M3 under the bellcrank arm. The screw clamps washer, sleeve and washer to the arm; the tower turns "
                    f"on the sleeve and slides between the washers ({brj[0]:g} axial play).",
                    f"Bore Ø{gsl[7]:.1f} through the lower part of the towers ({z_seat:.1f} long: sleeve {gsl[2]:g} minus the axial "
                    f"play {brj[0]:g}); the sleeve turns in it. Ream if the sleeve is tight after printing (MJF approx. ±0.3).",
                    "Ball of the servo link in the middle of the rear face (toward End B): thread M3 for a grub screw M3x8, ball with "
                    "internal thread screwed onto it. The boss reaches back to the ball of the servo horn.",
                    "Print flat on the bottom face."]),
        dict(key="steering_post", folder="cad/generic_parts/steering", step="steering_post.step", stem="steering_post",
             title="Steering post", number="SP", frame=(np.eye(3), sf["steering_post"]),
             material="To be defined (e.g. EN AW-7075-T6, turned)", quantity="2", tol=GENERAL_CNC, edges=EDGES_BREAK,
             status="measures qualified, not made",
             frame_note=f"Drawing frame: origin O on the axis of the post on the top face of the chassis plate (H25); z up. "
                        f"The STEP file is in the assembly position of the right post: O = ({sf['steering_post'][0]:.2f}, "
                        f"{sf['steering_post'][1]:.2f}, {sf['steering_post'][2]:.2f}).",
             sections=[dict(label="B", point=(0, 0, 0), d=(0, -1, 0), x=(1, 0, 0), title="Section B-B (axis of the post)",
                            axes=[((0, 0, -1.5), (0, 0, pst[3] + 1.5))],
                            callouts=[((pst[2] / 2, 0, pst[3] - 2.0), f"journal Ø{pst[2]:.1f}: 2 bearings 5x8x2.5 and the lip 0.5 of the "
                                       f"bellcrank (5.50)", (48, 6)),
                                      ((1.25, 0, pst[3] - t_top), f"end of the full thread M3 (stop of the screw M3x6): {t_top:.1f} deep", (52, 2)),
                                      ((pst[4] / 2, 0, z_shoulder - 0.6), f"shank Ø{pst[4]:.1f}, shoulder under the inner ring of the lower bearing",
                                       (48, -4)),
                                      ((pst[0] / 2 / np.cos(np.pi / 6), 0, pst[1] / 2), f"hexagon {pst[0]:g} across the flats", (45, 0))],
                            dims=[((pst[0] / 2 / np.cos(np.pi / 6), 0, 0), (pst[0] / 2 / np.cos(np.pi / 6), 0, pst[1]), "v", 6, f"{pst[1]:.2f}"),
                                  ((pst[4] / 2, 0, pst[1]), (pst[4] / 2, 0, z_shoulder), "v", 6 + 5 * (pst[0] / 2 / np.cos(np.pi / 6) - pst[4] / 2),
                                   f"{z_shoulder - pst[1]:.2f}"),
                                  ((pst[2] / 2, 0, z_shoulder), (pst[2] / 2, 0, pst[3]), "v", 6 + 5 * (pst[0] / 2 / np.cos(np.pi / 6) - pst[2] / 2),
                                   f"{pst[3] - z_shoulder:.2f}")])],
             notes=[f"Height {pst[3]:g} above the top face of the chassis plate (owner, as the original part). The shoulder (Ø{pst[4]:g}) "
                    "holds the inner ring of the lower bearing of the bellcrank.",
                    f"Journal Ø{pst[2]:g} (proposal: g6 for the bearings 5x8x2.5), {pst[3] - z_shoulder:.2f} long: flush with the "
                    "bearing stack (2 bearings and the lip of the bellcrank).",
                    f"Thread M3 on top: blind thread, full thread depth {t_top:.1f} (bottoming tap), drill Ø2.5 x {t_top + 1.0:.1f}. The "
                    f"screw M3x6 with washer 3.2x6x0.5 bottoms at the end of the thread and cannot be screwed in fully: the washer "
                    f"stays {pst[5]:g} above the journal and the bearing (axial play, the bellcrank turns freely). The thread depth is "
                    f"the stop: keep it within +0/-0.1. Check after assembly: the washer turns by hand.",
                    "Thread M3 from below (depth 5) for the screw through H24/H25 of the chassis plate. Both threads are tapped "
                    "(aluminium part; the model shows the tap drill)."]),
        dict(key="battery_tray", folder="cad/speedrun_parts/battery_tray", step="battery_tray_speedrun.step", stem="battery_tray_speedrun",
             title="Speedrun battery tray", number="BT", frame=(np.column_stack([(0, 1, 0), (-1, 0, 0), (0, 0, 1)]), sf["battery_tray"]),
             material="Nylon PA12 (MJF 3D print)", density=1.01, density_txt="PA12", quantity="1",
             tol="process tolerance (MJF approx. ±0.3)", edges="as modelled", status="verified", section_gap=10,
             frame_note=f"Drawing frame: origin O in the middle between the holes H11, H12, H22 and H23 of the chassis plate on its "
                        f"top face; x along the car (+x toward End A), y toward the left side of the car, z up. The STEP file is in "
                        f"the assembly position: O = ({sf['battery_tray'][0]:.2f}, {sf['battery_tray'][1]:.2f}, {sf['battery_tray'][2]:.2f}).",
             dims=[("T", (btx(btg["py0"]), bty(btg["px1"]), 0), (btx(btg["py1"]), bty(btg["px1"]), 0), "h", "below",
                    f"{btg['py1'] - btg['py0']:.2f} (battery {btg['L']:g} + 2 x {btp['clearance']:g})"),
                   ("T", (btx(btg["ys"][0]), bty(btg["px1"]), 0), (btx(btg["ys"][1]), bty(btg["px1"]), 0), "h", "below",
                    f"{btg['ys'][1] - btg['ys'][0]:.2f} (straps)"),
                   ("T", (btx(btg["py1"]), bty(btg["px1"]), 0), (btx(btg["py1"]), bty(btg["px0"]), 0), "v", "right",
                    f"{btg['px1'] - btg['px0']:.2f} (battery {btg['W']:g} + 2 x {btp['clearance']:g})")],
             hole_note=lambda h: "countersunk screw M3x6 from below through the chassis plate (4.0 of thread)",
             sections=[dict(label="B", point=(bt_rs, 0, 0), d=(-1, 0, 0), x=(0, -1, 0), title="Section B-B (rear strap, inner side)",
                            clip=(-bty(btg["x_in"]) - 13.0, -bty(btg["x_in"]) + 13.0, -1.5, 13.5), scale=5.0,
                            callouts=[((bt_rs, bt_si1 - 0.4, btp["floor_t"] - 0.4), "chamfer 0.8 x 45 deg", (6, 18)),
                                      ((bt_rs, bty(btg["x_in"]) + 9.0, btg["cd"] / 2), f"channel 24 wide, {btg['cd']:g} deep under the floor", (12, 34))],
                            dims=[((bt_rs, bt_si0, 0), (bt_rs, bt_si1, 0), "h", -6, f"{btg['sx']:.2f} (slot, 24 long)"),
                                  ((bt_rs, bt_si1 + 0.75, 0), (bt_rs, bt_si1 + 0.75, btp["floor_t"]), "v", 8, f"{btp['floor_t']:.2f}"),
                                  ((bt_rs, bty(btg["x_in"]) + 6.0, 0), (bt_rs, bty(btg["x_in"]) + 6.0, btg["cd"]), "v", 0, f"{btg['cd']:.2f}")]),
                       dict(label="C", point=(0, bt_h12, 0), d=(0, -1, 0), x=(1, 0, 0), title="Section C-C (rear end stop, line of H12)",
                            clip=(btx(btg["ty0"]) - 2.0, btx(btg["ty0"]) + 24.0, -1.5, 14.5), scale=5.0,
                            callouts=[((btx(btg["hs"][1][1]) + 1.25, bt_h12, 3.0), "blind hole Ø2.5 x 4.5 (M3x6 from below)", (40, 10))],
                            dims=[((btx(btg["ty0"]), bt_h12, btp["floor_t"] + btp["stop_h"]), (btx(btg["py0"]), bt_h12, btp["floor_t"] + btp["stop_h"]),
                                   "h", 6, f"{btg['py0'] - btg['ty0']:.2f}"),
                                  ((btx(btg["py0"]), bt_h12, btp["floor_t"]), (btx(btg["py0"]), bt_h12, btp["floor_t"] + btp["stop_h"]), "v", 8,
                                   f"{btp['stop_h']:.2f}"),
                                  ((btx(btg["ty0"]), bt_h12, 0), (btx(btg["ty0"]), bt_h12, btp["floor_t"] + btp["stop_h"]), "v", -8,
                                   f"{btp['floor_t'] + btp['stop_h']:.2f}")])],
             notes=[f"Battery Absima GreenHorn V2 3S 5000 mAh hardcase ({btg['L']:g} x {btg['W']:g} x {btg['H']:g}, spec): it lies on the floor "
                    f"between the end stops and the side walls, {btp['clearance']:g} all around.",
                    "Fixing: 4 countersunk screws M3x6 from below through H11, H12, H22 and H23 of the chassis plate into the blind holes "
                    "Ø2.5 x 4.5 (thread formed by the screws or tapped M3).",
                    "Straps: 2 velcro straps 20 mm over the battery, through the slots beside it and through the channels under the floor. "
                    "Lay the straps into the channels before the tray is screwed on.",
                    "Windows in the floor: mass. Print flat on the bottom face."]),
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


def find_cutouts(solid, bb):
    """Windows and cutouts of a plate: non-circular inner contours of a section at mid-thickness (edge chamfers do not
    change them). Returns dicts with the id, the bounding box (x0, x1, y0, y1) and the smallest corner radius."""
    zm = (bb.zmin + bb.zmax) / 2
    sec = solid.intersect(cq.Solid.makeBox(bb.xlen + 20, bb.ylen + 20, 0.002, cq.Vector(bb.xmin - 10, bb.ymin - 10, zm - 0.001)))
    cuts = []
    for f in sec.Faces():
        if f.geomType() != "PLANE" or f.normalAt().z < 0.999:
            continue
        for w in f.innerWires():
            es = w.Edges()
            if len(es) == 1 and es[0].geomType() == "CIRCLE":
                continue
            b = w.BoundingBox()
            radii = [e._geomAdaptor().Circle().Radius() for e in es if e.geomType() == "CIRCLE"]
            cuts.append({"box": (b.xmin, b.xmax, b.ymin, b.ymax), "r": min(radii) if radii else None})
    cuts.sort(key=lambda c: (round(c["box"][2], 1), round(c["box"][0], 1)))
    for i, c in enumerate(cuts, 1):
        c["id"] = f"W{i}"
    return cuts


def cutout_rows(cuts):
    return [(c["id"], f"{c['box'][0]:+.2f}", f"{c['box'][1]:+.2f}", f"{c['box'][2]:+.2f}", f"{c['box'][3]:+.2f}",
             f"{c['box'][1] - c['box'][0]:.2f} x {c['box'][3] - c['box'][2]:.2f}",
             f"R{c['r']:.2f}" if c["r"] else "–", "through") for c in cuts]


def draw_cutout(ax, V, c, dims=True):
    """Label and size of a window or cutout in a view from above."""
    x0m, x1m, y0m, y1m = c["box"]
    A, B = V.P((x0m, y0m, 0)), V.P((x1m, y1m, 0))
    px0, px1, py0, py1 = min(A[0], B[0]), max(A[0], B[0]), min(A[1], B[1]), max(A[1], B[1])
    text(ax, ((px0 + px1) / 2, (py0 + py1) / 2), c["id"], va="center", fs=8, weight="bold")
    if not dims:
        return
    if px1 - px0 > 6:
        linear(ax, (px0, py0), (px1, py0), "h", py0 + 4 if py1 - py0 > 14 else py0 - 4, f"{(px1 - px0) / V.s:.2f}",
               inside=(px1 - px0) > 12, shift=0 if (px1 - px0) > 12 else 8)
    if py1 - py0 > 6:
        linear(ax, (px0, py0), (px0, py1), "v", px0 + 4 if px1 - px0 > 14 else px0 - 4, f"{(py1 - py0) / V.s:.2f}",
               inside=(py1 - py0) > 12, shift=0 if (py1 - py0) > 12 else 8, tside="r" if px1 - px0 > 14 else "l")


def in_detail(cfg, c):
    x0m, x1m, y0m, y1m = c["box"]
    return any(d["box"][0] <= x0m and x1m <= d["box"][1] and d["box"][2] <= y0m and y1m <= d["box"][3]
               for d in cfg.get("details", []))


CUT_COLS = [("Id", 10), ("x from", 18), ("x to", 18), ("y from", 18), ("y to", 18), ("Size (x by y)", 32),
            ("Corner radius", 26), ("Depth", 236)]


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
            n_above = sum(1 for d_ in cfg.get("dims", []) if d_[0] == k and d_[4] == "above")       # room for dimensions above
            ly = y1 + 14 + 9 * n_above
            text(ax, (24, ly if ly < 280 else y0 - 12), names[k], fs=TD.LABEL_FS, ha="left", weight="bold")
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
    if flat:                                               # windows and cutouts: label and size in the view
        for c in find_cutouts(solid, bb):
            draw_cutout(ax, views["T"], c, dims=not in_detail(cfg, c))
    for k, V in views.items():                             # angles of the slanted straight edges
        if k != "E":
            TD.auto_angles(ax, solid, V)
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


def draw_detail(fig, solid, rows, det, xdir, left, top, label_names, cuts=()):
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
    for c in cuts:
        if xa <= c["box"][0] and c["box"][1] <= xb and ya <= c["box"][2] and c["box"][3] <= yb:
            draw_cutout(axd, V, c)
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
            for p0, p1, axis, off, txt in it.get("dims", []):
                Q0, Q1 = V.P(p0), V.P(p1)
                k = 1 if axis == "h" else 0
                at = (min(Q0[k], Q1[k]) + off) if off < 0 else (max(Q0[k], Q1[k]) + off)
                linear(ax, Q0, Q1, axis, at, txt, tside="r" if (axis == "v" and off > 0) else "l")
            for p3, txt, off in it.get("callouts", []):
                Pf = V.P(p3)
                if it.get("labels_right"):                  # labels in a column right of the view (mirrored parts)
                    leader(ax, Pf, np.array([x1 + 10.0, Pf[1] + off[1]]), txt, ha="left")
                else:
                    leader(ax, Pf, Pf + np.asarray(off, float), txt, ha="left" if off[0] >= 0 else "right")
        else:
            x0, y0, x1, y1 = draw_detail(fig, solid, rows, it, xdir, xcur, ytop, cfg.get("label_names"),
                                         find_cutouts(solid, bb) if cfg.get("flat") else ())
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
    holes = TD.find_holes(solid, cfg.get("max_hole_d", 6.5))
    table, rows = TD.hole_rows_generic(holes, names=cfg.get("names"), use=cfg.get("hole_note"),
                                       centroid=np.array(solid.Center().toTuple()))
    has_threads = any(r[5].startswith("M") for r in table)
    secs = cfg.get("sections", [])
    dets = cfg.get("details", [])
    cuts = find_cutouts(solid, bb) if cfg.get("flat") else []
    table_h = (len(table) + 1) * 4.6 + 14 + ((len(cuts) + 1) * 4.6 + 14 if cuts else 0)
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
    n_sheets = 3 if cfg.get("sheets") == 3 or ((secs or dets) and sec_h + 30 + table_h + notes_h > 255) else 2
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
            y_table = y_low - 16 - cfg.get("section_gap", 0)
    text(ax, (24, y_table + 3), "Holes (x, y, z of the start point in the drawing frame; O: origin of the drawing frame)",
         ha="left", fs=8, weight="bold")
    y_end = TD.hole_table(ax, 24, y_table, table, cols=HOLE_COLS) if table else y_table - 6
    if cuts:
        text(ax, (24, y_end - 8), "Windows and cutouts (inner contours of the plate; x, y in the drawing frame)",
             ha="left", fs=8, weight="bold")
        y_end = TD.hole_table(ax, 24, y_end - 11, cutout_rows(cuts), cols=CUT_COLS)
    notes_block(ax, cfg, (24, min(y_end - 10, max(150.0, 14 + notes_h))), has_threads)
    pdf = f"{cfg['folder']}/{cfg['stem']}_technical_drawing.pdf"
    TD.save(figs, pdf, f"{cfg['folder']}/{cfg['stem']}_technical_drawing")
    return pdf, s, table, n_sheets


FOLDERS = {
    "cad/speedrun_parts/chassis/chassis_plate_speedrun_wide_motor10": ("Speedrun chassis plate (wide) with longer motor window: technical drawing",
                                                        "../../../readme.md#speedrun-chassis-plate-wide-with-longer-motor-window"),
    "cad/speedrun_parts/chassis/top_brace_speedrun": ("Speedrun top brace: technical drawing", "../../../readme.md#speedrun-top-brace"),
    "cad/speedrun_parts/shock_tower": ("Speedrun shock towers: technical drawings", "../../readme.md#speedrun-shock-towers"),
    "cad/generic_parts/pivot_block": ("Pivot blocks: technical drawings", "../../readme.md#pivot-blocks"),
    "cad/generic_parts/motor_mount": ("Motor mount and cap: technical drawings", "../../readme.md#centre-driveshaft-and-drive-line"),
    "cad/generic_parts/front_corner": ("Front corner: technical drawings of the C-hubs and the steering knuckle",
                                      "../../readme.md#running-gear"),
    "cad/speedrun_parts/front_splitter": ("Speedrun front splitter: technical drawing", "../../readme.md#speedrun-front-splitter"),
    "cad/generic_parts/wishbone": ("Wishbones: technical drawings", "../../readme.md#wishbones"),
    "cad/generic_parts/steering": ("Steering: technical drawings of the bellcrank, the steering bridge and the steering post",
                                  "../../readme.md#running-gear"),
    "cad/generic_parts/servo_mount": ("Servo mount: technical drawings", "../../readme.md#running-gear"),
    "cad/speedrun_parts/battery_tray": ("Speedrun battery tray: technical drawing", "../../readme.md#speedrun-battery-tray"),
}
SHEET_TEXT = {1: "views, main dimensions, labels of the holes",
              2: "sections and detail views, hole table and notes",
              3: "hole table and notes"}


# sections of a directory readme in front of the overview (heading, lines), extra rows of the file table and extra
# lines of the generation section
FOLDER_EXTRA = {
    "cad/generic_parts/front_corner": {
        "sections": [("Kingpin of the C-hub: sleeves and washers to buy", [
            "Owner (2026-11-22): the knuckle mounts to the C-hub with standard parts instead of the Carten flanged "
            "sleeves. Per kingpin a plain brass spacer sleeve and a washer M3 take the place of the flanged sleeve.",
            "",
            "**Parts to buy for the kingpins (per car: 2 C-hubs, 2 knuckles):**",
            "",
            "| Quantity per car | Part | Size | Note |",
            "|:---|:---|:---|:---|",
            "| **4** | **Brass spacer sleeve without thread** (German: Distanzhülse or Distanzrolle, Messing, for M3) "
            "| **Ø4.8 mm outside, Ø3.2 mm inside, 4.0 mm long** | 2 per C-hub (2 more of the same sleeve for the joints of the "
            "steering bridge, see the [steering readme](../steering/readme.md#bridge-joint-sleeves-and-washers-to-buy)). "
            "Length 4.0 to 4.1 mm: the sleeve stands "
            "0.1 mm proud of the C-hub; at 3.9 mm or less the screw head or the ball stud presses on the C-hub. A "
            "length of 4.0 mm was not found as a stock part in a web search (2026-11-22): RS PRO sells Ø4.8 x Ø3.2 mm "
            "in the lengths 6, 10, 20 and 25 mm (6 mm: RS 606-759); no listing was found for Conrad, Bauhaus or "
            "Hornbach (to be checked in the store). Shorten a 6 mm sleeve to 4.0 mm (see below). |",
            "| **4** | **Washer M3 DIN 125-A (ISO 7089)** | **Ø3.2 mm inside, Ø7 mm outside, 0.5 mm thick** | 2 per "
            "C-hub. Steel or stainless steel; no plastic washers (other thickness). Standard part at DIY stores and "
            "Conrad. |",
            "| 2 | Socket head screw M3x8 DIN 912 (ISO 4762) | M3 x 8 mm | Bottom kingpin, 1 per C-hub. Not M3x10: "
            "it reaches into the entry bore of the knuckle. |",
            "| 2 | Ball stud 4.8x9 of the camber link | Ball Ø4.8 mm, thread M3 | Top kingpin, 1 per C-hub (as the "
            "original part). |",
            "",
            "Shortening a 6 mm sleeve to 4.0 mm: file or grind one end face flat and square to the axis, deburr the "
            "bore and the outer edge, check the length with a caliper (4.0 to 4.1 mm).",
            "",
            "![Kingpin of the front C-hub: section through the kingpin axis with the brass spacer sleeves and the "
            "washers](kingpin_sleeves_and_washers.png)",
            "",
            "How it works:",
            "* The Carten sleeve has a shank and a flange in one piece: the shank turns in the bore of the C-hub, the "
            "flange runs on the arm of the C-hub.",
            "* Here the washer takes the place of the flange: the washer lies on the boss of the knuckle, the sleeve "
            "lies on the washer and passes through the bore of the C-hub.",
            "* The screw M3x8 (bottom) and the ball stud (top) are screwed into the bores 2.7 mm of the knuckle bosses "
            "(thread formed by the screw) and clamp sleeve and washer to the boss. Knuckle, washer, sleeve and screw "
            "turn together as one unit.",
            "* Radial bearing: the sleeve Ø4.8 mm turns in the bore Ø4.9 mm of the C-hub. Axial bearing: the washer "
            "slides on the face of the C-hub arm toward the boss.",
            "* Gap between the boss and the C-hub: 0.55 mm = washer 0.5 mm + play 0.05 mm. The C-hub has no "
            "counterbores.",
            "* The sleeves stand 0.1 mm proud of the top face and of the bottom face of the C-hub: the screw head and "
            "the ball stud bear only on the sleeve, the knuckle moves freely.",
            "",
            "Assembly:",
            "1. Put a washer on each boss of the knuckle (a little grease holds it).",
            "2. Slide the knuckle with the washers into the C-hub from the wheel side.",
            "3. Insert the sleeves into the bores of the C-hub from above and from below, onto the washers.",
            "4. Screw in the ball stud (top) and the screw M3x8 (bottom). The knuckle must turn freely; if it does not, "
            "check the length of the sleeves and ream the bore Ø4.9 mm.",
            "5. Press in the bearings and insert the axle."])],
        "files": ["| `kingpin_sleeves_and_washers.png` | Explanation picture of the kingpin: section through the kingpin "
                  "axis with the sleeves and the washers to buy |"],
        "generate": ["", "The explanation picture of the kingpin is generated from the assembly STEP file (after "
                     "`scripts/cad/generate_speedrun_assembly.py`):", "", "```bash",
                     "python scripts/cad/generate_kingpin_stack_drawing.py", "```"],
    },
    "cad/generic_parts/steering": {
        "sections": [("Bridge joint: sleeves and washers to buy", [
            "Owner (2026-11-22): the steering bridge turns on the rear arms of the bellcranks with the same generic parts as "
            "the kingpins of the C-hub ([front corner](../front_corner/readme.md#kingpin-of-the-c-hub-sleeves-and-washers-to-buy)) "
            "instead of the flanged bearings MF63ZZ. The bellcranks keep their ball bearings 5x8x2.5 on the steering posts. "
            "The geometry of the steering is unchanged: only the towers of the bridge get a bore Ø4.9 instead of the bearing "
            "seats and reach 0.4 mm lower (onto the washer on the bellcrank arm).",
            "",
            "**Parts to buy for the 2 bridge joints (per car):**",
            "",
            "| Quantity per car | Part | Size | Note |",
            "|:---|:---|:---|:---|",
            "| **2** | **Brass spacer sleeve without thread** (German: Distanzhülse or Distanzrolle, Messing, for M3) "
            "| **Ø4.8 mm outside, Ø3.2 mm inside, 4.0 mm long** | 1 per joint; the same sleeve as at the C-hub. Length 4.0 to "
            "4.1 mm: at 3.9 mm or less the upper washer presses on the tower. 4.0 mm is not a stock length (web search, "
            "2026-11-22): shorten a 6 mm sleeve (RS PRO, RS 606-759) as described for the C-hub. |",
            "| **6** | **Washer M3 DIN 125-A (ISO 7089)** | **Ø3.2 mm inside, Ø7 mm outside, 0.5 mm thick** | 3 per joint: "
            "on the bellcrank arm, in the access bore of the tower, under the bellcrank arm. Steel or stainless steel. |",
            "| 2 | Button head screw M3x16 ISO 7380 | M3 x 16 mm | 1 per joint, from above (before: M3x18). |",
            "| 2 | Lock nut M3 DIN 985 | M3 | 1 per joint, under the bellcrank arm (as before). |",
            "",
            "No longer needed: 4 flanged bearings MF63ZZ, 4 shims 3x5x0.3, 2 screws M3x18.",
            "",
            "![Joint of the steering bridge on the bellcrank arm: section with the brass spacer sleeve and the washers]"
            "(bridge_joint_sleeves_and_washers.png)",
            "",
            "How it works:",
            "* The screw M3x16 from above, with a washer and the lock nut under the arm, clamps washer, sleeve and washer to "
            "the rear arm of the bellcrank.",
            "* Radial bearing: the tower of the bridge turns on the sleeve Ø4.8 mm in its bore Ø4.9 mm. Axial bearing: the "
            "tower slides between the lower washer (on the bellcrank arm) and the upper washer (in the access bore Ø8 mm), "
            "with 0.1 mm axial play.",
            "* The upper washer and the screw head lie in the access bore, below the top face of the bridge.",
            "",
            "Assembly (per joint):",
            "1. Put a washer on the rear arm of the bellcrank, over the hole.",
            "2. Set the tower of the bridge on the washer.",
            "3. Insert the sleeve into the bore of the tower from above, onto the washer.",
            "4. Put a washer into the access bore onto the sleeve and insert the screw M3x16 from above through washer, "
            "sleeve, washer and the bellcrank arm.",
            "5. Washer and lock nut under the arm, tighten. The bridge must turn freely on both bellcranks; if it does not, "
            "check the length of the sleeves and ream the bore Ø4.9 mm."])],
        "files": ["| `bridge_joint_sleeves_and_washers.png` | Explanation picture of the bridge joint: section with the sleeve "
                  "and the washers to buy |"],
        "generate": ["", "The explanation picture of the bridge joint is generated from the assembly STEP file (after "
                     "`scripts/cad/generate_speedrun_assembly.py`):", "", "```bash",
                     "python scripts/cad/generate_bridge_joint_drawing.py", "```"],
    },
}


def anchor(title):
    s = "".join(c for c in title.lower() if c.isalnum() or c in " -_")
    return s.replace(" ", "-")


def write_readmes(results):
    """readme.md per directory: the sheets of each part, generated from the part definitions."""
    for folder, (title, link) in FOLDERS.items():
        items = [(cfg, r) for cfg, r in results if cfg["folder"] == folder]
        if not items:
            continue
        ext = FOLDER_EXTRA.get(folder, {})
        lines = [f"# {title}", "", "## Table of contents"]
        lines += [f"* [{h}](#{anchor(h)})" for h, _ in ext.get("sections", [])]
        lines += ["* [Overview](#overview)"]
        lines += [f"* [{cfg['title']}](#{anchor(cfg['title'])})" for cfg, _ in items]
        lines += ["* [Files](#files)", "* [Generating the drawings](#generating-the-drawings)"]
        for h, body in ext.get("sections", []):
            lines += ["", f"## {h}"] + body
        lines += ["", "## Overview",
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
        lines += ext.get("files", [])
        lines += ["", "## Generating the drawings",
                  "The drawings are generated from the STEP files (from the root directory of the repository; packages "
                  "cadquery and matplotlib). After a change of a part, its generator runs first, then:", "", "```bash",
                  "python scripts/cad/generate_technical_drawings.py", "```", "",
                  "The option `--part` generates the drawings of the given parts (keys separated by commas: " +
                  ", ".join(f"`{cfg['key']}`" for cfg, _ in items) + "), the option `--date` sets the date in the title block."]
        lines += ext.get("generate", [])
        with open(f"{folder}/readme.md", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Technical drawings of the verified parts, the wishbones and the C-hub.")
    parser.add_argument("--part", help="keys of the parts, separated by commas (default: all)")
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    args = parser.parse_args()
    keys = set(args.part.split(",")) if args.part else None
    cfgs = parts()
    results = []
    for cfg in cfgs:
        if keys and cfg["key"] not in keys:
            continue
        res = draw_part(cfg, args.date)
        results.append((cfg, res))
        print(f"{cfg['key']}: scale {scale_text(res[1])}, {len(res[2])} holes, {res[3]} sheets -> {res[0]}")
    done = {cfg["key"] for cfg, _ in results}               # readme of a directory only if all of its parts are drawn
    complete = [(cfg, r) for cfg, r in results if all(c["key"] in done for c in cfgs if c["folder"] == cfg["folder"])]
    write_readmes(complete)
    print("wrote the readme files of the directories:", sorted({cfg["folder"] for cfg, _ in complete}))


if __name__ == "__main__":
    main()
