"""Helpers for technical drawings (A3 sheets with views, sections, dimensions, hole tables and title blocks).

The views and sections are projected from the solids with hidden line removal (OCCT HLR) and drawn with
matplotlib on a sheet in millimetres (paper coordinates). Used by generate_bulkhead_technical_drawings.py and
generate_technical_drawings.py.
"""
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.path import Path  # noqa: E402
from matplotlib.patches import PathPatch, Polygon, Circle  # noqa: E402
import cadquery as cq  # noqa: E402
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape  # noqa: E402
from OCP.HLRAlgo import HLRAlgo_Projector  # noqa: E402
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir  # noqa: E402
from OCP.TopExp import TopExp_Explorer  # noqa: E402
from OCP.TopAbs import TopAbs_EDGE, TopAbs_REVERSED  # noqa: E402
from OCP.BRepTools import BRepTools_WireExplorer  # noqa: E402
from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve  # noqa: E402
from OCP.Geom import Geom_RectangularTrimmedSurface  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh_views import load_stl, subdivide, draw_mesh, iso_basis  # noqa: E402

A3 = (420.0, 297.0)                                   # sheet size (mm), landscape
SCALE = 2.0                                           # default scale of a view
THICK, THIN = 0.5 / 25.4 * 72, 0.25 / 25.4 * 72      # line widths 0.5 and 0.25 mm in points
DIM_FS, LABEL_FS, TABLE_FS = 8.5, 10.5, 7.2           # font sizes (pt)
DENSITY_7075 = 2.81                                   # g/cm3
AUTHOR = "@kleinnconrad"


# ------------------------------------------------------------------ projection
class View:
    """Orthographic view: d points from the part toward the viewer, xdir is the paper x axis; paper y = d x xdir.
    om: model point that is placed at the paper point op."""

    def __init__(self, d, xdir, op, om=(0, 0, 0), scale=SCALE):
        self.d = np.asarray(d, float)
        self.xd = np.asarray(xdir, float)
        self.yd = np.cross(self.d, self.xd)
        self.op, self.om, self.s = np.asarray(op, float), np.asarray(om, float), scale

    def P(self, p):
        q = np.asarray(p, float) - self.om
        return self.op + self.s * np.array([q @ self.xd, q @ self.yd])

    def uv2paper(self, u, v):
        return self.op + self.s * (np.array([u, v]) - np.array([self.om @ self.xd, self.om @ self.yd]))


def sample_edge(e, step=0.15):
    e = cq.Edge(e) if not isinstance(e, cq.Edge) else e
    if e.geomType() == "LINE":
        ts = [0.0, 1.0]
    else:
        n = int(min(200, max(8, e.Length() / step)))
        ts = np.linspace(0, 1, n)
    try:
        return [(p.x, p.y) for p in (e.positionAt(t) for t in ts)]
    except Exception:
        # the hidden line removal can return nearly degenerate edges on which the length parameterisation
        # fails (Standard_ConstructionError): sample them by the curve parameter instead
        c = BRepAdaptor_Curve(e.wrapped)
        u0, u1 = c.FirstParameter(), c.LastParameter()
        return [(p.X(), p.Y()) for p in (c.Value(u0 + (u1 - u0) * t) for t in ts)]


def edges_of(compound):
    out = []
    if compound is None or compound.IsNull():
        return out
    ex = TopExp_Explorer(compound, TopAbs_EDGE)
    while ex.More():
        out.append(sample_edge(ex.Current()))
        ex.Next()
    return out


def hlr(shape, view):
    """Visible edges (sharp edges and silhouettes) and smooth edges, as lists of polylines in the projector frame."""
    algo = HLRBRep_Algo()
    algo.Add(shape.wrapped)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*view.d), gp_Dir(*view.xd))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    return edges_of(h.VCompound()) + [q for q in edges_of(h.OutLineVCompound()) if not folded(q)], \
        edges_of(h.Rg1LineVCompound())


def folded(line, tol=1e-3):
    """True for a silhouette that runs out and back on itself (closed, but encloses no area): the hidden line removal
    returns such spurious outlines on some blended surfaces (for example a line 4.8 mm out of the C-hub in its top view)."""
    q = np.asarray(line, float)
    if len(q) < 3 or np.linalg.norm(q[0] - q[-1]) > tol:
        return False
    length = np.linalg.norm(np.diff(q, axis=0), axis=1).sum()
    area = 0.5 * abs(np.dot(q[:-1, 0], q[1:, 1]) - np.dot(q[1:, 0], q[:-1, 1]))
    return length > 10 * tol and area < 1e-3 * length ** 2


