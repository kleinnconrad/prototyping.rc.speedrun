"""Study: electronics layout of the dual motor setup (picture only, not part of the build).

Adds the electronics to the assembly of the dual motor study (dual_motor_study_assembly.step):
* 2 ESCs (Hobbywing QuicRun WP 10BL120 G2, 52.8 x 39.8 x 38.2 mm, manufacturer data), one behind each motor,
  crosswise as on the car: between the end of the motor and the servo mount there are 43 mm along the car.
* 2 batteries 3S shorty hardcase (95.7 x 46.8 x 24.7 mm, for example Reedy Wolfpack 3S 3000 mAh), one on the outer
  side of each ESC, on edge: flat (46.8 mm wide) the battery does not fit beside the ESC within the chassis plate.
  Each battery feeds the ESC on its side (battery leads with an XT60 connector pair).
* Motor wires A, B, C from each ESC to its motor.
* Receiver (Konect RG4CHWP, 4 channels; size 36 x 24 x 14 mm assumed) on the top plate of the servo mount.
* Signal cables of both ESCs joined in a Y junction on the top brace, to channel 2 (throttle) of the receiver; servo
  cable to channel 1 (steering).

The wires are tubes along splines through the given points (simple bodies). The script checks the new parts for
interference with the parts of the assembly (each wire may touch the parts at its two ends) and draws the picture
dual_motor_study_electronics.png.

Usage (from the root directory of the repository, after generate_dual_motor_study.py):
    python cad/studies/dual_motor/generate_dual_motor_electronics.py

Requires the packages cadquery and matplotlib.
"""
import os
import sys
import time

import numpy as np
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath("scripts/cad"))
from generate_dual_motor_study import mesh, read_assembly, srgb, view  # noqa: E402

ASSEMBLY = os.path.join(HERE, "dual_motor_study_assembly.step")
OUT_PNG = os.path.join(HERE, "dual_motor_study_electronics.png")
PLATE_TOP = 2.0
MOTOR_X, MOTOR_Z, MOTOR_R, MOTOR_END = 31.90, 19.20, 18.0, 125.48    # motors of the dual motor study
ESC = (52.8, 39.8, 38.2)               # Hobbywing QuicRun WP 10BL120 G2: length, width, height (manufacturer)
ESC_X0, ESC_Y0 = 9.5, 129.4            # inner end (beside the top brace) and face toward the motor
BATTERY = (95.7, 46.8, 24.7)           # 3S shorty hardcase: length, width, height (Reedy Wolfpack 3S 3000 mAh)
BAT_X0, BAT_Y0 = 66.0, 100.0           # inner face (battery on edge) and end with the leads (toward End B)
XT60 = (8.0, 24.0, 15.5)               # XT60 pair, plugged: thickness (x), length (y), width (z)
XT60_X0, XT60_Y0, XT60_Z0 = 52.5, 99.0, 22.0
RECEIVER = (24.0, 36.0, 14.0)          # receiver (x, y, z), assumed
SERVO_PLATE_TOP = 29.2                 # top face of the top plate of the servo mount
RX_X0, RX_Y0 = 32.0, 172.0
PLUG = (14.0, 2.6, 7.6)                # servo plug (length along x, thickness, width)
CH_Y = {1: 200.0, 2: 194.0}            # channel 1 steering, channel 2 throttle (plugs on the inner face)
JUNCTION = (9.0, 12.0, 4.8)            # Y junction (heat shrink) on the top brace
JUNCTION_Y0, BRACE_TOP = 154.0, 36.6
COLOURS = {"esc": (0.55, 0.13, 0.13), "escfan": (0.22, 0.22, 0.24), "battery": (0.18, 0.5, 0.28),
           "xt60": (0.95, 0.78, 0.1), "receiver": (0.25, 0.55, 0.85), "plug": (0.15, 0.15, 0.16),
           "junction": (0.85, 0.85, 0.87), "motorwire": (0.95, 0.5, 0.1), "red": (0.85, 0.08, 0.08),
           "black": (0.08, 0.08, 0.09), "signal": (0.55, 0.3, 0.78), "servocable": (0.1, 0.6, 0.6)}
