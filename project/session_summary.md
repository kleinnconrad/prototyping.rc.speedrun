# Session summary (handover)

Handover of the CAD session that ended on 2026-11-17 (front splitter finished, dual motor study), for the next session. Read this file, `CLAUDE.md` and the [CAD readme](../cad/readme.md) first.

## Table of contents
* [State of the repository](#state-of-the-repository)
* [Rules of the owner](#rules-of-the-owner)
* [Workflow](#workflow)
* [Work of this session](#work-of-this-session)
* [Current geometry (key values)](#current-geometry-key-values)
* [Status of the parts](#status-of-the-parts)
* [Open points](#open-points)

## State of the repository
* Work branch: `ccr-40867872-qk7gsh`, started from `main` at `e100609` (merge of pull request #89, front splitter of the previous session). All changes are committed and pushed (last change: this file). No pull request was created; the branch is not merged into `main`.
* Commits of this session: `adadd19` (handover of the previous session carried to `main`), `ae25af2` (dual motor study), `9cb49fa` (electronics layout of the dual motor study), `7cf7178` (front splitter: bosses 3 mm higher, status verified), `51018cb` (three-part front splitter set removed), then this file.
* Generated files are up to date: front splitter files, drawing `photos/cad_front_splitter_one_piece_drawing.png`, measurement sheet `cad/front_splitter/front_splitter_measurement_sheet.pdf`, assembly `cad/assembly/speedrun_chassis_T410R.step` and its picture. `architecture/README.md` and `specs/full_spec.yaml` were not changed.
* The files of the dual motor study are a snapshot: `cad/studies/dual_motor/dual_motor_study_assembly.step` still contains the front splitter with the bosses up to 7.0 mm and the front corner with the kingpin axis in the middle of the wishbone (before the changes of the sessions on 2026-11-17). Regenerate the study when it is used again.

## Rules of the owner
* `CLAUDE.md`: English, sentence case also in headings, list items and table entries, table of contents as soon as a Markdown file has more than one heading, no emojis, objective style without filler words.
* Commits: `CLAUDE.md` requires the approval of the owner for each commit. In this session the owner approved commit and push for the whole session; ask again in a new session. The permission check of the environment blocked one commit that the owner had not asked for in that turn; after the explicit request of the owner it worked.
* Commit messages end with the 2 attribution lines given by the environment (`Co-Authored-By: ...` and `Claude-Session: ...`).
* The inside of the lower and upper bulkhead (verified with test prints) must not be changed; the generators of the bulkheads run a functional check.
* Do not change `scripts/generate_setup_drawing.py`, `photos/latest_setup_drawing.svg`, `docs/latest_setup_drawing.svg` or `.github/workflows/*`.
* No Carten part numbers (NBA..., NHA...) in docs, drawings or file names (purchase lists excepted).
* Wording: the parts besides the speedrun parts are "own design, partly based on the (Carten) T410R"; the group is called "further own parts". The word "re-engineered" is not used any more. The front splitter is a speedrun part (owner), directory `cad/front_splitter`.
* Front splitter: only the one-part design is kept (owner); the three-part set (body post mount, carbon splitter, holder plate) was removed in this session.
* Studies (owner: "just a study for now"): directory `cad/studies/<name>` with its own readme and script, not part of the build; the parts of the build and the assembly are not changed by a study.
* Third-party STL files stay in `cad/3d_print_fdm` (moved there from `cad/` on request of the owner). Force push is not allowed. The chassis plate is ordered: only its existing holes can be used (steering posts H24/H25, servo mount H17/H21, motor mount H09/H10, front splitter H34/H35/H36). The plate of the dual motor study is a study only.
* The owner sends photos and caliper values; values of the owner have the source `owner` in the parameter files and the measured column of the measurement sheets.

## Workflow
* The CAD packages are not preinstalled in a fresh container: `pip install cadquery ezdxf matplotlib reportlab` (approx. 2 min; cadquery 2.8 with Python 3.13 works). `pyflakes` is useful to check edited scripts.
* Run the scripts from the root directory with `PYTHONDONTWRITEBYTECODE=1`; delete `scripts/cad/__pycache__` before a commit.
* Generators and run times (approx.):
  * `scripts/cad/generate_running_gear.py`: running gear, drawing, steering lock check, bellcrank sweep and overlap check of all parts (10 to 15 min; `--no-check` skips the overlap check).
  * `scripts/cad/generate_speedrun_assembly.py`: assembly STEP, assembly picture and interference check of all 186 parts (approx. 10 min; with `python -u` the output is not buffered).
  * `scripts/cad/generate_front_splitter.py`: front splitter (one part), test print, drawing `photos/cad_front_splitter_one_piece_drawing.png` (top view with the tyres and the body edge, 3D views, sections with the ground), checks (approx. 1 min; `--no-check` skips the tyre check and the assembly check). It reads the assembly STEP for the overlap check, so after a change of the splitter run the assembly first and then this script once more.
  * `scripts/cad/generate_front_splitter_measurement_sheet.py`: measurement sheet `cad/front_splitter/front_splitter_measurement_sheet.pdf` (M1 to M16, B1 to B6, S1 to S3, measured values of the owner in the rows).
  * `cad/studies/dual_motor/generate_dual_motor_study.py`: parts, assembly, checks and 2 pictures of the dual motor study (approx. 1.5 min; reads the assembly STEP of the build). `cad/studies/dual_motor/generate_dual_motor_electronics.py`: picture of the electronics layout (approx. 1 min; reads the assembly STEP of the study).
  * `scripts/cad/generate_wishbones.py`, `generate_camber_links.py`, `generate_driveshaft.py`, `generate_measurement_sheets.py`, `generate_knuckle_measurement_sheet.py`, `generate_pivot_blocks.py`, `scripts/generate_adr_readme.py`, `scripts/merge_specs.py`.
* Run long generators in the background and commit only after the checks have passed.
* Expected check results: running gear "overlaps: 0"; assembly only the 3 known interferences (lower bulkhead End B / pivot block End B, outer: 0.82 mm³; lower bulkhead End A / front wishbone, left and right: 2.16 mm³ each); front splitter: no overlap with the chassis plate, the body posts and the 30 parts at End A, tyre clearance 11.44 mm (required 3 mm); dual motor study and electronics layout: 0 mm³.
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

* Files that change without a change of geometry and must be restored by hand: `cad/running_gear/steering/spacers_of_the_bridge.step`, `cad/parts/rear_drive/bearing_5x10x4.stl`, `cad/parts/camber_link/turnbuckle_M3x37.stl`; the assembly STEP when only the order of the colours changed; an STL file of a cut solid (test print) can come back with another triangle order (compare the number of triangles and the surface area).
* Boolean operations: do not fuse a solid onto an identical existing face; the following booleans fail silently. A closed spline with tangents loops: build the outline of the mount from one half spline with unit tangents (`scale=False`) and mirror it (`mount_outline_wire`).
* Wires and cables: one circle swept along a spline (`cq.Solid.sweep`). A compound of many cylinders and spheres made the interference check run for more than 20 min with high memory use.
* The assembly STEP can be read with the part names and colours through XCAF (`read_assembly` in `generate_dual_motor_study.py`, approx. 6 s for 186 parts); the colours in the file are linear RGB.

## Work of this session
* Handover of the previous session carried to `main` (the updated file was not part of pull request #89).
* Dual motor study (`cad/studies/dual_motor`, see its readme; owner: study, then committed on request):
  * Dual motor mount: the verified motor mount with the tall part mirrored to the left side instead of the hook beside the bearing seat; plate 6.0 mm at y = 59.48 to 65.48 mm, 99.0 mm wide, 33.0 mm above the chassis plate, approx. 33.7 g in 7075 (single mount 18.1 g). Bearing seat and cap unchanged. 3 screws M3 from below: H09, H10 and a new hole H37 (H09 mirrored, x = -45.33 mm).
  * 2 motors 3660 (simple bodies) at x = ±31.90 mm on the height of the pinion axis: pinions 48T on the spur gear 72T (ratio as 45T on 68T), centre distance 31.75 mm plus 0.15 mm backlash (the simplified teeth touch without it). Both motors turn in the same direction.
  * Study chassis plate: the right motor window mirrored to the left side (x = -40.06 to -16.59 mm, y = 65.63 to 128.90 mm). H12 and H15 lie in the window; H11 and H14 keep walls of 0.94 and 0.85 mm and their countersinks open into the window: the 4 holes are closed in the study plate. The motor axes are fixed by the spur gear, so the window cannot be moved clear of them.
  * Electronics layout (picture): ESC Hobbywing QuicRun WP 10BL120 G2 (52.8 x 39.8 x 38.2 mm, manufacturer) crosswise behind each motor (the servo mount leaves 43 mm on the right side); battery 3S shorty hardcase (95.7 x 46.8 x 24.7 mm, Reedy Wolfpack 3000 mAh) on edge on the outer side of each ESC (flat it does not fit within the plate), each battery feeds the ESC on its side through an XT60 pair; motor wires; receiver (size assumed 36 x 24 x 14 mm) on the top plate of the servo mount; signal cables of both ESCs joined in a Y junction on the top brace to channel 2, servo cable to channel 1; the red wire (BEC +) of one ESC is to be removed at the Y junction.
* Front splitter, 3D print of the owner: the tightened screws M3x6 broke through the top of the bosses (0.5 mm of material above the blind holes). The bosses on H34, H35 and H36 are 3.0 mm higher (top at z = 10.0 mm, 3.5 mm above the holes, parameter `one_piece`). Status verified (owner). Volume 37.6 cm³, approx. 48 g in PETG; speedrun mass total 465 g. Assembly regenerated.
* Three-part front splitter set removed (owner): body post mount, carbon splitter, holder plate (STEP, STL, DXF, geometry data, test print) and the drawing `photos/cad_front_splitter_drawing.png` are deleted. `generate_front_splitter.py` builds only the one part (geometry identical); its drawing also shows the top view with the tyres and the body edge. Parameter file: `screws`, `collar`, `test_print` instead of `stack_screws`, `splitter_t`, `splitter_holes`, `holder_plate` and `splitter_test_print`. Measurement sheet rewritten for the one part (S4 removed, B4 = 3.0 mm). Readmes (root, CAD, parts) and the comments of the assembly script describe the one part.

## Current geometry (key values)
| Value | Model |
|:---|:---|
| Front kingpin axis | x = 63.65 mm, 6.75 mm inside the outer hinge pin (x = 70.4 mm), caster 10 degrees; at the height of the axle y = 284.87 mm (2.0 mm toward the middle of the car from the middle of the front wishbone, parameter `kingpin_y`), z = 22.0 mm |
| Wheelbase | approx. 257.8 mm between the wheel centres (T410R: 258 mm) |
| Outer faces of the hex hubs | x = ±86.85 mm front and rear (front hex hubs 6 mm, rear 7 mm) |
| Overall width | 187 mm over tyres of 26 mm (as the original car, owner), 191 mm over tyres of 30 mm |
| Front wishbone | 49.7 mm axis to axis (measured 45.26 mm, prolonged by 4.44 mm) |
| Rear wishbone | 54.3 mm axis to axis (measured) |
| CVD drive shafts | centre to centre front 40.2 mm, rear 41.1 mm |
| Camber links | gap front 28.0 mm, rear 25.8 mm (turnbuckle M3x37) |
| Steering | Ackermann 84 / 100 / 118 % at 15 / 20 / 25 degrees; free steering angle 35 degrees toward the middle, 45 degrees or more toward the outside; servo approx. 51 degrees for 25 degrees of the inner wheel (horn 10 mm) |
| Motor axis of the motor mount | x = 24.6 to 33.85 mm (spur gear plus pinion 93 to 127 teeth, 48DP) |
| Front splitter | one part, 187 x 94 mm; front end y = 407.89 mm (90 mm ahead of the axis H34-H35, 82.3 mm ahead of the chassis plate); z = 0 to 3.0 mm (body on it at 3.0 mm); bosses 6.3 mm on H34, H35 and H36 up to z = 10.0 mm, blind tapped holes for countersunk screws M3x6 from below |
| Lower front edge of the body | 17.5 mm behind the front edge of the splitter (owner: 15 to 20 mm), on the centre line 72.5 mm ahead of the axis H34-H35; form assumed |
| Body posts | in the ears at x = ±32.8 mm, y = 329.98 mm; hexagon 7.06 mm from 2.31 mm above the bottom face of the chassis plate |
| Dual motor study (not part of the build) | motor axes x = ±31.90 mm, z = 19.20 mm; mount 99.0 x 6.0 x 33.0 mm; ESCs at x = ±9.5 to ±62.3 mm, y = 129.4 to 169.2 mm; batteries on edge at x = ±66.0 to ±90.7 mm, y = 100.0 to 195.7 mm |

## Status of the parts
* Verified (green): chassis plate, bulkheads, top brace, shock towers, pivot blocks, motor mount with cap, steering knuckles, front splitter (one part, 3D print of the owner; bosses 3 mm higher after the print).
* Measures qualified (yellow): centre driveshaft, rear and front drive line, differential, spool, front and rear wishbones (the front wishbone is longer than measured).
* Completely unqualified (red): cup joints, diff outdrives, inner hinge pins, camber links, C-hubs (3D print verification with the guide sleeves planned by the owner), rear hub carriers, axles and hex hubs, CVD drive shafts, steering, sway bars, dampers.

## Open points
* Front splitter: as a 3D print in PETG the plate (3.0 mm) is less stiff than a carbon plate. Measurement sheet: form of the lower front edge of the body (B1 to B3, the outline of the splitter follows `front_form`), wheel arches (B5), length of the body posts (B6), ramp of the mount (M10), droop of the front wheels (S3). The body posts and the body mounting holes must be set so that the body sits on the splitter (B4 = 3.0 mm).
* ADR-009 (foam bumper flush with the front apron of the body) and ADR-010 (GPS module on the front foam bumper) still refer to the foam bumper, which is no longer used; the GPS module needs a new position (for example on the splitter).
* Dual motor study: new position of the battery (on the car it lies on the left side); batteries on edge 48.8 mm high under the body (body not modelled); gap of 3.9 mm between the motor and the ESC for the motor wires; 2 ESCs with the same throttle signal; torque on the spur gear, the rear pinion shaft and the drive line doubles (not evaluated); the study assembly contains the splitter with the old bosses (7.0 mm).
* Front camber links: in the static position the rod ends lie 0.17 mm beside the narrowed wall of the upper bulkhead at End A (0.28 mm before the kingpin axis was moved 2.0 mm toward the middle of the car); the clearance over the suspension travel is not checked.
* C-hub: Owner: the top guide sleeve is inserted from below, so its foot (approx. 0.6 mm thick) lies between the C-hub and the knuckle and needs clearance there; the model still has the flange (1.0 mm) on top of the upper arm. The model is changed after further measurements of the owner (orientation of the lower sleeve, thickness of the foot, total length of the sleeve). 3D print verification with the guide sleeves; the dimensions of the sleeves are scaled from the manual (a caliper value of the original sleeve confirms them); the wall between the pocket of the lower screw head and the tube on the hinge pin is only 0.3 mm.
* Steering knuckle: open dimensions K11, K14, K16 and K19 of the measurement sheet.
* Track: the 0.5 mm gaps between the knuckle ring and the front hex hub and between the tube of the hub carrier and the rear hex hub, and the radius 3.6 mm of the lug of the hub carrier are assumptions. A measurement of the outer faces of the hex hubs on the car, front and rear, confirms the prolonged front wishbone.
* Rear hub carrier: in the photo the axle lies approx. 17 mm above the hinge pin, in the model 10.4 mm (ride height 15 mm, wishbone horizontal); a caliper value confirms or corrects it. The original part has 2 holes in the top tab; the model has one.
* Ackermann (84 to 118 %) and servo travel (approx. 51 degrees): the bellcranks are an assumption from the manual; extended end points or a horn of 12.5 mm (approx. 39 degrees).
* Wheels are not modelled; the wishbones are horizontal at the ride height of setup sheet 4 (10 mm front, 15 mm rear).
* Not changed to 130 km/h: the gearing plot `scripts/plots/gearing_plot.py` (100 km/h line thicker), `specs/mechanics/carten_t410r/spec_cartent410r.yaml` (track width 190 mm), the project name "RC100".