def draw_view(ax, shape, view):
    vis, smooth = hlr(shape, view)
    for line in vis:
        q = np.array([view.uv2paper(u, v) for u, v in line])
        ax.plot(q[:, 0], q[:, 1], color="k", lw=THICK, solid_capstyle="round", zorder=3)
    for line in smooth:
        q = np.array([view.uv2paper(u, v) for u, v in line])
        ax.plot(q[:, 0], q[:, 1], color="0.45", lw=THIN * 0.8, zorder=2)


def wire_polygon(w, view):
    ex = BRepTools_WireExplorer(w.wrapped)
    pts = []
    while ex.More():
        ps = [tuple(view.P((x, y, z))) for x, y, z in
              ((p.x, p.y, p.z) for p in (cq.Edge(ex.Current()).positionAt(t) for t in
                                          ([0, 1] if cq.Edge(ex.Current()).geomType() == "LINE" else np.linspace(0, 1, 40))))]
        if ex.Orientation() == TopAbs_REVERSED:
            ps = ps[::-1]
        pts += ps[:-1]
        ex.Next()
    return np.array(pts)


def signed_area(p):
    return 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])


def draw_section(ax, solid, view, p0):
    """Section view: the material between the viewer and the plane through p0 (normal = view direction) is removed,
    the cut faces are hatched, the edges behind the plane are drawn."""
    n = view.d
    big = 400.0
    c = np.asarray(p0, float) + n * big / 2
    box = cq.Solid.makeBox(big, big, big, cq.Vector(*(c - big / 2)))
    kept = solid.cut(box)
    for f in kept.Faces():
        if f.geomType() != "PLANE":
            continue
        fn = np.array(f.normalAt().toTuple())
        if abs(abs(fn @ n) - 1) > 1e-6 or abs((np.array(f.Center().toTuple()) - p0) @ n) > 1e-4:
            continue
        rings = []
        for i, w in enumerate([f.outerWire()] + f.innerWires()):
            p = wire_polygon(w, view)
            if len(p) < 3:
                continue
            a = signed_area(p)
            if (i == 0 and a < 0) or (i > 0 and a > 0):
                p = p[::-1]
            rings.append(p)
        verts, codes = [], []
        for p in rings:
            verts += list(p) + [p[0]]
            codes += [Path.MOVETO] + [Path.LINETO] * (len(p) - 1) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), facecolor="none", edgecolor="0.25", hatch="////", lw=0, zorder=1))
    draw_view(ax, kept, view)


# ------------------------------------------------------------------ dimensions
def arrow(ax, tip, direction, size=2.6):
    d = np.asarray(direction, float)
    d = d / np.linalg.norm(d)
    nrm = np.array([-d[1], d[0]])
    base = np.asarray(tip) - d * size
    ax.add_patch(Polygon([tip, base + nrm * size * 0.17, base - nrm * size * 0.17], closed=True, color="k", lw=0, zorder=6))


def text(ax, p, s, rot=0, fs=DIM_FS, ha="center", va="bottom", **kw):
    ax.text(p[0], p[1], s, rotation=rot, fontsize=fs, ha=ha, va=va, zorder=7, **kw)


def linear(ax, P1, P2, axis, at, label, inside=True, shift=0.0, tside="l"):
    """Linear dimension between the paper points P1 and P2: axis "h" (horizontal distance, dimension line at y = at)
    or "v" (vertical distance, dimension line at x = at). shift moves the text along the dimension line; tside: text
    left ("l") or right ("r") of a vertical dimension line."""
    P1, P2 = np.asarray(P1, float), np.asarray(P2, float)
    k = 0 if axis == "h" else 1
    j = 1 - k
    A, B = P1.copy(), P2.copy()
    A[j] = B[j] = at
    for P, Q in ((P1, A), (P2, B)):                    # extension lines: gap 1 mm, 2 mm beyond the dimension line
        s = np.sign(Q[j] - P[j]) or 1.0
        a, b = P.copy(), Q.copy()
        a[j] += s * 1.0
        b[j] += s * 2.0
        if abs(Q[j] - P[j]) > 1.0:
            ax.plot([a[0], b[0]], [a[1], b[1]], color="k", lw=THIN, zorder=5)
    lo, hi = (A, B) if A[k] < B[k] else (B, A)
    u = np.zeros(2)
    u[k] = 1.0
    if inside:
        ax.plot([lo[0], hi[0]], [lo[1], hi[1]], color="k", lw=THIN, zorder=5)
        arrow(ax, lo, -u)
        arrow(ax, hi, u)
    else:
        ax.plot([lo[0] - 6 * u[0], hi[0] + 6 * u[0]], [lo[1] - 6 * u[1], hi[1] + 6 * u[1]], color="k", lw=THIN, zorder=5)
        arrow(ax, lo, u)
        arrow(ax, hi, -u)
    m = (lo + hi) / 2 + u * shift
    if axis == "h":
        text(ax, (m[0], m[1] + 0.6), label)
    elif tside == "l":
        text(ax, (m[0] - 0.8, m[1]), label, rot=90, ha="right", va="center")
    else:
        text(ax, (m[0] + 0.8, m[1]), label, rot=90, ha="left", va="center")


