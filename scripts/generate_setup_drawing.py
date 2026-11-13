#!/usr/bin/env python3
"""Generate a technical drawing of the latest setup sheet as an SVG file.

The drawing combines the fixed geometry of the Carten T410R (wheelbase, width
and tire diameter from the specs in `specs/`) with the values of the latest
setup sheet in `setup_sheets/`. It contains a side view, a plan view, a front
and a rear view, the parameter list, a revision table and a title block.

The GitHub workflow `build_setup_drawing.yml` runs this script whenever a setup
sheet changes and commits the result to `photos/latest_setup_drawing.svg` (light
theme, readme) and `docs/latest_setup_drawing.svg` (dark theme, dashboard).

Usage:
    python scripts/generate_setup_drawing.py [--output PATH] [--theme light|dark]
"""

import argparse
import json
import math
import re
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
SETUP_DIR = ROOT_DIR / "setup_sheets"
CHASSIS_SPEC = ROOT_DIR / "specs" / "mechanics" / "carten_t410r" / "spec_cartent410r.yaml"
TIRE_SPEC = ROOT_DIR / "specs" / "mechanics" / "wheels" / "spec_tires.yaml"
DEFAULT_OUTPUT = ROOT_DIR / "photos" / "latest_setup_drawing.svg"
FRONT_TOWER = ROOT_DIR / "cad" / "shock_tower" / "shock_tower_front_geometry.json"
REAR_TOWER = ROOT_DIR / "cad" / "shock_tower" / "shock_tower_rear_geometry.json"
LOWER_BULKHEAD = ROOT_DIR / "cad" / "bulkhead" / "bulkhead_lower_parameters.json"
SHEET_PATTERN = re.compile(r"^(\d+)_setup_sheet\.ya?ml$")

# Scale 1:2 at 96 dpi: 1 mm on the car equals 0.5 mm on the sheet.
S = 96 / 25.4 / 2

SHEET_WIDTH = 1440
MARGIN = 30

PAPER = "#fbfbf8"
INK = "#1f2933"
INK_SOFT = "#52606d"
INK_FAINT = "#9aa5b1"
ACCENT = "#c2410c"
PART = "#eef1f4"
TIRE = "#cfd5dc"
CARBON = "#c3cad2"
FONT = "Arial, Helvetica, 'Liberation Sans', sans-serif"

# The dark theme matches the setup dashboard. It replaces each color of the
# light theme one to one in the finished drawing.
DARK_THEME = {
    PAPER: "#000000",
    INK: "#e6e6e6",
    INK_SOFT: "#aaaaaa",
    INK_FAINT: "#5c5c5c",
    ACCENT: "#ff8c42",
    PART: "#161616",
    TIRE: "#2e2e2e",
    CARBON: "#2b2b2b",
}

# Schematic component layout in millimeters, estimated from photos of the car.
# x: distance behind the front axle, y: lateral offset (positive = right side
# of the car), z: height above ground.
PLATE_X = (-48.0, 302.0)
PLATE_HALF_WIDTH = 52.0
PLATE_THICKNESS = 2.03  # bottom plate, measured, see spec_cartent410r.yaml
BATTERY = {"x": (70.0, 208.0), "y": (-54.0, -8.0), "height": 35.0}  # 138 x 46 x 35 mm
ESC = {"x": (100.0, 147.0), "y": (10.0, 46.0)}
SERVO = {"x": (34.0, 54.2), "y": (6.0, 46.8)}  # low profile servo 40.8 x 20.2 mm
GYRO = {"x": (36.0, 57.0), "y": (-40.0, -19.0)}  # 21 x 21 mm
MOTOR_REAR_X = 225.0
GEAR_PLANE_X = (230.0, 235.0)
CENTER_SHAFT_Y = -2.0
CENTER_SHAFT_Z = 35.0
GEAR_PITCH_DP = 48
TOWER_TOP = 70.0
SHOCK_TOP = 65.5

# Keys whose value null means that the part is not installed.
COMPONENT_KEYS = {"droop_screws", "sway_bars", "servo_saver"}

