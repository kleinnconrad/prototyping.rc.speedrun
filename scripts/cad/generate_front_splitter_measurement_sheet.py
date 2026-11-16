"""Measurement sheet of the front body post mount, the body posts, the body and the front splitter (End A).

The body post mount (own design, partly based on the T410R) is modelled from photos of the original part; the
front edge of the body (ZooRacing Hellcat) is assumed. The sheet shows the dimensions that are estimates or
assumptions as letters on the current model and lists the model values next to an empty field for the measured
value.

* page 1: body post mount: top view, section through a collar (H34) and through an ear with the body post
* page 2: splitter and body: top view of the front end with the front tyres, section with the heights
* pages 3 and 4: table M1 to M16 (mount, body posts), B1 to B6 (body), S1 to S4 (splitter)

Usage (from the root directory of the repository):
    python scripts/cad/generate_front_splitter_measurement_sheet.py

Output: cad/front_splitter/front_splitter_measurement_sheet.pdf (A4).
Requires cadquery and matplotlib.
"""
import math
import os
import sys
import textwrap

import numpy as np
import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, Polygon as MPoly, Rectangle, RegularPolygon  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_front_splitter as F  # noqa: E402
from generate_measurement_sheets import A4, RED, dimh, dimv, tag  # noqa: E402
from mesh_views import draw_mesh, subdivide  # noqa: E402

OUT = "cad/front_splitter/front_splitter_measurement_sheet.pdf"
PLATE_END = 325.62                                           # front end of the chassis plate (y)
SIDE = tuple(np.array(v) for v in ((-1.0, 0, 0), (0, 1.0, 0), (0, 0, 1.0)))     # view along -x: y right, z up
COL = {"plate": (0.86, 0.87, 0.89), "mount": (0.62, 0.65, 0.7), "splitter": (0.3, 0.31, 0.33),
       "holder": (0.08, 0.08, 0.09), "post": (0.75, 0.3, 0.25)}


def tris(s, edge=0.6):
    v, idx = s.tessellate(0.02, 0.15)
    return subdivide(np.array([[q.x, q.y, q.z] for q in v])[np.array(idx)], edge)


def section(ax, solids, x, lim):
    """Thin slab of the solids at x, seen along the x axis (y to the right, z up)."""
    slab = cq.Solid.makeBox(0.3, 200, 80, cq.Vector(x - 0.15, 250, -20))
    t, col = [], []
    for s, c in solids:
        cut = s.intersect(slab)
        if cut.Volume() > 1e-4:
            t.append(tris(cut))
            col.append(np.tile(c, (len(t[-1]), 1)))
    draw_mesh(ax, np.concatenate(t), SIDE, tri_colors=np.concatenate(col), depth_cue=0.0)
    ax.set_xlim(*lim[:2])
    ax.set_ylim(*lim[2:])
    ax.set_aspect("equal")
    ax.axis("off")


def values(p):
    """Values of the model used on the drawings and in the table."""
    holes = F.plate_holes()
    P = F.mount_outline_points(p, 0.2)
    be = F.body_edge(p)
    half = np.array(p["body_front_edge"])
    return {"holes": holes, "P": P, "x_max": float(P[:, 0].max()), "y_front": float(P[np.abs(P[:, 0]) < 0.3, 1].max()),
            "ex": p["ear_holes"][0], "ey": p["ear_holes"][1], "ft": p["front_t"], "dt": p["deck_t"],
            "z_deck": F.PLATE_T + p["deck_t"], "cd": p["collar"][0], "cb": p["collar"][1],
            "zs": F.splitter_z(p), "zt": F.splitter_z(p) + p["splitter_t"], "zh": F.holder_z(p) + p["holder_plate"][0],
        "be": be, "yb": float(half[0][1]),
            "yb60": float(np.interp(60.0, half[:, 0], half[:, 1])), "over": p["splitter_overhang"],
            "rear": p["mount_rear_y"], "lip": p["mount_outline"][0][0], "post": holes["H34"]}