def half_dia(ax, Pa, Pe, label, side=1, extra=4.0, toff=(1.0, 0.8), ha="left"):
    """Diameter of a half bore in a section: dimension line from slightly beyond the axis (Pa) to the bore (Pe),
    one arrow at the bore."""
    Pa, Pe = np.asarray(Pa, float), np.asarray(Pe, float)
    d = (Pe - Pa) / np.linalg.norm(Pe - Pa)
    start = Pa - d * extra
    ax.plot([start[0], Pe[0]], [start[1], Pe[1]], color="k", lw=THIN, zorder=5)
    arrow(ax, Pe, d)
    m = start + (Pe - start) * 0.5
    rot = np.degrees(np.arctan2(d[1], d[0]))
    if abs(rot) > 90:
        rot -= 180 * np.sign(rot)
    text(ax, (m[0] + toff[0] * side, m[1] + toff[1]), label, rot=rot, ha=ha, va="bottom")


def leader(ax, Pf, Pt, label, ha="left", dot=False, fs=DIM_FS):
    Pf, Pt = np.asarray(Pf, float), np.asarray(Pt, float)
    ax.plot([Pf[0], Pt[0]], [Pf[1], Pt[1]], color="k", lw=THIN, zorder=5)
    if dot:
        ax.add_patch(Circle(Pf, 0.5, color="k", zorder=6))
    else:
        arrow(ax, Pf, Pf - Pt)
    text(ax, (Pt[0] + (0.8 if ha == "left" else -0.8), Pt[1]), label, ha=ha, va="center", fs=fs)


def radius(ax, Pc, Pr, label, ext=8.0, ha="left"):
    Pc, Pr = np.asarray(Pc, float), np.asarray(Pr, float)
    d = (Pr - Pc) / np.linalg.norm(Pr - Pc)
    Pt = Pr - d * ext
    ax.plot([Pt[0], Pr[0]], [Pt[1], Pr[1]], color="k", lw=THIN, zorder=5)
    arrow(ax, Pr, d)
    text(ax, (Pt[0] + (-0.6 if ha == "right" else 0.6), Pt[1] + 0.4), label, ha=ha, va="bottom")


def centre_line(ax, P1, P2):
    ax.plot([P1[0], P2[0]], [P1[1], P2[1]], color="k", lw=THIN, ls=(0, (12, 2, 1.5, 2)), zorder=4)


def centre_mark(ax, P, r_paper):
    e = r_paper + 1.5
    centre_line(ax, (P[0] - e, P[1]), (P[0] + e, P[1]))
    centre_line(ax, (P[0], P[1] - e), (P[0], P[1] + e))


def balloon(ax, P, Pt, label):
    P, Pt = np.asarray(P, float), np.asarray(Pt, float)
    r = 2.6
    d = P - Pt
    d = d / np.linalg.norm(d)
    ax.plot([Pt[0] + d[0] * r, P[0]], [Pt[1] + d[1] * r, P[1]], color="k", lw=THIN, zorder=5)
    ax.add_patch(Circle(P, 0.45, color="k", zorder=6))
    ax.add_patch(Circle(Pt, r, facecolor="white", edgecolor="k", lw=THIN, zorder=6))
    text(ax, Pt, label, va="center", fs=7.5)


def view_label(ax, P, label):
    text(ax, P, label, fs=LABEL_FS, va="bottom", ha="center", weight="bold")


def section_marker(ax, P1, P2, look, letter):
    """Section line from P1 to P2 (paper) with arrows in the viewing direction look (paper vector)."""
    P1, P2 = np.asarray(P1, float), np.asarray(P2, float)
    centre_line(ax, P1, P2)
    look = np.asarray(look, float) / np.linalg.norm(look)
    for P in (P1, P2):
        ax.plot([P[0], P[0] + (P2 - P1)[0] * 0], [P[1], P[1]], color="k")
        ax.plot([P[0] - (P2 - P1)[0] / np.linalg.norm(P2 - P1) * (-3) * (1 if P is P1 else -1), P[0]],
                [P[1] - (P2 - P1)[1] / np.linalg.norm(P2 - P1) * (-3) * (1 if P is P1 else -1), P[1]], color="k", lw=THICK * 1.4)
        tip = P + look * 6
        ax.plot([P[0], tip[0]], [P[1], tip[1]], color="k", lw=THIN, zorder=5)
        arrow(ax, tip, look, size=3.0)
        text(ax, tip + look * 2.5, letter, fs=LABEL_FS, va="center", weight="bold")


