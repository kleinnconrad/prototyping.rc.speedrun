"""Assembly drawing of the speedrun chassis: views and main dimensions (one sheet A3, first angle projection, 1:2).

The views are projected from the assembly STEP file with hidden line removal. All dimensions are read from the model:
* overall length, width and height: extreme points of all parts
* track: outer face to outer face of the hex hubs (planar face of the hex hub square to the axle axis)
* wheelbase: between the axle axes at the outer faces of the hex hubs
* overhangs: from the axle axes to the ends of the car
* axle heights and the height of the front shock tower: from the bottom face of the chassis plate (z = 0)
* width of the chassis plate and of the front splitter
* caster: angle of the front kingpin axis (axis of the kingpin screws) to the vertical in the side view; distance of
  the kingpin axes at the height of the axle
* toe and camber: angles of the axle axes

Views: side view from the left side of the car (-x, End A left), top view below it, view from End A (front) right of
it (first angle). The wheels are not modelled: the side view shows the tyres as phantom lines (wheel radius and wheel
centre plane from the parameter file of the running gear) and the ground, from which the ride height is measured.

Usage (from the root directory of the repository, after generate_speedrun_assembly.py):
    python scripts/cad/generate_assembly_drawing.py [--date YYYY-MM-DD]

Outputs (directory cad/assembly): speedrun_chassis_T410R_technical_drawing.pdf, the sheet as PNG and readme.md.

Requires the packages cadquery and matplotlib.
"""
import argparse
import datetime
import json
import os
import sys
import textwrap

import numpy as np
import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import technical_drawing as TD  # noqa: E402
from technical_drawing import View, text, linear, centre_line, centre_mark, view_label  # noqa: E402

FOLDER = "cad/assembly"
STEM = "speedrun_chassis_T410R"
STEP = f"{FOLDER}/{STEM}.step"
PARAMS = "cad/running_gear/running_gear_parameters.json"
NUMBER = "AS"
SCALE = 0.5
MEASURED_TRACK = 173.7          # outer face to outer face of the hex hubs, front and rear (owner, original car)
ENDS = {"A": "front", "B": "rear"}
SIDES = ("right", "left")


# ------------------------------------------------------------------ model
def read_named_solids(path):
    """Parts of the assembly STEP file: list of (name, shape)."""
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TDocStd import TDocStd_Document
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from OCP.TDF import TDF_LabelSequence
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.ReadFile(path)
    reader.Transfer(doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    labels = TDF_LabelSequence()
    tool.GetFreeShapes(labels)
    out = []

    def walk(lab):
        if tool.IsAssembly_s(lab):
            comps = TDF_LabelSequence()
            tool.GetComponents_s(lab, comps)
            for i in range(1, comps.Length() + 1):
                walk(comps.Value(i))
            return
        name = TDataStd_Name()
        nm = name.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), name) else ""
        out.append((nm, cq.Shape.cast(tool.GetShape_s(lab))))
    for i in range(1, labels.Length() + 1):
        walk(labels.Value(i))
    return out


def bbox(shape):
    """Exact bounding box (xmin, ymin, zmin, xmax, ymax, zmax), without the tolerance gap of the mesh box."""
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped, b, False, False)
    return np.array(b.Get())


def part(parts, start, end, side):
    hits = [s for n, s in parts if n.startswith(start) and n.endswith(f"End_{end}_{side}")]
    if len(hits) != 1:
        raise SystemExit(f"{start} End {end} {side}: {len(hits)} parts found")
    return hits[0]


def cylinder_axis(shape):
    """Axis (point, unit direction) of the largest cylindrical face of a part (axle, kingpin screw)."""
    best = None
    for f in shape.Faces():
        s = BRepAdaptor_Surface(f.wrapped)
        if s.GetType() == GeomAbs_Cylinder and (best is None or f.Area() > best[0]):
            ax = s.Cylinder().Axis()
            p, d = ax.Location(), ax.Direction()
            best = (f.Area(), np.array([p.X(), p.Y(), p.Z()]), np.array([d.X(), d.Y(), d.Z()]))
    return best[1], best[2] / np.linalg.norm(best[2])


