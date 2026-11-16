# Session summary (handover)

Handover of the CAD session that ended on 2026-11-16, for the next session. Read this file, `CLAUDE.md` and the [CAD readme](../cad/readme.md) first.

## Table of contents
* [State of the repository](#state-of-the-repository)
* [Rules of the owner](#rules-of-the-owner)
* [Workflow](#workflow)
* [Work of this session](#work-of-this-session)
* [Current geometry (key values)](#current-geometry-key-values)
* [Status of the parts](#status-of-the-parts)
* [Open points](#open-points)

## State of the repository
* Work branch: `ccr-a9bb1886-3anw1b`. All changes are committed and pushed (last commit `42cb4ee`, motor mount with a round upper inner corner). No pull request was created; the branch is not merged into `main`.
* The previous handover (branch `claude/new-session-1yf69h`) no longer exists on the remote; this file replaces it.
* Generated files are up to date: STEP/STL files, drawings in `photos/`, measurement sheets, the assembly `cad/assembly/speedrun_chassis_T410R.step`, `architecture/README.md` and `specs/full_spec.yaml`.

## Rules of the owner
* `CLAUDE.md`: English, sentence case also in headings, list items and table entries, table of contents as soon as a Markdown file has more than one heading, no emojis, objective style without filler words.
* Commits: `CLAUDE.md` requires the approval of the owner for each commit. In this session the owner approved commit and push for the whole session; ask again in a new session.
* Commit messages end with the 2 attribution lines given by the environment (`Co-Authored-By: ...` and `Claude-Session: ...`).
* The inside of the lower and upper bulkhead (verified with test prints) must not be changed; the generators of the bulkheads run a functional check.
* Do not change `scripts/generate_setup_drawing.py`, `photos/latest_setup_drawing.svg`, `docs/latest_setup_drawing.svg` or `.github/workflows/*`.
* No Carten part numbers (NBA..., NHA...) in docs, drawings or file names (purchase lists excepted).
* Wording: the parts besides the speedrun chassis are "own design, partly based on the (Carten) T410R"; the group is called "further own parts". The word "re-engineered" is not used any more.
* Third-party STL files stay in `cad/`. Force push is not allowed. The chassis plate is ordered: only its existing holes can be used (steering posts H24/H25, servo mount H17/H21, motor mount H09/H10).

## Workflow
* Run the scripts from the root directory with `PYTHONDONTWRITEBYTECODE=1`; delete `scripts/cad/__pycache__` before a commit.
* Generators and run times (approx.):
  * `scripts/cad/generate_running_gear.py`: running gear, drawing, steering lock check, bellcrank sweep and overlap check of all parts (10 to 15 min; `--no-check` skips the overlap check).
  * `scripts/cad/generate_speedrun_assembly.py`: assembly STEP, assembly picture and interference check of all 183 parts (approx. 10 min).
  * `scripts/cad/generate_wishbones.py`, `generate_camber_links.py`, `generate_driveshaft.py` (drive line, motor mount, drawings), `generate_measurement_sheets.py`, `generate_knuckle_measurement_sheet.py`, `generate_pivot_blocks.py`.
  * `scripts/generate_adr_readme.py` (ADR readme from `architecture/adr_*.yaml`) and `scripts/merge_specs.py` (`specs/full_spec.yaml`).
* Run long generators in the background and commit only after the checks have passed.
* Expected check results: running gear "overlaps: 0"; assembly only the 3 known interferences (lower bulkhead End B / pivot block End B, outer: 0.82 mm³; lower bulkhead End A / front wishbone, left and right: 2.16 mm³ each).
* The generators rewrite all STEP and STL files with new headers. Before a commit, restore the files whose geometry did not change (normalised comparison with `HEAD`). The following script did this in the session (save it in a scratch directory and run it from the root directory):

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

* Files that change without a change of geometry and must be restored by hand: `cad/running_gear/steering/spacers_of_the_bridge.step`, `cad/parts/rear_drive/bearing_5x10x4.stl`, `cad/parts/camber_link/turnbuckle_M3x37.stl`; the assembly STEP when only the order of the colours changed.
* Boolean operations: do not fuse a solid onto an identical existing face (for example a cylinder on the existing lug); the following booleans fail silently and the overlap check is no longer reliable. Leave the region out of the cut instead.

## Work of this session
* Readme and documents:
  * Design goal: top speed over 130 km/h (root readme, CAD readme, ADRs, specs). Values derived from the speed are recalculated (36.1 m/s, axle approx. 10,800 rpm, 45T pinion for 130 km/h with the 68T spur gear). Not changed: load capacities of the spur gear and the differentials (marked "not evaluated for 130 km/h"), the GPS function "0-100 km/h", the project name "RC100", the test drive logs.
  * The root readme describes the CAD model of the 1:10 on-road car with speedrun-specific parts, refers to the status tables and notes that the photos show the parts of the manufacturers.
  * The differential inset is removed from the assembly picture.
* Sway bars (manual steps 22 and 23) and the floating servo mount (manual step 10) are reworked.
* Motor mount and cap: rebuilt from the photos of the owner; long holes of the motor screws extended; grooves removed (smooth faces); upper inner corner one radius R9.0 below the end of the top brace (upper long hole from x = 19.05 mm, wall 2.1 mm). Verified by a test print of the owner (status green).
* Steering knuckle: built from the measurement sheet of the owner (K1 to K21: ring 14.1 x 16.7 mm from the kingpin axis, seats 4.29 mm, lip 2.33 mm, entry bore 12.4 x 5.79 mm, bosses 7 mm with 21.1 mm between the end faces, kingpin bores 2.7 x 4.5 mm, steering ball 5 mm inboard and 25 mm behind the kingpin axis, arm 4.9 mm, tab 7.4 mm). Verified by a 3D print of the owner (status green).
* C-hub (front): solid upper arm with a U-slot for the upper boss (the knuckle slides in from the wheel side); passage 10 mm for the CVD bone with its pin; back plate and upper arm 15 mm wide (13.5 mm above the shock plate of the wishbone, 11.6 mm below); kingpin bores 5 mm through both arms with 2 identical flanged guide sleeves (4.95 x 3.1 mm, flange 6.4 x 1.0 mm, shank 3.6 mm; sizes scaled from the manual drawing). Top: flange outside, the camber ball stud 4.8x9 is the top kingpin (the ball sits on the kingpin axis). Bottom: flange inside in a counterbore, socket head screw M3x8 from below, its head in a pocket beside the tube on the hinge pin.
* Wishbones: second measurement of the owner over the lugs: front 52.46 mm, rear 61.5 mm (axis to axis 45.26 mm and 54.3 mm). The front wishbone is prolonged by 4.44 mm (49.7 mm axis to axis, owner) so that the kingpin lies 6.75 mm inside the outer hinge pin (lower bore clear of the hinge pin tube) and the track is equal front and rear.
* Rear hub carrier: as the original part (photos of the owner): tube 10 mm long, approx. 14.6 mm in diameter, outer end flush with the lug on the hinge pin, bearings in the ends of the tube against a lip of 2 mm, sloped arm to the camber seat.
* Camber links: front outer ball on the top kingpin (gap 28.0 mm, screwed out from the manual value 24.0 mm); rear gap 25.8 mm (manual).
* Hinge pin of the C-hub 3 mm (owner); joint cups of the axles 10 mm (owner).

## Current geometry (key values)
| Value | Model |
|:---|:---|
| Front kingpin axis | x = 63.65 mm, 6.75 mm inside the outer hinge pin (x = 70.4 mm), caster 10 degrees |
| Outer faces of the hex hubs | x = ±86.85 mm front and rear (front hex hubs 6 mm, rear 7 mm) |
| Overall width | 187 mm over tyres of 26 mm (as the original car, owner), 191 mm over tyres of 30 mm |
| Front wishbone | 49.7 mm axis to axis (measured 45.26 mm, prolonged by 4.44 mm) |
| Rear wishbone | 54.3 mm axis to axis (measured) |
| CVD drive shafts | centre to centre front 40.2 mm, rear 41.1 mm |
| Camber links | gap front 28.0 mm, rear 25.8 mm (turnbuckle M3x37) |
| Steering | Ackermann 114 / 128 / 144 % at 15 / 20 / 25 degrees; free steering angle 30 degrees toward the middle, 45 degrees or more toward the outside; servo approx. 48 degrees for 25 degrees of the inner wheel (horn 10 mm) |
| Motor axis of the motor mount | x = 24.6 to 33.85 mm (spur gear plus pinion 93 to 127 teeth, 48DP) |

## Status of the parts
* Verified (green): chassis plate, bulkheads, top brace, shock towers, pivot blocks, motor mount with cap, steering knuckles.
* Measures qualified (yellow): centre driveshaft, rear and front drive line, differential, spool, front and rear wishbones (the front wishbone is longer than measured).
* Completely unqualified (red): cup joints, diff outdrives, inner hinge pins, camber links, C-hubs (3D print verification with the guide sleeves planned by the owner), rear hub carriers, axles and hex hubs, CVD drive shafts, steering, sway bars, dampers.

## Open points
* C-hub: 3D print verification with the guide sleeves; the dimensions of the sleeves are scaled from the manual (a caliper value of the original sleeve confirms them); the wall between the pocket of the lower screw head and the tube on the hinge pin is only 0.3 mm.
* Steering knuckle: open dimensions K11, K14, K16 and K19 of the measurement sheet.
* Track: the 0.5 mm gaps between the knuckle ring and the front hex hub and between the tube of the hub carrier and the rear hex hub, and the radius 3.6 mm of the lug of the hub carrier are assumptions. A measurement of the outer faces of the hex hubs on the car, front and rear, confirms the prolonged front wishbone.
* Rear hub carrier: in the photo the axle lies approx. 17 mm above the hinge pin, in the model 10.4 mm (ride height 15 mm, wishbone horizontal); a caliper value confirms or corrects it. The original part has 2 holes in the top tab; the model has one.
* Ackermann (114 to 144 %) and servo travel (approx. 48 degrees): the bellcranks are an assumption from the manual; extended end points or a horn of 12.5 mm (approx. 37 degrees).
* Wheels are not modelled; the wishbones are horizontal at the ride height of setup sheet 4 (10 mm front, 15 mm rear).
* Not changed to 130 km/h: the gearing plot `scripts/plots/gearing_plot.py` (100 km/h line thicker), `specs/mechanics/carten_t410r/spec_cartent410r.yaml` (track width 190 mm), the project name "RC100".