def rows(p, v):
    """(letter, what to measure, model value, measured value of the owner; empty: open)."""
    pd, hl, pl, pb = p["body_post"]
    ed, eh, eaf, edep = p["ear_boss"]
    d_c, c_hex = p["splitter_holes"]
    hx, hy = v["post"]
    return [
        ("M1", "Width of the mount over the ears (outer ends).", f"{2 * v['x_max']:.1f}", "79.5"),
        ("M2", "Distance between the holes of the ears (body posts), centre to centre.", f"{2 * v['ex']:.1f}", "65.6"),
        ("M3", "Distance of the ear holes ahead of the holes H34/H35 (along the car).", f"{v['ey'] - hy:.2f}", "12"),
        ("M4", "Distance from the straight rear edge to the centre of the holes H34/H35.", f"{hy - v['rear']:.2f}",
         "4"),
        ("M5", "Depth of the mount on the centre line: rear edge to the front edge.", f"{v['y_front'] - v['rear']:.2f}",
         "19.2"),
        ("M6", "Width over the side lips at the rear edge (the lips reach down beside the chassis plate).",
         f"{2 * v['lip']:.1f}", "47.7"),
        ("M7", "Height of the deck at the rear edge (read as the total height from the bottom face of the lips, with "
               "the pocket M9).", f"{F.PLATE_T + v['dt']:g} (deck {v['dt']:g} above the chassis plate)", "4.5"),
        ("M8", "Thickness of the front part outside the bosses (front edge between the ears).", f"{v['ft']:g}", "3"),
        ("M9", "Depth of the pocket (step in the bottom face). Is the bottom face in front of the plate flush with the "
               "bottom face of the chassis plate when the part is mounted?", f"{F.PLATE_T:g}: flush", "2, flush"),
        ("M10", "Width of the ramp on the top face (top view) and its form (slope or radius).",
         f"{p['ramp_w']:g}, slope (photo)", ""),
        ("M11", "Collars on H34/H35 of the original part: outer diameter, hole diameter. Own part: boss with a base "
                "that carries the splitter and a pin (this diameter) through the splitter, tapped M3 for a screw M3x6 "
                "from below and a screw M3x6 from above (owner).",
         f"pin {v['cd']:g}, base {v['cb']:g} up to {v['zs']:g}, tapped 2.5", "6.3 / 3.2"),
        ("M12", "Height of the top of the ear bosses compared with the top of the deck. Own part: the ear bosses "
                "reach up to the bottom face of the splitter (support).",
         f"{v['zs']:g} (original: deck {F.PLATE_T + v['dt']:g}, ears {eh:g})", "4.5 / 4.41"),
        ("M13", "Body posts: diameter, hexagon across flats, length of the hexagon section; how is the post held?",
         f"{pd:g} / {eaf:g} / {hl:g}; countersunk screw M3x6 from below", "5.92 / 7.06 / 8; screw M3x6 from below"),
        ("M14", "Round boss on H36 of the original part. Own part: no boss, tapped hole M3 through the deck for a "
                "countersunk screw M3x6 from below (owner).", "no boss, tapped 2.5",
         "boss only for the stock bumper; hole needed"),
        ("M15", "Bosses of the ears of the original part: height above the bottom face (diameter not measured: "
                "photo). Own part: raised to the splitter (M12).", f"{eh:g} (diameter {ed:g})", "4.41"),
        ("M16", "Hexagon recess of the ears (press fit of the body posts): depth in the original part; hole diameter "
                "at the bottom. Own part: the recess reaches from the same bottom up to the top of the raised boss.",
         f"{edep:g} (bottom at {eh - edep:.2f}) / {p['screw_hole_d']:g} with countersink", "2.1 / 3.2"),
        ("B1", "Lower front edge of the body on the centre line: distance ahead of the front end of the chassis plate "
               "(body on the posts at the planned height).", f"{v['yb'] - PLATE_END:.1f} (assumed)", ""),
        ("B2", "Lower front edge of the body 60 from the centre line: distance ahead of the front end of the plate.",
         f"{v['yb60'] - PLATE_END:.1f} (assumed)", ""),
        ("B3", "Front corners of the body: half width where the front edge turns into the side, and its distance "
               "ahead of the front end of the plate.",
         f"approx. {p['body_front_edge'][-2][0]:g} / {p['body_front_edge'][-2][1] - PLATE_END:.0f} (assumed)", ""),
        ("B4", "Height of the lower front edge of the body above the bottom face of the chassis plate. The splitter "
               f"shows below the body only if B4 is at least the top face of the splitter ({v['zt']:g}).",
         f">= {v['zt']:g} (assumed)", ""),
        ("B5", "Front wheel arches of the body: distance of their front edge ahead of the front axle and the height "
               "of their lower edge.", "not modelled", ""),
        ("B6", "Height of the body mounting holes at the front body posts above the bottom face of the chassis plate "
               "(needed length of the posts).", f"{v['zt'] + pl:g} = top of the posts (assumed)", ""),
        ("S1", "Front end of the splitter on the centre line: distance ahead of the axis through H34/H35.",
         f"{p['splitter_front_distance']:g}", "70 (owner)"),
        ("S2", "Ride height at the front for the speedruns; height of the bottom face of the splitter above the "
               f"ground = S2 + {v['zs']:g}.", f"10 -> {10 + v['zs']:g} (setup sheet 4)", ""),
        ("S3", "Droop of the front wheels: how far the wheel centre drops below the ride height when the car is "
               "lifted. The tyre check uses it.", f"{p['tyre_check'][1]:g} (assumed)", ""),
        ("S4", "Material and thickness of the splitter and of the holder plate.",
         f"carbon {p['splitter_t']:g} / carbon {p['holder_plate'][0]:g} (design)", ""),
    ]