def hub_face_point(hub, axle):
    """Point of the axle axis on the outer face of the hex hub (planar face square to the axis, farthest out in x)."""
    p0, d = cylinder_axis(axle)
    faces = []
    for f in hub.Faces():
        s = BRepAdaptor_Surface(f.wrapped)
        if s.GetType() != GeomAbs_Plane:
            continue
        n = s.Plane().Axis().Direction()
        n = np.array([n.X(), n.Y(), n.Z()])
        if abs(n @ d) > 0.999:
            c = np.array(f.Center().toTuple())
            faces.append((abs(c[0]), c, n))
    _, c, n = max(faces, key=lambda t: t[0])
    t = ((c - p0) @ n) / (d @ n)
    return p0 + t * d


def label_of(name):
    """Readable name of a part of the STEP file (without the group prefix and the side)."""
    nm = name.replace("running_gear_", "").replace("speedrun_", "").replace("_one-piece", "")
    for s in ("_right", "_left", "_End_A", "_End_B"):
        nm = nm.removesuffix(s)
    return nm.replace("_", " ")


def model_values(parts):
    """Main dimensions and their reference points (chassis plate coordinates)."""
    boxes = [(n, bbox(s)) for n, s in parts]
    lo = np.min([b[:3] for _, b in boxes], axis=0)
    hi = np.max([b[3:] for _, b in boxes], axis=0)

    def at(k, v):
        return sorted({label_of(n) for n, b in boxes if abs(b[k] - v) < 0.01})
    def named(prefix):
        return next(s for n, s in parts if n.startswith(prefix))
    H = {e: {s: hub_face_point(part(parts, "running_gear_hex_hub", e, s),
                               part(parts, "running_gear_axle_with_joint_cup", e, s)) for s in SIDES} for e in ENDS}
    out = {}                                                 # axle axes, unit direction toward the outside of the car
    for e in ENDS:
        out[e] = {}
        for s in SIDES:
            d = cylinder_axis(part(parts, "running_gear_axle_with_joint_cup", e, s))[1]
            out[e][s] = d * np.sign(d[0] * H[e][s][0])
    K, kdir = {}, None                                       # front kingpin axes: point at the height of the axle
    for s in SIDES:
        p0, d = cylinder_axis(part(parts, "running_gear_kingpins", "A", s))
        kdir = d if d[2] > 0 else -d
        K[s] = p0 + (H["A"][s][2] - p0[2]) / kdir[2] * kdir
    rg = json.load(open(PARAMS, encoding="utf-8"))["parameters"]
    wheel_r = rg["wheel_r"]["value"]
    offset = H["A"]["right"][0] - rg["wheel_centre_x"]["value"]     # wheel centre plane inside the outer face of the hub
    W = {e: {s: H[e][s] - offset * out[e][s] for s in SIDES} for e in ENDS}
    tower = bbox(named("speedrun_front_shock_tower"))
    plate = bbox(named("chassis_plate"))
    splitter = bbox(named("speedrun_front_splitter"))
    ol = {e: out[e]["left"] for e in ENDS}
    v = {"lo": lo, "hi": hi, "H": H, "out": out, "K": K, "kdir": kdir, "W": W, "wheel_offset": offset,
         "tower_front": tower, "plate": plate, "splitter": splitter, "wheel_r": wheel_r,
         "length": hi[1] - lo[1], "width": hi[0] - lo[0], "height": hi[2],
         "plate_width": plate[3] - plate[0], "splitter_width": splitter[3] - splitter[0],
         "track": {e: H[e]["right"][0] - H[e]["left"][0] for e in ENDS},
         "wheelbase": H["A"]["left"][1] - H["B"]["left"][1],
         "overhang": {"A": hi[1] - H["A"]["left"][1], "B": H["B"]["left"][1] - lo[1]},
         "axle_z": {e: H[e]["left"][2] for e in ENDS},
         "ground": {e: W[e]["left"][2] - wheel_r for e in ENDS},
         "ride": {e: wheel_r - W[e]["left"][2] for e in ENDS},
         "caster": np.degrees(np.arctan2(abs(kdir[1]), kdir[2])),
         "caster_top": "top toward the rear, End B" if kdir[1] < 0 else "top toward the front, End A",
         "kingpin_dist": K["right"][0] - K["left"][0],
         "toe": {e: np.degrees(np.arctan2(ol[e][1], abs(ol[e][0]))) for e in ENDS},      # toe-in > 0 (front: +y)
         "camber": {e: -np.degrees(np.arctan2(ol[e][2], abs(ol[e][0]))) for e in ENDS},
         "ext": {"ymin": at(1, lo[1]), "ymax": at(4, hi[1]), "x": at(3, hi[0]), "zmax": at(5, hi[2]), "zmin": at(2, lo[2])}}
    return v


