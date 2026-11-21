"""Edge treatment of 3D printed parts: chamfer on the sharp outer edges, radius in the sharp inner corners.

An edge between two faces is sharp when the faces meet at an angle of up to max_angle (default 120 degrees). Its kind
follows from two test points beside the edge (0.02 mm, along the difference of the face normals): both outside the
solid = outer (convex) edge, both inside = inner (concave) corner. Edges whose middle lies in a keep zone (for example
a bearing seat) are left as they are.

Each kind is treated all at once, else per group of touching edges (the kernel blends the meeting points of edges only
when they are treated in one operation), else edge by edge; an edge that fails with the full size gets a smaller one.
Three variants are made (radii first; chamfers first; radii first with the outer edges that fail in it chamfered
before) and the one with the smallest deficit is kept (1 per sharp edge left, 0.05 per sharp edge shorter than twice
the chamfer, plus the missing fraction of each reduced size). Every kernel operation runs in a forked child process
with a time limit (the kernel can crash or hang on some edge layouts); results with a tolerance above TOL_LIMIT are
rejected (later operations on them fail), and the kept result must survive a STEP export and a tessellation. An edge
that cannot be treated stays sharp and is reported. Results are cached in the temporary directory.

Used by generate_running_gear.py (C-hub, steering knuckle, rear hub carrier). Requires cadquery (Linux: os.fork).
"""
import hashlib
import io
import math
import os
import pickle
import select
import signal
import tempfile
import time

import cadquery as cq
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.ShapeAnalysis import ShapeAnalysis_ShapeTolerance
from OCP.TopAbs import TopAbs_IN, TopAbs_EDGE, TopAbs_FACE
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
from OCP.gp import gp_Pnt

EPS = 0.02
TIME_LIMIT = 30.0                                       # s per kernel operation
CACHE = os.path.join(tempfile.gettempdir(), "edge_treatment_cache")
TOL_LIMIT = 1e-2                                        # largest tolerance of a result (mm)


def _inside(solid, v):
    c = BRepClass3d_SolidClassifier(solid.wrapped, gp_Pnt(v.x, v.y, v.z), 1e-7)
    return c.State() == TopAbs_IN


def sharp_edges(solid, keep=(), max_angle=120.0):
    """[(edge, kind, middle)] of the sharp edges outside the keep zones; kind 'outer' or 'inner'."""
    amap = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(solid.wrapped, TopAbs_EDGE, TopAbs_FACE, amap)
    out = []
    for i in range(1, amap.Extent() + 1):
        e = cq.Edge(amap.FindKey(i))
        faces = []
        for f in amap.FindFromIndex(i):
            if not any(f.IsSame(g) for g in faces):
                faces.append(f)
        if len(faces) != 2 or e.Length() < 1e-3:
            continue
        m = e.positionAt(0.5)
        if any(z.isInside(m, 1e-6) for z in keep):
            continue
        n1, n2 = (cq.Face(f).normalAt(m) for f in faces)
        a = math.degrees(n1.getAngle(n2))
        if 180.0 - a > max_angle - 0.5:                    # faces meet at more than max_angle: not sharp
            continue
        d = n2 - n1
        if d.Length < 1e-9:
            continue
        d = d.normalized() * EPS
        i1, i2 = _inside(solid, m + d), _inside(solid, m - d)
        if i1 == i2:
            out.append((e, "inner" if i1 else "outer", m))
    return out


def _tolerance(solid):
    return ShapeAnalysis_ShapeTolerance().Tolerance(solid.wrapped, 1)


def _op_direct(solid, kind, size, edges):
    try:
        r = solid.fillet(size, edges) if kind == "inner" else solid.chamfer(size, None, edges)
    except Exception:
        return None
    if not r.isValid() or len(r.Solids()) != 1:
        return None
    if _tolerance(r) > max(TOL_LIMIT, _tolerance(solid)):     # inexact result: later operations would fail
        return None
    dv = r.Volume() - solid.Volume()
    if (kind == "inner" and dv < -1e-6) or (kind == "outer" and dv > 1e-6):
        return None
    return r


