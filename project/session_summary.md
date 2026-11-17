# Session summary (handover)

Handover of the CAD session that ended on 2026-11-16 (front splitter), for the next session. Read this file, `CLAUDE.md` and the [CAD readme](../cad/readme.md) first.

## Table of contents
* [State of the repository](#state-of-the-repository)
* [Rules of the owner](#rules-of-the-owner)
* [Workflow](#workflow)
* [Work of this session](#work-of-this-session)
* [Changes after the handover](#changes-after-the-handover)
* [Current geometry (key values)](#current-geometry-key-values)
* [Status of the parts](#status-of-the-parts)
* [Open points](#open-points)

## State of the repository
* Work branch of the session: `ccr-a9bb1886-3anw1b` (last design commit `df05c50`, one-piece front splitter on the car). The design commits are merged into `main` with pull request #89 (`e100609`).
* This file was updated on the work branch after the merge (commit `c5a986f`) and is carried to `main` through the branch `ccr-40867872-qk7gsh`. It replaces the previous handover of the same branch (commit `4e9bf2a`).
* Generated files are up to date: STEP/STL/DXF files, drawings in `photos/`, measurement sheets and the assembly `cad/assembly/speedrun_chassis_T410R.step`. `architecture/README.md` and `specs/full_spec.yaml` were not changed in this session.

## Rules of the owner
* `CLAUDE.md`: English, sentence case also in headings, list items and table entries, table of contents as soon as a Markdown file has more than one heading, no emojis, objective style without filler words.
* Commits: `CLAUDE.md` requires the approval of the owner for each commit. In this session the owner approved commit and push for the whole session; ask again in a new session.
* Commit messages end with the 2 attribution lines given by the environment (`Co-Authored-By: ...` and `Claude-Session: ...`).
* The inside of the lower and upper bulkhead (verified with test prints) must not be changed; the generators of the bulkheads run a functional check.
* Do not change `scripts/generate_setup_drawing.py`, `photos/latest_setup_drawing.svg`, `docs/latest_setup_drawing.svg` or `.github/workflows/*`.
* No Carten part numbers (NBA..., NHA...) in docs, drawings or file names (purchase lists excepted).
* Wording: the parts besides the speedrun parts are "own design, partly based on the (Carten) T410R"; the group is called "further own parts". The word "re-engineered" is not used any more. The front splitter parts are speedrun parts (owner), directory `cad/front_splitter`.
* Third-party STL files stay in `cad/`. Force push is not allowed. The chassis plate is ordered: only its existing holes can be used (steering posts H24/H25, servo mount H17/H21, motor mount H09/H10, front splitter H34/H35/H36).
* The owner sends photos and caliper values; values of the owner have the source `owner` in the parameter files and the measured column of the measurement sheets.

## Workflow
* The CAD packages are not preinstalled in a fresh container: `pip install cadquery ezdxf matplotlib reportlab` (approx. 2 min; cadquery 2.8 with Python 3.13 works).
* Run the scripts from the root directory with `PYTHONDONTWRITEBYTECODE=1`; delete `scripts/cad/__pycache__` before a commit.
* Generators and run times (approx.):
  * `scripts/cad/generate_running_gear.py`: running gear, drawing, steering lock check, bellcrank sweep and overlap check of all parts (10 to 15 min; `--no-check` skips the overlap check).
  * `scripts/cad/generate_speedrun_assembly.py`: assembly STEP, assembly picture and interference check of all 186 parts (approx. 10 min; with `python -u` the output is not buffered).
  * `scripts/cad/generate_front_splitter.py`: front splitter (one-piece version and three-part alternative), DXF and geometry data, test prints, drawings `photos/cad_front_splitter_drawing.png` and `photos/cad_front_splitter_one_piece_drawing.png`, checks (approx. 1 min; `--no-check` skips the tyre check and the assembly check). It reads the assembly STEP for the overlap check, so after a change of the splitter run the assembly first and then this script once more.
  * `scripts/cad/generate_front_splitter_measurement_sheet.py`: measurement sheet `cad/front_splitter/front_splitter_measurement_sheet.pdf` (M1 to M16, B1 to B6, S1 to S4, measured values of the owner in the rows).
  * `scripts/cad/generate_wishbones.py`, `generate_camber_links.py`, `generate_driveshaft.py`, `generate_measurement_sheets.py`, `generate_knuckle_measurement_sheet.py`, `generate_pivot_blocks.py`, `scripts/generate_adr_readme.py`, `scripts/merge_specs.py`.
* Run long generators in the background and commit only after the checks have passed.
* Expected check results: running gear "overlaps: 0"; assembly only the 3 known interferences (lower bulkhead End B / pivot block End B, outer: 0.82 mm³; lower bulkhead End A / front wishbone, left and right: 2.16 mm³ each); front splitter: no overlap with the chassis plate, the body posts and the 30 parts at End A, tyre clearance >= 3 mm.
* The generators rewrite all STEP, STL and DXF files with new headers. Before a commit, restore the files whose geometry did not change (normalised comparison with `HEAD`). The following script did this in the session (save it in a scratch directory and run it from the root directory):

```python
import re, subprocess

def norm_step(b):
    t = b.decode("latin-1")
    lines = [l for l in t.splitlines() if not l.startswith(("FILE_NAME", "/* ")) and "PRODUCT(" not in l and "Open CASCADE" not in l]
    t = re.sub(r"#\d+", "#", "\n".join(lines))
    t = re.sub(r"-?\d+\.\d*(?:E[-+]?\d+)?", lambda m: f"{float(m.group(0)):.3f}", t)
    return t.replace("-0.000", "0.000")

def norm_stl(b):
    if b[:5] == b"solid" and b"facet" in b[:400]:
        t = b.decode("latin-1").splitlines()[1:-1]
        return "\n".join(re.sub(r"-?\d+\.\d+(?:e[-+]?\d+)?", lambda m: f"{float(m.group(0)):.3f}", l) for l in t)
    return b[80:]

for f in subprocess.run(["git", "diff", "--name-only", "--diff-filter=M"], capture_output=True, text=True).stdout.split():
    if f.lower().endswith((".step", ".stl")):
        new, old = open(f, "rb").read(), subprocess.run(["git", "show", f"HEAD:{f}"], capture_output=True).stdout
        fn = norm_step if f.lower().endswith(".step") else norm_stl
        if fn(new) == fn(old):
            subprocess.run(["git", "checkout", "--", f])
```

* Files that change without a change of geometry and must be restored by hand: `cad/running_gear/steering/spacers_of_the_bridge.step`, `cad/parts/rear_drive/bearing_5x10x4.stl`, `cad/parts/camber_link/turnbuckle_M3x37.stl`; the assembly STEP when only the order of the colours changed; the DXF files of the splitter and the holder plate when their `_geometry.json` is unchanged (only the date and IDs change); an STL file of a cut solid (test print) can come back with another triangle order (compare the number of triangles and the surface area).
* Boolean operations: do not fuse a solid onto an identical existing face; the following booleans fail silently. A closed spline with tangents loops: build the outline of the mount from one half spline with unit tangents (`scale=False`) and mirror it (`mount_outline_wire`).

## Work of this session
* Speedrun front splitter at End A (new, `cad/front_splitter`, section "Speedrun front splitter" of the CAD readme). The car runs without the front foam bumper; the splitter takes its place, the body sits on it and the splitter shows 15 to 20 mm ahead of the body (owner).
* Body post mount: built from photos of the original part and the measurements of the owner (M1 to M16 of the measurement sheet: 79.5 mm over the ears, ear holes 65.6 mm apart and 12.0 mm ahead of H34/H35, rear edge 4.0 mm behind H34/H35, 19.2 mm deep, 47.7 mm over the side lips, total height 4.5 mm at the rear edge, front part 3.0 mm, pocket 2.0 mm flush with the chassis plate, ear bosses 4.41 mm, hexagon recess 7.06 x 2.1 mm, body posts 5.92 mm with a hexagon section 8 mm long, held with countersunk screws M3x6 from below). Pocket and side lips around the front end of the chassis plate, ramp on the top face. The original boss on H36 (stock bumper) is left out.
* Planform of the splitter: front end 90 mm ahead of the axis through H34/H35 (owner); outer form after the form of the lower front edge of the body (parameter `front_form`, assumed), from tip to tip; rear edge as variant C of the design suggestions (owner): straight in the middle at y = 313 mm, concave rear edges, deeper beside the mount, narrower toward the tips; tyre check in 3D (cylinder 64 x 30 mm turned about the kingpin axis, -45 to +45 degrees, droop 0 and 4 mm).
* Three-part version (verified with a 3D print of the owner, now the alternative): mount with bosses on H34/H35 (base 8.0 mm up to 8.5 mm, pin 6.3 mm through the splitter), carbon splitter 2.0 mm (8.5 to 10.5 mm), carbon holder plate 2.0 mm on top (outline as the mount, like the carbon plate on the original foam bumper); screws M3x6 from below and M3x6 from above into the same bosses (0.5 mm between the tips); H36 tapped through the deck. DXF files of the splitter and the holder plate, test print of the middle part of the splitter.
* One-piece version (used on the car, owner): the body post mount enlarged to the outline of the splitter at the thickness of its front part (3.0 mm, z = 0 to 3.0 mm, bottom face flush with the chassis plate); bosses 6.3 mm up to 7.0 mm on H34, H35 and H36 with blind tapped holes for countersunk screws M3x6 from below (not visible from above); ears with the hexagon recesses as the original part. 187 x 94 mm, approx. 47 g in PETG, tyre clearance 10.18 mm. STEP, STL, test print `front_splitter_one_piece_end_a_test_print.stl` (middle part 92 x 32 mm, bottom face on the bed) and drawing.
* Assembly: contains the one-piece version with the body posts (186 parts); the front splitter is a speedrun part with a material (PETG), the speedrun mass total is 464 g. Readmes (root, CAD, parts) updated: the one-piece version as the speedrun front splitter (yellow), the three-part parts as the verified alternative (not in the total).
* Design study (not in the repository): planform variants A (band and tongue), B (straight taper) and C (curved taper, chosen).

## Changes after the handover
* One-piece front splitter: 3D print of the owner. The tightened screws M3x6 broke through the top of the bosses (0.5 mm of material above the blind holes); the bosses on H34, H35 and H36 are 3.0 mm higher (top at z = 10.0 mm, 3.5 mm above the holes, parameter `one_piece`). Status verified (owner). Volume 37.6 cm³, approx. 48 g in PETG; speedrun mass total 465 g.
* Dual motor study in `cad/studies/dual_motor` (not part of the build): symmetric motor mount for 2 motors 3660, chassis plate with a second motor window on the left side, electronics layout with 2 ESCs and 2 batteries 3S shorty (see its readme).

## Current geometry (key values)
| Value | Model |
|:---|:---|
| Front kingpin axis | x = 63.65 mm, 6.75 mm inside the outer hinge pin (x = 70.4 mm), caster 10 degrees; at the height of the axle y = 286.87 mm, z = 22.0 mm |
| Outer faces of the hex hubs | x = ±86.85 mm front and rear (front hex hubs 6 mm, rear 7 mm) |
| Overall width | 187 mm over tyres of 26 mm (as the original car, owner), 191 mm over tyres of 30 mm |
| Front wishbone | 49.7 mm axis to axis (measured 45.26 mm, prolonged by 4.44 mm) |
| Rear wishbone | 54.3 mm axis to axis (measured) |
| CVD drive shafts | centre to centre front 40.2 mm, rear 41.1 mm |
| Camber links | gap front 28.0 mm, rear 25.8 mm (turnbuckle M3x37) |
| Steering | Ackermann 114 / 128 / 144 % at 15 / 20 / 25 degrees; free steering angle 30 degrees toward the middle, 45 degrees or more toward the outside; servo approx. 48 degrees for 25 degrees of the inner wheel (horn 10 mm) |
| Motor axis of the motor mount | x = 24.6 to 33.85 mm (spur gear plus pinion 93 to 127 teeth, 48DP) |
| Front splitter | front end y = 407.98 mm (90 mm ahead of the axis H34-H35, 82.3 mm ahead of the chassis plate), width 187 mm; one-piece version z = 0 to 3.0 mm (body on it at 3.0 mm), three-part version 8.5 to 10.5 mm (body at 10.5 mm) |
| Lower front edge of the body | 17.5 mm behind the front edge of the splitter (owner: 15 to 20 mm), on the centre line 72.5 mm ahead of the axis H34-H35; form assumed |
| Body posts | in the ears at x = ±32.8 mm, y = 329.98 mm; hexagon 7.06 mm from 2.31 mm above the bottom face of the chassis plate |

## Status of the parts
* Verified (green): chassis plate, bulkheads, top brace, shock towers, pivot blocks, motor mount with cap, steering knuckles, one-piece front splitter (used on the car, 3D print of the owner; bosses 3 mm higher after the print), three-part front splitter (body post mount, splitter, holder plate; alternative, 3D print of the owner).
* Measures qualified (yellow): centre driveshaft, rear and front drive line, differential, spool, front and rear wishbones (the front wishbone is longer than measured).
* Completely unqualified (red): cup joints, diff outdrives, inner hinge pins, camber links, C-hubs (3D print verification with the guide sleeves planned by the owner), rear hub carriers, axles and hex hubs, CVD drive shafts, steering, sway bars, dampers.

## Open points
* One-piece front splitter: as a 3D print in PETG the plate (3.0 mm) is less stiff than the carbon splitter.
* Front splitter, measurement sheet: form of the lower front edge of the body (B1 to B3, the outline of the splitter follows `front_form`), wheel arches (B5), length of the body posts (B6), ramp of the mount (M10), droop of the front wheels (S3). The body posts and the body mounting holes must be set so that the body sits on the splitter (B4 = 3.0 mm for the one-piece version).
* ADR-009 (foam bumper flush with the front apron of the body) and ADR-010 (GPS module on the front foam bumper) still refer to the foam bumper, which is no longer used; the GPS module needs a new position (for example on the splitter).
* C-hub: 3D print verification with the guide sleeves; the dimensions of the sleeves are scaled from the manual (a caliper value of the original sleeve confirms them); the wall between the pocket of the lower screw head and the tube on the hinge pin is only 0.3 mm.
* Steering knuckle: open dimensions K11, K14, K16 and K19 of the measurement sheet.
* Track: the 0.5 mm gaps between the knuckle ring and the front hex hub and between the tube of the hub carrier and the rear hex hub, and the radius 3.6 mm of the lug of the hub carrier are assumptions. A measurement of the outer faces of the hex hubs on the car, front and rear, confirms the prolonged front wishbone.
* Rear hub carrier: in the photo the axle lies approx. 17 mm above the hinge pin, in the model 10.4 mm (ride height 15 mm, wishbone horizontal); a caliper value confirms or corrects it. The original part has 2 holes in the top tab; the model has one.
* Ackermann (114 to 144 %) and servo travel (approx. 48 degrees): the bellcranks are an assumption from the manual; extended end points or a horn of 12.5 mm (approx. 37 degrees).
* Wheels are not modelled; the wishbones are horizontal at the ride height of setup sheet 4 (10 mm front, 15 mm rear).
* Not changed to 130 km/h: the gearing plot `scripts/plots/gearing_plot.py` (100 km/h line thicker), `specs/mechanics/carten_t410r/spec_cartent410r.yaml` (track width 190 mm), the project name "RC100".