def plan_mount(ax, p, v, geometry=None):
    """Top view of the mount (and, with geometry, the holes of the splitter as dashed lines)."""
    holes = v["holes"]
    ax.add_patch(MPoly(v["P"], closed=True, fc="#c9ccd2", ec="black", lw=0.8))
    C = F.plate_front_contour(F.plate_geometry())
    for d, ls in ((p["pocket_clearance"], "--"), (p["pocket_clearance"] + p["ramp_w"], ":")):
        q = F.offset(C, d)
        q = q[q[:, 1] > v["rear"] + 0.05]
        ax.plot(q[:, 0], q[:, 1], ls, color="#333333", lw=0.7)
    tap = p["stack_screws"][3] / 2
    for hid in ("H34", "H35"):
        x, y = holes[hid]
        ax.add_patch(Circle((x, y), v["cb"] / 2, fc="#b7bbc2", ec="black", lw=0.6))
        ax.add_patch(Circle((x, y), v["cd"] / 2, fc="#a5aab2", ec="black", lw=0.5))
        ax.add_patch(Circle((x, y), tap, fc="white", ec="black", lw=0.5))
    ax.add_patch(Circle(holes["H36"], tap, fc="white", ec="black", lw=0.5))
    ed, eh, eaf, edep = p["ear_boss"]
    for sx in (1, -1):
        c = (sx * v["ex"], v["ey"])
        ax.add_patch(Circle(c, ed / 2, fc="#b7bbc2", ec="black", lw=0.6))
        ax.add_patch(RegularPolygon(c, 6, radius=eaf / math.sqrt(3), orientation=math.pi / 6, fc="#8a8f99", ec="black",
                                    lw=0.5))
        ax.add_patch(Circle(c, p["screw_hole_d"] / 2, fc="white", ec="black", lw=0.5))