# ------------------------------------------------------------------ drawing
def placed(d, xdir, lo, hi, left=None, bottom=None):
    """View whose paper bounding box of the model box (lo, hi) starts at the paper point (left, bottom)."""
    v = View(d, xdir, (0, 0), scale=SCALE)
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    q = np.array([v.P(c) for c in corners])
    return View(d, xdir, (left - q[:, 0].min(), bottom - q[:, 1].min()), scale=SCALE)


def box(V, lo, hi):
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    q = np.array([V.P(c) for c in corners])
    return q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()


def draw(ax, shape, V):
    """Visible lines of the view (hidden line removal); returns all points of the visible lines (paper)."""
    vis, smooth = TD.hlr(shape, V)
    pts = []
    for line in vis:
        q = np.array([V.uv2paper(u, w) for u, w in line])
        ax.plot(q[:, 0], q[:, 1], color="k", lw=TD.THICK * 0.7, solid_capstyle="round", zorder=3)
        pts.append(q)
    for line in smooth:
        q = np.array([V.uv2paper(u, w) for u, w in line])
        ax.plot(q[:, 0], q[:, 1], color="0.45", lw=TD.THIN * 0.6, zorder=2)
    return np.concatenate(pts)


def extreme(pts, k, sense, other, tol=0.05):
    """Paper point of the visible lines at the extreme of coordinate k (sense +1: max, -1: min); among the points
    within tol of the extreme the one with the extreme of the other coordinate (other: +1 max, -1 min)."""
    e = pts[:, k].max() if sense > 0 else pts[:, k].min()
    cand = pts[np.abs(pts[:, k] - e) < tol]
    j = 1 - k
    return cand[np.argmax(cand[:, j] * other)]


def title_rows(v, n_parts, date):
    return {"title": "Speedrun Chassis",
            "subtitle": f"Assembly drawing: views and main dimensions. {STEM}.step (master geometry), {FOLDER}",
            "grid": [
                [("Drawn", TD.AUTHOR), ("Date", date), ("Drawing number", f"RC-SR-{NUMBER}, revision A")],
                [("Drawing type", "Assembly, main dimensions"), ("Parts", f"{n_parts} (assembly STEP file)"),
                 ("Scale", "1:2 (A3)")],
                [("Materials", "see the part drawings"), ("Tolerances", "see the part drawings"), ("Units", "mm")],
                [("Heights from", "bottom face of the chassis plate"),
                 ("Tyres", f"not modelled, Ø{2 * v['wheel_r']:.0f} as phantom lines"),
                 ("Projection", "first angle")],
                [("Status", "see the CAD readme"), ("Model", "STEP = master geometry"),
                 ("Ends", "End A front, End B rear")],
            ]}


def angle(a):
    return "0.0°" if abs(a) < 0.05 else f"{a:.1f}°"


def toe_text(a):
    return ("toe-in " if a >= 0.05 else ("toe-out " if a <= -0.05 else "toe ")) + angle(abs(a))


def toe_value(a):
    """Toe for a table entry (sentence case): the angle alone if it is 0, otherwise "Toe-in ..." or "Toe-out ..."."""
    s = toe_text(a)
    return angle(a) if abs(a) < 0.05 else s[0].upper() + s[1:]


