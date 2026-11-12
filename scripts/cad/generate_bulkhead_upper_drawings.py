"""Preview image and measurement sheet of the upper bulkhead (new design).

The preview shows the upper part alone, the assembly with the lower part and two sections of
the assembly with the bearings, the gears, the shock tower plate and the end of the top brace
(simplified bodies). The measurement sheet shows the interfaces of the stock upper part on
photos with numbered dimensions and lists the estimates of the model.

Usage (from the root directory of the repository):
    python scripts/cad/generate_bulkhead_upper_drawings.py

Outputs:
    photos/cad_bulkhead_upper_preview.png
    cad/bulkhead/bulkhead_upper_measurement_sheet.pdf

Requires the packages cadquery and matplotlib.
"""
import argparse
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
import cadquery as cq  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh_views import subdivide, draw_mesh, iso_basis  # noqa: E402
from generate_bulkhead_lower import bulkhead_lower, cyl_x, cyl_y, box, load_params  # noqa: E402
from generate_bulkhead_upper import bulkhead_upper  # noqa: E402
from generate_bulkhead_drawings import section, frame, balloon, DIM_COLOR, A4_LANDSCAPE  # noqa: E402

COL = {"lower": (0.45, 0.5, 0.56), "upper": (0.8, 0.56, 0.3), "steel": (0.78, 0.8, 0.82),
       "gear": (0.85, 0.72, 0.35), "carbon": (0.22, 0.22, 0.24), "case": (0.3, 0.3, 0.32)}


def tess(shape, tol=0.05):
    """Triangles (n, 3, 3) of a cadquery shape."""
    verts, idx = shape.tessellate(tol, 0.2)
    v = np.array([[p.x, p.y, p.z] for p in verts])
    return v[np.array(idx)]


def ring_x(r_in, r_out, x0, x1, y, z):
    return cyl_x(r_out, x0, x1, y, z).cut(cyl_x(r_in, x0 - 1, x1 + 1, y, z))


def ring_y(r_in, r_out, y0, y1, x, z):
    return cyl_y(r_out, y0, y1, x, z).cut(cyl_y(r_in, y0 - 1, y1 + 1, x, z))


def drivetrain(lp, up):
    """Simplified bodies of the parts around the bulkhead: (name, colour key, shape)."""
    zc, yd = lp["axis_z"], lp["diff_axis_y"]
    xl = lp["diff_lip_inner_x"]
    play = (2 * xl - 30.0) / 2                     # diff with bearings 30.0 (caliper no. 28)
    b = lp["diff_bearing"]
    parts = []
    for sx in (-1, 1):
        xa, xb = sorted((sx * (xl - play), sx * (xl - play - b[2])))
        parts.append(("diff bearing", "steel", ring_x(b[0] / 2, b[1] / 2, xa, xb, yd, zc)))
    hub_x = xl - play - b[2]
    parts.append(("diff case", "case", cyl_x(10.5, -hub_x + 1.5, 5.0, yd, zc)
                  .fuse(cyl_x(b[0] / 2, -xl + play, xl - play, yd, zc))))
    parts.append(("ring gear", "gear", ring_x(11.0, 31.93 / 2, 5.0, 9.4, yd, zc)))
    yp_in = lp["pinion_seat_y_inner"]
    pb = lp["pinion_bearing"]
    y_r = yp_in + pb[2] + lp["pinion_rib_t"]
    for y0 in (yp_in, y_r):
        parts.append(("pinion bearing", "steel", ring_y(pb[0] / 2, pb[1] / 2, y0, y0 + pb[2], 0.0, zc)))
    parts.append(("pinion", "gear", cyl_y(14.1 / 2, 11.8, 16.3, 0.0, zc)
                  .fuse(cyl_y(pb[0] / 2, 11.8, y_r + pb[2] + 3, 0.0, zc))))
    fy, h = up["tower_face_y"], lambda v: zc + v
    parts.append(("shock tower", "carbon", box(-18, 18, fy - up["tower_plate_t"], fy,
                                               h(up["tower_keepout_h"] + 0.5), h(up["wall_top_h"] + 8))))
    parts.append(("top brace", "carbon", box(-19, 19, up["deck_end_y"], 40,
                                             h(up["deck_h"]), h(up["deck_h"]) + 2)))
    return parts