def hole_table(ax, x0, y_top, rows, cols=None):
    cols = cols or [("Id", 9), ("x", 15), ("y", 15), ("z", 11), ("Direction", 22), ("Size", 31), ("Depth", 30), ("Use", 130)]
    h = 4.6
    xs = [x0]
    for _, w in cols:
        xs.append(xs[-1] + w)
    y = y_top
    ax.add_patch(plt.Rectangle((x0, y - h), xs[-1] - x0, h, facecolor="0.9", edgecolor="k", lw=THIN, zorder=5))
    for (name, _), xa in zip(cols, xs):
        text(ax, (xa + 1.0, y - h / 2), name, ha="left", va="center", fs=TABLE_FS, weight="bold")
    for r in rows:
        y -= h
        ax.add_patch(plt.Rectangle((x0, y - h), xs[-1] - x0, h, facecolor="none", edgecolor="k", lw=THIN, zorder=5))
        for v, xa in zip(r, xs):
            text(ax, (xa + 1.0, y - h / 2), v, ha="left", va="center", fs=TABLE_FS)
    for xa in xs:
        ax.plot([xa, xa], [y_top, y - h], color="k", lw=THIN, zorder=5)
    return y - h


# ------------------------------------------------------------------ sheet
def sheet(title_rows, sheet_no, n_sheets=2):
    fig = plt.figure(figsize=(A3[0] / 25.4, A3[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A3[0])
    ax.set_ylim(0, A3[1])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(plt.Rectangle((20, 10), A3[0] - 30, A3[1] - 20, fill=False, lw=THICK * 1.4, zorder=8))
    title_block(ax, title_rows, sheet_no, n_sheets)
    return fig, ax


def first_angle_symbol(ax, x, y):
    """Projection symbol, first angle (ISO 5456-2)."""
    ax.add_patch(Polygon([(x, y + 1.5), (x + 9, y), (x + 9, y + 7), (x, y + 5.5)], closed=True, fill=False, lw=THIN, zorder=8))
    centre_line(ax, (x - 2, y + 3.5), (x + 25, y + 3.5))
    ax.add_patch(Circle((x + 17, y + 3.5), 3.5, fill=False, lw=THIN, zorder=8))
    ax.add_patch(Circle((x + 17, y + 3.5), 1.75, fill=False, lw=THIN, zorder=8))


def title_block(ax, rows, sheet_no, n_sheets=2):
    x0, x1, y0 = 230.0, A3[0] - 10, 10.0
    hs = [9, 9, 9, 9, 9, 9]
    y = y0
    widths = [(0, 60), (60, 120), (120, 180)]
    grid = rows["grid"]                 # 5 rows x 3 cells (label, value), bottom row first
    for r, cells in enumerate(grid):
        for (a, b), (lab, val) in zip(widths, cells):
            ax.add_patch(plt.Rectangle((x0 + a, y), b - a, hs[r], fill=False, lw=THIN, zorder=8))
            text(ax, (x0 + a + 1, y + hs[r] - 1.0), lab, ha="left", va="top", fs=5.5, color="0.35")
            text(ax, (x0 + a + 1, y + 1.3), val, ha="left", va="bottom", fs=max(5.0, min(7.6, 7.6 * 38 / max(len(val), 1))))
        y += hs[r]
    ax.add_patch(plt.Rectangle((x0, y), x1 - x0, 12, fill=False, lw=THICK, zorder=8))
    text(ax, (x0 + 2, y + 6.5), rows["title"], ha="left", va="center", fs=12.5, weight="bold")
    text(ax, (x0 + 2, y + 2.0), rows["subtitle"], ha="left", va="center", fs=7.2)
    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y + 12 - y0, fill=False, lw=THICK, zorder=8))
    text(ax, (x1 - 2, y + 6.5), f"Sheet {sheet_no} of {n_sheets}", ha="right", va="center", fs=8)
    first_angle_symbol(ax, x0 + 152, y0 + 2 * hs[0] + 1.2)


def iso_inset(fig, stl, rect, azim):
    tris = subdivide(load_stl(stl), 1.2)
    a = fig.add_axes(rect)
    lo, hi = draw_mesh(a, tris, iso_basis(azim, 28))
    a.set_aspect("equal")
    a.axis("off")


def origin_mark(ax, P):
    ax.add_patch(Circle(P, 0.8, color="k", zorder=7))
    text(ax, (P[0] + 1.5, P[1] - 4.8), "O", fs=8, ha="left", weight="bold")


