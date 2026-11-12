"""Generate a DXF file for CNC manufacturing from a geometry JSON file.

The geometry JSON files (*_geometry.json) are stored in the part directories
of cad/chassis. The DXF file has the same layout as the DXF files in those
directories:

* DXF version R2010, units mm
* OUTLINE: outer contour (LINE and ARC entities)
* CUTOUT: windows and slots (LINE and ARC entities)
* HOLE_THROUGH: through holes (CIRCLE entities, diameter hole_d)
* CSK_BOTTOM_INFO: countersink diameter on the bottom face (CIRCLE entities,
  diameter csk_d, for information only). The layer is empty if csk_d is 0.
* NOTES: empty

Usage (from the root directory of the repository):
    python scripts/cad/generate_dxf.py <geometry.json> <output.dxf>

Example:
    python scripts/cad/generate_dxf.py \\
        cad/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_speedrun_wide_motor10_geometry.json \\
        cad/chassis/chassis_plate_speedrun_wide_motor10/chassis_plate_T410R_speedrun_wide_motor10.dxf

Requires the package ezdxf (pip install ezdxf).
"""
import argparse
import json
import math
from collections import Counter

import ezdxf
from ezdxf import units

# Layer name and AutoCAD color index
LAYERS = [
    ("OUTLINE", 7),
    ("CUTOUT", 7),
    ("HOLE_THROUGH", 1),
    ("CSK_BOTTOM_INFO", 3),
    ("NOTES", 2),
]

# Lines shorter than this are skipped (mm)
MIN_LINE_LENGTH = 1e-6


def angle_deg(center, point):
    """Angle of a point around a center in degrees."""
    return math.degrees(math.atan2(point[1] - center[1], point[0] - center[0]))


def add_contour(msp, primitives, layer):
    """Add the lines and arcs of a closed contour to the model space.

    Each primitive is a dict with the type "line" (start, end) or "arc"
    (start, mid, end, center, r). DXF arcs always run counterclockwise, so a
    clockwise arc is written with start and end swapped.
    """
    for p in primitives:
        if p["type"] == "line":
            length = math.hypot(p["end"][0] - p["start"][0], p["end"][1] - p["start"][1])
            if length > MIN_LINE_LENGTH:
                msp.add_line(p["start"], p["end"], dxfattribs={"layer": layer})
            continue
        center = p["center"]
        a_start = angle_deg(center, p["start"])
        a_mid = angle_deg(center, p["mid"])
        a_end = angle_deg(center, p["end"])
        counterclockwise = (a_mid - a_start) % 360 < (a_end - a_start) % 360
        if not counterclockwise:
            a_start, a_end = a_end, a_start
        msp.add_arc(center, p["r"], a_start, a_end, dxfattribs={"layer": layer})


def build_dxf(geometry):
    """Create the DXF document from the geometry data."""
    doc = ezdxf.new("R2010", setup=True)
    doc.units = units.MM
    doc.header["$MEASUREMENT"] = 1  # metric
    for name, color in LAYERS:
        doc.layers.add(name, color=color)

    msp = doc.modelspace()
    add_contour(msp, geometry["outline"], "OUTLINE")
    for contour in geometry["cutouts"].values():
        add_contour(msp, contour, "CUTOUT")
    for hole in geometry["holes"]:
        center = (hole["x"], hole["y"])
        msp.add_circle(center, geometry["hole_d"] / 2, dxfattribs={"layer": "HOLE_THROUGH"})
        if geometry.get("csk_d", 0) > 0:
            msp.add_circle(center, geometry["csk_d"] / 2, dxfattribs={"layer": "CSK_BOTTOM_INFO"})
    return doc


def main():
    parser = argparse.ArgumentParser(description="Generate a DXF file from a geometry JSON file.")
    parser.add_argument("geometry", help="geometry JSON file (*_geometry.json)")
    parser.add_argument("output", help="DXF file to write")
    args = parser.parse_args()

    with open(args.geometry, encoding="utf-8") as f:
        geometry = json.load(f)
    doc = build_dxf(geometry)
    doc.saveas(args.output)

    counts = Counter((e.dxf.layer, e.dxftype()) for e in doc.modelspace())
    summary = ", ".join(f"{layer} {kind} {n}" for (layer, kind), n in sorted(counts.items()))
    print(f"Wrote {args.output}: {summary}")


if __name__ == "__main__":
    main()
