"""Generate a 1:1 print template (PDF) of the speedrun chassis plate (wide).

The template has two A4 pages in landscape format with a 20 mm overlap zone. It
shows the outline, the cutouts, the through holes with centre cross, the
countersinks (dashed), the outline of the chassis plate v2 (grey, dashed) and the
longer motor window (green, dashed). Each page has a 100 mm bar in x and in y.

The drawing is pre-scaled for a PDF viewer that prints at a fixed scale
(default 97 %): the content is enlarged by 1/print_scale, so that the printed
drawing is 1:1.

Usage (from the root directory of the repository):
    python scripts/cad/generate_print_template.py [--print-scale 0.97]

Without arguments, the script writes
cad/chassis_v2/chassis_plate_speedrun_wide/chassis_plate_T410R_speedrun_wide_1to1_A4x2_print97.pdf.
Use --output for another print scale.

Requires the package reportlab (pip install reportlab).
"""
import argparse
import json
import math

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

CAD = "cad/chassis_v2"
MARGIN = 5.0                     # printed mm between page edge and drawing area
ZONE = (150.0, 170.0)            # overlap zone (plate y), no holes inside
TOP = 329.1                      # upper end of page 2 (plate y)
BOTTOM = -6.0                    # lower end of page 1 (plate y)
RED, CSK, BLUE, GREY, GREEN = (0.85, 0, 0), (0.78, 0.2, 0.85), (0, 0.35, 0.8), (0.55, 0.55, 0.55), (0.1, 0.55, 0.3)


def ang(c, p):
    return math.degrees(math.atan2(p[1] - c[1], p[0] - c[0]))


def add_prims(path, prims):
    for q in prims:
        if q["type"] == "line":
            path.lineTo(*q["end"])
        else:
            a0, am, a1 = ang(q["center"], q["start"]), ang(q["center"], q["mid"]), ang(q["center"], q["end"])
            e = (a1 - a0) % 360
            sweep = e if (am - a0) % 360 < e else e - 360      # through mid
            cx, cy, r = q["center"][0], q["center"][1], q["r"]
            path.arcTo(cx - r, cy - r, cx + r, cy + r, a0, sweep)


def contour_path(c, prims, closed=True):
    p = c.beginPath()
    p.moveTo(*prims[0]["start"])
    add_prims(p, prims)
    if closed:
        p.close()
    return p


def window_extension(old_window, new_window):
    """Part of the new window above the start of the old +y corner arcs."""
    y_cut = max(p[k][1] for p in old_window for k in ("start", "end")) - \
        [p["r"] for p in old_window if p["type"] == "arc"][0]
    ext = []
    for p in new_window:
        if max(p["start"][1], p["end"][1]) <= y_cut + 1e-9:
            continue
        if p["type"] == "line" and min(p["start"][1], p["end"][1]) < y_cut:
            (xs, ys), (xe, ye) = p["start"], p["end"]
            cut = [xs + (y_cut - ys) / (ye - ys) * (xe - xs), y_cut]
            p = dict(p, start=cut) if ys < y_cut else dict(p, end=cut)
        ext.append(p)
    return ext


def text(c, x, y, s, size=2.2, color=(0, 0, 0), bold=False, anchor="l", rot=0):
    c.saveState()
    c.setFillColorRGB(*color)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.translate(x, y)
    c.rotate(rot)
    {"l": c.drawString, "c": c.drawCentredString, "r": c.drawRightString}[anchor](0, 0, s)
    c.restoreState()


def bar(c, x0, y0, horizontal, label):
    """100 mm scale bar with ticks every 10 mm."""
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.3)
    c.setDash()
    if horizontal:
        c.line(x0, y0, x0 + 100, y0)
        for i in range(11):
            c.line(x0 + 10 * i, y0, x0 + 10 * i, y0 + (4 if i in (0, 5, 10) else 2))
        text(c, x0 + 50, y0 - 3.2, label, 2.4, anchor="c")
    else:
        c.line(x0, y0, x0, y0 + 100)
        for i in range(11):
            c.line(x0, y0 + 10 * i, x0 - (4 if i in (0, 5, 10) else 2), y0 + 10 * i)
        text(c, x0 + 3.2, y0 + 50, label, 2.4, anchor="c", rot=90)