def view_arrow(ax, tip, letter):
    """Viewing direction of a separate view: arrow pointing up to the bottom face, with its letter."""
    tip = np.asarray(tip, float)
    ax.plot([tip[0], tip[0]], [tip[1] - 10, tip[1] - 3], color="k", lw=THIN, zorder=5)
    arrow(ax, tip, (0, 1), size=3.0)
    text(ax, tip + (2.0, -6.0), letter, fs=LABEL_FS, weight="bold", ha="left", va="center")


def save(figs, pdf_path, png_stem, colors=64):
    """PDF with all sheets and one PNG per sheet (150 dpi, palette of 64 colours without dithering: small files)."""
    from PIL import Image
    with PdfPages(pdf_path, metadata={"CreationDate": None}) as pdf:
        for fig in figs:
            pdf.savefig(fig)
    for i, fig in enumerate(figs, 1):
        png = f"{png_stem}_sheet_{i}.png"
        fig.savefig(png, dpi=150)
        plt.close(fig)
        Image.open(png).convert("RGB").quantize(colors=colors, method=Image.Quantize.MEDIANCUT,
                                                dither=Image.Dither.NONE).save(png, optimize=True)


# ------------------------------------------------------------------ generic parts
def to_frame(solid, R, origin):
    """Solid in a local frame: p_local = R^T (p - origin); R has the local axes as columns (chassis coordinates)."""
    from OCP.gp import gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    R = np.asarray(R, float)
    M = R.T
    tv = -M @ np.asarray(origin, float)
    tr = gp_Trsf()
    tr.SetValues(*[float(v) for v in (M[0, 0], M[0, 1], M[0, 2], tv[0], M[1, 0], M[1, 1], M[1, 2], tv[1],
                                      M[2, 0], M[2, 1], M[2, 2], tv[2])])
    return cq.Shape.cast(BRepBuilderAPI_Transform(solid.wrapped, tr, True).Shape())


def solid_tris(solid, tol=0.02, max_edge=1.2):
    vs, idx = solid.tessellate(tol, 0.2)
    v = np.array([[p.x, p.y, p.z] for p in vs])
    return subdivide(v[np.array(idx)], max_edge)


def iso_inset_solid(fig, solid, rect, azim, elev=28):
    a = fig.add_axes(rect)
    draw_mesh(a, solid_tris(solid), iso_basis(azim, elev))
    a.set_aspect("equal")
    a.axis("off")