def _in_child(fn):
    """Run fn() (returns a solid or None) in a forked child process: the kernel can crash or hang on some edge
    layouts. The solid comes back as BRep data; None on failure, crash or after TIME_LIMIT seconds."""
    rd, wr = os.pipe()
    pid = os.fork()
    if pid == 0:                                                       # child
        os.close(rd)
        data = b""
        try:
            r = fn()
            if r is not None:
                buf = io.BytesIO()
                r.exportBrep(buf)
                data = buf.getvalue()
        except Exception:
            data = b""
        with os.fdopen(wr, "wb") as f:
            f.write(data)
        os._exit(0)
    os.close(wr)
    data, t_end = b"", time.time() + TIME_LIMIT
    with os.fdopen(rd, "rb") as f:
        while True:
            ready, _, _ = select.select([f], [], [], max(0.0, t_end - time.time()))
            if not ready:                                              # no answer within the time limit
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
                return None
            chunk = os.read(f.fileno(), 1 << 20)
            if not chunk:
                break
            data += chunk
    _, status = os.waitpid(pid, 0)
    if status != 0 or not data:
        return None
    r = cq.Shape.importBrep(io.BytesIO(data))
    return cq.Solid(r.Solids()[0].wrapped) if r.Solids() else None


def _op(solid, kind, size, edges):
    """Fillet (inner) or chamfer (outer) of the edges; None if it fails."""
    return _in_child(lambda: _op_direct(solid, kind, size, edges))


def _healthy(solid):
    """True if the solid survives a STEP export and a tessellation (some valid results crash the STEP writer)."""
    def fn():
        path = f"/tmp/edge_treatment_check_{os.getpid()}.step"
        try:
            cq.exporters.export(solid, path)
            solid.tessellate(0.01, 0.1)
            return solid if solid.isValid() else None
        finally:
            if os.path.exists(path):
                os.remove(path)
    return _in_child(fn) is not None


def _clean(solid):
    """Merge faces of the same surface (cadquery clean); the solid as it is if that fails."""
    def fn():
        r = solid.clean()
        return r if r.isValid() and abs(r.Volume() - solid.Volume()) < 1e-3 else None
    r = _in_child(fn)
    return r if r is not None else solid


def _find(solid, m):
    """Edge of the current solid through the middle m of an edge found before (None: the edge is treated already)."""
    v = cq.Vertex.makeVertex(m.x, m.y, m.z)
    best = None
    for e in solid.Edges():
        bb = e.BoundingBox()
        if not (bb.xmin - 1e-3 <= m.x <= bb.xmax + 1e-3 and bb.ymin - 1e-3 <= m.y <= bb.ymax + 1e-3
                and bb.zmin - 1e-3 <= m.z <= bb.zmax + 1e-3):
            continue
        dist = e.distance(v)
        if dist < 1e-3 and (best is None or dist < best[0]):
            best = (dist, e)
    return best[1] if best else None


def _groups(edges, link):
    """Groups of edges that touch or lie closer than link to each other (the kernel blends their meeting points only
    when they are treated in one operation)."""
    n = len(edges)
    parent = list(range(n))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    bbs = [e.BoundingBox() for e in edges]
    for i in range(n):
        for j in range(i + 1, n):
            a, b = bbs[i], bbs[j]
            if (a.xmin - link > b.xmax or b.xmin - link > a.xmax or a.ymin - link > b.ymax or b.ymin - link > a.ymax
                    or a.zmin - link > b.zmax or b.zmin - link > a.zmax):
                continue
            if edges[i].distance(edges[j]) < link:
                parent[root(i)] = root(j)
    out = {}
    for i in range(n):
        out.setdefault(root(i), []).append(i)
    return list(out.values())


def _apply(solid, kind, sizes, keep, max_angle, link=1.0):
    """Treat all sharp edges of one kind with sizes[0]: all at once, else per group of touching edges, else edge by
    edge; an edge that fails with sizes[0] gets the next smaller size. Returns (solid, {size: edges}, middles left)."""
    todo = [(e, m) for e, k, m in sharp_edges(solid, keep, max_angle) if k == kind]
    done = {sz: 0 for sz in sizes}
    if not todo:
        return solid, done, []
    r = _op(solid, kind, sizes[0], [e for e, _ in todo])
    if r is not None:
        done[sizes[0]] = len(todo)
        return r, done, []
    left = []
    for grp in sorted(_groups([e for e, _ in todo], link), key=len, reverse=True):
        ms = [todo[i][1] for i in grp]
        es = [e for e in (_find(solid, m) for m in ms) if e is not None]
        r = _op(solid, kind, sizes[0], es) if es else None
        if r is not None:
            solid, done[sizes[0]] = r, done[sizes[0]] + len(es)
        else:
            for m in ms:
                for sz in sizes:
                    e = _find(solid, m)
                    if e is None:
                        break                               # treated with a neighbour (tangent chain)
                    r = _op(solid, kind, sz, [e])
                    if r is not None:
                        solid, done[sz] = r, done[sz] + 1
                        break
                else:
                    left.append(m)
    return solid, done, left