LABELS = {"esc": "ESC (2 x Hobbywing QuicRun WP 10BL120 G2)", "battery": "battery 3S shorty hardcase (2 x, on edge)",
          "xt60": "XT60 connector pair", "receiver": "receiver (4 channels) on the servo plate",
          "junction": "Y junction of the ESC signal cables", "motorwire": "motor wires A, B, C",
          "red": "battery lead +", "black": "battery lead -", "signal": "ESC signal cables, Y cable to channel 2",
          "servocable": "servo cable to channel 1"}


# ------------------------------------------------------------------ parts
def rbox(x0, x1, y0, y1, z0, z1, r=1.5):
    """Box with rounded vertical edges."""
    w = cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0).edges("|Z").fillet(r)
    return w.val().translate(cq.Vector((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def span(sx, a, b):
    """Interval from a to b on the side sx (+1 right, -1 left), sorted."""
    return tuple(sorted((sx * a, sx * b)))


def esc(sx):
    """ESC crosswise behind the motor: body and fan shroud on the top."""
    lx, wy, hz = ESC
    x0, x1 = span(sx, ESC_X0, ESC_X0 + lx)
    body = rbox(x0, x1, ESC_Y0, ESC_Y0 + wy, PLATE_TOP, PLATE_TOP + hz - 8.2, 2.0)
    xc, yc = (x0 + x1) / 2, ESC_Y0 + wy / 2
    fan = rbox(xc - 18, xc + 18, yc - 18, yc + 18, PLATE_TOP + hz - 8.2, PLATE_TOP + hz, 3.0)
    fan = fan.cut(cq.Solid.makeCylinder(15.0, 3.0, cq.Vector(xc, yc, PLATE_TOP + hz - 2.0)))
    return body, fan


def battery(sx):
    """Battery on edge on the outer side of the ESC."""
    lb, wb, hb = BATTERY
    x0, x1 = span(sx, BAT_X0, BAT_X0 + hb)
    return rbox(x0, x1, BAT_Y0, BAT_Y0 + lb, PLATE_TOP, PLATE_TOP + wb, 2.0)


def xt60(sx):
    t, ln, w = XT60
    x0, x1 = span(sx, XT60_X0, XT60_X0 + t)
    return rbox(x0, x1, XT60_Y0, XT60_Y0 + ln, XT60_Z0, XT60_Z0 + w, 1.0)


def tube(points, r):
    """Wire: circle of the radius r swept along a spline through the points."""
    path = cq.Wire.assembleEdges([cq.Edge.makeSpline([cq.Vector(*p) for p in points])])
    profile = cq.Wire.makeCircle(r, cq.Vector(*points[0]), path.tangentAt(0))
    s = cq.Solid.sweep(profile, [], path, makeSolid=True, isFrenet=False)
    assert s.isValid(), f"wire through {points[0]} is not valid"
    return s


def mirror_pts(points, sx):
    return [(sx * x, y, z) for x, y, z in points]


def electronics():
    """New parts: list of (name, key, solid, names of the parts the wire may touch at its ends)."""
    parts = []
    for sx, side in ((1, "right"), (-1, "left")):
        body, fan = esc(sx)
        parts += [(f"ESC {side}", "esc", body, ()), (f"fan of the ESC {side}", "escfan", fan, (f"ESC {side}",)),
                  (f"battery {side}", "battery", battery(sx), ()), (f"XT60 {side}", "xt60", xt60(sx), ())]
        motor = f"motor 3660 {side}"
        # motor wires A, B, C: from the face of the ESC toward the motor, over the gap to the top of the motor
        for k, d in enumerate((-5.0, 0.0, 5.0)):
            x = MOTOR_X + d
            zs = MOTOR_Z + np.sqrt(MOTOR_R ** 2 - d ** 2) + 1.35
            pts = [(x, ESC_Y0, 33.0), (x, 127.8, 36.5), (x, 126.6, 40.5), (x, 125.0, 42.3), (x, 122.6, 40.6),
                   (x, 121.0, zs)]
            parts.append((f"motor wire {'ABC'[k]} {side}", "motorwire", tube(mirror_pts(pts, sx), 1.3),
                          (f"ESC {side}", motor)))
        # battery leads: from the end of the battery to the XT60 pair, from the XT60 pair to the ESC
        xm = XT60_X0 + XT60[0] / 2
        for colour, xb, zl, zb, ym in (("red", 70.0, 33.5, 43.0, 94.0), ("black", 75.0, 26.0, 43.0, 88.5)):
            pts = [(xb, BAT_Y0, zb), (xb, ym + 2.5, zb), (63.0, ym, (zb + zl) / 2), (xm, ym + 1.5, zl), (xm, XT60_Y0, zl)]
            parts.append((f"battery lead {colour} {side} (battery - XT60)", colour, tube(mirror_pts(pts, sx), 1.65),
                          (f"battery {side}", f"XT60 {side}")))
            pts = [(xm, XT60_Y0 + XT60[1], zl), (xm, 126.2, zl), (xm, ESC_Y0, zl)]
            parts.append((f"battery lead {colour} {side} (XT60 - ESC)", colour, tube(mirror_pts(pts, sx), 1.65),
                          (f"XT60 {side}", f"ESC {side}")))
        # signal cable of the ESC to the Y junction on the top brace
        pts = [(ESC_X0, 160.0, 33.0), (9.3, 160.0, 38.3), (7.4, 160.0, 39.3), (JUNCTION[0] / 2, 160.0, 39.3)]
        parts.append((f"signal cable ESC {side}", "signal", tube(mirror_pts(pts, sx), 1.0),
                      (f"ESC {side}", "Y junction", f"fan of the ESC {side}")))
    zj0 = BRACE_TOP + 0.2
    parts.append(("Y junction", "junction", rbox(-JUNCTION[0] / 2, JUNCTION[0] / 2, JUNCTION_Y0, JUNCTION_Y0 + JUNCTION[1],
                                                zj0, zj0 + JUNCTION[2], 1.5), ()))
    zr = SERVO_PLATE_TOP
    parts.append(("receiver", "receiver", rbox(RX_X0, RX_X0 + RECEIVER[0], RX_Y0, RX_Y0 + RECEIVER[1], zr,
                                               zr + RECEIVER[2], 2.5), ()))
    zp = zr + 3.0 + PLUG[2] / 2
    for ch in (1, 2):
        parts.append((f"plug channel {ch}", "plug", rbox(RX_X0 - PLUG[0], RX_X0, CH_Y[ch] - PLUG[1] / 2,
                                                         CH_Y[ch] + PLUG[1] / 2, zp - PLUG[2] / 2, zp + PLUG[2] / 2, 0.4),
                      ("receiver",)))
    pts = [(0.0, JUNCTION_Y0 + JUNCTION[1], 39.2), (0.0, 171.0, 40.2), (6.0, 182.0, 39.5), (12.0, 191.0, 37.0),
           (RX_X0 - PLUG[0], CH_Y[2], zp)]
    parts.append(("Y cable to channel 2", "signal", tube(pts, 1.0), ("Y junction", "plug channel 2")))
    pts = [(55.0, 212.2, 12.0), (55.5, 215.3, 15.0), (56.0, 215.3, 27.0), (55.0, 211.5, 36.0), (40.0, 212.0, 38.5),
           (26.0, 210.0, 37.5), (21.0, 204.0, 36.2), (RX_X0 - PLUG[0], CH_Y[1], zp)]
    parts.append(("servo cable to channel 1", "servocable", tube(pts, 1.0), ("running gear servo", "plug channel 1")))
    return parts


# ------------------------------------------------------------------ picture
def project(p, basis):
    d, r, u = basis
    return float(np.dot(p, r)), float(np.dot(p, u))


def callouts(ax, basis, items, lo, hi, margin=50.0, fontsize=8):
    """Labels at the left or right margin of a view with a leader to the 3D anchor point. The labels of each side are
    spaced evenly over the height of the view, in the order of the height of their anchor points.
    items: (anchor, text, side "l" or "r")."""
    for side in ("l", "r"):
        its = [(project(np.asarray(p, float), basis), text) for p, text, s in items if s == side]
        its.sort(key=lambda q: -q[0][1])
        n = len(its)
        for k, ((x, y), text) in enumerate(its):
            yt = hi[1] - (k + 0.5) * (hi[1] - lo[1]) / n
            xt = lo[0] - 3 if side == "l" else hi[0] + 3
            ax.annotate(text, (x, y), (xt, yt), fontsize=fontsize, ha="right" if side == "l" else "left",
                        va="center", arrowprops=dict(arrowstyle="-", lw=0.6, color="#333", shrinkA=2, shrinkB=0))
            ax.plot([x], [y], "o", ms=2.5, color="#333")
    ax.set_xlim(lo[0] - margin, hi[0] + margin)


def schematic(ax):
    """Wiring diagram of the electronics."""
    from matplotlib.patches import FancyBboxPatch
    boxes = {"bat_l": (0.02, 0.70, "battery left\n3S shorty", COLOURS["battery"]),
             "esc_l": (0.30, 0.70, "ESC left", COLOURS["esc"]),
             "mot_l": (0.58, 0.70, "motor left\n3660", (0.15, 0.35, 0.55)),
             "bat_r": (0.02, 0.10, "battery right\n3S shorty", COLOURS["battery"]),
             "esc_r": (0.30, 0.10, "ESC right", COLOURS["esc"]),
             "mot_r": (0.58, 0.10, "motor right\n3660", (0.15, 0.35, 0.55)),
             "y": (0.32, 0.42, "Y junction", COLOURS["junction"]),
             "rx": (0.62, 0.42, "receiver", COLOURS["receiver"]),
             "servo": (0.84, 0.42, "servo", (0.2, 0.2, 0.22))}
    w, h = 0.16, 0.17
    centre = {}
    for k, (x, y, text, col) in boxes.items():
        ww = 0.12 if k in ("y", "servo") else w
        ax.add_patch(FancyBboxPatch((x, y), ww, h, boxstyle="round,pad=0.01", fc=col, ec="#222", lw=0.8))
        light = sum(col) / 3 > 0.55
        ax.text(x + ww / 2, y + h / 2, text, ha="center", va="center", fontsize=8.5,
                color="#111" if light else "white")
        centre[k] = (x, y, ww)

    def link(a, b, col, text="", lw=2.0, ya=0.5, yb=0.5, side_a="r", side_b="l", dy=0.0):
        xa, ya0, wa = centre[a]
        xb, yb0, wb = centre[b]
        pa = (xa + (wa if side_a == "r" else 0), ya0 + ya * h)
        pb = (xb + (wb if side_b == "r" else 0), yb0 + yb * h)
        ax.annotate("", pb, pa, arrowprops=dict(arrowstyle="-", lw=lw, color=col, connectionstyle="arc3,rad=0.0"))
        if text:
            ax.text((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2 + 0.035 + dy, text, ha="center", va="bottom", fontsize=7.5)
    for s in ("l", "r"):
        link(f"bat_{s}", f"esc_{s}", COLOURS["red"], "+ / - (XT60)", lw=2.6, ya=0.62, yb=0.62)
        link(f"bat_{s}", f"esc_{s}", COLOURS["black"], lw=2.6, ya=0.38, yb=0.38)
        for k, yy in enumerate((0.3, 0.5, 0.7)):
            link(f"esc_{s}", f"mot_{s}", COLOURS["motorwire"], "A, B, C" if k == 2 else "", lw=1.6, ya=yy, yb=yy)
    def mid(k, fx, fy):
        x, y, ww = centre[k]
        return x + fx * ww, y + fy * h
    sig, srv = COLOURS["signal"], COLOURS["servocable"]
    for a, b in ((mid("esc_l", 0.5, 0.0), mid("y", 0.5, 1.0)), (mid("esc_r", 0.5, 1.0), mid("y", 0.5, 0.0))):
        ax.plot([a[0], a[0], b[0]], [a[1], (a[1] + b[1]) / 2, b[1]], color=sig, lw=1.4)
    a, b = mid("y", 1.0, 0.5), mid("rx", 0.0, 0.5)
    ax.plot([a[0], b[0]], [a[1], b[1]], color=sig, lw=1.4)
    ax.text((a[0] + b[0]) / 2, a[1] + 0.02, "CH2 (throttle)", fontsize=7.5, ha="center", va="bottom")
    a, b = mid("servo", 0.0, 0.5), mid("rx", 1.0, 0.5)
    ax.plot([a[0], b[0]], [a[1], b[1]], color=srv, lw=1.4)
    ax.text((a[0] + b[0]) / 2, a[1] + 0.02, "CH1", fontsize=7.5, ha="center", va="bottom")
    ax.text(0.31, 0.505, "signal\ncables", fontsize=7.5, ha="right", va="center", color="#444")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


def picture(parts, new):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from mesh_views import iso_basis
    allp = parts + [(n, k, s, COLOURS[k]) for n, k, s, _ in new]
    fig = plt.figure(figsize=(16, 14))
    fig.suptitle("Study: dual motor setup with 2 ESCs, 2 batteries 3S shorty and the receiver on the servo plate "
                 "(not part of the build)", fontsize=13, y=0.985)
    # overview from End B, right side
    tris, cols = mesh(allp)
    basis = iso_basis(-62, 32)
    ax = fig.add_axes([0.0, 0.44, 0.6, 0.47])
    lo, hi = view(ax, tris, cols, basis, "Overview from End B, right side")
    callouts(ax, basis, [((-90.7, 120, 40), "battery left (on edge)", "l"),
                         ((-36, 140, 40.2), "ESC left", "l"),
                         ((-XT60_X0 - 4, 105, XT60_Z0 + XT60[2]), "XT60, battery leads", "l"),
                         ((-31.9, 125.0, 42.3), "motor wires A, B, C", "l"),
                         ((44, 196, 43.2), "receiver (servo plate)", "r"),
                         ((0, 160, 41.6), "Y junction", "r"),
                         ((48, 140, 40.2), "ESC right", "r"),
                         ((90.7, 150, 40), "battery right (on edge)", "r")], lo, hi, margin=66)
    # top view of the middle section
    top = tuple(np.asarray(v, float) for v in ((0, 0, -1), (1, 0, 0), (0, 1, 0)))
    tb, cb = mesh(allp, (-101, 40, -5, 202, 190, 90), edge=1.5, tol=0.03)
    ax = fig.add_axes([0.6, 0.44, 0.4, 0.47])
    lo, hi = view(ax, tb, cb, top, "Top view (y = 40 to 230 mm)")
    ax.text(lo[0] + 2, hi[1] - 2, "left side", fontsize=9, va="top", color="white")
    ax.text(hi[0] - 2, hi[1] - 2, "right side", fontsize=9, va="top", ha="right", color="white")
    ax.text(0, lo[1] - 1, "End B", fontsize=9, ha="center", va="top")
    ax.set_ylim(lo[1] - 7, hi[1] + 2)
    # close-up: right side seen from End B, above
    tc, cc = mesh(allp, (-12, 88, -3, 108, 134, 62), edge=1.0, tol=0.02)
    basis_c = iso_basis(-112, 38)
    ax = fig.add_axes([0.0, 0.01, 0.52, 0.41])
    lo, hi = view(ax, tc, cc, basis_c, "Close-up of the right side from End B (section at y = 88 mm): battery, XT60, "
                                       "ESC, motor wires,\nreceiver with the servo cable (CH1) and the Y cable (CH2)")
    callouts(ax, basis_c, [((XT60_X0 + 8, 99, XT60_Z0 + 12), "XT60 pair", "r"),
                           ((90.7, 105, 30), "battery right (on edge)", "r"),
                           ((70, 99, 43), "battery leads + and -", "r"),
                           ((61, 140, 40.2), "ESC right", "r"),
                           ((31.9, 125.0, 42.3), "motor wires A, B, C", "l"),
                           ((0, 160, 41.6), "Y junction", "l"),
                           ((RX_X0 - 7, CH_Y[2], 41), "plugs CH1, CH2", "l"),
                           ((44, 190, 43.2), "receiver", "r"),
                           ((56.0, 215.3, 24), "servo cable", "r")], lo, hi, margin=45)
    # wiring diagram and notes
    ax = fig.add_axes([0.52, 0.17, 0.46, 0.25])
    ax.set_title("Wiring (schematic)", fontsize=10, loc="left")
    schematic(ax)
    notes = ("Each battery feeds the ESC on its side; both ESCs get the same throttle signal from channel 2 through the "
             "Y junction.\nRemove the red wire (BEC +) of one ESC at the Y junction: 2 BEC outputs must not work in "
             "parallel.\nESC 52.8 x 39.8 x 38.2 mm (manufacturer); battery 3S shorty 95.7 x 46.8 x 24.7 mm (Reedy "
             "Wolfpack 3000 mAh); receiver size assumed.\nBattery on edge: flat (46.8 mm) it does not fit beside the "
             "ESC within the plate; on edge its top is 48.8 mm above the plate.\nNot modelled: body (190 mm wide), "
             "battery straps, switches of the ESCs, antenna; the wires are simple bodies.")
    fig.text(0.52, 0.15, notes, fontsize=8.3, va="top", linespacing=1.5)
    keys = ["esc", "battery", "xt60", "receiver", "junction", "motorwire", "red", "black", "signal", "servocable"]
    handles = [Patch(color=COLOURS[k], label=LABELS[k]) for k in keys]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.01, 0.968), fontsize=8.5, frameon=False, ncol=5)
    fig.savefig(OUT_PNG, dpi=100)
    plt.close(fig)


def main():
    t0 = time.time()
    base = read_assembly(ASSEMBLY)
    parts = []
    for nm, s, col in base:
        name = nm.replace("_", " ").rsplit(" ", 1)[0]          # name without the index of the study assembly
        parts.append((name, "base", s, srgb(col)))
    new = electronics()
    print(f"read {len(parts)} parts and built {len(new)} new parts ({time.time() - t0:.0f} s)")
    # interference: new parts with the parts of the assembly and with each other (wires may touch their end parts)
    names = [q[0] for q in parts] + [q[0] for q in new]
    solids = [q[2] for q in parts] + [q[2] for q in new]
    allowed = {q[0]: set(q[3]) for q in new}
    boxes = [s.BoundingBox() for s in solids]
    worst, n0 = 0.0, len(parts)
    for i in range(n0, len(solids)):
        for j in range(len(solids)):
            if j == i or (j >= n0 and j < i):
                continue
            if names[j] in allowed.get(names[i], ()) or names[i] in allowed.get(names[j], ()):
                continue
            a, b = boxes[i], boxes[j]
            if a.xmin > b.xmax or b.xmin > a.xmax or a.ymin > b.ymax or b.ymin > a.ymax or a.zmin > b.zmax \
                    or b.zmin > a.zmax:
                continue
            v = solids[i].intersect(solids[j]).Volume()
            if v > 1e-3:
                print(f"  interference {names[i]} / {names[j]}: {v:.3f} mm3")
            worst = max(worst, v)
    print(f"interference check of the {len(new)} new parts: largest {worst:.4f} mm3")
    by = {q[0]: q[2] for q in parts + [(n, k, s, None) for n, k, s, _ in new]}
    for a, b in (("ESC right", "running gear servo mount top plate"), ("ESC right", "speedrun top brace"),
                 ("ESC right", "motor shaft right"), ("battery right", "running gear servo mount floating post"),
                 ("battery right", "ESC right"), ("XT60 right", "motor 3660 right"), ("receiver", "speedrun top brace"),
                 ("Y junction", "speedrun top brace")):
        print(f"  clearance {a} / {b}: {by[a].distance(by[b]):.2f} mm")
    picture(parts, new)
    print(f"wrote {OUT_PNG} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