THREADS = {2.5: "M3", 3.3: "M4", 2.05: "M2.5", 1.6: "M2", 4.2: "M5"}       # tap drill -> thread
CLEARANCE = {3.2: "M3", 3.4: "M3", 4.3: "M4"}


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def find_holes(solid, max_d=6.5):
    """Holes of a solid with any axis direction: coaxial concave cylinders and cones that touch each other along the
    axis. A cluster is a hole when its smallest full cylinder (360 degrees) has a diameter up to max_d. Returns dicts
    with the axis (point p, unit direction d), the extent along the axis (t0, t1), the main diameter, the coaxial
    features and the open ends."""
    groups = {}
    for f in solid.Faces():
        gt = f.geomType()
        if gt not in ("CYLINDER", "CONE"):
            continue
        g = f._geomAdaptor()
        while isinstance(g, Geom_RectangularTrimmedSurface):              # solids built in memory (not read from STEP)
            g = g.BasisSurface()
        prim = g.Cylinder() if gt == "CYLINDER" else g.Cone()
        ax = prim.Axis()
        d = _unit([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
        k = int(np.argmax(np.abs(d)))
        if d[k] < 0:
            d = -d
        loc = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()])
        foot0 = loc - d * (loc @ d)                       # point of the axis line closest to the origin
        u0, u1, v0, v1 = f._uvBounds()
        srf = BRepAdaptor_Surface(f.wrapped)
        xyz = lambda q: (q.X(), q.Y(), q.Z())               # noqa: E731
        pts = np.array([xyz(srf.Value(u, v)) for u in np.linspace(u0, u1, 9) for v in np.linspace(v0, v1, 5)])
        ts = (pts - foot0) @ d
        radial = np.linalg.norm((pts - foot0) - np.outer(ts, d), axis=1)
        pcv = np.array(xyz(srf.Value(0.5 * (u0 + u1), 0.5 * (v0 + v1))))
        nrm = np.array(f.normalAt(cq.Vector(*pcv)).toTuple())
        foot = foot0 + d * ((pcv - foot0) @ d)
        if nrm @ (foot - pcv) <= 0:                       # convex (boss, rounded edge): not a hole
            continue
        key = (tuple(np.round(d, 3)), tuple(np.round(foot0 / 0.02) * 0.02))
        feat = {"type": gt, "r": float(radial.max()) if gt == "CONE" else round(prim.Radius(), 4),
                "r_min": float(radial.min()), "t0": float(ts.min()), "t1": float(ts.max()), "span": u1 - u0,
                "semi": float(np.degrees(abs(prim.SemiAngle()))) if gt == "CONE" else 0.0}
        groups.setdefault(key, {"d": d, "p": foot0, "feats": []})["feats"].append(feat)
    holes = []
    for g in groups.values():
        clusters = []
        for ft in sorted(g["feats"], key=lambda e: e["t0"]):
            if clusters and ft["t0"] <= max(e["t1"] for e in clusters[-1]) + 0.05:
                clusters[-1].append(ft)
            else:
                clusters.append([ft])
        for feats in clusters:
            segs = []                                   # cylinders: one segment per radius and continuous range along the axis
            for ft in sorted((e for e in feats if e["type"] == "CYLINDER"), key=lambda e: e["t0"]):
                c = next((q for q in segs if q["r"] == round(ft["r"], 3) and ft["t0"] <= q["t1"] + 0.05), None)
                if c:
                    c["span"] += ft["span"]
                    c["t1"] = max(c["t1"], ft["t1"])
                else:
                    segs.append({"r": round(ft["r"], 3), "span": ft["span"], "t0": ft["t0"], "t1": ft["t1"]})
            fulls = [c for c in segs if c["span"] > 2 * np.pi * 0.98]
            if not fulls or 2 * min(c["r"] for c in fulls) > max_d + 1e-6:
                continue
            r_main = min(c["r"] for c in fulls)
            main = max((c for c in fulls if c["r"] == r_main), key=lambda c: c["t1"] - c["t0"])
            t0 = min(ft["t0"] for ft in feats)
            t1 = max(ft["t1"] for ft in feats)
            d, p = g["d"], g["p"]
            open0 = not solid.isInside(cq.Vector(*(p + d * (t0 - 0.05))))
            open1 = not solid.isInside(cq.Vector(*(p + d * (t1 + 0.05))))
            extras = []
            for c in sorted(fulls, key=lambda c: (c["r"], c["t0"])):
                if c is not main:
                    extras.append({"kind": "bore", "d": 2 * c["r"], "t0": c["t0"], "t1": c["t1"]})
            for ft in feats:
                if ft["type"] == "CONE":
                    extras.append({"kind": "csk", "d": 2 * ft["r"], "d_min": 2 * ft["r_min"], "angle": 2 * ft["semi"],
                                   "t0": ft["t0"], "t1": ft["t1"]})
            holes.append({"d": d, "p": p, "t0": t0, "t1": t1, "dia": 2 * r_main, "main": main,
                          "open": (open0, open1), "extras": extras})
    return holes


def hole_point(h, which):
    return h["p"] + h["d"] * (h["t0"] if which == 0 else h["t1"])


FACE_NAMES = {(0, 0, 1): "top face", (0, 0, -1): "bottom face", (1, 0, 0): "+x side", (-1, 0, 0): "-x side",
              (0, 1, 0): "+y side", (0, -1, 0): "-y side"}


def face_name(v):
    key = tuple(int(round(c)) if abs(abs(c) - 1) < 1e-3 or abs(c) < 1e-3 else 9 for c in v)
    return FACE_NAMES.get(key, "upper end" if v[2] > 0 else "lower end")


def describe_direction(v, through=False):
    """Text for a drilling direction (unit vector, into the material) or for the axis of a through hole."""
    k = int(np.argmax(np.abs(v)))
    if abs(abs(v[k]) - 1) < 1e-3:
        if through:
            return f"through ({'xyz'[k]})"
        return {(2, -1): "from above", (2, 1): "from below"}.get((k, int(np.sign(v[k]))),
                                                                 f"from the {'-' if v[k] > 0 else '+'}{'xyz'[k]} side")
    ang = np.degrees(np.arccos(min(1.0, abs(v[k]))))
    return ("through, " if through else "") + f"axis {ang:.1f} deg to {'xyz'[k]}"