# Display names and units of known setup sheet keys. Unknown keys are
# formatted from their name, see describe_key().
KEY_INFO = {
    "front_toe_deg": ("Toe front", "°"),
    "rear_toe_deg": ("Toe rear", "°"),
    "front_camber_deg": ("Camber front", "°"),
    "rear_camber_deg": ("Camber rear", "°"),
    "front_caster_deg": ("Caster front", "°"),
    "ride_height_front_mm": ("Ride height front", " mm"),
    "ride_height_rear_mm": ("Ride height rear", " mm"),
    "spring_rate_stiffness": ("Spring rate", ""),
    "shock_oil_wt": ("Shock oil", " wt"),
    "spring_preload_mm": ("Spring preload", " mm"),
    "droop_screws": ("Droop screws", ""),
    "sway_bars": ("Sway bars", ""),
    "servo_saver": ("Servo saver", ""),
    "ackermann_angle_diff": ("Ackermann", ""),
    "tire_type": ("Tire type", ""),
    "tire_hardness_shore": ("Tire hardness", " Shore"),
    "tire_width_rear_mm": ("Tire width rear", " mm"),
    "tire_width_front_mm": ("Tire width front", " mm"),
    "front_diff": ("Differential front", ""),
    "rear_diff": ("Differential rear", ""),
    "pinion_gear_t": ("Pinion", " T"),
    "spur_gear_t": ("Spur gear", " T"),
    "internal_gear_ratio": ("Internal ratio", ""),
    "final_drive_ratio": ("Final drive ratio", ""),
    "lipo_cells": ("LiPo cells", ""),
    "lipo_capacity_mah": ("LiPo capacity", " mAh"),
    "max_discharge_c": ("Max. discharge", " C"),
    "max_current_a": ("Max. current", " A"),
    "motor_type": ("Motor size", ""),
    "motor_kv": ("Motor rating", " kV"),
    "esc_a": ("ESC rating", " A"),
    "esc_punch_level": ("ESC punch level", ""),
    "bec_voltage_v": ("BEC voltage", " V"),
    "steering_torque_nm": ("Servo torque", " Nm"),
    "steering_type": ("Servo type", ""),
    "dual_rate": ("Dual rate", ""),
    "throttle_curve": ("Throttle curve", ""),
    "steering_curve": ("Steering curve", ""),
    "steering_trim_right": ("Steering trim right", ""),
    "steering_base_trim_right": ("Base trim right", ""),
    "steering_trim_left": ("Steering trim left", ""),
    "steering_base_trim_left": ("Base trim left", ""),
    "gyro_gain": ("Gyro gain", ""),
}
UNIT_SUFFIXES = (
    ("_deg", "°"), ("_mm", " mm"), ("_wt", " wt"), ("_kmh", " km/h"), ("_mah", " mAh"),
    ("_nm", " Nm"), ("_kv", " kV"), ("_shore", " Shore"), ("_pct", " %"), ("_a", " A"),
    ("_v", " V"), ("_c", " C"), ("_t", " T"),
)
ACRONYMS = {"esc": "ESC", "bec": "BEC", "lipo": "LiPo", "rpm": "rpm", "gps": "GPS"}
SECTION_TITLES = {
    "suspension_and_geometry": "Suspension and geometry",
    "drivetrain": "Drivetrain",
    "electronics_and_control": "Electronics and control",
}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def read_yaml(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except FileNotFoundError:
        return {}


def nested(data, *keys, default=None):
    for key in keys:
        if not isinstance(data, dict) or data.get(key) is None:
            return default
        data = data[key]
    return data


def as_number(value, default=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


class SetupSheet:
    def __init__(self, number, path, data):
        self.number = number
        self.path = path
        self.meta = data.get("meta") or {}
        self.properties = data.get("properties") or {}

    @property
    def version(self):
        return self.meta.get("version", self.number)

    @property
    def date(self):
        return str(self.meta.get("date") or "n/a")[:10]

    def section(self, name):
        return self.properties.get(name) or {}

    def value(self, section, key):
        return self.section(section).get(key)

    def number_value(self, section, key, default=None):
        return as_number(self.value(section, key), default)


def load_setup_sheets():
    sheets = []
    for path in SETUP_DIR.iterdir():
        match = SHEET_PATTERN.match(path.name)
        if match and path.is_file():
            sheets.append(SetupSheet(int(match.group(1)), path, read_yaml(path)))
    return sorted(sheets, key=lambda sheet: sheet.number)


def load_vehicle():
    chassis = read_yaml(CHASSIS_SPEC)
    tires = read_yaml(TIRE_SPEC)
    dimensions = nested(chassis, "spec", "properties", "carten_t410r", "dimensions", default={})
    return {
        "wheelbase": as_number(dimensions.get("wheelbase_mm"), 258.0),
        "width": as_number(dimensions.get("track_width_mm"), 190.0),
        "tire_diameter": as_number(nested(tires, "spec", "properties", "dimensions", "diameter_mm"), 64.0),
    }


def load_tower(path=FRONT_TOWER, bulkhead=LOWER_BULKHEAD):
    """Speedrun shock tower from the CAD files: outline (polygon), holes (u, v, radius, id) and
    thickness. u: across the car (positive = right side), v: height above the top face of the
    bottom plate (bottom face of the bulkheads). Returns None if a file is missing."""
    try:
        geometry = json.loads(path.read_text(encoding="utf-8"))
        parting = json.loads(bulkhead.read_text(encoding="utf-8"))["parameters"]["axis_z"]["value"]
    except (OSError, ValueError, KeyError):
        return None
    outline = []
    for prim in geometry["outline"]:
        if prim["type"] != "arc":
            outline.append(tuple(prim["start"]))
            continue
        cx, cy = prim["center"]
        a0, am, a1 = (math.atan2(prim[k][1] - cy, prim[k][0] - cx) for k in ("start", "mid", "end"))
        sweep = (a1 - a0) % (2 * math.pi)
        if (am - a0) % (2 * math.pi) > sweep:  # clockwise arc
            sweep -= 2 * math.pi
        steps = max(2, math.ceil(abs(sweep) / math.radians(10)))
        outline += [(cx + prim["r"] * math.cos(a0 + sweep * k / steps),
                     cy + prim["r"] * math.sin(a0 + sweep * k / steps)) for k in range(steps)]
    outline = [(u, v + parting) for u, v in outline]
    holes = [(h["x"], h["y"] + parting, h.get("d", geometry["hole_d"]) / 2, h["id"]) for h in geometry["holes"]]
    right = {hole[3][0]: (hole[0], hole[1]) for hole in holes if hole[0] > 0}
    return {"outline": outline, "holes": holes, "thickness": geometry["thickness"],
            "bottom": min(v for _, v in outline), "top": max(v for _, v in outline),
            "damper": right["D"], "camber": right["C"]}


# ---------------------------------------------------------------------------
# Formatting of setup values
# ---------------------------------------------------------------------------

def humanize(name):
    words = [ACRONYMS.get(word, word) for word in name.split("_") if word]
    text = " ".join(words)
    return text[:1].upper() + text[1:]


def describe_key(key):
    if key in KEY_INFO:
        return KEY_INFO[key]
    for suffix, unit in UNIT_SUFFIXES:
        if key.endswith(suffix) and len(key) > len(suffix):
            return humanize(key[: -len(suffix)]), unit
    return humanize(key), ""


def format_number(value):
    if isinstance(value, float):
        text = str(value)
        return text if len(text) <= 8 else f"{value:.4g}"
    return str(value)


def format_length(value):
    """Formats a dimension: 258.0 -> 258, 2.25 -> 2.25."""
    return str(int(value)) if float(value).is_integer() else format_number(value)


def format_value(key, value):
    unit = describe_key(key)[1]
    if value is None:
        return "none" if key in COMPONENT_KEYS else "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, dict):
        values = list(value.values())
        if values and all(item == values[0] for item in values):
            return f"{format_value(key, values[0])} (all)"
        corners = {"front_left": "FL", "front_right": "FR", "rear_left": "RL", "rear_right": "RR"}
        parts = [f"{corners.get(name, humanize(name))} {format_value('', item)}" for name, item in value.items()]
        return " / ".join(parts) + unit
    if isinstance(value, (int, float)):
        text = format_number(value)
        if key == "lipo_cells":
            return f"{text}S"
        if key in ("internal_gear_ratio", "final_drive_ratio"):
            return f"{text} : 1"
        if key in ("front_toe_deg", "rear_toe_deg") and value != 0:
            kind = "toe-in" if value > 0 else "toe-out"
            return f"{format_number(abs(value))}° {kind}"
        return f"{text}{unit}"
    return str(value)


def compared_keys(previous, current):
    """Yields the (section, key) pairs of both sheets, in the order of the current sheet."""
    sections = list(current.properties) + [name for name in previous.properties if name not in current.properties]
    for section in sections:
        old, new = previous.section(section), current.section(section)
        for key in list(new) + [name for name in old if name not in new]:
            yield section, key


def changed_keys(previous, current):
    """Returns the (section, key) pairs that differ from the previous sheet."""
    if previous is None:
        return set()
    changes = set()
    for section, key in compared_keys(previous, current):
        old, new = previous.section(section), current.section(section)
        if key not in old or key not in new or old[key] != new[key]:
            changes.add((section, key))
    return changes


def describe_changes(previous, current):
    if previous is None:
        return ["Initial setup sheet"]
    items = []
    for section, key in compared_keys(previous, current):
        old, new = previous.section(section), current.section(section)
        label = describe_key(key)[0]
        if key not in old:
            items.append(f"{label} {format_value(key, new[key])} (added)")
        elif key not in new:
            items.append(f"{label} removed")
        elif old[key] != new[key]:
            items.append(f"{label} {format_value(key, old[key])} → {format_value(key, new[key])}")
    return items or ["No parameter changes"]


def text_width(text, size):
    """Approximate width of a text in Arial, used for line breaks and layout."""
    width = 0.0
    for char in text:
        if char in "ijl|":
            width += 0.23
        elif char in ".,:;'!() ":
            width += 0.29
        elif char in "ftrI-/":
            width += 0.34
        elif char in "mwMW":
            width += 0.84
        elif char == "→":
            width += 1.0
        elif char.isupper():
            width += 0.68
        elif char.isdigit():
            width += 0.56
        else:
            width += 0.53
    return width * size


def wrap_items(items, max_width, size, max_lines=2, separator=" · "):
    lines, current = [], ""
    for item in items:
        candidate = item if not current else current + separator + item
        if text_width(candidate, size) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = item
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1] + " …"
    clipped = []
    for line in lines:
        while text_width(line, size) > max_width and len(line) > 4:
            line = line[:-3].rstrip() + "…"
        clipped.append(line)
    return clipped


# ---------------------------------------------------------------------------
# SVG primitives
# ---------------------------------------------------------------------------

def num(value):
    text = f"{value:.2f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)
    return "0" if text == "-0" else text


def tag(name, content=None, **attrs):
    parts = [name]
    for key, value in attrs.items():
        if value is None:
            continue
        key = "class" if key == "cls" else key.rstrip("_").replace("_", "-")
        text = num(value) if isinstance(value, (int, float)) else str(value)
        parts.append(f'{key}="{escape(text, {chr(34): "&quot;"})}"')
    if content is None:
        return "<" + " ".join(parts) + "/>"
    return "<" + " ".join(parts) + ">" + content + "</" + name + ">"


def points(pts):
    return " ".join(f"{num(x)},{num(y)}" for x, y in pts)


def add(p, q, factor=1.0):
    return (p[0] + q[0] * factor, p[1] + q[1] * factor)


def unit_vector(p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    length = math.hypot(dx, dy) or 1.0
    return dx / length, dy / length


class Projection:
    """Maps view coordinates in millimeters to sheet coordinates in pixels."""

    def __init__(self, origin_x, origin_y, mirror=False):
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.direction = -1.0 if mirror else 1.0

    def __call__(self, u, v):
        return (self.origin_x + self.direction * u * S, self.origin_y - v * S)

    def poly(self, pts):
        return [self(u, v) for u, v in pts]


class Sheet:
    def __init__(self):
        self.items = []

    def add(self, markup):
        self.items.append(markup)

    def line(self, p, q, cls):
        self.add(tag("line", x1=p[0], y1=p[1], x2=q[0], y2=q[1], cls=cls))

    def polyline(self, pts, cls):
        self.add(tag("polyline", points=points(pts), cls=cls))

    def polygon(self, pts, cls):
        self.add(tag("polygon", points=points(pts), cls=cls))

    def rect(self, x, y, w, h, cls=None, rx=None, fill=None):
        self.add(tag("rect", x=x, y=y, width=w, height=h, rx=rx, cls=cls, fill=fill))

    def circle(self, center, radius, cls=None, fill=None):
        self.add(tag("circle", cx=center[0], cy=center[1], r=radius, cls=cls, fill=fill))

    def path(self, d, cls):
        self.add(tag("path", d=d, cls=cls))

    def group(self, items, rotate=None, center=None):
        transform = None
        if rotate:
            transform = f"rotate({num(rotate)} {num(center[0])} {num(center[1])})"
        self.add(tag("g", "".join(items), transform=transform))

    def text(self, x, y, segments, size=13, anchor="start", fill=None, weight=None, rotate=None):
        if isinstance(segments, str):
            segments = [segments]
        content = ""
        for segment in segments:
            if isinstance(segment, str):
                content += escape(segment)
            else:
                text, style = segment
                content += tag("tspan", escape(text), **style)
        transform = f"rotate({num(rotate)} {num(x)} {num(y)})" if rotate else None
        anchor = None if anchor == "start" else anchor
        self.add(tag("text", content, x=x, y=y, font_size=size, text_anchor=anchor, fill=fill or INK,
                     font_weight=weight, transform=transform))

    def arrow(self, tip, behind, color=INK, length=9.0, half_width=2.4):
        ux, uy = unit_vector(behind, tip)
        base = (tip[0] - ux * length, tip[1] - uy * length)
        left = (base[0] - uy * half_width, base[1] + ux * half_width)
        right = (base[0] + uy * half_width, base[1] - ux * half_width)
        self.add(tag("polygon", points=points([tip, left, right]), fill=color))

    def dimension(self, a, b, offset, label, accent=False, size=13, gap=3.0):
        """Linear dimension between the points a and b (pixels).

        The dimension line runs parallel to a-b, shifted by `offset` pixels to
        the left of the direction a -> b. The text is placed above the line.
        """
        color = ACCENT if accent else INK
        ux, uy = unit_vector(a, b)
        normal = (uy, -ux)
        side = 1.0 if offset >= 0 else -1.0
        a2, b2 = add(a, normal, offset), add(b, normal, offset)
        if abs(offset) > gap:
            self.line(add(a, normal, side * gap), add(a2, normal, side * 5), "dim")
            self.line(add(b, normal, side * gap), add(b2, normal, side * 5), "dim")
        length = math.hypot(b2[0] - a2[0], b2[1] - a2[1])
        if length >= 32:
            self.line(a2, b2, "dim-accent" if accent else "dim")
            middle = ((a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2)
            self.arrow(a2, middle, color)
            self.arrow(b2, middle, color)
        else:
            outer_a, outer_b = add(a2, (ux, uy), -14), add(b2, (ux, uy), 14)
            self.line(outer_a, outer_b, "dim-accent" if accent else "dim")
            self.arrow(a2, outer_a, color)
            self.arrow(b2, outer_b, color)
        angle = math.degrees(math.atan2(uy, ux))
        if angle > 90:
            angle -= 180
        elif angle <= -90:
            angle += 180
        theta = math.radians(angle)
        above = (math.sin(theta), -math.cos(theta))
        middle = ((a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2)
        position = add(middle, above, 4.5)
        self.text(position[0], position[1], label, size, "middle", fill=color, rotate=angle or None)

    def arc(self, center, radius, start_deg, end_deg, cls):
        start, end = math.radians(start_deg), math.radians(end_deg)
        p1 = (center[0] + radius * math.cos(start), center[1] + radius * math.sin(start))
        p2 = (center[0] + radius * math.cos(end), center[1] + radius * math.sin(end))
        sweep = 1 if end_deg > start_deg else 0
        large = 1 if abs(end_deg - start_deg) > 180 else 0
        self.path(f"M{num(p1[0])},{num(p1[1])} A{num(radius)},{num(radius)} 0 {large} {sweep} "
                  f"{num(p2[0])},{num(p2[1])}", cls)

    def callout(self, target, elbow, lines, side=1, size=13.5, dot=True):
        """Leader from a target point to a text. `lines` holds (label, value) pairs."""
        shoulder = (elbow[0] + side * 10, elbow[1])
        self.polyline([target, elbow, shoulder], "leader")
        if dot:
            self.circle(target, 2.0, fill=INK)
        x = shoulder[0] + side * 6
        for index, (label, value) in enumerate(lines):
            segments = []
            if label:
                segments.append(label + (" " if value else ""))
            if value:
                segments.append((value, {"fill": ACCENT, "font_weight": 700}))
            self.text(x, elbow[1] + 4.7 + index * (size + 3), segments, size, "start" if side > 0 else "end")

    def revision_marker(self, center, revision, size=8.0):
        cx, cy = center
        self.polygon([(cx, cy - size), (cx - size * 0.95, cy + size * 0.65), (cx + size * 0.95, cy + size * 0.65)],
                     "revision")
        self.text(cx, cy + size * 0.5, str(revision), 9, "middle", fill=ACCENT, weight=700)

    def render(self, height):
        style = f"""
    text {{ font-family: {FONT}; }}
    .outline {{ fill: none; stroke: {INK}; stroke-width: 1.7; stroke-linejoin: round; stroke-linecap: round; }}
    .part {{ fill: {PART}; stroke: {INK}; stroke-width: 1.4; stroke-linejoin: round; }}
    .part-light {{ fill: {PAPER}; stroke: {INK}; stroke-width: 1.2; stroke-linejoin: round; }}
    .plate {{ fill: url(#carbon); stroke: {INK}; stroke-width: 1.5; stroke-linejoin: round; }}
    .tire {{ fill: {TIRE}; stroke: {INK}; stroke-width: 1.7; stroke-linejoin: round; }}
    .thin {{ fill: none; stroke: {INK}; stroke-width: 0.9; stroke-linecap: round; }}
    .rod {{ fill: none; stroke: {INK}; stroke-width: 2.6; stroke-linecap: round; stroke-linejoin: round; }}
    .hidden {{ fill: none; stroke: {INK_SOFT}; stroke-width: 1.1; stroke-dasharray: 6 3.5; }}
    .center {{ fill: none; stroke: {INK_SOFT}; stroke-width: 0.8; stroke-dasharray: 18 3 3 3; }}
    .center-accent {{ fill: none; stroke: {ACCENT}; stroke-width: 1.2; stroke-dasharray: 18 3 3 3; }}
    .phantom {{ fill: none; stroke: {INK_FAINT}; stroke-width: 1.2; stroke-dasharray: 20 3 3 3 3 3; }}
    .hatch {{ fill: none; stroke: {INK_SOFT}; stroke-width: 0.8; }}
    .dim {{ fill: none; stroke: {INK}; stroke-width: 0.8; }}
    .dim-accent {{ fill: none; stroke: {ACCENT}; stroke-width: 0.9; }}
    .angle {{ fill: none; stroke: {ACCENT}; stroke-width: 1.1; }}
    .leader {{ fill: none; stroke: {INK}; stroke-width: 0.8; stroke-linejoin: round; }}
    .frame {{ fill: none; stroke: {INK}; stroke-width: 2.2; }}
    .grid {{ fill: none; stroke: {INK}; stroke-width: 0.8; }}
    .grid-faint {{ fill: none; stroke: {INK_FAINT}; stroke-width: 0.6; }}
    .revision {{ fill: {PAPER}; stroke: {ACCENT}; stroke-width: 1.2; stroke-linejoin: round; }}
"""
        defs = (
            '<pattern id="carbon" width="7" height="7" patternUnits="userSpaceOnUse" '
            'patternTransform="rotate(45)">'
            f'<rect width="7" height="7" fill="{PART}"/>'
            f'<line x1="0" y1="0" x2="0" y2="7" stroke="{CARBON}" stroke-width="1"/></pattern>'
        )
        header = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_WIDTH}" height="{num(height)}" '
            f'viewBox="0 0 {SHEET_WIDTH} {num(height)}" role="img" '
            'aria-label="Technical drawing of the latest Carten T410R speedrun setup">'
        )
        return "\n".join([header, f"<style>{style}</style>", f"<defs>{defs}</defs>", *self.items, "</svg>", ""])


# ---------------------------------------------------------------------------
# Vehicle geometry
# ---------------------------------------------------------------------------

class Car:
    """Geometry of the car, combined from the specs and the setup sheet."""

    def __init__(self, vehicle, setup):
        geo, drive, elec = "suspension_and_geometry", "drivetrain", "electronics_and_control"
        self.setup = setup
        self.wheelbase = vehicle["wheelbase"]
        self.width = vehicle["width"]
        self.radius = vehicle["tire_diameter"] / 2
        self.tire_width_front = setup.number_value(geo, "tire_width_front_mm", 30.0)
        self.tire_width_rear = setup.number_value(geo, "tire_width_rear_mm", 30.0)
        self.toe_front = setup.number_value(geo, "front_toe_deg", 0.0)
        self.toe_rear = setup.number_value(geo, "rear_toe_deg", 0.0)
        self.camber_front = setup.number_value(geo, "front_camber_deg", 0.0)
        self.camber_rear = setup.number_value(geo, "rear_camber_deg", 0.0)
        self.caster = setup.number_value(geo, "front_caster_deg", 0.0)
        self.ride_height_front = setup.number_value(geo, "ride_height_front_mm", 10.0)
        self.ride_height_rear = setup.number_value(geo, "ride_height_rear_mm", self.ride_height_front)
        self.sway_bars = setup.value(geo, "sway_bars")
        self.pinion = setup.number_value(drive, "pinion_gear_t", 43.0)
        self.spur = setup.number_value(drive, "spur_gear_t", 68.0)
        motor = str(setup.value(elec, "motor_type") or "3660")
        match = re.fullmatch(r"(\d{2})(\d{2})", motor.strip())
        self.motor_diameter = float(match.group(1)) if match else 36.0
        self.motor_length = float(match.group(2)) if match else 60.0
        # Pitch diameters of the 48 dp gears; the motor axis sits at their center distance
        self.pinion_diameter = self.pinion / GEAR_PITCH_DP * 25.4
        self.spur_diameter = self.spur / GEAR_PITCH_DP * 25.4
        self.motor_axis_y = CENTER_SHAFT_Y + (self.spur_diameter + self.pinion_diameter) / 2

    def wheel_y(self, axle):
        tire = self.tire_width_front if axle == "front" else self.tire_width_rear
        return self.width / 2 - tire / 2

    def plate_bottom(self, x):
        slope = (self.ride_height_rear - self.ride_height_front) / self.wheelbase
        return self.ride_height_front + slope * x

    def value(self, section, key):
        return format_value(key, self.setup.value(section, key))


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def draw_ground(sheet, proj, u0, u1):
    left, right = proj(u0, 0), proj(u1, 0)
    if left[0] > right[0]:
        left, right = right, left
    sheet.line(left, right, "outline")
    x = left[0] + 4
    while x < right[0] - 2:
        sheet.line((x, left[1] + 1), (x - 6, left[1] + 7), "hatch")
        x += 9


def draw_shock(sheet, top, bottom):
    """Coilover shock between two eye centers (pixels)."""
    ux, uy = unit_vector(top, bottom)
    normal = (-uy, ux)
    length = math.hypot(bottom[0] - top[0], bottom[1] - top[1])
    body_end = add(top, (ux, uy), length * 0.58)
    half = 5.5 * S
    body = [add(add(top, (ux, uy), 3.5 * S), normal, half), add(body_end, normal, half),
            add(body_end, normal, -half), add(add(top, (ux, uy), 3.5 * S), normal, -half)]
    sheet.line(body_end, add(bottom, (ux, uy), -2.5 * S), "rod")
    sheet.polygon(body, "part")
    coils = 9
    start = add(top, (ux, uy), length * 0.22)
    spring = [start]
    for index in range(1, coils * 2):
        t = length * (0.22 + 0.66 * index / (coils * 2))
        spring.append(add(add(top, (ux, uy), t), normal, (1 if index % 2 else -1) * 7.5 * S))
    spring.append(add(top, (ux, uy), length * 0.88))
    sheet.polyline(spring, "thin")
    sheet.circle(top, 2.6 * S, "part-light")
    sheet.circle(bottom, 2.6 * S, "part-light")


def draw_side_view(sheet, car, origin_x, ground_y):
    proj = Projection(origin_x, ground_y)
    wb, r = car.wheelbase, car.radius
    sheet.text(MARGIN + 28, 64, "Side view (left side)", 16, weight=700)

    draw_ground(sheet, proj, -95, wb + 105)

    # Shock towers and shocks, mostly hidden behind the wheels: speedrun shock towers from the CAD
    # files, the dampers on the outer face of the tower
    for axle_x, tower_x, path in ((0.0, 12.0, FRONT_TOWER), (wb, wb - 15.5, REAR_TOWER)):
        tower = load_tower(path)
        tower_base = car.plate_bottom(tower_x) + PLATE_THICKNESS
        if tower is not None:
            low, high, thick = tower_base + tower["bottom"], tower_base + tower["top"], tower["thickness"]
            shock_top = tower_base + tower["damper"][1]
            shock_x = tower_x - 1.5 if axle_x == 0 else tower_x + thick + 1.5
        else:
            low, high, thick, shock_top, shock_x = tower_base + 28, TOWER_TOP, 3.5, SHOCK_TOP, tower_x - 1.5
        sheet.polygon(proj.poly([(tower_x, low), (tower_x + thick, low), (tower_x + thick, high),
                                 (tower_x, high)]), "part")
        draw_shock(sheet, proj(shock_x, shock_top), proj(axle_x + (6 if axle_x == 0 else -6), 21))

    # Bottom plate with the rake defined by the ride heights, front bumper
    x0, x1 = PLATE_X
    sheet.polygon(proj.poly([(x0, car.plate_bottom(x0)), (x1, car.plate_bottom(x1)),
                             (x1, car.plate_bottom(x1) + PLATE_THICKNESS),
                             (x0, car.plate_bottom(x0) + PLATE_THICKNESS)]), "part")
    bumper_bottom = car.plate_bottom(x0) - 1
    corner = proj(-65, bumper_bottom + 18)
    sheet.rect(corner[0], corner[1], 17 * S, 18 * S, "part", rx=4)

    def on_plate(x, height):
        return x, car.plate_bottom(x) + PLATE_THICKNESS + height

    # Battery (left side, visible) and motor (right side, partly hidden)
    bx0, bx1 = BATTERY["x"]
    sheet.polygon(proj.poly([on_plate(bx0, 0), on_plate(bx1, 0), on_plate(bx1, BATTERY["height"]),
                             on_plate(bx0, BATTERY["height"])]), "part")
    mx1 = MOTOR_REAR_X
    mx0 = mx1 - car.motor_length
    d = car.motor_diameter
    visible_from = max(mx0, bx1)
    if visible_from > mx0:
        sheet.polyline(proj.poly([on_plate(visible_from, d), on_plate(mx0, d), on_plate(mx0, 0),
                                  on_plate(visible_from, 0)]), "hidden")
    sheet.polygon(proj.poly([on_plate(visible_from, 0), on_plate(mx1, 0), on_plate(mx1, d),
                             on_plate(visible_from, d)]), "part")
    sheet.polygon(proj.poly([on_plate(mx1, 0), on_plate(mx1 + 4, 0), on_plate(mx1 + 4, d + 12),
                             on_plate(mx1, d + 12)]), "part")
    g0, g1 = GEAR_PLANE_X
    half = car.spur_diameter / 2
    sheet.polygon(proj.poly([(g0, CENTER_SHAFT_Z - half), (g1, CENTER_SHAFT_Z - half),
                             (g1, CENTER_SHAFT_Z + half), (g0, CENTER_SHAFT_Z + half)]), "part")
    sheet.line(proj(17, CENTER_SHAFT_Z), proj(wb - 17, CENTER_SHAFT_Z), "center")

    # Wheels
    for axle_x in (0.0, wb):
        center = proj(axle_x, r)
        sheet.circle(center, r * S, "tire")
        sheet.circle(center, r * S * 0.74, "part-light")
        for index in range(6):
            angle = math.radians(index * 60 + 15)
            inner = add(center, (math.cos(angle), math.sin(angle)), r * S * 0.24)
            outer = add(center, (math.cos(angle), math.sin(angle)), r * S * 0.68)
            sheet.line(inner, outer, "thin")
        sheet.circle(center, r * S * 0.2, "part")
        sheet.line(add(center, (-1, 0), r * S + 9), add(center, (1, 0), r * S + 9), "center")
        sheet.line(add(center, (0, 1), r * S + 9), add(center, (0, -1), r * S + 9), "center")

    # Body as phantom line, reference only
    sheet.path(body_path(proj), "phantom")

    # Caster: steering axis through the front wheel center, top leaning rearward
    caster = math.radians(car.caster)
    center = proj(0, r)
    direction = (math.sin(caster), -math.cos(caster))
    top = add(center, direction, 62 * S)
    bottom = add(center, direction, -(r / max(math.cos(caster), 0.2)) * S)
    sheet.line(bottom, top, "center-accent")
    sheet.line(center, add(center, (0, -1), 62 * S), "center")
    if car.caster:
        sheet.arc(center, 50 * S, -90, -90 + car.caster, "angle")
    anchor = add(center, (math.sin(caster / 2), -math.cos(caster / 2)), 50 * S)
    sheet.callout(anchor, (anchor[0] - 34, anchor[1] - 22),
                  [("Caster front", car.value("suspension_and_geometry", "front_caster_deg"))], side=-1)

    # Reference arrows for the views A and B
    for start, end, letter in ((-112.0, -94.0, "A"), (wb + 122.0, wb + 104.0, "B")):
        p, q = proj(start, 45), proj(end, 45)
        sheet.line(p, q, "rod")
        sheet.arrow(q, p, INK, 14, 5)
        sheet.text((p[0] + q[0]) / 2, p[1] - 12, letter, 17, "middle", weight=700)

    # Dimensions
    sheet.dimension(proj(0, 0), proj(wb, 0), -34, format_length(car.wheelbase), gap=10)
    sheet.dimension(proj(wb, 2 * r), proj(wb, 0), (r + 14) * S, f"Ø{format_length(2 * r)}")


def body_path(proj):
    """Schematic outline of a 190 mm touring car body (x, z in millimeters)."""
    def p(x, z):
        px, py = proj(x, z)
        return f"{num(px)},{num(py)}"

    arch = 38 * S
    return " ".join([
        f"M{p(-80, 12)}",
        f"C{p(-86, 13)} {p(-89, 20)} {p(-89, 28)}",
        f"C{p(-89, 36)} {p(-87, 44)} {p(-82, 49)}",
        f"C{p(-72, 56)} {p(-45, 62)} {p(-10, 66)}",
        f"C{p(10, 68)} {p(30, 70)} {p(45, 73)}",
        f"L{p(98, 109)}",
        f"C{p(104, 112)} {p(112, 113)} {p(120, 113)}",
        f"L{p(170, 113)}",
        f"C{p(182, 113)} {p(190, 110)} {p(198, 106)}",
        f"C{p(225, 95)} {p(250, 88)} {p(275, 85)}",
        f"L{p(330, 82)}",
        f"C{p(338, 82)} {p(344, 80)} {p(347, 76)}",
        f"L{p(350, 42)}",
        f"C{p(351, 30)} {p(349, 22)} {p(342, 17)}",
        f"L{p(293.3, 18)}",
        f"A{num(arch)},{num(arch)} 0 1 0 {p(222.7, 18)}",
        f"L{p(35.3, 18)}",
        f"A{num(arch)},{num(arch)} 0 1 0 {p(-35.3, 18)}",
        "Z",
        f"M{p(62, 80)} L{p(98, 103)}",
        f"C{p(104, 107)} {p(112, 108)} {p(120, 108)}",
        f"L{p(168, 108)} C{p(178, 108)} {p(186, 106)} {p(194, 102)}",
        f"L{p(226, 89)} C{p(231, 87)} {p(229, 84)} {p(222, 84)} Z",
        f"M{p(322, 82)} L{p(326, 108)}",
        f"M{p(298, 112)} L{p(302, 108)} L{p(348, 106)} L{p(353, 111)} L{p(353, 124)} L{p(300, 126)} Z",
    ])


def draw_plan_view(sheet, car, origin_x, center_y, title_y):
    proj = Projection(origin_x, center_y)
    wb, r = car.wheelbase, car.radius
    sheet.text(MARGIN + 28, title_y, "Plan view (from above)", 16, weight=700)

    # Front bumper and bottom plate
    sheet.path("M" + " L".join(f"{num(x)},{num(y)}" for x, y in proj.poly(
        [(-48, -44), (-56, -46), (-63, -38), (-66, 0), (-63, 38), (-56, 46), (-48, 44)])) + " Z", "part")
    x0, x1 = PLATE_X
    w = PLATE_HALF_WIDTH
    sheet.polygon(proj.poly([(x0, -28), (x0, 28), (x0 + 18, 46), (x0 + 36, w), (x1 - 32, w), (x1 - 12, 44),
                             (x1, 30), (x1, -30), (x1 - 12, -44), (x1 - 32, -w), (x0 + 36, -w),
                             (x0 + 18, -46)]), "plate")

    # Lower arms, bulkheads and drive shafts
    for axle_x in (0.0, wb):
        for side in (1, -1):
            sheet.polygon(proj.poly([(axle_x - 15, side * 29), (axle_x + 15, side * 29),
                                     (axle_x + 8, side * 64), (axle_x - 8, side * 64)]), "part")
        sheet.polygon(proj.poly([(axle_x - 17, -30), (axle_x + 17, -30), (axle_x + 17, 30),
                                 (axle_x - 17, 30)]), "part")
        sheet.add(tag("rect", x=proj(axle_x - 11, 0)[0], y=proj(0, 17)[1], width=22 * S, height=34 * S,
                      rx=5, cls="part-light"))
        for side in (1, -1):
            sheet.polygon(proj.poly([(axle_x - 2.2, side * 17), (axle_x + 2.2, side * 17),
                                     (axle_x + 2.2, side * 67), (axle_x - 2.2, side * 67)]), "part")

    # Steering: bellcranks, drag link and tie rods
    for side in (1, -1):
        sheet.line(proj(24, side * 12), proj(15, side * 60), "rod")
        sheet.circle(proj(24, side * 12), 3.2 * S, "part-light")
        sheet.circle(proj(15, side * 60), 2.2 * S, "part-light")
    sheet.line(proj(24, -12), proj(24, 12), "rod")

    # Sway bars
    if car.sway_bars is not None:
        for bar_x, leg_x in ((-26.0, -6.0), (wb + 26.0, wb + 6.0)):
            sheet.polyline(proj.poly([(leg_x, 44), (bar_x, 44), (bar_x, -44), (leg_x, -44)]), "rod")
            sheet.circle(proj(leg_x, 44), 2.2 * S, "part-light")
            sheet.circle(proj(leg_x, -44), 2.2 * S, "part-light")

    # Center shaft, gears, motor and electronics
    sheet.polygon(proj.poly([(17, CENTER_SHAFT_Y - 2.5), (wb - 17, CENTER_SHAFT_Y - 2.5),
                             (wb - 17, CENTER_SHAFT_Y + 2.5), (17, CENTER_SHAFT_Y + 2.5)]), "part")
    g0, g1 = GEAR_PLANE_X
    half_spur, half_pinion = car.spur_diameter / 2, car.pinion_diameter / 2
    sheet.polygon(proj.poly([(g0, CENTER_SHAFT_Y - half_spur), (g1, CENTER_SHAFT_Y - half_spur),
                             (g1, CENTER_SHAFT_Y + half_spur), (g0, CENTER_SHAFT_Y + half_spur)]), "part")
    my = car.motor_axis_y
    sheet.polygon(proj.poly([(g0 - 1, my - half_pinion), (g1, my - half_pinion), (g1, my + half_pinion),
                             (g0 - 1, my + half_pinion)]), "part")
    mx1 = MOTOR_REAR_X
    mx0 = mx1 - car.motor_length
    half_motor = car.motor_diameter / 2
    sheet.polygon(proj.poly([(mx1, my - half_motor - 6), (mx1 + 4, my - half_motor - 6),
                             (mx1 + 4, my + half_motor + 6), (mx1, my + half_motor + 6)]), "part")
    sheet.polygon(proj.poly([(mx0, my - half_motor), (mx1, my - half_motor), (mx1, my + half_motor),
                             (mx0, my + half_motor)]), "part")
    sheet.line(proj(mx0 + 6, my - half_motor), proj(mx0 + 6, my + half_motor), "thin")
    sheet.line(proj(mx1 - 6, my - half_motor), proj(mx1 - 6, my + half_motor), "thin")
    for box in (ESC, SERVO, GYRO):
        (bx0, bx1), (by0, by1) = box["x"], box["y"]
        sheet.polygon(proj.poly([(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)]), "part")
    (bx0, bx1), (by0, by1) = BATTERY["x"], BATTERY["y"]
    sheet.polygon(proj.poly([(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)]), "part")

    # Wheels with toe angle, toe-in positive
    for axle, axle_x in (("front", 0.0), ("rear", wb)):
        toe = car.toe_front if axle == "front" else car.toe_rear
        tire = car.tire_width_front if axle == "front" else car.tire_width_rear
        for side in (1, -1):
            center = proj(axle_x, side * car.wheel_y(axle))
            width, height = 2 * r * S, tire * S
            nut_y = center[1] - height / 2 - 2.5 * S if side > 0 else center[1] + height / 2
            reach = width / 2 + 10 * S
            sheet.group([
                tag("rect", x=center[0] - width / 2, y=center[1] - height / 2, width=width, height=height,
                    rx=3 * S, cls="tire"),
                tag("rect", x=center[0] - 4.5 * S, y=nut_y, width=9 * S, height=2.5 * S, cls="part"),
                tag("line", x1=center[0] - reach, y1=center[1], x2=center[0] + reach, y2=center[1],
                    cls="center-accent" if toe else "center"),
            ], -side * toe, center)

    # Center lines
    sheet.line(proj(-74, 0), proj(x1 + 10, 0), "center")
    for axle_x in (0.0, wb):
        sheet.line(proj(axle_x, -car.width / 2 - 5), proj(axle_x, car.width / 2 + 5), "center")

    # Labels inside the components
    geo, drive, elec = "suspension_and_geometry", "drivetrain", "electronics_and_control"
    battery_center = proj(sum(BATTERY["x"]) / 2, sum(BATTERY["y"]) / 2)
    sheet.text(battery_center[0], battery_center[1] - 3, [
        "LiPo ", (f"{car.value(elec, 'lipo_cells')} {car.value(elec, 'lipo_capacity_mah')}",
                  {"fill": ACCENT, "font_weight": 700})], 13, "middle")
    sheet.text(battery_center[0], battery_center[1] + 14, [
        (f"{car.value(elec, 'max_discharge_c')}, max. {car.value(elec, 'max_current_a')}",
         {"fill": ACCENT, "font_weight": 700})], 12, "middle")
    motor_center = proj((mx0 + mx1) / 2, my)
    sheet.text(motor_center[0], motor_center[1] - 3, ["Motor ", (car.value(elec, "motor_type"),
                                                                 {"fill": ACCENT, "font_weight": 700})], 12,
               "middle")
    sheet.text(motor_center[0], motor_center[1] + 13, [(car.value(elec, "motor_kv"),
                                                        {"fill": ACCENT, "font_weight": 700})], 12, "middle")
    esc_center = proj(sum(ESC["x"]) / 2, sum(ESC["y"]) / 2)
    sheet.text(esc_center[0], esc_center[1] - 3, "ESC", 12, "middle")
    sheet.text(esc_center[0], esc_center[1] + 13, [(car.value(elec, "esc_a"),
                                                    {"fill": ACCENT, "font_weight": 700})], 12, "middle")
    servo_center = proj(sum(SERVO["x"]) / 2, sum(SERVO["y"]) / 2)
    sheet.text(servo_center[0] + 4, servo_center[1], "Servo", 11, "middle", rotate=-90)
    gyro_center = proj(sum(GYRO["x"]) / 2, sum(GYRO["y"]) / 2)
    sheet.text(gyro_center[0], gyro_center[1] + 4, "Gyro", 10.5, "middle")

    # Callouts
    top = proj(0, car.width / 2)[1]
    bottom = proj(0, -car.width / 2)[1]
    rear_edge = proj(wb + r, 0)[0]
    front_wheel = proj(-r, car.wheel_y("front"))
    sheet.callout(front_wheel, (front_wheel[0] - 30, front_wheel[1]),
                  [("Toe front", car.value(geo, "front_toe_deg"))], side=-1)
    rear_wheel = proj(wb + r, car.wheel_y("rear"))
    sheet.callout(rear_wheel, (rear_edge + 36, rear_wheel[1]),
                  [("Toe rear", car.value(geo, "rear_toe_deg"))])
    servo = proj(SERVO["x"][0] + 4, sum(SERVO["y"]) / 2 + 8)
    sheet.callout(servo, (servo[0] + 14, top - 34),
                  [("Servo", f"{car.value(elec, 'steering_type')}, {car.value(elec, 'steering_torque_nm')}"),
                   ("Servo saver", car.value(geo, "servo_saver"))])
    pinion = proj(g1 - 1, my)
    sheet.callout(pinion, (rear_edge + 36, proj(0, car.wheel_y("rear") - 25)[1]),
                  [("Pinion", f"{car.value(drive, 'pinion_gear_t')}, spur {car.value(drive, 'spur_gear_t')}"),
                   ("Final drive", car.value(drive, "final_drive_ratio"))])
    sway_label = car.value(geo, "sway_bars")
    front_bar = proj(-26, -30)
    if car.sway_bars is None:
        front_bar = proj(-17, -24)
    sheet.callout(front_bar, (front_bar[0] - 46, bottom - 46),
                  [("Sway bar front" if car.sway_bars is not None else "Sway bars", ""), ("", sway_label)],
                  side=-1)
    if car.sway_bars is not None:
        rear_bar = proj(wb + 26, 22)
        sheet.callout(rear_bar, (rear_edge + 36, rear_bar[1] - 4),
                      [("Sway bar rear", ""), ("", sway_label)])
    front_diff = proj(-11, 8)
    sheet.callout(front_diff, (front_diff[0] - 84, front_diff[1] - 4),
                  [("Diff front", car.value(drive, "front_diff"))], side=-1)
    rear_diff = proj(wb + 11, -8)
    sheet.callout(rear_diff, (rear_edge + 36, rear_diff[1] + 38),
                  [("Diff rear", car.value(drive, "rear_diff"))])
    gyro = proj(GYRO["x"][1] - 3, GYRO["y"][0] + 3)
    sheet.callout(gyro, (gyro[0] + 24, bottom + 30), [("Gyro gain", car.value(elec, "gyro_gain"))])
    return bottom


def draw_axle_view(sheet, car, axle, origin_x, ground_y, title_y):
    """Front view (axle 'front', view A) or rear view (axle 'rear', view B)."""
    front = axle == "front"
    proj = Projection(origin_x, ground_y, mirror=front)
    geo, drive = "suspension_and_geometry", "drivetrain"
    r = car.radius
    ride_height = car.ride_height_front if front else car.ride_height_rear
    camber = car.camber_front if front else car.camber_rear
    tire = car.tire_width_front if front else car.tire_width_rear
    wheel_y = car.wheel_y(axle)
    inner_face = wheel_y - tire / 2
    title = "View A (front axle)" if front else "View B (rear axle)"
    sheet.text(origin_x - car.width / 2 * S, title_y, title, 16, weight=700)

    draw_ground(sheet, proj, -car.width / 2 - 12, car.width / 2 + 12)

    # Bottom plate and shock tower (speedrun front or rear shock tower from the CAD files, drawn in
    # front of the bulkhead; schematic tower if the files are missing)
    sheet.polygon(proj.poly([(-PLATE_HALF_WIDTH, ride_height), (PLATE_HALF_WIDTH, ride_height),
                             (PLATE_HALF_WIDTH, ride_height + PLATE_THICKNESS),
                             (-PLATE_HALF_WIDTH, ride_height + PLATE_THICKNESS)]), "part")
    base = ride_height + PLATE_THICKNESS
    tower = load_tower(FRONT_TOWER if front else REAR_TOWER)
    if tower is None:
        sheet.polygon(proj.poly([(-26, 46), (26, 46), (50, TOWER_TOP - 7), (50, TOWER_TOP), (-50, TOWER_TOP),
                                 (-50, TOWER_TOP - 7)]), "part")
        for side in (1, -1):
            for hole_y in (32, 44):
                sheet.circle(proj(side * hole_y, SHOCK_TOP), 1.6 * S, "part-light")
        camber_inner, shock_top = (14, 56), (44, SHOCK_TOP)
    else:
        camber_inner = (tower["camber"][0], base + tower["camber"][1])
        shock_top = (tower["damper"][0], base + tower["damper"][1])

    # Lower arms, hub carriers, camber links and drive shafts
    for side in (1, -1):
        sheet.polygon(proj.poly([(side * 28, base + 2), (side * 66, base + 4), (side * 66, base + 10),
                                 (side * 28, base + 9)]), "part")
        sheet.polygon(proj.poly([(side * (inner_face - 6), 16), (side * (inner_face + 2), 16),
                                 (side * (inner_face + 2), 50), (side * (inner_face - 6), 50)]), "part")
        sheet.line(proj(side * camber_inner[0], camber_inner[1]), proj(side * (inner_face - 3), 48), "rod")
        sheet.circle(proj(side * camber_inner[0], camber_inner[1]), 2.2 * S, "part-light")
        sheet.circle(proj(side * (inner_face - 3), 48), 2.2 * S, "part-light")
    sheet.polygon(proj.poly([(-30, base), (30, base), (30, 46), (-30, 46)]), "part")
    if tower is not None:
        sheet.polygon(proj.poly([(u, base + v) for u, v in tower["outline"]]), "part")
        for u, v, radius, _ in tower["holes"]:
            sheet.circle(proj(u, base + v), radius * S, "part-light")
    for side in (1, -1):
        sheet.polygon(proj.poly([(side * 19, r - 2.3), (side * inner_face, r - 2.3),
                                 (side * inner_face, r + 2.3), (side * 19, r + 2.3)]), "part")
    corner = proj(-20, r + 10) if not front else proj(20, r + 10)
    sheet.rect(corner[0], corner[1], 40 * S, 20 * S, "part-light", rx=5)
    diff_label = car.value(drive, "front_diff" if front else "rear_diff")
    center = proj(0, r)
    sheet.text(center[0], center[1] + 4.5, [(diff_label, {"fill": ACCENT, "font_weight": 700})], 12, "middle")

    # Shocks
    for side in (1, -1):
        draw_shock(sheet, proj(side * shock_top[0], shock_top[1]), proj(side * 58, base + 7))

    # Sway bar with drop links to the lower arms
    if car.sway_bars is not None:
        sheet.line(proj(-46, 25), proj(46, 25), "rod")
        for side in (1, -1):
            sheet.line(proj(side * 46, 25), proj(side * 46, base + 9), "thin")
            sheet.circle(proj(side * 46, 25), 1.8 * S, "part-light")

    # Wheels with camber, negative camber leans the top of the wheel inward
    angle = math.radians(camber)
    for side in (1, -1):
        up = (side * math.sin(angle), math.cos(angle))
        center_mm = (side * wheel_y + up[0] * r, up[1] * r)
        center = proj(*center_mm)
        top_px = proj(center_mm[0] + up[0], center_mm[1] + up[1])
        rotation = math.degrees(math.atan2(top_px[0] - center[0], center[1] - top_px[1]))
        outward = 1 if proj(side, 0)[0] > proj(0, 0)[0] else -1
        width, height = tire * S, 2 * r * S
        nut_x = center[0] + width / 2 if outward > 0 else center[0] - width / 2 - 2.5 * S
        sheet.group([
            tag("rect", x=center[0] - width / 2, y=center[1] - height / 2, width=width, height=height,
                rx=3 * S, cls="tire"),
            tag("rect", x=nut_x, y=center[1] - 4.5 * S, width=2.5 * S, height=9 * S, cls="part"),
        ], rotation, center)

    # Center lines
    sheet.line(proj(0, -4), proj(0, TOWER_TOP + 8), "center")
    sheet.line(proj(-car.width / 2 - 8, r), proj(car.width / 2 + 8, r), "center")

    # Camber on the wheel on the right of the view
    side = -1 if front else 1
    contact = (side * wheel_y, 0.0)
    up = (side * math.sin(angle), math.cos(angle))
    reach = 2 * r + 12
    top = (contact[0] + up[0] * reach, contact[1] + up[1] * reach)
    sheet.line(proj(contact[0], -4), proj(contact[0], reach), "center")
    sheet.line(proj(contact[0] - up[0] * 4, -4), proj(*top), "center-accent")
    if camber:
        tilt = math.degrees(math.atan2(proj(*top)[1] - proj(*contact)[1], proj(*top)[0] - proj(*contact)[0]))
        sheet.arc(proj(*contact), (reach - 6) * S, -90.0, tilt, "angle")
    label = proj(*top)
    sheet.callout(label, (label[0] - 12, label[1] - 16),
                  [("Camber", car.value(geo, "front_camber_deg" if front else "rear_camber_deg"))], side=-1)

    # Tire width on the wheel on the left of the view
    other = -side
    inner, outer = proj(other * inner_face, 2 * r), proj(other * (wheel_y + tire / 2), 2 * r)
    left, right = (inner, outer) if inner[0] < outer[0] else (outer, inner)
    sheet.dimension(left, right, 16, format_length(tire), accent=True)

    # Ride height between ground and bottom plate, left of the center line
    gap_top = proj(0, ride_height)[1]
    gap_bottom = proj(0, 0)[1]
    dim_x = origin_x - 80
    sheet.line((dim_x, gap_bottom), (dim_x, gap_top), "dim-accent")
    sheet.arrow((dim_x, gap_top), (dim_x, gap_top + 20), ACCENT, 7, 2.2)
    sheet.arrow((dim_x, gap_bottom), (dim_x, gap_bottom - 20), ACCENT, 7, 2.2)
    key = "ride_height_front_mm" if front else "ride_height_rear_mm"
    text_y = (gap_top + gap_bottom) / 2 + 4.5
    if gap_bottom - gap_top < 15:
        text_y = gap_bottom + 21
    sheet.text(dim_x + 8, text_y, ["Ride height ", (car.value(geo, key), {"fill": ACCENT, "font_weight": 700})],
               12.5)

    # Overall width over the tires
    left_outer = proj(-car.width / 2, 0)
    right_outer = proj(car.width / 2, 0)
    a, b = (left_outer, right_outer) if left_outer[0] < right_outer[0] else (right_outer, left_outer)
    sheet.dimension(a, b, -36, format_length(car.width), gap=10)
    return ground_y + 52


# ---------------------------------------------------------------------------
# Sheet elements
# ---------------------------------------------------------------------------

def draw_frame(sheet, height):
    sheet.add(tag("rect", x=0, y=0, width=SHEET_WIDTH, height=height, fill=PAPER))
    sheet.rect(10, 10, SHEET_WIDTH - 20, height - 20, "grid-faint")
    sheet.rect(MARGIN, MARGIN, SHEET_WIDTH - 2 * MARGIN, height - 2 * MARGIN, "frame")
    columns = 8
    step = (SHEET_WIDTH - 2 * MARGIN) / columns
    for index in range(columns):
        x = MARGIN + index * step
        if index:
            sheet.line((x, 10), (x, MARGIN), "grid-faint")
            sheet.line((x, height - MARGIN), (x, height - 10), "grid-faint")
        for y in (24, height - 15):
            sheet.text(x + step / 2, y, str(index + 1), 11, "middle", fill=INK_SOFT)
    rows = max(1, round((height - 2 * MARGIN) / step))
    row_step = (height - 2 * MARGIN) / rows
    for index in range(rows):
        y = MARGIN + index * row_step
        if index:
            sheet.line((10, y), (MARGIN, y), "grid-faint")
            sheet.line((SHEET_WIDTH - MARGIN, y), (SHEET_WIDTH - 10, y), "grid-faint")
        letter = chr(ord("A") + index)
        for x in (20, SHEET_WIDTH - 20):
            sheet.text(x, y + row_step / 2 + 4, letter, 11, "middle", fill=INK_SOFT)
    for x, y, dx, dy in ((SHEET_WIDTH / 2, 10, 0, 1), (SHEET_WIDTH / 2, height - 10, 0, -1),
                         (10, height / 2, 1, 0), (SHEET_WIDTH - 10, height / 2, -1, 0)):
        sheet.line((x, y), (x + dx * (MARGIN + 6), y + dy * (MARGIN + 6)), "outline")


def draw_legend(sheet, x, y, revision):
    sheet.text(x, y, "Legend", 14, weight=700)
    rows = [
        ("value", "Setup sheet value"),
        ("revision", f"Changed in rev. {revision}"),
        ("outline", "Visible outline"),
        ("hidden", "Hidden outline"),
        ("center", "Center line, axis"),
        ("phantom", "Body (reference)"),
    ]
    for index, (kind, text) in enumerate(rows):
        column, row = index % 2, index // 2
        cx = x + column * 190
        cy = y + 24 + row * 23
        if kind == "value":
            sheet.text(cx + 18, cy + 4.5, [("10°", {"fill": ACCENT, "font_weight": 700})], 13, "middle")
        elif kind == "revision":
            sheet.revision_marker((cx + 18, cy), revision)
        else:
            sheet.line((cx, cy), (cx + 36, cy), kind)
        sheet.text(cx + 46, cy + 4.5, text, 12.5)
    return y + 24 + 3 * 23


def draw_notes(sheet, x, y, width, vehicle):
    sheet.text(x, y, "Notes", 14, weight=700)
    notes = [
        "Dimensions in mm, angles in degrees. Toe and camber are drawn per wheel.",
        f"Wheelbase {format_length(vehicle['wheelbase'])} mm and width {format_length(vehicle['width'])} mm "
        f"from the chassis spec, tire diameter {format_length(vehicle['tire_diameter'])} mm from the tire spec.",
        "Outlines are schematic. Shock towers: CAD model.",
        "Generated by scripts/generate_setup_drawing.py. Do not edit manually.",
    ]
    line_y = y + 22
    for note in notes:
        for line in wrap_items(note.split(" "), width, 12, max_lines=3, separator=" "):
            sheet.text(x, line_y, line, 12, fill=INK_SOFT)
            line_y += 17
        line_y += 3
    # Graphic scale bar, 100 mm at drawing scale
    bar_y = line_y + 6
    for index in range(10):
        sheet.rect(x + index * 10 * S, bar_y, 10 * S, 6, fill=INK if index % 2 == 0 else PAPER)
    sheet.rect(x, bar_y, 100 * S, 6, "grid")
    for value in (0, 50, 100):
        sheet.text(x + value * S, bar_y + 20, str(value), 11, "middle", fill=INK_SOFT)
    sheet.text(x + 100 * S + 14, bar_y + 7, "mm (scale 1:2)", 11, fill=INK_SOFT)
    return bar_y + 26


def parameter_blocks(car, previous):
    setup = car.setup
    changes = changed_keys(previous, setup)
    blocks = []
    for section, title in SECTION_TITLES.items():
        rows = []
        for key, value in setup.section(section).items():
            rows.append((describe_key(key)[0], format_value(key, value), True, (section, key) in changes))
        blocks.append((title, rows))
    for section, values in setup.properties.items():
        if section not in SECTION_TITLES and isinstance(values, dict):
            rows = [(describe_key(key)[0], format_value(key, value), True, (section, key) in changes)
                    for key, value in values.items()]
            blocks.append((humanize(section), rows))
    blocks.append(("Derived values", derived_rows(car)))
    return blocks


def derived_rows(car):
    setup = car.setup
    drive, elec = "drivetrain", "electronics_and_control"
    pinion = setup.number_value(drive, "pinion_gear_t")
    spur = setup.number_value(drive, "spur_gear_t")
    final_drive = setup.number_value(drive, "final_drive_ratio")
    kv = setup.number_value(elec, "motor_kv")
    cells = setup.number_value(elec, "lipo_cells")
    circumference = math.pi * car.radius * 2 / 1000
    rows = []
    rows.append(("Spur/pinion ratio", f"{spur / pinion:.2f} : 1" if pinion and spur else "n/a", False, False))
    front = setup.number_value("suspension_and_geometry", "ride_height_front_mm")
    rear = setup.number_value("suspension_and_geometry", "ride_height_rear_mm")
    rake = math.degrees(math.atan((rear - front) / car.wheelbase)) if front is not None and rear is not None else None
    rows.append(("Rake angle", f"{rake:.1f}°" if rake is not None else "n/a", False, False))
    rows.append((None, "= arctan((ride height rear − ride height front) / wheelbase)", False, False))
    if rake is not None:
        rows.append((None, f"= arctan(({format_length(rear)} mm − {format_length(front)} mm) / "
                           f"{format_length(car.wheelbase)} mm)", False, False))
    if final_drive:
        motor_rpm = 100000 / 60 / circumference * final_drive
        rows.append(("Motor speed at 100 km/h", f"{motor_rpm:,.0f} rpm".replace(",", " "), False, False))
    if final_drive and kv and cells:
        # Theoretical speed without load: motor kV x battery voltage, no voltage sag or drag
        for label, cell_voltage in (("No-load speed, fully charged (4.2 V/cell)", 4.2),
                                    ("No-load speed, nominal (3.7 V/cell)", 3.7)):
            speed = kv * cells * cell_voltage / final_drive * circumference * 60 / 1000
            rows.append((label, f"{speed:.1f} km/h", False, False))
    return rows


def layout_parameter_columns(blocks, columns=3):
    """Distributes the blocks over the columns, the last block is appended to the shortest column."""
    main, extra = blocks[:-1], blocks[-1:]
    layout = [[] for _ in range(columns)]
    for index, block in enumerate(main):
        layout[min(index, columns - 1) if len(main) <= columns else index % columns].append(block)
    for block in extra:
        shortest = min(range(columns), key=lambda i: sum(len(rows) + 1.6 for _, rows in layout[i]))
        layout[shortest].append(block)
    return layout


def draw_parameter_table(sheet, car, previous, top):
    blocks = parameter_blocks(car, previous)
    columns = layout_parameter_columns(blocks)
    x0, x1 = MARGIN, SHEET_WIDTH - MARGIN
    header_height, row_height, note_height, block_gap = 30, 19.5, 16.5, 26
    column_width = (x1 - x0) / len(columns)
    # Rows without label are explanations of the row above, e.g. a formula
    heights = [sum(block_gap + sum(note_height if label is None else row_height for label, *_ in rows)
                   for _, rows in column) for column in columns]
    height = header_height + max(heights) + 10
    sheet.line((x0, top), (x1, top), "grid")
    sheet.line((x0, top + height), (x1, top + height), "grid")
    sheet.line((x0, top + header_height), (x1, top + header_height), "grid")
    sheet.text(x0 + 12, top + 20, "Setup parameters", 15, weight=700)
    source = car.setup.path.relative_to(ROOT_DIR).as_posix()
    sheet.text(x1 - 12, top + 20, f"Source: {source}", 12.5, "end", fill=INK_SOFT)
    for index, column in enumerate(columns):
        cx = x0 + index * column_width
        if index:
            sheet.line((cx, top + header_height), (cx, top + height), "grid")
        y = top + header_height
        for title, rows in column:
            sheet.text(cx + 12, y + 19, title, 13.5, weight=700)
            y += block_gap
            for label, value, from_sheet, changed in rows:
                if label is None:
                    sheet.text(cx + 24, y + 12, value, 11.5, fill=INK_SOFT)
                    y += note_height
                    continue
                sheet.line((cx + 12, y), (cx + column_width - 12, y), "grid-faint")
                sheet.text(cx + 12, y + 14, label, 13, fill=INK_SOFT)
                sheet.text(cx + column_width - 34, y + 14, value, 13, "end", fill=ACCENT if from_sheet else INK,
                           weight=700 if from_sheet else None)
                if changed:
                    sheet.revision_marker((cx + column_width - 20, y + 9), car.setup.version)
                y += row_height
    return top + height


def draw_revision_table(sheet, sheets, x0, top, x1):
    columns = [("Rev.", 46), ("Date", 96), ("Changes from the previous revision", None), ("Top speed", 92)]
    fixed = sum(width for _, width in columns if width)
    widths = [width or (x1 - x0 - fixed) for _, width in columns]
    header_height, line_height = 26, 16
    recent = list(reversed(sheets))[:6]
    rows = []
    for sheet_data in recent:
        index = sheets.index(sheet_data)
        previous = sheets[index - 1] if index > 0 else None
        lines = wrap_items(describe_changes(previous, sheet_data), widths[2] - 20, 12)
        speed = as_number(sheet_data.meta.get("top_speed_kmh"))
        rows.append((sheet_data, lines, f"{format_length(speed)} km/h" if speed else "n/a"))
    sheet.text(x0, top + 14, "Revisions", 14, weight=700)
    table_top = top + 24
    height = header_height + sum(10 + len(lines) * line_height for _, lines, _ in rows)
    sheet.rect(x0, table_top, x1 - x0, height, "grid")
    sheet.line((x0, table_top + header_height), (x1, table_top + header_height), "grid")
    x = x0
    for (title, _), width in zip(columns, widths):
        sheet.text(x + 10, table_top + 17.5, title, 12.5, weight=700)
        if x > x0:
            sheet.line((x, table_top), (x, table_top + height), "grid")
        x += width
    y = table_top + header_height
    latest = sheets[-1]
    for sheet_data, lines, speed in rows:
        row_height = 10 + len(lines) * line_height
        if y > table_top + header_height:
            sheet.line((x0, y), (x1, y), "grid-faint")
        is_latest = sheet_data is latest
        weight = 700 if is_latest else None
        color = ACCENT if is_latest else INK
        sheet.text(x0 + 10, y + 17, str(sheet_data.version), 12.5, fill=color, weight=weight)
        sheet.text(x0 + widths[0] + 10, y + 17, sheet_data.date, 12.5, fill=color, weight=weight)
        for index, line in enumerate(lines):
            sheet.text(x0 + widths[0] + widths[1] + 10, y + 17 + index * line_height, line, 12, fill=color)
        sheet.text(x0 + sum(widths[:3]) + 10, y + 17, speed, 12.5, fill=color, weight=weight)
        y += row_height
    return table_top + height


def draw_title_block(sheet, setup, x0, bottom, x1):
    """Title block in the lower right corner, its right and bottom edges are the frame."""
    height = 176
    top = bottom - height
    sheet.line((x0, top), (x1, top), "frame")
    sheet.line((x0, top), (x0, bottom), "frame")
    title_height = 62
    sheet.line((x0, top + title_height), (x1, top + title_height), "grid")
    description = setup.meta.get("description") or "Carten T410R speedrun setup"
    sheet.text(x0 + 14, top + 31, str(description), 24, weight=700)
    sheet.text(x0 + 14, top + 52, f"Setup drawing, generated from setup sheet version {setup.version}", 13,
               fill=INK_SOFT)
    speed = as_number(setup.meta.get("top_speed_kmh"))
    source = setup.path.relative_to(ROOT_DIR).as_posix()
    rows = [
        [("Date", setup.date), ("Version", str(setup.version)),
         ("Top speed", f"{format_length(speed)} km/h" if speed else "n/a"), ("Sheet", "1 of 1")],
        [("Scale", "1:2"), ("Units", "mm, °"), ("Projection", "first angle"), ("Copyright", "All rights reserved")],
        [("Source", source), ("Repository", "prototyping.rc.speedrun")],
    ]
    row_height = (height - title_height) / len(rows)
    for row_index, cells in enumerate(rows):
        y = top + title_height + row_index * row_height
        if row_index:
            sheet.line((x0, y), (x1, y), "grid")
        width = (x1 - x0) / len(cells)
        for cell_index, (caption, value) in enumerate(cells):
            x = x0 + cell_index * width
            if cell_index:
                sheet.line((x, y), (x, y + row_height), "grid")
            sheet.text(x + 10, y + 14, caption, 10.5, fill=INK_SOFT)
            sheet.text(x + 10, y + 31, value, 13.5, weight=700 if caption in ("Version", "Date") else None)
    # First angle projection symbol in the projection cell
    width = (x1 - x0) / 4
    cx, cy = x0 + 3 * width - 34, top + title_height + row_height * 1.5 + 3
    sheet.polygon([(cx - 22, cy - 5), (cx - 4, cy - 10), (cx - 4, cy + 10), (cx - 22, cy + 5)], "outline")
    sheet.circle((cx + 14, cy), 10, "outline")
    sheet.circle((cx + 14, cy), 5, "outline")
    return top


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def build_drawing(sheets, vehicle):
    setup = sheets[-1]
    previous = sheets[-2] if len(sheets) > 1 else None
    car = Car(vehicle, setup)
    sheet = Sheet()

    side_origin_x, side_ground_y = 265.0, 330.0
    draw_side_view(sheet, car, side_origin_x, side_ground_y)
    axle_view_x = 1205.0
    right_column_x = axle_view_x - car.width / 2 * S
    draw_legend(sheet, right_column_x, 64, setup.version)
    draw_axle_view(sheet, car, "front", axle_view_x, side_ground_y, 168)

    plan_title_y = 425.0
    plan_center_y = plan_title_y + 65 + car.width / 2 * S
    plan_bottom = draw_plan_view(sheet, car, side_origin_x, plan_center_y, plan_title_y)
    rear_ground_y = plan_title_y + 200
    rear_bottom = draw_axle_view(sheet, car, "rear", axle_view_x, rear_ground_y, plan_title_y)
    notes_bottom = draw_notes(sheet, right_column_x, rear_bottom + 36, SHEET_WIDTH - MARGIN - 14 - right_column_x,
                              vehicle)

    table_top = max(plan_bottom + 60, notes_bottom + 24)
    table_bottom = draw_parameter_table(sheet, car, previous, table_top)

    band_top = table_bottom + 22
    title_x0 = SHEET_WIDTH - MARGIN - 520
    revisions_bottom = draw_revision_table(sheet, sheets, MARGIN + 14, band_top, title_x0 - 26)
    bottom = max(revisions_bottom + 18, band_top + 186)
    draw_title_block(sheet, setup, title_x0, bottom, SHEET_WIDTH - MARGIN)
    height = bottom + MARGIN

    frame = Sheet()
    draw_frame(frame, height)
    sheet.items = frame.items + sheet.items
    return sheet.render(height)


def apply_theme(svg, theme):
    """Replaces the colors of the light theme in a finished drawing."""
    if theme == "light":
        return svg
    return re.sub(r"#[0-9a-f]{6}", lambda match: DARK_THEME.get(match.group(0), match.group(0)), svg)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="path of the SVG file to write")
    parser.add_argument("--theme", choices=("light", "dark"), default="light",
                        help="light for the readme, dark for the setup dashboard")
    args = parser.parse_args()

    sheets = load_setup_sheets()
    if not sheets:
        print("No setup sheets found.")
        raise SystemExit(1)
    svg = apply_theme(build_drawing(sheets, load_vehicle()), args.theme)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8")
    print(f"Wrote {args.output} from {sheets[-1].path.name}")


if __name__ == "__main__":
    main()
