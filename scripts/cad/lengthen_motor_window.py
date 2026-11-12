"""Lengthen the motor window of a chassis plate toward End A (+y).

All points of the window contour (start, mid, end, center) above the middle of
the window are moved by the given length in +y. The end edge at y min, the
x position of the long sides and the corner radii do not change. All other
features are copied unchanged.

Usage (from the root directory of the repository):
    python scripts/cad/lengthen_motor_window.py [--length 10]

Without arguments, the script reads the geometry data of the speedrun chassis
plate (wide) and writes the geometry data of the variant with the longer motor
window (chassis_plate_speedrun_wide_motor10_geometry.json).
"""
import argparse
import copy
import json

CAD = "cad/chassis"
DEFAULT_INPUT = f"{CAD}/chassis_plate_speedrun_wide/chassis_plate_speedrun_wide_geometry.json"
DEFAULT_OUTPUT = f"{CAD}/chassis_plate_speedrun_wide_motor10/chassis_plate_speedrun_wide_motor10_geometry.json"


def lengthen(geometry, length, cutout="window"):
    """Return a copy of the geometry data with the cutout lengthened in +y."""
    result = copy.deepcopy(geometry)
    contour = result["cutouts"][cutout]
    ys = [p[k][1] for p in contour for k in ("start", "end")]
    y_mid = (min(ys) + max(ys)) / 2
    moved = 0
    for p in contour:
        for k in ("start", "mid", "end", "center"):
            if k in p and p[k][1] > y_mid:
                p[k][1] += length
                moved += 1
    result["basis"] = geometry["basis"] + f" + motor window +{length:g} mm toward End A"
    return result, y_mid, moved


def main():
    parser = argparse.ArgumentParser(description="Lengthen the motor window toward End A (+y).")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="geometry JSON file to read")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="geometry JSON file to write")
    parser.add_argument("--length", type=float, default=10.0, help="extension in mm (default 10)")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        geometry = json.load(f)
    result, y_mid, moved = lengthen(geometry, args.length)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    ys = [p[k][1] for p in result["cutouts"]["window"] for k in ("start", "end")]
    print(f"Wrote {args.output}: {moved} points above y = {y_mid:.3f} moved by {args.length:g} mm, "
          f"window y {min(ys):.3f} to {max(ys):.3f}")


if __name__ == "__main__":
    main()