def notes(c, x, y, page, plate, print_scale):
    hid = {h["id"]: h for h in plate["holes"]}
    d1123 = math.hypot(hid["H11"]["x"] - hid["H23"]["x"], hid["H11"]["y"] - hid["H23"]["y"])
    pct = f"{print_scale * 100:g}"
    k_, g_ = (0, 0, 0), (0.3, 0.3, 0.3)
    lines = [
        ("Carten T410R speedrun chassis plate (wide)", 3.0, True, k_),
        ("1:1 template, A4 landscape, page %d of 2" % page, 2.6, True, k_),
        ("", 1.2, False, k_),
        (f"PRINT AT {pct} % (scale of your PDF viewer).", 2.3, True, k_),
        (f"The drawing is pre-scaled to {100 / print_scale:.2f} % (100/{pct}).", 2.2, False, k_),
        ("Check both 100 mm bars with a ruler before use.", 2.2, False, k_),
        (f'Printed at 100 % ("actual size") it is {(1 / print_scale - 1) * 100:.1f} % too large.', 2.2, False, k_),
        ("", 1.2, False, k_),
        ("Top view (side without countersinks):", 2.2, False, k_),
        ("place the part with the countersinks facing down.", 2.2, False, k_),
        (f"Red: through holes Ø{plate['hole_d']:g} mm with centre cross.", 2.2, False, k_),
        (f"Dashed circles: countersinks Ø{plate['csk_d']:g} mm (bottom face).", 2.2, False, k_),
        ("Blue dashed: 20 mm overlap zone. Lay page 2 over", 2.2, False, BLUE),
        ("page 1 so that both pairs of lines coincide.", 2.2, False, BLUE),
        ("Grey dashed: outline of the chassis plate v2.", 2.2, False, g_),
        ("Green dashed: longer motor window (3660 motor).", 2.2, False, g_),
        ("After joining: H11 to H23 = %.2f mm (centres)." % d1123, 2.2, False, k_),
    ]
    for s, size, bold, col in lines:
        text(c, x, y, s, size, col, bold)
        y -= max(size * 1.45, 1.2)