def note_lines(v, n_parts):
    tr, r = v["track"], v["wheel_r"]
    diff = {e: tr[e] - MEASURED_TRACK for e in ENDS}
    if all(abs(d) < 0.05 for d in diff.values()):
        track = f"The model has the track measured by the owner on the original car ({MEASURED_TRACK:.1f} front and rear)."
    else:
        dev = ", ".join(f"{ENDS[e]} " + ("0.0" if abs(d) < 0.05 else f"{d:+.1f}") for e, d in diff.items())
        track = (f"Track measured by the owner on the original car: {MEASURED_TRACK:.1f} front and rear. Model against "
                 f"the measured track: {dev}. The change of the model is an open point (CAD readme, running gear).")
    zmin = v["lo"][2]
    lines = [
        f"The views are projected from the assembly STEP file ({n_parts} parts, hidden line removal). The STEP file is "
        "the master geometry: dimensions that are not shown are taken from the model and from the drawings of the parts.",
        "Heights from the bottom face of the chassis plate (z = 0)." +
        (f" The {', '.join(v['ext']['zmin'])} reaches {-zmin:.1f} below it." if zmin < -0.05 else ""),
        f"The wheels are not modelled. Side view: tyres Ø{2 * r:.0f} as phantom lines on the wheel centre planes "
        f"({v['wheel_offset']:.2f} inside the outer faces of the hex hubs) and the ground at the wheel radius {r:.0f} "
        f"below the axles: ride height front {v['ride']['A']:.1f}, rear {v['ride']['B']:.1f}.",
        "Track: outer face to outer face of the hex hubs. Wheelbase and overhangs: from the axle axes at the outer "
        "faces of the hex hubs.",
        f"Front: caster {angle(v['caster'])} (kingpin axis, {v['caster_top']}), kingpin axes {v['kingpin_dist']:.1f} "
        f"apart at the height of the axle, {toe_text(v['toe']['A'])}, camber {angle(v['camber']['A'])}. Rear: "
        f"{toe_text(v['toe']['B'])} on each side (axle axes in the top view), camber {angle(v['camber']['B'])}.",
        track,
        f"Overall length: from the {', '.join(v['ext']['ymin'])} (End B) to the {', '.join(v['ext']['ymax'])} "
        f"(End A). Overall width: {', '.join(v['ext']['x'])}. Overall height: top of the {', '.join(v['ext']['zmax'])}.",
        "End A: front (front splitter, steering). End B: rear (motor, spur gear).",
        "Parts, status and orders: CAD readme (speedrun chassis). Technical drawings of the parts: readme of the "
        "directory of each part.",
    ]
    return lines


def notes_block(ax, lines, x, y, width=78):
    text(ax, (x, y), "Notes", ha="left", va="top", fs=9, weight="bold")
    y -= 5.0
    for i, s in enumerate(lines, 1):
        for j, part_ in enumerate(textwrap.wrap(s, width)):
            text(ax, (x + (0 if j == 0 else 4), y), (f"{i}. " if j == 0 else "") + part_, ha="left", va="top", fs=7.0)
            y -= 3.6
        y -= 0.6
    return y


def phantom(ax, xs, ys):
    ax.plot(xs, ys, color="0.3", lw=TD.THIN, ls=(0, (9, 1.5, 1.5, 1.5, 1.5, 1.5)), zorder=4)