def hole_rows_generic(holes, names=None, use=None, thread_extra=1.0, centroid=(0, 0, 0)):
    """Rows (id, x, y, z, direction, size, depth, note) of a hole table and the data of each row. names: list of
    (name, point) to name holes by position (within 0.1 mm of the hole axis); use: function(hole) -> text or None."""
    rows = []
    for h in holes:
        dia = round(h["dia"], 2)
        thread = next((v for k, v in THREADS.items() if abs(k - dia) < 0.01), None)
        size = f"{thread} (tap drill Ø{dia:g})" if thread else f"Ø{dia:g}"
        through = h["open"] == (True, True)
        csk = [e for e in h["extras"] if e["kind"] == "csk"]
        ends = []
        for e in csk:
            ends.append(0 if abs((e["t0"] + e["t1"]) / 2 - h["t0"]) < abs((e["t0"] + e["t1"]) / 2 - h["t1"]) else 1)
        if not through:
            start = 0 if h["open"][0] else 1
        elif csk and any(e["d"] - e["d_min"] > 1.2 for e in csk):
            start = ends[[i for i, e in enumerate(csk) if e["d"] - e["d_min"] > 1.2][0]]
        else:                                             # outer end (farther from the centroid), else the upper end
            e0, e1 = (np.linalg.norm(hole_point(h, i) - np.asarray(centroid, float)) for i in (0, 1))
            start = (0 if e0 > e1 else 1) if abs(e0 - e1) > 0.1 else (0 if hole_point(h, 0)[2] >= hole_point(h, 1)[2] else 1)
        P = hole_point(h, start)
        dirv = h["d"] if start == 0 else -h["d"]
        m = h["main"]
        if through:
            depth = f"through ({h['t1'] - h['t0']:.2f})"
        else:
            drill = (m["t1"] - h["t0"]) if start == 0 else (h["t1"] - m["t0"])
            depth = f"drill {drill:.1f}" + (f", thread {max(drill - thread_extra, 0):.1f}" if thread else "")
        notes = []
        chamfers = [(e, end) for e, end in zip(csk, ends) if (e["d"] - e["d_min"]) / 2 <= 0.6]
        if chamfers:
            e0 = chamfers[0][0]
            c = (e0["d"] - e0["d_min"]) / 2
            notes.append(f"chamfer {c:.1f} x 45 deg" + (f" of Ø{e0['d_min']:.1f}" if abs(e0["d_min"] - h["dia"]) > 0.05 else "")
                         + (" on both faces" if len(chamfers) == 2 else ""))
        for e, end in zip(csk, ends):
            if (e["d"] - e["d_min"]) / 2 > 0.6:
                outward = -h["d"] if end == 0 else h["d"]
                notes.append(f"countersink Ø{e['d']:.1f} x {e['angle']:.0f} deg on the {face_name(outward)}")
        for e in h["extras"]:
            if e["kind"] == "bore":                       # a bore that reaches a face through a chamfer starts at the face
                ch0 = any(abs(c["t0"] - h["t0"]) < 0.05 and abs(c["t1"] - e["t0"]) < 0.05 for c in csk)
                ch1 = any(abs(c["t1"] - h["t1"]) < 0.05 and abs(c["t0"] - e["t1"]) < 0.05 for c in csk)
                end = 0 if (abs(e["t0"] - h["t0"]) < 0.05 or ch0) else (1 if (abs(e["t1"] - h["t1"]) < 0.05 or ch1) else None)
                length = (e["t1"] - h["t0"]) if end == 0 else ((h["t1"] - e["t0"]) if end == 1 else (e["t1"] - e["t0"]))
                where = f" from the {face_name(-h['d'] if end == 0 else h['d'])}" if end is not None else " (inside)"
                notes.append(f"Ø{e['d']:.2f} x {length:.2f}{where}")
        u = use(h) if use else None
        rows.append({"hole": h, "P": P, "dir": dirv, "dirtxt": describe_direction(h["d"] if through else dirv, through),
                     "size": size, "depth": depth, "note": "; ".join(([u] if u else []) + notes),
                     "sig": (size, depth, tuple(notes), u)})
    for r in rows:
        r["id"] = None
        for n, q in (names or []):
            v = np.asarray(q, float) - r["hole"]["p"]
            if np.linalg.norm(v - (v @ r["hole"]["d"]) * r["hole"]["d"]) < 0.1:
                r["id"] = n
                break
    sigs = []
    for r in rows:
        if r["id"] is None and r["sig"] not in sigs:
            sigs.append(r["sig"])
    for i, s in enumerate(sigs):
        grp = [r for r in rows if r["id"] is None and r["sig"] == s]
        grp.sort(key=lambda r: (-round(r["P"][1], 1), round(r["P"][0], 1), -round(r["P"][2], 1)))
        for j, r in enumerate(grp, 1):
            r["id"] = f"{chr(65 + i)}{j}"
    rows.sort(key=lambda r: (r["id"][0], int("".join(c for c in r["id"][1:] if c.isdigit()) or 0), r["id"]))
    c2 = lambda v: f"{round(v, 2) + 0.0:+.2f}"                       # no "-0.00"
    table = [(r["id"], c2(r['P'][0]), c2(r['P'][1]), c2(r['P'][2]), r["dirtxt"], r["size"], r["depth"],
              r["note"]) for r in rows]
    return table, rows