def _score(rest, done, sizes, short):
    """Deficit of a result: 1 per sharp edge left (0.05 if shorter than short), plus the missing fraction of each
    reduced size."""
    d = sum(1.0 if e.Length() >= short else 0.05 for e, _, _ in rest)
    for kind in done:
        d += sum(n * (1.0 - sz / sizes[kind][0]) for sz, n in done[kind].items())
    return round(d, 2)


def _treat(solid, chamfer, radius, keep=(), max_angle=120.0):
    """Radii in the sharp inner corners and chamfers on the sharp outer edges, in both orders (radii first, chamfers
    first, and radii first with the edges that fail in it chamfered before); kept: the variant with the smallest
    deficit (_score). Where the full size fails (faces too narrow), an edge gets a smaller size (radius 0.6 / 0.4 of the full size, chamfer 0.67 / 0.33); where no size works, it stays sharp.
    Returns (solid, report)."""
    v0 = solid.Volume()
    sizes = {"inner": [radius, round(radius * 0.6, 2), round(radius * 0.4, 2)],
             "outer": [chamfer, round(chamfer * 2 / 3, 2), round(chamfer / 3, 2)]}
    results = []
    short = 2 * chamfer                                    # shorter edges: facets of the chamfers at corners, slivers
    for order in (("inner", "outer"), ("outer", "inner")):
        s, done = solid, {}
        for kind in order:
            s, done[kind], _ = _apply(s, kind, sizes[kind], keep, max_angle)
        rest = sharp_edges(s, keep, max_angle)
        results.append((_score(rest, done, sizes, short), s, done, rest, order))
    first = [m for e, k, m in results[0][3] if k == "outer" and e.Length() >= short]
    if first:                       # third variant: the outer edges left by "radii first" get their chamfers first
        s, done = solid, {"outer": {sz: 0 for sz in sizes["outer"]}}
        for m in first:
            for sz in sizes["outer"]:
                e = _find(s, m)
                r = _op(s, "outer", sz, [e]) if e is not None else None
                if r is not None:
                    s, done["outer"][sz] = r, done["outer"][sz] + 1
                    break
        if s is not solid:
            for kind in ("inner", "outer"):
                s, d, _ = _apply(s, kind, sizes[kind], keep, max_angle)
                done[kind] = {sz: done.get(kind, {}).get(sz, 0) + n for sz, n in d.items()}
            rest = sharp_edges(s, keep, max_angle)
            results.append((_score(rest, done, sizes, short), s, done, rest,
                            ("outer (left by inner first)", "inner", "outer")))
    results.sort(key=lambda r: r[0])
    best = next((r for r in results if _healthy(r[1])), None)
    if best is None:                                   # no healthy result: the part stays as it is
        return solid, {"order": "none (no healthy result)", "deficit of the orders tried": [r[0] for r in results]}
    s, done, rest, order = best[1:]
    cl = _clean(s)
    s = cl if _healthy(cl) else s
    rest_l = [(e, k, m) for e, k, m in rest if e.Length() >= short]
    rep = {"order": ", then ".join(order), "radii": done["inner"], "chamfers": done["outer"],
           "deficit of the orders tried": [r[0] for r in results],
           "sharp edges remaining": {k: sum(1 for _, kk, _ in rest_l if kk == k) for k in ("inner", "outer")},
           f"short sharp edges (< {short:g})": len(rest) - len(rest_l),
           "volume change mm3": round(s.Volume() - v0, 2),
           "remaining": [(k, round(e.Length(), 2), tuple(round(c, 2) for c in m.toTuple())) for e, k, m in rest_l]}
    return s, rep


def _brep(shape):
    buf = io.BytesIO()
    shape.exportBrep(buf)
    return buf.getvalue()


def treat(solid, chamfer, radius, keep=(), max_angle=120.0):
    """Edge treatment (see _treat), cached in the temporary directory: the key is the geometry of the solid and of the
    keep zones, the sizes and the code of this module, so a cached result is used only for the same input."""
    h = hashlib.sha1(_brep(solid))
    for z in keep:
        h.update(_brep(z))
    h.update(repr((chamfer, radius, max_angle)).encode())
    with open(__file__, "rb") as f:
        h.update(f.read())
    path = os.path.join(CACHE, h.hexdigest() + ".pickle")
    try:
        with open(path, "rb") as f:
            data, rep = pickle.load(f)
        return cq.Solid(cq.Shape.importBrep(io.BytesIO(data)).Solids()[0].wrapped), rep
    except Exception:
        pass
    r, rep = _treat(solid, chamfer, radius, keep, max_angle)
    try:
        os.makedirs(CACHE, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump((_brep(r), rep), f)
    except OSError:
        pass
    return r, rep