def draw_assembly(ax, items, view, sub=1.2):
    tris, cols = [], []
    for key, shape in items:
        t = subdivide(tess(shape), sub)
        tris.append(t)
        cols.append(np.tile(COL[key], (len(t), 1)))
    return draw_mesh(ax, np.concatenate(tris), view, tri_colors=np.concatenate(cols), depth_cue=0.35)


def draw_sections(ax, items, origin, normal, right, up_dir):
    for key, shape in items:
        tris, lines = section(shape, origin, normal, right, up_dir)
        if not tris:
            continue
        ax.add_collection(PolyCollection(tris, facecolors=[COL[key]], edgecolors=[COL[key]], lw=0.3))
        for ln in lines:
            ax.plot(ln[:, 0], ln[:, 1], color="k", lw=0.5)


def preview(path, lp, up, lower, upper):
    zc, yd = lp["axis_z"], lp["diff_axis_y"]
    fig = plt.figure(figsize=(15, 10))
    fig.suptitle("Carten T410R upper bulkhead, new design (shock tower holes and top brace height measured, "
                 "contact face and top brace position not yet measured)", fontsize=12, y=0.985)
    for rect, view, title in (([0.0, 0.5, 0.33, 0.44], iso_basis(-55, 30), "Upper part, view from the outer side"),
                              ([0.33, 0.5, 0.33, 0.44], iso_basis(125, 30), "Upper part, view from the pinion side"),
                              ([0.02, 0.03, 0.3, 0.42], iso_basis(-120, -40), "Upper part, underside")):
        ax = fig.add_axes(rect)
        lo, hi = draw_assembly(ax, [("upper", upper.val())], view)
        frame(ax, lo, hi, pad=(2, 2, 2, 2), title=title)

    parts = drivetrain(lp, up)
    ax = fig.add_axes([0.66, 0.5, 0.34, 0.44])
    items = [("lower", lower.val()), ("upper", upper.val())] + [(k, s) for _, k, s in parts]
    lo, hi = draw_assembly(ax, items, iso_basis(-60, 25), sub=1.6)
    frame(ax, lo, hi, pad=(2, 2, 2, 2), title="Assembly with shock tower and top brace (dark grey)")

    sec_items = [("lower", lower.val()), ("upper", upper.val())] + [(k, s) for _, k, s in parts]
    ax = fig.add_axes([0.33, 0.03, 0.33, 0.42])
    draw_sections(ax, sec_items, (0, yd, 0), (0, 1, 0), (-1, 0, 0), (0, 0, 1))
    frame(ax, (-22, -1), (22, zc + up["wall_top_h"] + 9), pad=(0, 0, 0, 0),
          title="Section through the diff axis, seen from the pinion side")
    ax = fig.add_axes([0.66, 0.03, 0.34, 0.42])
    draw_sections(ax, sec_items, (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
    frame(ax, (-33, -1), (36, zc + up["wall_top_h"] + 9), pad=(0, 0, 0, 0),
          title="Section along the pinion axis (x = 0)")
    fig.savefig(path, dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- measurement sheet
def dim_px(ax, p1, p2, n, off=(0, 0), txt=(0, 0)):
    """Dimension line between two pixel positions of a photo, balloon at the middle + txt."""
    a = np.asarray(p1, float) + off
    b = np.asarray(p2, float) + off
    ax.annotate("", xy=a, xytext=b, arrowprops=dict(arrowstyle="<|-|>", color=DIM_COLOR, lw=1.2,
                                                    shrinkA=0, shrinkB=0, mutation_scale=9))
    m = (a + b) / 2 + txt
    balloon(ax, m[0], m[1], n, r=48)


def lead_px(ax, p, q, n):
    ax.plot([p[0], q[0]], [p[1], q[1]], color=DIM_COLOR, lw=1.0)
    ax.plot([p[0]], [p[1]], "o", color=DIM_COLOR, ms=3)
    balloon(ax, q[0], q[1], n, r=48)


def photo_ax(fig, rect, path, title):
    ax = fig.add_axes(rect)
    im = plt.imread(path)
    ax.imshow(im)
    ax.set_xlim(0, im.shape[1])
    ax.set_ylim(im.shape[0], 0)
    ax.axis("off")
    ax.set_title(title, fontsize=9, loc="left")
    return ax


ROWS = [
    # (no, priority, feature, how to measure, model, caliper value)
    ("U1", "A", "Shock tower holes: spacing across (x)", "inside jaws, far edge to far edge, minus hole diameter",
     "19.1", "19.1"),
    ("U2", "A", "Shock tower holes: spacing up/down (one ear)", "as U1", "6.1", "6.1"),
    ("U3", "A", "Lower shock tower holes: height of the centre above the parting face",
     "depth rod to the lower hole edge, plus d/2", "22.5", "22.5"),
    ("U4", "B", "Shock tower holes: diameter / length (through)", "inside jaws / depth rod", "M3: 2.5 / 6.0",
     "2.9 / 5.8"),
    ("U5", "A", "Contact face of the shock tower to the outer edge of the lip opening at the parting face (y)",
     "square against the contact face, depth rod", "face 0.3 inside", ""),
    ("U6", "A", "Contact face of the shock tower to the outer end face (y)", "square against the face, depth rod",
     "20.2", ""),
    ("U7", "A", "Top brace holes: spacing across (x)", "as U1", "25.6", "25.6"),
    ("U8", "A", "Top brace hole to the screw hole on the pinion side (y)", "as U1", "6.94", ""),
    ("U9", "A", "Top brace contact face (top of the 2 raised bosses): height above the parting face",
     "part on its parting face, depth rod", "15.4", "15.4"),
    ("U10", "B", "Ear tops: height above the parting face", "as U9", "31.5", "31.5"),
    ("U11", "A", "Shock towers (front and rear): lower hole centre to the lowest edge of the tower",
     "on the shock tower, depth rod", "4.7", ""),
    ("U12", "B", "Outer end face to the centre of the outer screw holes (y)", "depth rod, plus d/2", "4.2", ""),
    ("U13", "A", "Scan of both shock towers with a ruler on the glass (gives U1, U2 and U11 directly)",
     "flatbed scanner, 600 to 1200 dpi", "-", ""),
    ("U14", "A", "Rear end of the top brace: where do the 2 screws M3x18 with the block NBA201 go?",
     "look (manual step 25)", "open", ""),
]


def sheet(path, photos):
    with PdfPages(path) as pdf:
        fig = plt.figure(figsize=A4_LANDSCAPE)
        fig.text(0.04, 0.955, "Measurement sheet - stock upper bulkhead - page 1: interfaces",
                 fontsize=14, fontweight="bold")
        fig.text(0.04, 0.925, "Interfaces of the stock upper part that the new design must keep: shock tower "
                 "(4 screws M3x8) and top brace (2 screws M3x8). Parting face = face on the lower part.",
                 fontsize=8.5, color="#444")
        ax = photo_ax(fig, [0.02, 0.06, 0.3, 0.82], photos["end_view"], "View from the outer side")
        dim_px(ax, (512, 244), (950, 244), "U1", off=(0, -95))
        ax.plot([512, 512], [244, 140], color=DIM_COLOR, lw=0.6)
        ax.plot([950, 950], [244, 140], color=DIM_COLOR, lw=0.6)
        dim_px(ax, (1060, 244), (1060, 366), "U2", txt=(55, 0))
        ax.plot([950, 1070], [244, 244], color=DIM_COLOR, lw=0.6)
        ax.plot([950, 1070], [366, 366], color=DIM_COLOR, lw=0.6)
        dim_px(ax, (330, 368), (330, 925), "U3", txt=(-60, 0))
        ax.plot([330, 512], [368, 368], color=DIM_COLOR, lw=0.6)
        lead_px(ax, (950, 366), (1110, 720), "U4")
        dim_px(ax, (1150, 174), (1150, 925), "U10", txt=(0, 60))
        ax.plot([1000, 1160], [174, 174], color=DIM_COLOR, lw=0.6)
        lead_px(ax, (540, 495), (700, 640), "U11")

        ax = photo_ax(fig, [0.33, 0.47, 0.42, 0.41], photos["side_view"], "Side view (outer end on the right)")
        lead_px(ax, (1034, 920), (1180, 820), "U5")
        ax.plot([1034, 1034], [130, 950], color=DIM_COLOR, lw=0.8, ls="--")
        dim_px(ax, (1034, 975), (1594, 975), "U6", txt=(0, -40))
        dim_px(ax, (470, 466), (470, 934), "U9", txt=(-45, 0))
        ax.plot([470, 560], [466, 466], color=DIM_COLOR, lw=0.6)

        ax = photo_ax(fig, [0.33, 0.04, 0.42, 0.41], photos["top_view"], "Top view (outer end on the left)")
        dim_px(ax, (862, 164), (866, 678), "U7", txt=(-60, 0))
        dim_px(ax, (862, 110), (1000, 110), "U8", txt=(0, -40))
        ax.plot([862, 862], [164, 100], color=DIM_COLOR, lw=0.6)
        ax.plot([1000, 1000], [240, 100], color=DIM_COLOR, lw=0.6)
        dim_px(ax, (83, 432), (166, 432), "U12", txt=(0, 45))
        ax.plot([166, 166], [216, 440], color=DIM_COLOR, lw=0.6)

        fig.text(0.77, 0.86, "Notes", fontsize=10, fontweight="bold")
        notes = ["Hole spacings: inside jaws from far edge",
                 "to far edge, minus the hole diameter.",
                 "Heights: part on its parting face on a",
                 "flat surface, depth rod.",
                 "U5: the contact face is almost above the",
                 "edge of the lip opening (side view).",
                 "Write + if the face is further out than",
                 "the edge, - if it is further in.",
                 "U13 (scan of the shock towers) is the",
                 "most accurate source for U1, U2, U11.",
                 "U14: the manual shows 2 screws M3x18",
                 "and a block NBA201 at the rear end of",
                 "the top brace (step 25)."]
        for i, t in enumerate(notes):
            fig.text(0.77, 0.83 - i * 0.025, t, fontsize=7.6)
        fig.text(0.96, 0.02, "Carten T410R - upper bulkhead - measurement sheet", fontsize=7, ha="right",
                 color="#666")
        pdf.savefig(fig, dpi=200)
        plt.close(fig)

        fig = plt.figure(figsize=A4_LANDSCAPE)
        fig.text(0.04, 0.955, "Measurement sheet - stock upper bulkhead - page 2: values", fontsize=14,
                 fontweight="bold")
        fig.text(0.04, 0.925, "Priority A: interfaces of the new design. Priority B: shape and checks. "
                 "Rows without a caliper value are open, their model values are estimates from photos. Values in mm.", fontsize=8.5, color="#444")
        ax = fig.add_axes([0.03, 0.08, 0.94, 0.82])
        ax.axis("off")
        cols = [0.0, 0.045, 0.085, 0.53, 0.8, 0.885]
        heads = ["No.", "Prio", "Feature", "How to measure", "Model", "Caliper value"]
        ytop = 0.98
        for c, t in zip(cols, heads):
            ax.text(c, ytop, t, fontsize=8.5, fontweight="bold", va="center", transform=ax.transAxes)
        dy = 0.9 / (len(ROWS) + 1)
        for i, row in enumerate(ROWS):
            y = ytop - (i + 1) * dy
            if i % 2 == 0:
                ax.add_patch(plt.Rectangle((0, y - dy / 2), 1, dy, transform=ax.transAxes, color="#eef2f6",
                                           zorder=0))
            for c, t in zip(cols, row):
                ax.text(c, y, t, fontsize=7.6, va="center", transform=ax.transAxes)
            if not row[5]:
                ax.plot([cols[5], 0.995], [y - dy * 0.3, y - dy * 0.3], color="#888", lw=0.5,
                        transform=ax.transAxes)
        fig.text(0.96, 0.02, "Carten T410R - upper bulkhead - measurement sheet", fontsize=7, ha="right",
                 color="#666")
        pdf.savefig(fig, dpi=200)
        plt.close(fig)
        pdf.infodict()["Title"] = "T410R upper bulkhead - measurement sheet"


def main():
    parser = argparse.ArgumentParser(description="Preview and measurement sheet of the upper bulkhead.")
    parser.add_argument("--lower-params", default="cad/bulkhead/bulkhead_lower_parameters.json")
    parser.add_argument("--params", default="cad/bulkhead/bulkhead_upper_parameters.json")
    parser.add_argument("--preview", default="photos/cad_bulkhead_upper_preview.png")
    parser.add_argument("--sheet", default="cad/bulkhead/bulkhead_upper_measurement_sheet.pdf")
    args = parser.parse_args()

    lp = load_params(args.lower_params)
    up = load_params(args.params)
    lower = bulkhead_lower(lp)
    upper = bulkhead_upper(lp, up)
    preview(args.preview, lp, up, lower, upper)
    photos = {k: f"photos/bulkhead_upper_stock_{k}.jpg" for k in ("end_view", "side_view", "top_view")}
    sheet(args.sheet, photos)
    print(f"Wrote {args.preview} and {args.sheet}")


if __name__ == "__main__":
    main()