def mount_page(pdf, p, v, parts):
    named = {n: s for n, _, s in parts}
    mount, splitter = named["speedrun front body post mount End A"], named["speedrun front splitter End A"]
    holder = named["speedrun splitter holder plate End A"]
    post = named["body post End A right"]
    plate = cq.importers.importStep(F.PLATE_STEP).val()
    hx, hy = v["post"]
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Measurement sheet: front body post mount (End A)", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.945, "Speedrun part, based on the original mount of the T410R. The drawings show the current "
             "model.\nDimensions in mm, values on pages 3 and 4.", fontsize=7.5, va="top")
    # 1: top view
    ax = fig.add_axes([0.05, 0.55, 0.9, 0.36])
    plan_mount(ax, p, v)
    xm, ex, ey, rear = v["x_max"], v["ex"], v["ey"], v["rear"]
    dimh(ax, -xm, xm, 343.5, "M1", ext=[(-xm, 331.0), (xm, 331.0)])
    dimh(ax, -ex, ex, 340.5, "M2", ext=[(-ex, ey + 1.6), (ex, ey + 1.6)])
    dimv(ax, hy, ey, 42.0, "M3", ext=[(hx + 3.5, hy), (ex + 5.4, ey)], side=1)
    dimv(ax, rear, hy, -28.0, "M4", ext=[(-v["lip"], rear), (-hx - 3.5, hy)])
    dimv(ax, rear, v["y_front"], -5.0, "M5", ext=[(-0.5, v["y_front"]), (-0.5, rear)])
    dimh(ax, -v["lip"], v["lip"], 311.0, "M6", ext=[(-v["lip"], rear), (v["lip"], rear)], side=-1)
    tag(ax, (11.0, 324.8), (12.0, 329.0), "M10")
    tag(ax, (hx + 2.4, hy + 2.4), (hx + 7.5, hy + 4.5), "M11")
    x36, y36 = v["holes"]["H36"]
    tag(ax, (x36 + 1.0, y36 + 1.0), (x36 + 5.0, y36 + 5.5), "M14")
    tag(ax, (-ex - 3.8, ey + 3.6), (-ex - 9.5, ey + 7.0), "M15")
    tag(ax, (ex + 1.9, ey - 1.6), (ex + 7.5, ey - 6.5), "M16")
    ax.text(0, 306.8, "dashed: step of the pocket (front contour of the chassis plate + 0.2); dotted: foot of the ramp",
            ha="center", fontsize=7)
    ax.set_xlim(-48, 48)
    ax.set_ylim(305, 347)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("1  Top view (front of the car at the top)", fontsize=9, loc="left")
    cols = [(plate, COL["plate"]), (mount, COL["mount"]), (splitter, COL["splitter"]), (holder, COL["holder"])]
    zd, ft = v["z_deck"], v["ft"]
    # 2: section through the collar on H34
    ax = fig.add_axes([0.04, 0.25, 0.55, 0.27])
    section(ax, cols, hx, (309, 342, -3, 16))
    ys = [q for q in F.plate_front_contour(F.plate_geometry()) if q[1] > 318 and q[0] > 0]
    ys = sorted((q[0], q[1]) for q in ys)
    y_step = float(np.interp(hx, [q[0] for q in ys], [q[1] for q in ys])) + p["pocket_clearance"]
    dimv(ax, F.PLATE_T, zd, rear - 2.6, "M7", ext=[(rear, zd)])
    dimv(ax, 0, ft, y_step + p["ramp_w"] + 2.5, "M8", side=1)
    dimv(ax, 0, F.PLATE_T, y_step + 1.4, "M9", side=1)
    dimh(ax, y_step, y_step + p["ramp_w"], v["zh"] + 1.2, "M10", ext=[(y_step, zd), (y_step + p["ramp_w"], ft)])
    dimv(ax, zd, v["zs"], hy - v["cb"] / 2 - 1.0, "M11", ext=[(hy - v["cb"] / 2, v["zs"])])
    tag(ax, (hy + 13.0, v["zh"] - 0.4), (hy + 16.5, v["zh"] + 2.6), "S4")
    ax.text(310, -2.6, "chassis plate light, mount grey, splitter dark grey, holder plate black", fontsize=6.5)
    ax.set_title(f"2  Section through the collar on H34 (x = {hx:.2f}), seen from the right", fontsize=9, loc="left")
    # 3: section through the ear with the body post
    ax = fig.add_axes([0.6, 0.25, 0.37, 0.27])
    section(ax, cols + [(post, COL["post"])], ex, (322, 340, -3, 20))
    ed, eh, eaf, edep = p["ear_boss"]
    dimv(ax, 0, eh, ey + ed / 2 + 1.0, "M15", ext=[(ey + ed / 2, eh)], side=1)
    dimv(ax, eh - edep, eh, ey - ed / 2 - 0.8, "M16", ext=[(ey - eaf / 2, eh - edep), (ey - ed / 2, eh)])
    tag(ax, (ey + ed / 2 - 0.5, v["zs"] - 0.5), (ey + ed / 2 + 2.0, v["zs"] + 3.5), "M12")
    tag(ax, (ey + 1.0, v["zh"] + 3.0), (ey + 5.5, v["zh"] + 5.5), "M13")
    ax.set_title(f"3  Section through the ear (x = {ex:.2f})", fontsize=9, loc="left")
    fig.text(0.06, 0.21, "Notes", fontsize=9, fontweight="bold")
    fig.text(0.06, 0.195, "\n".join(textwrap.wrap(
        "The mount lies with its deck on the top face of the chassis plate and is screwed to it with countersunk "
        "screws M3x6 from below through H34, H35 and H36. Its pocket follows the front contour of the plate; in front"
        " of the plate the part is cranked down by the thickness of the plate. The body posts sit with a hexagon in "
        "the recesses of the raised ears (press fit), each held by a countersunk screw M3x6 from below. Stack: the "
        "splitter lies on the bases of the bosses on H34/H35 and on the ears, the pins pass through its holes; the "
        "holder plate lies on the splitter; screws M3x6 from above through the holder plate into the pins clamp the "
        "splitter (0.5 between the tips of the screws from below and from above). The outline is the photo form "
        "scaled to M1, M4, M5 and M6. The measured values of the owner are applied (pages 3 and 4).", 125)),
        fontsize=7.2, va="top", linespacing=1.4)
    pdf.savefig(fig)
    plt.close(fig)


