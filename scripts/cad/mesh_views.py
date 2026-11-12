"""Shaded orthographic views of an STL mesh with matplotlib.

Helper module for the drawing scripts. The views are rendered with the painter's
algorithm: the triangles are projected onto the view plane, sorted by depth and
filled with a grey value from the angle between the face normal and the light.
"""
import struct

import numpy as np
from matplotlib.collections import PolyCollection

# view name: (view direction from the viewer into the part, screen right, screen up)
VIEWS = {
    "top": ((0, 0, -1), (1, 0, 0), (0, 1, 0)),
    "bottom": ((0, 0, 1), (-1, 0, 0), (0, 1, 0)),
    "side": ((-1, 0, 0), (0, 1, 0), (0, 0, 1)),        # looking at the +x face
    "end_pinion": ((0, -1, 0), (-1, 0, 0), (0, 0, 1)),  # looking at the pinion end
    "end_outer": ((0, 1, 0), (1, 0, 0), (0, 0, 1)),     # looking at the outer end
}


def load_stl(path):
    """Triangles (n, 3, 3) of a binary STL file."""
    with open(path, "rb") as f:
        data = f.read()
    n = struct.unpack("<I", data[80:84])[0]
    rec = np.frombuffer(data[84:84 + n * 50],
                        dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return rec["v"].reshape(-1, 3, 3).astype(float)


def subdivide(tris, max_edge=1.5):
    """Split triangles at the midpoint of the longest edge until all edges are short.

    Short triangles reduce the sorting errors of the painter's algorithm.
    """
    done = []
    work = tris
    for _ in range(12):
        e = np.stack([np.linalg.norm(work[:, 1] - work[:, 0], axis=1),
                      np.linalg.norm(work[:, 2] - work[:, 1], axis=1),
                      np.linalg.norm(work[:, 0] - work[:, 2], axis=1)], axis=1)
        big = e.max(axis=1) > max_edge
        done.append(work[~big])
        work = work[big]
        if len(work) == 0:
            break
        k = e[big].argmax(axis=1)
        # rotate the vertices so that the longest edge is v0-v1
        idx = np.stack([(k + i) % 3 for i in range(3)], axis=1)
        w = np.take_along_axis(work, idx[:, :, None].repeat(3, axis=2), axis=1)
        m = (w[:, 0] + w[:, 1]) / 2
        a = np.stack([w[:, 0], m, w[:, 2]], axis=1)
        b = np.stack([m, w[:, 1], w[:, 2]], axis=1)
        work = np.concatenate([a, b])
    done.append(work)
    return np.concatenate(done)


def basis(direction, right, up):
    d, r, u = (np.asarray(v, float) for v in (direction, right, up))
    return d / np.linalg.norm(d), r / np.linalg.norm(r), u / np.linalg.norm(u)


def iso_basis(azim_deg=-55.0, elev_deg=30.0):
    """View basis for an axonometric view (viewer above, rotated about z)."""
    az, el = np.radians(azim_deg), np.radians(elev_deg)
    # direction from the viewer into the scene
    d = -np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    r = np.cross(d, [0, 0, 1.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, d)
    return d, r, u


def draw_mesh(ax, tris, view, light=(-0.35, 0.55, 0.75), color=(0.55, 0.6, 0.66), edge=False,
              depth_cue=0.45, rasterized=True, tri_colors=None):
    """Draw the shaded mesh on a 2D axes. view: name in VIEWS or a basis tuple.

    tri_colors: optional base colour per triangle (n, 3), for example to show an assembly
    of several parts in one view with a common depth order.
    """
    base = np.tile(np.asarray(color, float), (len(tris), 1)) if tri_colors is None \
        else np.asarray(tri_colors, float)
    d, r, u = basis(*VIEWS[view]) if isinstance(view, str) else view
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(n, axis=1)
    keep = ln > 1e-12
    tris, n, base = tris[keep], n[keep] / ln[keep][:, None], base[keep]
    facing = n @ d < 0                      # back faces are hidden by front faces
    tris, n, base = tris[facing], n[facing], base[facing]
    depth = (tris.mean(axis=1) @ d)
    order = np.argsort(-depth)              # far triangles first
    tris, n, base = tris[order], n[order], base[order]
    lv = np.asarray(light, float)
    # light relative to the viewer: rotate the light vector into the view basis
    lw = lv[0] * r + lv[1] * u - lv[2] * d
    lw /= np.linalg.norm(lw)
    shade = 0.35 + 0.65 * np.clip(n @ lw, 0, 1)
    # depth cue: faces far from the viewer are darker, so holes and pockets are visible
    depth = depth[order]
    span = max(depth.max() - depth.min(), 1e-9)
    shade = shade * (1.0 - depth_cue * (depth - depth.min()) / span)
    cols = np.clip(shade[:, None] * base + 0.08, 0, 1)
    pts = np.stack([tris @ r, tris @ u], axis=-1)
    pc = PolyCollection(pts, facecolors=cols, edgecolors=cols if not edge else "k",
                        linewidths=0.8, antialiased=True)
    pc.set_rasterized(rasterized)   # raster image inside vector files (PDF size)
    ax.add_collection(pc)
    lo, hi = pts.reshape(-1, 2).min(0), pts.reshape(-1, 2).max(0)
    return lo, hi
