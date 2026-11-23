"""Colour scheme of the CAD pictures: blue and grey shades only (owner, 2026-11-20).

One colour per group of parts, the same in all pictures (assembly, running gear, drive line, bulkheads, shock
towers, battery tray, front splitter, studies). Values are sRGB from 0 to 1. Annotations (dimensions, labels, markers
of new or closed holes) and the red and black battery wires (plus and minus) keep their own colours.
"""

PARTS = {
    # speedrun parts
    "plate": (0.24, 0.26, 0.29),          # chassis plate
    "lower": (0.27, 0.42, 0.62),          # lower bulkhead
    "upper": (0.43, 0.6, 0.8),            # upper bulkhead
    "brace": (0.56, 0.63, 0.72),          # top brace
    "tower_front": (0.17, 0.19, 0.23),    # shock towers
    "tower_rear": (0.17, 0.19, 0.23),
    "onepiece": (0.12, 0.16, 0.26),       # front splitter
    "battery_tray": (0.78, 0.81, 0.86),
    "battery": (0.11, 0.2, 0.4),
    "strap": (0.08, 0.08, 0.1),
    # further own parts and stock parts
    "pivot": (0.1, 0.1, 0.11),            # pivot blocks
    "shaft": (0.18, 0.38, 0.72),          # centre driveshaft
    "cup": (0.72, 0.74, 0.77),            # cup joints, outdrives, hinge pins
    "drive": (0.45, 0.47, 0.5),           # pinion shafts, pinions, spur gear, bearings
    "mount": (0.55, 0.6, 0.67),           # motor mount with cap
    "arm": (0.26, 0.35, 0.55),            # wishbones
    "diff": (0.16, 0.16, 0.18),           # differential case, spool
    "rodend": (0.12, 0.12, 0.13),
    "link": (0.78, 0.79, 0.82),           # turnbuckles, ball studs, nuts
    "upright": (0.12, 0.42, 0.82),        # C-hubs, knuckles, hub carriers
    "axle": (0.62, 0.64, 0.68),           # axles, hex hubs, pins, wheel bearings
    "cvd": (0.5, 0.52, 0.56),
    "steer": (0.36, 0.6, 0.9),            # steering, servo mount, sway bar holders
    "damper": (0.13, 0.24, 0.52),
    "spring": (0.62, 0.79, 0.95),
    "servo": (0.2, 0.2, 0.22),
    "swaybar": (0.4, 0.5, 0.62),
    "bodypost": (0.62, 0.63, 0.66),
    "screw": (0.07, 0.07, 0.08),          # hex socket screws (black oxide; picture of the assembly)
    # further groups of single pictures
    "gear": (0.5, 0.56, 0.66),            # ring gear, spur gear, pinions
    "bearing": (0.62, 0.64, 0.68),
    "motor": (0.27, 0.42, 0.62),          # motor can (studies)
    "motor_end": (0.62, 0.64, 0.68),
    "esc": (0.36, 0.6, 0.9),              # speed controller (studies)
    "receiver": (0.62, 0.79, 0.95),
    "study": (0.12, 0.42, 0.82),          # new part of a study (for example the dual motor mount)
    "wire": (0.5, 0.52, 0.56),            # motor wires
    "signal": (0.12, 0.42, 0.82),         # signal cables
    "print_a": (0.27, 0.42, 0.62),        # pieces of a test print
    "print_b": (0.43, 0.6, 0.8),
    "ghost": (0.86, 0.88, 0.91),          # reference outlines, removed material
}


def rgb(key):
    """sRGB tuple of a group of parts."""
    return PARTS[key]


def hexcolor(key):
    """Colour of a group of parts as '#rrggbb' (for matplotlib patches and lines)."""
    return "#" + "".join(f"{round(v * 255):02x}" for v in PARTS[key])