def main():
    parser = argparse.ArgumentParser(description="Generate the 1:1 print template of the speedrun chassis plate (wide).")
    parser.add_argument("--geometry", default=f"{CAD}/chassis_plate_speedrun_wide/chassis_plate_speedrun_wide_geometry.json")
    parser.add_argument("--reference", default=f"{CAD}/chassis_plate/chassis_plate_v2_geometry.json")
    parser.add_argument("--window", default=f"{CAD}/chassis_plate_speedrun_wide_motor10/chassis_plate_speedrun_wide_motor10_geometry.json")
    parser.add_argument("--print-scale", type=float, default=0.97, help="scale of the PDF viewer (default 0.97)")
    parser.add_argument("--output", default=f"{CAD}/chassis_plate_speedrun_wide/chassis_plate_T410R_speedrun_wide_1to1_A4x2_print97.pdf")
    args = parser.parse_args()

    plate, ref, m10 = (json.load(open(p, encoding="utf-8")) for p in (args.geometry, args.reference, args.window))
    page_w, page_h = landscape(A4)                   # pt
    k = mm / args.print_scale                        # pt per printed mm
    pw, ph = page_w / k, page_h / k                  # page size in printed mm
    xmax = pw / 2 - MARGIN                           # drawing area x = -xmax..xmax (plate x = 0 at page centre)
    dh = ph - 2 * MARGIN                             # height of the drawing area in printed mm
    tiles = [(BOTTOM, BOTTOM + dh), (TOP - dh, TOP)]
    if not (tiles[0][1] > ZONE[1] and tiles[1][0] < ZONE[0]):
        raise ValueError("the overlap zone is not on both pages")
    if any(ZONE[0] - plate["csk_d"] / 2 < h["y"] < ZONE[1] + plate["csk_d"] / 2 for h in plate["holes"]):
        raise ValueError("a hole lies in the overlap zone")
    extension = window_extension(plate["cutouts"]["window"], m10["cutouts"]["window"])
    pct = f"{args.print_scale * 100:g}"

    c = canvas.Canvas(args.output, pagesize=landscape(A4))
    c.setTitle(f"Speedrun chassis plate (wide) - 1:1 template for printing at {pct} %")
    c.setAuthor("prototyping.rc.speedrun")
    c.setSubject("Carten T410R speedrun chassis plate (wide), 2 x A4 landscape")
    for page, (y0, y1) in enumerate(tiles, start=1):
        c.saveState()
        c.scale(k, k)                                # 1 unit = 1 printed mm
        c.translate(pw / 2, MARGIN - y0)             # plate coordinates
        clip = c.beginPath()
        clip.rect(-xmax, y0, 2 * xmax, y1 - y0)
        c.clipPath(clip, stroke=0, fill=0)
        # outline and cutouts
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0.25)
        c.setDash()
        c.drawPath(contour_path(c, plate["outline"]), stroke=1, fill=0)
        for cut in plate["cutouts"].values():
            c.drawPath(contour_path(c, cut), stroke=1, fill=0)
        # reference lines
        c.setLineWidth(0.18)
        c.setStrokeColorRGB(*GREY)
        c.setDash([1.5, 1.0])
        c.drawPath(contour_path(c, ref["outline"]), stroke=1, fill=0)
        c.setStrokeColorRGB(*GREEN)
        c.setDash([1.2, 0.8])
        c.drawPath(contour_path(c, extension, closed=False), stroke=1, fill=0)
        # holes
        for h in plate["holes"]:
            x, y = h["x"], h["y"]
            c.setDash([0.6, 0.5])
            c.setLineWidth(0.15)
            c.setStrokeColorRGB(*CSK)
            c.circle(x, y, plate["csk_d"] / 2, stroke=1, fill=0)
            c.setDash()
            c.setLineWidth(0.2)
            c.setStrokeColorRGB(*RED)
            c.circle(x, y, plate["hole_d"] / 2, stroke=1, fill=0)
            c.setLineWidth(0.1)
            c.setStrokeColorRGB(0, 0, 0)
            c.line(x - 2.6, y, x + 2.6, y)
            c.line(x, y - 2.6, x, y + 2.6)
            text(c, x + 2.4, y + 2.4, h["id"], 1.9, (0.2, 0.2, 0.2))
        # overlap zone
        c.setStrokeColorRGB(*BLUE)
        c.setLineWidth(0.3)
        c.setDash([2.0, 1.2])
        for yz in ZONE:
            c.line(-xmax, yz, xmax, yz)
        text(c, -xmax + 1, ZONE[0] + 8.6, "overlap zone (20 mm)", 2.2, BLUE)
        # scale bars and notes
        if page == 1:
            bar(c, 36.0, 4.0, True, "100 mm (x)")
            bar(c, 128.0, 40.0, False, "100 mm (y)")
            notes(c, -xmax + 1, 46.0, page, plate, args.print_scale)
            text(c, 0, -4.2, "End B (H01 to H04)", 2.4, anchor="c")
        else:
            bar(c, 36.0, 316.0, True, "100 mm (x)")
            bar(c, 128.0, 212.0, False, "100 mm (y)")
            notes(c, -xmax + 1, 325.5, page, plate, args.print_scale)
            text(c, 30.0, 326.2, "End A (H34 to H36)", 2.4)
        c.restoreState()
        c.showPage()
    c.save()
    print(f"Wrote {args.output}: printed page {pw:.2f} x {ph:.2f} mm, "
          f"page 1 y {tiles[0][0]:.1f} to {tiles[0][1]:.1f}, page 2 y {tiles[1][0]:.1f} to {tiles[1][1]:.1f}")


if __name__ == "__main__":
    main()