def body_page(pdf, p, v, parts, geometry):
    rg, J, kd = F.kingpin()
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Measurement sheet: body and front splitter (End A)", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.945, "The outer form of the splitter follows the lower front edge of the body (B1 to B3), moved "
             "forward to the front end S1. Dimensions in mm, values on page 4.", fontsize=7.5)
    ax = fig.add_axes([0.04, 0.47, 0.92, 0.45])
    geom = F.plate_geometry()
    contour = []
    for prim in geom["outline"]:
        contour += [np.array(prim["start"])] if prim["type"] == "line" else F.arc_samples(prim)
    ax.add_patch(MPoly(np.array(contour), closed=True, fc="#e3e5e9", ec="#55595f", lw=0.7))
    ax.add_patch(MPoly(v["P"], closed=True, fc="#9aa0aa", ec="black", lw=0.6))
    spl = []
    for prim in geometry["outline"]:
        spl += [np.array(prim["start"])] if prim["type"] == "line" else F.arc_samples(prim, 0.3)
    ax.add_patch(MPoly(np.array(spl), closed=True, fc="#3a3d42", ec="black", lw=0.8, alpha=0.8))
    for prims in geometry["cutouts"].values():
        q = []
        for prim in prims:
            q += [np.array(prim["start"])] if prim["type"] == "line" else F.arc_samples(prim, 0.2)
        ax.add_patch(MPoly(np.array(q), closed=True, fc="white", ec="black", lw=0.5))
    for h in geometry["holes"]:
        ax.add_patch(Circle((h["x"], h["y"]), geometry["hole_d"] / 2, fc="white", ec="black", lw=0.5))
    width, droop = p["tyre_check"][:2]
    hz = J[2] - droop - v["zt"]
    half = math.sqrt(rg["wheel_r"] ** 2 - hz ** 2)
    for sx in (1, -1):
        xc = sx * rg["wheel_centre_x"]
        ax.add_patch(Rectangle((xc - width / 2, J[1] - half), width, 2 * half, fill=False, ec="#2f6db5", lw=0.8))
    ax.text(rg["wheel_centre_x"], J[1] - half - 3, "front tyre at the height\nof the splitter (straight)", ha="center",
            fontsize=6.5, color="#2f6db5", va="top")
    be, yb = v["be"], v["yb"]
    ax.plot(be[:, 0], be[:, 1], "--", color="#e8833a", lw=1.2)
    dimv(ax, PLATE_END, yb, -6.0, "B1", ext=[(-2.0, PLATE_END)])
    dimv(ax, PLATE_END, v["yb60"], 60.0, "B2", ext=[(40.0, PLATE_END)], side=1)
    xc3, yc3 = p["body_front_edge"][-2]
    tag(ax, (-xc3, yc3), (-xc3 + 12, yc3 - 10), "B3")
    tag(ax, (-rg["wheel_centre_x"], J[1] + half + 2), (-rg["wheel_centre_x"] + 16, J[1] + half + 10), "B5")
    y_ax, y_f = v["post"][1], v["post"][1] + p["splitter_front_distance"]
    dimv(ax, y_ax, y_f, 10.0, "S1", ext=[(v["post"][0], y_ax), (1.0, y_f)], side=1)
    ax.plot([-100, 100], [J[1], J[1]], color="#777777", lw=0.4, ls="-.")
    ax.text(-99, J[1] + 1, f"front axle (y = {J[1]:.1f})", fontsize=6.5, color="#555555")
    ax.text(-45, yb + 3.0, "dashed: assumed lower front edge of the body", ha="center", fontsize=7, color="#e8833a")
    ax.set_xlim(-100, 100)
    ax.set_ylim(J[1] - half - 10, y_f + 5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("1  Top view of the front end: chassis plate, mount, splitter on the mount, front tyres", fontsize=9,
                 loc="left")
    # section through the body post: heights
    ax = fig.add_axes([0.06, 0.2, 0.88, 0.24])
    named = {n: s for n, _, s in parts}
    plate = cq.importers.importStep(F.PLATE_STEP).val()
    ex, ey = v["ex"], v["ey"]
    section(ax, [(plate, COL["plate"]), (named["speedrun front body post mount End A"], COL["mount"]),
                 (named["speedrun front splitter End A"], COL["splitter"]),
                 (named["speedrun splitter holder plate End A"], COL["holder"]),
                 (named["body post End A right"], COL["post"])],
            ex, (300, 392, -13, 40))
    ax.plot([300, 392], [-10, -10], color="#6b4f2a", lw=1.0)
    ax.text(301, -12.6, "ground at the ride height of 10", fontsize=6.5, color="#6b4f2a")
    zb = v["zt"] + 4.0
    ax.plot([yb - 8, yb, yb], [zb + 6, zb, zb], "--", color="#e8833a", lw=1.2)
    ax.text(yb - 8, zb + 7, "body", fontsize=7, color="#c2410c")
    dimv(ax, 0, zb, yb + 3.5, "B4", side=1)
    ztop = v["zt"] + p["body_post"][2]
    dimv(ax, 0, ztop, ey - 6.0, "B6", ext=[(ey - 3.0, ztop)])
    dimv(ax, -10, v["zs"], 352, "S2", ext=[(350, v["zs"])], side=1)
    ax.set_title(f"2  Section through the ear and the body post (x = {ex:.2f}): heights", fontsize=9, loc="left")
    fig.text(0.06, 0.17, "Notes", fontsize=9, fontweight="bold")
    fig.text(0.06, 0.155, "\n".join(textwrap.wrap(
        "The splitter lies on the bosses of the mount, clamped by the holder plate; its front end lies S1 ahead of the "
        "axis H34-H35, in front of the lower front edge of the body. Its outer parts stay in front of the front "
        "tyres at full steering lock (tyre check of "
        "generate_front_splitter.py with the droop S3). The front edge of the body is not measured: B1 to B5 set the "
        "outline of the splitter. B4 must be at least the height of the top face of the splitter, otherwise the body "
        "hides the splitter or touches it. B6 gives the length of the body posts.", 125)), fontsize=7.2, va="top",
        linespacing=1.4)
    pdf.savefig(fig)
    plt.close(fig)


def table_page(pdf, p, v):
    all_rows = rows(p, v)
    for page, chunk in enumerate((all_rows[:16], all_rows[16:])):
        fig = plt.figure(figsize=A4)
        fig.text(0.06, 0.965, "Measurement sheet: body post mount, body and splitter, values" +
                 (" (continued)" if page else ""), fontsize=13, fontweight="bold")
        fig.text(0.06, 0.95, "Model: current value in the model and its source. Measured: caliper value of the "
                 "original part or on the car (owner);\nan empty field is still open. Dimensions in mm.", fontsize=7.5,
                 va="top")
        y = 0.912
        for x, head in ((0.05, "No."), (0.11, "What to measure"), (0.6, "Model"), (0.8, "Measured")):
            fig.text(x, y, head, fontsize=7.5, fontweight="bold", va="top")
        y -= 0.02
        for row, (no, text, val, meas) in enumerate(chunk):
            lines = textwrap.wrap(text, 72)
            vals = textwrap.wrap(val, 26)
            meas_l = textwrap.wrap(meas, 24)
            hgt = 0.0125 * max(len(lines), len(vals), len(meas_l), 2) + 0.008
            if row % 2 == 0:
                fig.add_artist(Rectangle((0.04, y - hgt + 0.004), 0.92, hgt, transform=fig.transFigure, fc="#f2f3f5",
                                         ec="none", zorder=0))
            fig.text(0.05, y, no, fontsize=8, fontweight="bold", color=RED, va="top")
            fig.text(0.11, y, "\n".join(lines), fontsize=7.2, va="top", linespacing=1.35)
            fig.text(0.6, y, "\n".join(vals), fontsize=7.2, va="top", linespacing=1.35)
            if meas:
                fig.text(0.8, y, "\n".join(meas_l), fontsize=7.2, va="top", linespacing=1.35, color="#1f5fa8")
            else:
                fig.add_artist(plt.Line2D([0.8, 0.95], [y - hgt + 0.012] * 2, transform=fig.transFigure,
                                          color="#999999", lw=0.5))
            y -= hgt
        pdf.savefig(fig)
        plt.close(fig)


def main():
    p = F.load_params(F.PARAMS)
    v = values(p)
    parts = F.parts_in_plate(p)
    geometry = F.splitter_geometry(p)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with PdfPages(OUT) as pdf:
        mount_page(pdf, p, v, parts)
        body_page(pdf, p, v, parts, geometry)
        table_page(pdf, p, v)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