def view_box(view, bb):
    """Paper bounding box (x0, y0, x1, y1) of a bounding box of the model in a view."""
    cs = np.array([view.P((x, y, z)) for x in (bb.xmin, bb.xmax) for y in (bb.ymin, bb.ymax) for z in (bb.zmin, bb.zmax)])
    return cs[:, 0].min(), cs[:, 1].min(), cs[:, 0].max(), cs[:, 1].max()


def place_balloons(ax, items, centre, dist=8.0, avoid=()):
    """Balloons with labels for the points (paper) in items [(P, label)], pushed radially away from centre."""
    placed = [np.asarray(a, float) for a in avoid]
    for P, label in items:
        P = np.asarray(P, float)
        v = P - np.asarray(centre, float)
        base = np.degrees(np.arctan2(v[1], v[0])) if np.linalg.norm(v) > 1e-6 else 45.0
        best = None
        for dd in (dist, dist + 4, dist + 8):
            for k in range(25):
                ang = np.radians(base + ((k + 1) // 2) * 15 * (1 if k % 2 else -1))
                Q = P + dd * np.array([np.cos(ang), np.sin(ang)])
                if all(np.linalg.norm(Q - o) > 5.8 for o in placed) and \
                        all(np.linalg.norm(Q - np.asarray(o, float)) > 3.5 for o in avoid):
                    best = Q
                    break
            if best is not None:
                break
        if best is None:
            best = P + dist * _unit(v if np.linalg.norm(v) > 1e-6 else (1, 1))
        placed.append(best)
        balloon(ax, P, best, label)


# ------------------------------------------------------------------ angles
def angle_dim(ax, E, u, ref, r, label):
    """Angular dimension at the vertex E (paper) between the unit directions ref and u: arc of radius r with arrows,
    a thin reference line along ref and the text at the middle of the arc."""
    E, u, ref = (np.asarray(v, float) for v in (E, u, ref))
    a0, a1 = np.arctan2(ref[1], ref[0]), np.arctan2(u[1], u[0])
    da = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi                    # shorter way from ref to u
    ts = a0 + np.linspace(0, da, 40)
    ax.plot(E[0] + r * np.cos(ts), E[1] + r * np.sin(ts), color="k", lw=THIN, zorder=5)
    ax.plot([E[0], E[0] + (r + 3) * ref[0]], [E[1], E[1] + (r + 3) * ref[1]], color="k", lw=THIN, zorder=5)
    s = np.sign(da) or 1.0
    for t, sg in ((a0, -s), (a0 + da, s)):                           # arrows tangent to the arc, pointing outward
        tip = E + r * np.array([np.cos(t), np.sin(t)])
        tang = sg * np.array([-np.sin(t), np.cos(t)])
        arrow(ax, tip, tang, size=2.2)
    tm = a0 + da / 2
    P = E + (r + 2.2) * np.array([np.cos(tm), np.sin(tm)])
    text(ax, P, label, ha="left" if np.cos(tm) > 0.2 else ("right" if np.cos(tm) < -0.2 else "center"),
         va="bottom" if np.sin(tm) > 0.2 else ("top" if np.sin(tm) < -0.2 else "center"), fs=7.8)


def auto_angles(ax, shape, view, min_len=10.0, max_groups=4, r_max=12.0):
    """Angles of the slanted straight edges of a view (paper length at least min_len): one dimension per distinct angle
    (at the longest edge), measured to the horizontal (up to 45 degrees) or to the vertical. Returns the angles."""
    vis, _ = hlr(shape, view)
    segs = []
    for line in vis:
        if len(line) != 2:
            continue
        P1, P2 = view.uv2paper(*line[0]), view.uv2paper(*line[1])
        d = P2 - P1
        L = np.linalg.norm(d)
        if L < min_len:
            continue
        th = np.degrees(np.arctan2(abs(d[1]), abs(d[0])))
        if th < 3.0 or th > 87.0:
            continue
        segs.append((L, th, P1, P2))
    groups = {}
    for L, th, P1, P2 in segs:
        key = round(min(th, 90 - th) * 2) / 2 * (1 if th <= 45 else -1)
        if key not in groups or L > groups[key][0]:
            groups[key] = (L, th, P1, P2)
    out = []
    for key, (L, th, P1, P2) in sorted(groups.items(), key=lambda kv: -kv[1][0])[:max_groups]:
        E, F = (P1, P2) if P1[1] <= P2[1] else (P2, P1)               # vertex at the lower end
        u = (F - E) / np.linalg.norm(F - E)
        if th <= 45:
            ref = np.array([np.sign(u[0]) or 1.0, 0.0])
            val = th
        else:
            ref = np.array([0.0, 1.0])
            val = 90 - th
        lab = f"{val:.0f}°" if abs(val - round(val)) < 0.05 else f"{val:.1f}°"
        angle_dim(ax, E, u, ref, min(r_max, 0.6 * L), lab)
        out.append(val)
    return out