def draw_sheet(parts, v, date):
    lo, hi = v["lo"], v["hi"]
    comp = cq.Compound.makeCompound([s for _, s in parts])
    fig, ax = TD.sheet(title_rows(v, len(parts), date), 1, 1)
    # side view (principal view) from the left side of the car: End A left; top view below; view from End A right
    S = placed((-1, 0, 0), (0, -1, 0), lo, hi, left=40.0, bottom=221.0)
    T = placed((0, 0, 1), (0, -1, 0), lo, hi, left=40.0, bottom=99.0)
    E = placed((0, 1, 0), (-1, 0, 0), lo, hi, left=296.0, bottom=221.0)
    ps = draw(ax, comp, S)
    pt = draw(ax, comp, T)
    draw(ax, comp, E)
    bs, bt, be = box(S, lo, hi), box(T, lo, hi), box(E, lo, hi)
    H, W, K, kd = v["H"], v["W"], v["K"], v["kdir"]

    def f1(x):
        return f"{x:.1f}"

    # labels of the views
    text(ax, (bs[0], bs[3] + 27), "Side view (from the left side of the car, -x)", fs=TD.LABEL_FS, ha="left", weight="bold")
    text(ax, (bt[0], bt[3] + 5), "Top view", fs=TD.LABEL_FS, ha="left", weight="bold")
    view_label(ax, ((be[0] + be[2]) / 2, be[3] + 27), "View from End A (front, +y)")

    # side view: tyres (phantom lines) and ground, linear between the front and the rear wheel
    ya, yb = W["A"]["left"][1], W["B"]["left"][1]
    za, zb = v["ground"]["A"], v["ground"]["B"]

    def ground(y):
        return zb + (y - yb) * (za - zb) / (ya - yb)
    tt = np.linspace(0, 2 * np.pi, 160)
    for e in ENDS:
        C = S.P(W[e]["left"])
        phantom(ax, C[0] + v["wheel_r"] * SCALE * np.cos(tt), C[1] + v["wheel_r"] * SCALE * np.sin(tt))
    G0, G1 = S.P((0, hi[1], ground(hi[1]))), S.P((0, lo[1], ground(lo[1])))
    ax.plot([G0[0], G1[0]], [G0[1], G1[1]], color="k", lw=TD.THIN, zorder=4)
    text(ax, ((G0[0] + G1[0]) / 2, (G0[1] + G1[1]) / 2 - 1.2),
         f"Ground (tyres Ø{2 * v['wheel_r']:.0f} as phantom lines, not modelled)", va="top", fs=7.0)
    for k, (lab, ha) in enumerate((("End A (front)", "left"), ("End B (rear)", "right"))):
        text(ax, (bs[2 * k], min(G0[1], G1[1]) - 1.2), lab, ha=ha, va="top", fs=7.5)

    # side view: overall length (above); left: ride height and front shock tower; right: ride height, rear axle
    # and overall height; caster at the front kingpin axis
    A, B = extreme(ps, 0, -1, +1), extreme(ps, 0, +1, +1)
    linear(ax, A, B, "h", bs[3] + 9, f1(v["length"]))
    zero_a = S.P((0, hi[1], 0))
    tw = v["tower_front"]
    # short ride height dimensions: arrows outside, text below the ground (clear of the extension lines)
    linear(ax, S.P((0, ya, za)), S.P((0, ya, 0)), "v", bs[0] - 8, f1(v["ride"]["A"]), inside=False, tside="l",
           shift=-(v["ride"]["A"] * SCALE / 2 + 5.5))
    linear(ax, zero_a, S.P((0, (tw[1] + tw[4]) / 2, tw[5])), "v", bs[0] - 8, f1(tw[5]), tside="l")
    zero_b = S.P((0, v["plate"][1], 0))
    top = extreme(ps, 1, +1, +1)
    linear(ax, S.P((0, yb, zb)), zero_b, "v", bs[2] + 8, f1(v["ride"]["B"]), inside=False, tside="r",
           shift=-(v["ride"]["B"] * SCALE / 2 + 5.5))
    linear(ax, zero_b, S.P(H["B"]["left"]), "v", bs[2] + 8, f1(v["axle_z"]["B"]), tside="r")
    linear(ax, zero_b, top, "v", bs[2] + 17, f1(v["height"]), tside="r")
    for e in ENDS:
        centre_mark(ax, S.P(H[e]["left"]), 3.0)
    J = K["left"]
    PJ = S.P(J)
    u = S.P(J + 10 * kd) - PJ
    u = u / np.linalg.norm(u)
    centre_line(ax, S.P(J - 27 * kd), S.P(J + 52 * kd))
    rr = 21.0
    TD.angle_dim(ax, PJ, u, (0.0, 1.0), rr, "")
    tip = PJ + rr * u
    text(ax, (tip[0] + 2.0, tip[1]), f"{angle(v['caster'])} caster", ha="left", va="center", fs=7.8)

    # top view: front overhang, wheelbase and rear overhang (below, left side of the car), rear track and width of
    # the chassis plate (right), rear toe, centre line of the car, axle axes
    TA, TB = extreme(pt, 0, -1, -1), extreme(pt, 0, +1, -1)
    ab = bt[1] - 9
    linear(ax, TA, T.P(H["A"]["left"]), "h", ab, f1(v["overhang"]["A"]))
    linear(ax, T.P(H["A"]["left"]), T.P(H["B"]["left"]), "h", ab, f1(v["wheelbase"]))
    linear(ax, T.P(H["B"]["left"]), TB, "h", ab, f1(v["overhang"]["B"]))
    linear(ax, T.P(H["B"]["right"]), T.P(H["B"]["left"]), "v", bt[2] + 8, f1(v["track"]["B"]), tside="r")
    linear(ax, extreme(pt, 1, +1, +1), extreme(pt, 1, -1, +1), "v", bt[2] + 17,
           f"{f1(v['plate_width'])} (chassis plate)", tside="r")
    centre_line(ax, T.P((0, hi[1] + 6, 0)), T.P((0, lo[1] - 6, 0)))
    for e in ENDS:
        for s in SIDES:
            o = v["out"][e][s]
            centre_line(ax, T.P(H[e][s] - 14 * o), T.P(H[e][s] + 10 * o))
    if abs(v["toe"]["B"]) >= 0.05:
        Pf = T.P(H["B"]["left"] - 10 * v["out"]["B"]["left"])
        lab = toe_text(v["toe"]["B"])
        TD.leader(ax, Pf, (Pf[0] - 28, bt[1] - 4.0), lab[0].upper() + lab[1:], ha="right")    # below the plate edge

    # view from End A: kingpin axes and front track (above), width of the front splitter (below), front axle height
    # (left), centre line
    for s in SIDES:
        centre_line(ax, E.P((K[s][0], 0, 4.0)), E.P((K[s][0], 0, 48.0)))
    linear(ax, E.P((K["right"][0], 0, 48.0)), E.P((K["left"][0], 0, 48.0)), "h", be[3] + 9, f1(v["kingpin_dist"]))
    linear(ax, E.P(H["A"]["right"]), E.P(H["A"]["left"]), "h", be[3] + 18, f1(v["track"]["A"]))
    sp = v["splitter"]
    linear(ax, E.P((sp[3], 0, sp[2])), E.P((sp[0], 0, sp[2])), "h", be[1] - 9,
           f"{f1(v['splitter_width'])} (front splitter)")
    linear(ax, E.P((hi[0], 0, 0)), E.P(H["A"]["right"]), "v", be[0] - 8, f1(v["axle_z"]["A"]), tside="l")
    centre_line(ax, E.P((0, 0, lo[2] - 4)), E.P((0, 0, hi[2] + 4)))
    for s in SIDES:
        centre_mark(ax, E.P(H["A"][s]), 3.0)

    notes_block(ax, note_lines(v, len(parts)), 280.0, 196.0, width=86)
    return fig


