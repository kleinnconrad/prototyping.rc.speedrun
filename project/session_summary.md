# Session summary (handover)

Handover of the CAD session that ended on 2026-11-20, for the next session. Work of the session: rear hub carrier reworked with the values of the owner, C-hub as right and left part, track measured by the owner, wishbones with bores Ø3.2 and a new optical design, grub screw bosses, battery tray and servo mount verified, colour scheme of all CAD pictures in blue and grey; in a follow-up session the assembly drawing (views and main dimensions). Read this file, `CLAUDE.md` and the [CAD readme](../cad/readme.md) first.

## Table of contents
* [State of the repository](#state-of-the-repository)
* [Next step: track front and rear](#next-step-track-front-and-rear)
* [Rules of the owner](#rules-of-the-owner)
* [Workflow](#workflow)
* [Work of this session](#work-of-this-session)
* [Current geometry (key values)](#current-geometry-key-values)
* [Status of the parts](#status-of-the-parts)
* [Open points](#open-points)

## State of the repository
* The work of the session (rear hub carrier, C-hub right and left, wishbones, grub screw bosses, battery tray and servo mount verified, colour scheme, this handover) is merged into `main` with pull request #105 (`a4e2a6d`).
* Follow-up session (2026-11-20, branch `ccr-1e4a1ee8-mogryr`, pushed, no pull request): assembly drawing with the views and the main dimensions (see [work of this session](#work-of-this-session)).
* Generated files are up to date: running gear, camber links, wishbones, assembly (STEP with the colours of the scheme, picture), front splitter, battery tray, drive line pictures, bulkhead previews, shock tower pictures, dual motor study and electronics layout; technical drawings of the C-hubs (CH-R, CH-L), the steering knuckle, the wishbones, the battery tray and the servo mount. The other technical drawings keep their date. `architecture/README.md` and `specs/full_spec.yaml` were not changed.
* The dual motor study was regenerated on 2026-11-20 with the current build (without the battery of the build, see below).

## Next step: track front and rear
Measured by the owner on the original car (2026-11-20):
* Outer face to outer face of the hex hubs: 173.7 mm front and rear (equal track).
* Outer face of the hub (knuckle ring at the front, bearing tube of the hub carrier at the rear) to the outer end of the hex hub: front 5.6 mm, rear 6.6 mm. The model has 6.5 (gap 0.5 + hex hub 6.0) and 7.5 (gap 0.5 + hex hub 7.0): both 0.9 mm shorter.

The model is not yet changed to these values. Per side (centre line to the outer face of the hex hub):

| | Front | Rear |
|:---|:---|:---|
| Model now | 88.85 | 86.85 |
| With 5.6 / 6.6 of the owner | 87.95 | 85.95 |
| Measured (173.7 / 2) | 86.85 | 86.85 |
| Rest | 1.1 too wide | 0.9 too narrow |

* **Front chain (model):** centre line to inner hinge pin 20.70 (pivot blocks, verified) + front wishbone 51.70 (owner: equal to the original part) - kingpin 6.75 inside the outer hinge pin (C-hub) + kingpin axis to the outer face of the knuckle ring 16.70 (K2, K10) + 6.5. The owner compared the C-hub, the knuckle and the wishbone with the original parts (OK); 1.1 mm can be missed in such a comparison. The front CVD drive shafts of the T410R fit with the kingpin at x = 65.65 (CVD 42.3); a kingpin further in shortens the CVD.
* **Rear chain (model):** 21.50 + rear wishbone 54.26 + R1 3.6 (outer face of the bearing tube beyond the hinge pin axis: flush with the tube on the hinge pin, radius 3.6 assumed) + 7.5. With 6.6 the measured track needs R1 = 4.5: either the tube on the hinge pin is approx. Ø9 (flush) or the bearing tube stands approx. 0.9 out beyond it.
* **Asked from the owner (not answered yet):**
  1. Rear hub carrier, pin Ø3 in the hinge pin bore: outer face of the bearing tube to the far side of the pin (outside jaws): model 5.1, the track needs 6.0; and the outer diameter of the tube on the hinge pin (model 7.2).
  2. Front C-hub, pin Ø3 in the hinge pin bore and drill Ø5 in a kingpin bore: across both along the axle: model 10.75 (6.75 + 1.5 + 2.5); 11.85 if the 1.1 lies in the C-hub.
  3. Front knuckle, drill Ø2.7 in a kingpin bore: outer face of the ring to the far side of the drill along the axle: model 18.05 (16.7 + 1.35); 16.95 if the 1.1 lies in the knuckle.
* **Option offered (not decided):** change the model now with derived values: hex hubs 5.6 / 6.6 from the face, the rear bearing tube 0.9 further out, the front kingpin 1.1 further in (front CVD approx. 1.1 shorter).
* **Where to change:** `hex_hub` (or the gap 0.5 in `axle_group` calls) and `kingpin_x` or `knuckle` in `cad/generic_parts/running_gear_parameters.json`; `rear_carrier`, `rear_carrier_bores` (radius of the tube on the hinge pin), `rear_carrier_layout()` and `rear_corner()` in `scripts/cad/generate_running_gear.py`. Consequences: CVD lengths, camber link gaps (the rear camber ball follows the stud of the hub carrier: `rear_camber_ball()`), `wheel_centre_x` and its note (wheel offset 6.35 from the face of the hex hub), the front splitter tyre check, the track rows of the CAD readme and of this file, the main dimensions of the assembly drawing (the CAD readme lists them). Generators: running gear, camber links, assembly, then front splitter, battery tray and the assembly drawing; expected: running gear "overlaps: 0", assembly only the 3 known interferences.
* A picture of what to measure for the track was made for the owner (scratch, not in the repository).

## Rules of the owner
* `CLAUDE.md`: English, sentence case also in headings, list items and table entries, table of contents as soon as a Markdown file has more than one heading, no emojis, objective style without filler words.
* Commits: `CLAUDE.md` requires the approval of the owner for each commit. In both sessions of 2026-11-20 the owner approved commit and push for the whole session; ask again in a new session.
* Commit messages end with the 2 attribution lines given by the environment (`Co-Authored-By: ...` and `Claude-Session: ...`).
* The inside of the lower and upper bulkhead (verified with test prints) must not be changed; the generators of the bulkheads run a functional check.
* Do not change `scripts/generate_setup_drawing.py`, `photos/latest_setup_drawing.svg`, `docs/latest_setup_drawing.svg` or `.github/workflows/*`.
* No Carten part numbers (NBA..., NHA...) in docs, drawings or file names (purchase lists excepted).
* Wording: the parts besides the speedrun parts are "own design, partly based on the (Carten) T410R"; the group is called "further own parts". The word "re-engineered" is not used any more. The front splitter is a speedrun part (owner), directory `cad/speedrun_parts/front_splitter`.
* Headline of the assembly picture: only "Speedrun Chassis" (owner: everyone checking the repository knows that it is based on the Carten).
* Colour scheme: all CAD pictures in blue and grey shades only, one colour per group of parts, defined in `scripts/cad/palette.py`; the assembly picture has no legend (owner). New picture scripts use the palette.
* Optical design changes leave the technical function fully untouched (owner); the interfaces (lugs, bores, bosses, holes) stay, the overlap checks run before a commit.
* Front splitter: only the one-part design is kept (owner).
* CAD readme (owner, 2026-11-21): of the chassis plates only the speedrun chassis plate (wide) with the longer motor window is described; the T410R chassis plate, the first wide plate without the longer window and the original top brace are not described any more. Their files stay in `cad/speedrun_parts/chassis` as source data (geometry of the holes, outline of the wide plate, test print), the scripts table names them as such.
* Studies (owner: "just a study for now"): directory `cad/studies/<name>` with its own readme and script, not part of the build; the parts of the build and the assembly are not changed by a study.
* Third-party STL files stay in `cad/3d_print_fdm`. Force push is not allowed. The chassis plate is ordered: only its existing holes can be used (steering posts H24/H25, servo mount H17/H21, motor mount H09/H10, front splitter H34/H35/H36). The plate of the dual motor study is a study only.
* The owner sends photos and caliper values; values of the owner have the source `owner` (or `user`) in the parameter files and the measured column of the measurement sheets.

## Workflow
* The CAD packages are not preinstalled in a fresh container: `pip install cadquery ezdxf matplotlib reportlab pyflakes` (approx. 2 min; cadquery 2.8 with Python 3.13 works).
* Run the scripts from the root directory with `PYTHONDONTWRITEBYTECODE=1`; delete `scripts/cad/__pycache__` and `cad/studies/dual_motor/__pycache__` before a commit.
* Generators and run times (approx.):
  * `scripts/cad/generate_running_gear.py`: running gear, drawing, steering lock check, bellcrank sweep and overlap check of all parts (10 to 15 min; `--no-check` skips the overlap check). It writes a file per side for the handed parts (`HANDED`: C-hub).
  * `scripts/cad/generate_speedrun_assembly.py`: assembly STEP (with the colours of the palette), assembly picture and interference check of all 192 parts (approx. 10 min). For the picture alone (geometry and colours unchanged): `import generate_speedrun_assembly as A; A.image(A.build(), A.OUT_PNG)` (approx. 3 min).
  * `scripts/cad/generate_camber_links.py`: camber links, drawing, check (approx. 8 min; builds the assembly for the check).
  * `scripts/cad/generate_wishbones.py`: wishbones, hinge pins, drawing, checks (approx. 1 min).
  * `scripts/cad/generate_front_splitter.py` and `scripts/cad/generate_battery_tray.py`: approx. 1 min each; both read the assembly STEP, so run the assembly first.
  * `cad/studies/rear_fork_carrier/generate_rear_fork_carrier_study.py` (approx. 5 min, reads the assembly STEP; study parts, checks, pictures).
  * `cad/studies/dual_motor/generate_dual_motor_study.py` (approx. 1.5 min, reads the assembly STEP of the build without its battery, tray and straps: `BUILD_BATTERY`) and `generate_dual_motor_electronics.py` (approx. 1 min, reads the assembly STEP of the study).
  * `scripts/cad/generate_assembly_drawing.py`: assembly drawing `cad/assembly/speedrun_chassis_T410R_technical_drawing.pdf` (one sheet A3, 1:2: side view from -x, top view, view from End A; main dimensions read from the assembly STEP: hex hub faces, axle axes, extremes), PNG and `cad/assembly/readme.md` (approx. 1.5 min; run after the assembly; `--date`).
  * `scripts/cad/generate_technical_drawings.py`: technical drawings, PDF and one PNG per sheet plus a generated readme per directory (`--part KEY1,KEY2`; the readme of a directory is written when all of its parts are drawn; the date in the title block is today, so redraw only the changed parts). Keys of the front corner: `c_hub`, `c_hub_left`, `steering_knuckle`. Option `labels_right` of a section puts the callouts in a column right of the view (mirrored parts).
  * `scripts/cad/generate_bulkhead_drawings.py` (`--sheet` to a scratch path writes only the preview), `generate_bulkhead_upper_drawings.py`, `generate_shock_towers.py`, `generate_driveshaft.py`, `generate_drawing.py`: pictures of the bulkheads, shock towers, drive line and chassis plate.
  * Further: `generate_measurement_sheets.py`, `generate_knuckle_measurement_sheet.py`, `generate_front_splitter_measurement_sheet.py`, `generate_pivot_blocks.py`, `generate_bulkhead_technical_drawings.py`, `scripts/generate_adr_readme.py`, `scripts/merge_specs.py`.
* Run long generators in the background with separate log files; do not delete log files in a command that runs in parallel with the generators (the logs of 2 runs were lost that way in this session).
* Expected check results: running gear "overlaps: 0"; camber links largest overlap 0; assembly only the 3 known interferences (lower bulkhead End B / pivot block End B, outer: 0.82 mm³; lower bulkhead End A / front wishbone, left and right: 4.47 mm³ each since the tube on the inner hinge pin is closed, before 2.16 mm³); front splitter: no overlap, tyre clearance 12.81 mm; battery tray: no overlap, left steering 2.35 mm clear; dual motor study and electronics layout: 0 mm³.
* The generators rewrite all STEP, STL and DXF files (and the shock tower generator its templates and DXF) with new headers. Before a commit, restore the files whose geometry did not change (normalised comparison with `HEAD`, script below; for renamed files compare with the old path). Restore by hand: `cad/generic_parts/rear_drive/bearing_5x10x4.stl`, `cad/generic_parts/camber_link/turnbuckle_M3x37.stl`, the shock tower DXF and PDF templates, pictures whose pixels differ only by noise (compare the images).

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

* When a description of the owner is ambiguous (for example "king pin bore" on the rear hub carrier, which meant the camber stud bore), ask before changing the model.
* Boolean operations: do not fuse a solid onto an identical existing face; the following booleans fail silently. Symmetry of a part: compare the part with its reflection about a candidate plane (volume of the difference); a part without a plane of symmetry needs a left and a right file.
* The assembly STEP can be read with the part names and colours through XCAF (`read_assembly` in `generate_dual_motor_study.py`, approx. 6 s for 192 parts); the colours in the file are linear RGB.

## Work of this session
* **Rear hub carrier** (owner, 2 steps; parameters `rear_carrier`, `rear_carrier_bores`): tube on the hinge pin with bore Ø3.1 for the pin Ø3.0 (radius 3.6 assumed); bearing tube 10 long, outer end flush with the tube on the hinge pin, 2 bearings 5x10x4 in its ends, separated by a lip 1.0 high (bore 8.0, 2.0 wide); lower end of the bearing tube 11.4 above the outer lower end of the tube on the hinge pin (axle 15.1 above the hinge pin with the tube 14.6 from the photo); height 30.4 to the upper end; camber stud bore 13.7 from the outer face of the bearing tube, centred on the vertical middle plane (the owner's "king pin bore"; the first value 13.3 is replaced). Status yellow (owner).
* **Rear axle height** (owner: the rear wishbones stay horizontal): follows from the hub carrier, 21.7 instead of 17.0; rear ride height 10.3 in the model (setup sheet 4: 15, parameter `ride_height` rear not used, note).
* **Rear camber links:** the outer ball sits on the stud of the hub carrier (`rear_camber_ball()`, used by `generate_camber_links.py` as for the front); gap 30.1 (manual 25.8), ball 1.1 below the inner ball. Parameter `outer_height_offset` removed.
* **C-hub as right and left part** (owner: the same part cannot be used on both sides because of the caster): files `c_hub_end_a_right` (old `c_hub_end_a`, geometry unchanged) and `c_hub_end_a_left` (mirror image); technical drawings CH-R and CH-L. Symmetry check: the steering knuckle (turned upside down on the left side) and the rear hub carrier are the same part on both sides.
* **Track:** measured by the owner (see next step); picture of the measurements for the owner.
* **Wishbones:** hinge pin bores Ø3.2 instead of Ø3.1 (owner: the pins Ø3.0 had to be pressed into an FDM print; MJF prints; ream with a drill Ø3.1 to Ø3.2 if tight); technical drawings with nylon PA12 (MJF) and the MJF process tolerance.
* **Wishbones, optical design** (owner: 5 concepts shown, concept E chosen, then refined): the inner lugs form one tube Ø7.2 of constant diameter (notch closed); a closed plate as high as the rails from the tube to the outer cross bar (no step) with lightening holes of the same size: front 3 x Ø3.5 (pitch 4.75), rear 4 x Ø5.0 (evenly spaced, pitch 8.88); X ribs removed (`rib_w`, `rib_top`); no engraving. New parameters `web`, `front_web_holes`, `rear_web_holes`. Front shock plate: middle hole added (owner); the damper hole is a parameter now (`damper_hole_z`: front upper hole 9.9, rear middle hole 6.6), damper geometry unchanged. Mass front 6.3 g, rear 8.0 g (before 5.2 and 5.5); clearance to the CVD drive shafts 3.7 / 3.6 (static).
* **Grub screws M3x4** on the outer hinge pins of the C-hub and the rear hub carrier (owner): the thread reached only approx. 2 mm into the tube; boss Ø6.0 below the tube (parameter `grub_screw_boss`), face 5.7 below the pin axis, thread 4.2, the screw lies fully in it.
* **Status:** battery tray verified (owner); servo mount (top plate, fixed post, floating post) verified (owner) with the note that the holes for the servo ears are to be checked against the servo before printing (parts lists, open points, drawings of the posts).
* **Colour scheme** (owner): all CAD pictures in blue and grey shades (`scripts/cad/palette.py`, used by all picture scripts), assembly picture without legend and with the headline "Speedrun Chassis". The test print picture (no generator) was recoloured from the old picture. Annotations (red dimensions and labels, orange hole labels of the chassis drawing, markers of new or closed holes) and the red and black battery wires keep their colours.
* **Dual motor study:** regenerated with the current build; the battery, tray and straps of the build are left out (`BUILD_BATTERY`, the study has its own batteries), the servo cable runs behind the servo horn (the horn moved with the refined servo mount); checks 0 mm³.
* **Assembly drawing** (follow-up session, owner: views and main dimensions only, now, before the track change): drawing number RC-SR-AS, one sheet A3, scale 1:2, first angle projection; side view from the left side of the car (End A left), top view below it, view from End A right of it. Main dimensions from the model: overall length 419.4 (sway bar holder at End B to the tip of the front splitter), width 200.0 (chassis plate), height 61.6 (rear shock tower; the spur gear reaches 0.4 below the plate), wheelbase 257.5 (axle axes at the outer faces of the hex hubs), track 177.7 front and 173.7 rear, axle heights 22.0 front and 21.7 rear, front shock tower 53.3. Added on request (2026-11-21): caster 10.0 degrees at the front kingpin axis (axis of the kingpin screws, angle arc in the side view), width of the chassis plate labelled in the top view, overhangs 123.0 front and 38.8 rear in a chain with the wheelbase, ride height 10.0 front and 10.3 rear from a ground line with the tyres Ø64 as phantom lines (wheel centre plane 6.35 inside the face of the hex hub, `wheel_centre_x`), front kingpin axes 131.3 apart, front splitter 187.0 wide, rear toe-in 2.3 degrees on each side (axle axes); toe front and camber 0.0 in the notes. A note compares the track with the measured 173.7 (now: front +4.0, rear 0.0); it updates itself when the drawing is regenerated after the track change. Item numbers and a parts list were offered and not chosen.
* **CAD readme cleaned up** (follow-up session, owner): the sections of the T410R chassis plate and top brace and of the first wide plate are replaced by one section of the speedrun chassis plate (wide) with the longer motor window (design, motor window, measurement basis with the test print of the T410R plate, print template, files and coordinate system); the speedrun top brace section describes only the speedrun part; scripts table, regeneration commands and DXF generation reduced to the speedrun chassis plate. The anchor `#longer-motor-window-for-a-3660-motor` is kept; the plate readme and `generate_technical_drawings.py` link to the new section.
* **Study rear fork carrier** (owner: optional design, concept E "fork carrier on a tongue arm"; `cad/studies/rear_fork_carrier`, not part of the build; moved to `cad/generic_parts/rear_corner` and back to the studies on request of the owner): the rear wishbone ends in one tongue (tube 7.2, 7.0 long, bore 3.2); the grub screw M3x4 goes in from below in the middle of the tongue (owner), one boss below, no boss on top (owner), so the study has a right and a left wishbone (mirror images, the left one is not turned upside down); the rear hub carrier has a fork (2 lugs 6.0, bore 3.1, 22.0 over the lugs, bridge 1.5 above the tongue, no grub screw), above the column as the build. 6 shims 3x6x0.5 (3 per side in the middle position, axle as the build) set the wheelbase from 256.0 to 259.0 in steps of 0.5 (258.0 with 2 shims in front); the pin stays fixed in the tongue, the hub carrier slides on it. Rear wishbone as an A-frame (owner: need not be as massive): strut A = rail of the build with the shock plate, then to the tongue; strut B straight from the shoulder to the tongue; cross bar with the pad of the sway ball stud at x = 24.9; open window; all interfaces of the build; 5.04 cm³ (build 7.87, first draft with closed plate 7.79). Checks: 0 mm³ with the assembly (both sides); CVD distance 3.56 (as the build); swing free over ±25 degrees (1.02 mm at -15, 1.31 mm at +15); both shim end positions 0 mm³. Open: strength (test print), radii, swing against the suspension travel, shims to be bought. Script approx. 5 min after the assembly.
* **Top brace picture** (owner): the dashed outline of the original top brace is removed from `photos/cad_top_brace_speedrun_drawing.png` (function `drawing()` of `generate_top_brace_speedrun.py`, regenerated alone; the other files of the top brace are unchanged). The check of the outline against the original top brace stays.
* **Camber links purchased** (owner: the camber links will be bought, not made): the section of the camber links, its entry in the table of contents and in the list of the further own parts are removed from the CAD readme; the CAD readme and `cad/generic_parts/readme.md` describe `/generic_parts/camber_link` as a simplified model of purchased parts. The model and `generate_camber_links.py` stay for the assembly and its checks.
* **Study scale 1:8** (follow-up session): started (scaled assembly, plates with M4, batteries at the plate edges, drive line of the Arrma Limitless V2) and dropped by the owner (it does not work this way); the branch was deleted, nothing of it is on `main`. Do not resume it without a new request of the owner.
* **Folder structure of `cad`** (owner): the speedrun parts are in `cad/speedrun_parts` (`bulkhead`, `chassis`, `shock_tower`, `front_splitter`, `battery_tray`); the former `cad/parts` and `cad/running_gear` are merged into `cad/generic_parts` (no useful distinction between the groups; the running gear parameter file is `cad/generic_parts/running_gear_parameters.json`). `assembly`, `studies` and `3d_print_fdm` stay. Paths updated in all scripts, parameter files and readmes (the readme links of the speedrun parts are one level deeper); `cad/generic_parts/readme.md` describes the running gear folders too. All generators were run with the new paths in a copy of the repository; the functional checks of both bulkheads pass. The CHANGELOG keeps the old paths.
* **CAD tool** (owner): the CAD readme states that the project uses CadQuery (Python, OpenCascade kernel); the parts are generated by the scripts in `scripts/cad`. FluidCAD (JavaScript, same kernel) was proposed by the owner and not used (no better chamfers or fillets, the parts would leave the Python pipeline).
* **Edge treatment of the C-hubs and the rear hub carriers** (owner: chamfer on each sharp edge, radius in each sharp corner; sizes chosen by the owner: chamfer 0.3, radius 0.5; bearing seats, lip and sleeve counterbores kept sharp with an entry chamfer): new module `scripts/cad/edge_treatment.py`, parameter `edge_treatment` (sharp: faces at up to 120 degrees). It tries all edges at once, then groups of touching edges, then single edges with smaller sizes, in 3 variants, and keeps the one with the smallest deficit; each kernel operation runs in a forked child process with a time limit of 30 s (the kernel crashed and hung on some edges), results with a tolerance above 0.01 are rejected (one chamfer returned 0.23 and blocked all later operations), the kept result must pass a STEP export; results are cached in the temporary directory (95 s without, 15 s with the cache). Result: hub carrier 9 radii, 43 chamfers; C-hub 12 radii (one 0.3), 40 chamfers (3 reduced), 12 sharp edges shorter than 0.6 left (chamfer facets at the caster faces). Shape changes needed for it (features closer than 0.8): C-hub lower arm 11.0 wide (was 11.6) and 3.0 beyond the hinge pin axis, tube top trimmed by the face toward the lower boss (up to 0.2), upper arm 4.5 beyond the kingpin axis (was 3.5, the counterbore touched its end face); hub carrier column 5.2 x 7.2 (was 6.0 x 8.0), camber stud thread through. Checks: running gear 0 overlaps, free steering angle unchanged (35.0 toward the middle, 45 toward the outside), walls of the lower arm around the counterbore 2.04 / 1.97 (were 2.34 / 2.27). The steering knuckle was treated too (18 radii, 25 chamfers, arm root and gussets moved by 0.4 to 0.7) and then restored by the owner: it is verified and stays as it is (no risk). Regenerated: running gear, assembly, assembly drawing, technical drawings CH-R and CH-L, camber links, front splitter and battery tray checks, studies.

## Current geometry (key values)
| Value | Model |
|:---|:---|
| Front kingpin axis | x = 65.65 mm, 6.75 mm inside the outer hinge pin (x = 72.4 mm), caster 10 degrees; at the height of the axle y = 284.87 mm (2.0 mm toward the middle of the car from the middle of the front wishbone), z = 22.0 mm |
| Wheelbase | approx. 257.8 mm between the wheel centres (T410R: 258 mm) |
| Outer faces of the hex hubs | x = ±88.85 mm front, ±86.85 mm rear (model: gap 0.5 and hex hubs 6 / 7 mm); measured on the car 173.7 mm front and rear, 5.6 / 6.6 mm from the face of the hub (not yet in the model) |
| Front wishbone | 51.7 mm axis to axis; one tube Ø7.2 on the inner hinge pin, closed plate with 3 holes Ø3.5, bores Ø3.2 |
| Rear wishbone | 54.3 mm axis to axis; one tube Ø7.2, closed plate with 4 holes Ø5.0, bores Ø3.2 |
| Ride height and axle height | front 10 mm (axle 22.0 mm), rear 10.3 mm in the model (axle 21.7 mm from the hub carrier, wishbones horizontal; setup sheet 4: 15 mm) |
| CVD drive shafts | centre to centre front 42.3 mm, rear 41.1 mm |
| Camber links | gap front 30.3 mm, rear 30.1 mm (turnbuckle M3x37: thread engagement 3.4 and 3.45 mm per rod end) |
| Rear hub carrier | bearing tube 10 mm (lip 1.0 mm), flush with the tube on the hinge pin (x = 3.6 mm from the pin axis, radius assumed); pin bore Ø3.1 mm; grub screw M3x4 in a boss Ø6.0; axle 15.1 mm above the pin; height 30.4 mm; camber stud bore 13.7 mm from the outer face of the bearing tube; column 5.2 x 7.2 mm; camber stud thread through; edge treatment (chamfer 0.3, radius 0.5) |
| C-hub | right and left part (mirror images); pin bore Ø3.0 mm (H7 proposal); grub screw M3x4 in a boss Ø6.0; lower arm 11.0 mm wide; edge treatment (chamfer 0.3, radius 0.5) |
| Steering | posts 20.3 high, bellcranks at z = 16.8 to 22.3, symmetric bellcranks (arms 15 mm), bridge as a flat bar at z = 23.2 to 29.5: Ackermann 85 / 99 / 116 % at 15 / 20 / 25 degrees; steering link gap 21.0; servo approx. 19 degrees for 25 degrees of the inner wheel |
| Front splitter | one part, 187 x 94 mm, bosses on H34, H35, H36 up to z = 10.0 mm |
| Dual motor study (not part of the build) | motor axes x = ±31.90 mm, z = 19.20 mm; mount 99.0 x 6.0 x 33.0 mm |

## Status of the parts
* Verified (green): chassis plate, bulkheads, top brace, shock towers, front splitter, battery tray, servo mount (holes for the servo ears to be checked before printing), pivot blocks, motor mount with cap, steering knuckles, wishbones (the new optical design and the bores Ø3.2 are not printed yet).
* Orders (owner): chassis plate CNC part (aluminium 6082); bulkheads and front splitter MJF 3D print (nylon PA12); top brace and shock towers carbon plates (2D milling). The battery tray has no order entry.
* Measures qualified (yellow): centre driveshaft, rear and front drive line, differential, spool, steering posts, bellcranks, steering bridge, rear hub carriers.
* Purchased (owner): camber links (simplified model in the assembly).
* Completely unqualified (red): cup joints, diff outdrives, inner hinge pins, C-hubs (3D print verification with the guide sleeves planned by the owner), axles and hex hubs, CVD drive shafts, steering (links, horn), sway bars, dampers.

## Open points
* Track: see [next step](#next-step-track-front-and-rear).
* Wishbones: test print of the new shape. The tube on the inner hinge pin reaches 0.14 mm into the side faces of the lower bulkhead at End A over its whole length (4.47 mm³ per arm): check on the car; if it rubs, a tube Ø6.72 (0.1 clearance) or a narrower outer side face of the bulkhead. The 3 front holes are still spaced as in the old window (toward the outer cross bar); spreading them evenly over the plate was offered.
* Hinge pin bores of the C-hub (Ø3.0 H7, proposal) and of the rear hub carrier (Ø3.1): Ø3.2 as the wishbones for MJF prints was offered, not decided.
* Camber links (purchased): the turnbuckle M3x37 engages only 3.4 / 3.45 mm per rod end in the model; a longer turnbuckle (M3x40 or M3x42) is to be decided by the owner when buying. Rod ends 0.19 / 0.24 mm beside the narrowed wall of the upper bulkhead (static); clearances over the suspension travel are not checked (also the grub screw bosses and the plate of the wishbones).
* Colour scheme: the annotation colours (red dimensions, orange hole labels, red and green hole markers, red and black battery wires) can be changed to blues on request.
* Rear hub carrier: outer diameter of the bearing tube (14.6 from the photo) and radius of the tube on the hinge pin (3.6) not measured; the original part has 2 holes in the top tab, the model has one.
* Front splitter: as a 3D print the plate (3.0 mm) is less stiff than a carbon plate; measurement sheet open points (B1 to B3, B5, B6, M10, S3).
* ADR-009 and ADR-010 still refer to the foam bumper, which is no longer used; the GPS module needs a new position.
* Dual motor study: batteries on edge 48.8 mm high under the body (body not modelled); 2 ESCs with the same throttle signal; torque on the drive line doubles (not evaluated).
* C-hub: thickness of the foot of the guide sleeves (model 1.0, owner approx. 0.6) and their total length to be measured; 3D print verification with the guide sleeves.
* Steering knuckle: open dimensions K11, K14, K16 and K19 of the measurement sheet.
* Steering and servo: servo angle approx. 19 degrees for 25 degrees of the inner wheel; servo height and output shaft from the caliper values to be confirmed; clearance of the horn to the body not checked; fit of the bearings in the MJF bellcrank to be checked.
* Technical drawings: materials of the pivot blocks, the C-hub and the steering knuckle to be defined; fits and the bulkhead tolerances are proposals.
* Wheels are not modelled; the wishbones are horizontal (ride height front 10 mm, rear 10.3 mm in the model).
* Not changed to 130 km/h: the gearing plot `scripts/plots/gearing_plot.py`, `specs/mechanics/carten_t410r/spec_cartent410r.yaml` (track width 190 mm), the project name "RC100".