# ------------------------------------------------------------------ readme
def write_readme(v, n_parts):
    def mm(x):
        return f"{x:.1f} mm"
    ride = f"ground to the bottom face of the chassis plate (wheel radius {v['wheel_r']:.0f}, wheels not modelled)"
    rows = [("Overall length", mm(v["length"]),
             f"{', '.join(v['ext']['ymin'])} (End B) to {', '.join(v['ext']['ymax'])} (End A)"),
            ("Overall width, width of the chassis plate", mm(v["width"]), ", ".join(v["ext"]["x"])),
            ("Overall height", mm(v["height"]),
             f"bottom face of the chassis plate to the top of the {', '.join(v['ext']['zmax'])}"),
            ("Wheelbase", mm(v["wheelbase"]), "axle axes at the outer faces of the hex hubs"),
            ("Front overhang", mm(v["overhang"]["A"]), f"front axle axis to the {', '.join(v['ext']['ymax'])}"),
            ("Rear overhang", mm(v["overhang"]["B"]), f"rear axle axis to the {', '.join(v['ext']['ymin'])}"),
            ("Track front (End A)", mm(v["track"]["A"]), "outer face to outer face of the hex hubs"),
            ("Track rear (End B)", mm(v["track"]["B"]), "outer face to outer face of the hex hubs"),
            ("Axle height front", mm(v["axle_z"]["A"]), "from the bottom face of the chassis plate"),
            ("Axle height rear", mm(v["axle_z"]["B"]), "from the bottom face of the chassis plate"),
            ("Ride height front", mm(v["ride"]["A"]), ride),
            ("Ride height rear", mm(v["ride"]["B"]), ride),
            ("Height of the front shock tower", mm(v["tower_front"][5]), "from the bottom face of the chassis plate"),
            ("Width of the front splitter", mm(v["splitter_width"]), "front splitter (End A)"),
            ("Distance of the front kingpin axes", mm(v["kingpin_dist"]), "at the height of the front axle"),
            ("Caster", angle(v["caster"]), f"front kingpin axis to the vertical, {v['caster_top']}"),
            ("Toe front", toe_value(v["toe"]["A"]), "axle axes in the top view"),
            ("Toe rear", toe_value(v["toe"]["B"]), "axle axes in the top view, each side"),
            ("Camber front and rear", f"{angle(v['camber']['A'])}, {angle(v['camber']['B'])}",
             "axle axes in the view from the end")]
    lines = ["# Speedrun chassis: assembly drawing", "", "## Table of contents", "* [Overview](#overview)",
             "* [Main dimensions](#main-dimensions)", "* [Sheet](#sheet)", "* [Files](#files)",
             "* [Generating the drawing](#generating-the-drawing)", "", "## Overview",
             "* Assembly drawing of the speedrun chassis with the further own parts: views and main dimensions, one sheet "
             "A3, first angle projection, scale 1:2.",
             f"* The views are projected from the assembly STEP file ({n_parts} parts, hidden line removal). All dimensions "
             "are read from the model.",
             "* Views: side view from the left side of the car (End A left), top view below it, view from End A (front) "
             "right of it.",
             "* The wheels are not modelled. The side view shows the tyres as phantom lines and the ground, from which the "
             "ride height is measured. Heights are measured from the bottom face of the chassis plate (z = 0).",
             "* Description of the assembly, parts and status: [CAD readme](../readme.md#speedrun-chassis).",
             "* This page is generated by `scripts/cad/generate_assembly_drawing.py`.", "", "## Main dimensions",
             "| Dimension | Value | Reference |", "|:---|:---|:---|"]
    lines += [f"| {a} | {b} | {c[0].upper() + c[1:]} |" for a, b, c in rows]
    lines += ["", f"Track measured by the owner on the original car: {MEASURED_TRACK:.1f} mm front and rear (outer face to "
              "outer face of the hex hubs). The change of the model to this value is an open point."
              if any(abs(v["track"][e] - MEASURED_TRACK) >= 0.05 for e in ENDS) else
              f"The model has the track measured by the owner on the original car ({MEASURED_TRACK:.1f} mm front and rear).",
              "", "## Sheet", "", f"![Speedrun chassis, assembly drawing, sheet 1]({STEM}_technical_drawing_sheet_1.png)",
              "", "## Files", "| File | Content |", "|:---|:---|",
              f"| `{STEM}_technical_drawing.pdf` | Assembly drawing, 1 sheet A3 |",
              f"| `{STEM}_technical_drawing_sheet_1.png` | The sheet as an image (150 dpi) |",
              f"| `{STEM}.step` | Assembly (master geometry), generated by `scripts/cad/generate_speedrun_assembly.py` |",
              "", "## Generating the drawing",
              "The drawing is generated from the assembly STEP file (from the root directory of the repository; packages "
              "cadquery and matplotlib). After a change of the assembly, `generate_speedrun_assembly.py` runs first, then:",
              "", "```bash", "python scripts/cad/generate_assembly_drawing.py", "```", "",
              "The option `--date` sets the date in the title block."]
    with open(f"{FOLDER}/readme.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Assembly drawing of the speedrun chassis (views and main dimensions).")
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    args = parser.parse_args()
    parts = read_named_solids(STEP)
    v = model_values(parts)
    print(f"{len(parts)} parts; length {v['length']:.2f}, width {v['width']:.2f}, height {v['height']:.2f} "
          f"(lowest point z = {v['lo'][2]:.2f}); wheelbase {v['wheelbase']:.2f}; track front {v['track']['A']:.2f}, "
          f"rear {v['track']['B']:.2f}; axle height front {v['axle_z']['A']:.2f}, rear {v['axle_z']['B']:.2f}; "
          f"front shock tower {v['tower_front'][5]:.2f}; overhang front {v['overhang']['A']:.2f}, rear "
          f"{v['overhang']['B']:.2f}; ride height front {v['ride']['A']:.2f}, rear {v['ride']['B']:.2f}; plate "
          f"{v['plate_width']:.2f}; splitter {v['splitter_width']:.2f}; caster {v['caster']:.2f} ({v['caster_top']}); "
          f"kingpin axes {v['kingpin_dist']:.2f}; toe-in front {v['toe']['A']:.2f}, rear {v['toe']['B']:.2f}; camber "
          f"front {v['camber']['A']:.2f}, rear {v['camber']['B']:.2f}; wheel offset {v['wheel_offset']:.2f}")
    for e in ENDS:
        for s in ("right", "left"):
            print(f"  outer face of the hex hub End {e} {s}: {np.round(v['H'][e][s], 2)}")
    print("  extremes:", v["ext"])
    fig = draw_sheet(parts, v, args.date)
    pdf = f"{FOLDER}/{STEM}_technical_drawing.pdf"
    TD.save([fig], pdf, f"{FOLDER}/{STEM}_technical_drawing")
    write_readme(v, len(parts))
    print("wrote", pdf, "and", f"{FOLDER}/readme.md")


if __name__ == "__main__":
    main()
