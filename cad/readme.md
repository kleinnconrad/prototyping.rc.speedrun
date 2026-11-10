# CAD and 3D print files

## Table of contents
* [Overview](#overview)
* [Chassis plate and top brace v2](#chassis-plate-and-top-brace-v2)
  * [Parts](#parts)
  * [Files](#files)
  * [Coordinate system](#coordinate-system)
  * [Measurement basis](#measurement-basis)
  * [Test print](#test-print)
  * [Open points](#open-points)
* [Speedrun chassis plate (wide)](#speedrun-chassis-plate-wide)
  * [Longer motor window for a 3660 motor](#longer-motor-window-for-a-3660-motor)
* [3D printed parts](#3d-printed-parts)
  * [1. Motor fan mount (`fan_mount.stl`)](#1-motor-fan-mount-fan_mountstl)
  * [2. LiPo battery dummy (`lipo_mock.stl`)](#2-lipo-battery-dummy-lipo_mockstl)
  * [3. RC car maintenance stand (`stojan_3dprint_25.stl`)](#3-rc-car-maintenance-stand-stojan_3dprint_25stl)
  * [4. Rear diffuser (`T410R_DIFFUSOR_V2_2.stl`)](#4-rear-diffuser-t410r_diffusor_v2_2stl)
* [Sources](#sources)

## Overview
This directory contains CAD data and 3D print files for the RC car **Carten T410R**:
* **`/chassis_v2`**: CAD data of the chassis plate and the top brace, version 2, in several formats (STEP, STL, DXF, OpenSCAD, PDF templates), STL files for a test print on a home 3D printer, a wide variant of the chassis plate for speedruns (STEP, STL) and a version of the wide variant with a longer motor window for a 3660 motor (STEP, STL, DXF)
* **STL files in this directory**: 3D printed parts for the car and a maintenance stand

Own files are released under the licenses of this repository (see the root readme). Third-party files are subject to the licenses of their authors (see [sources](#sources)). The preview images of the chassis plate and the top brace are stored in the `/photos` directory of the repository. The preview image of the wide chassis plate with the longer motor window is stored in the directory `/chassis_v2`.

## Chassis plate and top brace v2
* **Author:** [@kleinnconrad](https://github.com/kleinnconrad)
* **Description:** CAD models of the chassis plate and the top brace of the Carten T410R. The geometry is derived from photos of the original parts and scaled to caliper measurements (see [measurement basis](#measurement-basis)). Version 2 replaces version 1, which is not part of this repository.
* **Status:** Not yet verified. The test print is used to check the hole positions and the overall length (see [open points](#open-points)).

![Top view of the chassis plate and the top brace v2 with hole labels](../photos/cad_chassis_v2_drawing.png)

### Parts
| Part | Size (width × length × thickness) | Holes | Cutouts | Volume |
|:---|:---|:---|:---|---:|
| Chassis plate | 100.0 × 325.6 × 2.0 mm | 36 through holes Ø3.2 mm (H01 to H36), countersunk Ø6.2 mm × 90° on the bottom face | Window approx. 23.5 × 53.3 mm, slot approx. 22.3 × 6.7 mm | 49.4 cm³ |
| Top brace | 38.0 × 243.3 × 2.0 mm | 15 through holes Ø3.2 mm (B01 to B15), not countersunk | Hexagon, short slot approx. 3.2 × 17.5 mm, long slot approx. 3.2 × 88.2 mm, obround approx. 27.0 × 9.3 mm | 7.8 cm³ |

* The width of the main section of the chassis plate is 99.98 mm. The bar of the top brace is 15.09 mm wide.
* The hole diameter of 3.2 mm is the clearance hole for M3 screws.
* Sizes and volumes are taken from the STL files. The cutout sizes are approximate values from the geometry data.

### Files
All files are stored in the directory `/chassis_v2`. The STEP, STL, DXF, OpenSCAD and PDF files and the hole tables are generated from the geometry data (`*_geometry.json`).

| File | Format | Use |
|:---|:---|:---|
| `chassis_plate_T410R_v2.step`, `top_brace_T410R_v2.step` | STEP (AP214) | Solid models for CAD programs |
| `chassis_plate_T410R_v2.stl`, `top_brace_T410R_v2.stl` | STL (binary) | Complete parts as triangle meshes |
| `testprint_chassis_plate_v2_halfA.stl`, `testprint_chassis_plate_v2_halfB.stl` | STL (binary) | Chassis plate in two halves for the test print |
| `testprint_top_brace_v2_halfA.stl`, `testprint_top_brace_v2_halfB.stl` | STL (binary) | Top brace in two halves for the test print |
| `chassis_plate_T410R_v2.dxf`, `top_brace_T410R_v2.dxf` | DXF | 2D drawings for CNC manufacturing with the layers `OUTLINE`, `CUTOUT`, `HOLE_THROUGH` and `CSK_BOTTOM_INFO` (countersinks, chassis plate only) |
| `chassis_plate_T410R_v2.scad`, `top_brace_T410R_v2.scad` | OpenSCAD | Parametric models. The parameters `thickness`, `hole_d`, `csk_d` and `csk_angle` are defined at the top of the file. |
| `chassis_plate_T410R_v2_1to1_A3.pdf` | PDF (A3, 1 page) | 1:1 template of the chassis plate |
| `chassis_plate_T410R_v2_1to1_A4x2.pdf` | PDF (A4, 2 pages) | 1:1 template of the chassis plate on two A4 sheets |
| `top_brace_T410R_v2_1to1_A4.pdf` | PDF (A4, 1 page) | 1:1 template of the top brace |
| `chassis_plate_v2_hole_table.csv`, `top_brace_v2_hole_table.csv` | CSV | Hole coordinates (x, y), through hole diameter and countersink diameter |
| `chassis_plate_v2_geometry.json`, `top_brace_v2_geometry.json` | JSON | Geometry data: outline, cutouts, holes, thickness and countersink parameters |

The PDF templates must be printed at 100 % scale. The 100 mm bar on the template is used to check the scale.

### Coordinate system
* Units are millimeters. All coordinates refer to the top view.
* x = 0 is the center line of the part.
* y = 0 is the end edge: on the chassis plate the end with the 2 × 2 hole pattern (holes H01 to H04), on the top brace the end with the hexagon cutout. The OpenSCAD files refer to this edge as the rear end edge.
* z = 0 is the bottom face. The countersinks of the chassis plate are located on the bottom face.

### Measurement basis
The outlines were taken from photos of the original parts and scaled to caliper measurements:
* **Chassis plate:** x scaled by 1.00522 (width of the main section 99.98 mm), y scaled by 1.00609 (distance between the holes H11 and H23 145.82 mm)
* **Top brace:** uniformly scaled by 1.006 (bar width 15.09 mm)
* **Holes:** through holes Ø3.2 mm (measured on the original part: 3.18 mm)
* **Shape:** The window and the slot of the chassis plate are part of the model. Two marks on the surface of the original parts are not holes and are therefore not modelled.

### Test print
The test print checks the hole positions and the overall length with a home 3D printer before the parts are manufactured. Both parts are split into two halves that are connected with dovetails.

![Test print halves of the chassis plate and the top brace](../photos/cad_chassis_v2_test_print.png)

| File | Size (width × length × thickness) | Split |
|:---|:---|:---|
| `testprint_chassis_plate_v2_halfA.stl` | 100.0 × 168.7 × 2.0 mm | Split at half length (y = 162.8 mm), three dovetails, 0.2 mm joint gap |
| `testprint_chassis_plate_v2_halfB.stl` | 100.0 × 162.7 × 2.0 mm | See half A |
| `testprint_top_brace_v2_halfA.stl` | 34.9 × 97.4 × 2.0 mm | Split at y = 92.5 mm between the short and the long slot, so that the long slot is not cut. One dovetail, 0.2 mm joint gap. |
| `testprint_top_brace_v2_halfB.stl` | 38.0 × 150.7 × 2.0 mm | See half A |

* The halves of the chassis plate are oriented with the top side on the print bed, so that the countersinks face upwards.
* The largest half requires a print area of 100.0 × 168.7 mm.

Recommended procedure:
* Print with 100 % infill.
* Disable the XY hole compensation of the slicer for a true check of the hole positions.
* Printed holes with Ø3.2 mm are usually undersized. Ream them with a 3.2 mm drill before screws are inserted.
* Glue the halves together on a flat surface, preferably on the 1:1 template.
* Check the fit on the car: if the holes at both ends of the parts align with the mounting points, the overall length is correct.

### Open points
1. **Overall length:** With the caliper scaling, the chassis plate is 325.6 mm and the top brace 243.3 mm long. Measurements with a ruler resulted in 324 mm and 242 mm. If these values were taken with the plastic ruler visible in the photos, the ruler deviates by approx. 0.5 %, which would also explain the deviation of the photo scale. Check of the ruler: set the caliper to 150.00 mm and read the value on the ruler. The test print clarifies the length.
2. **Thickness of the chassis plate:** The model uses 2.0 mm. The chassis specification lists 2.25 mm for the bottom plate (`specs/mechanics/carten_t410r/spec_cartent410r.yaml`). The thickness has to be measured before manufacturing. It can be changed with the parameter `thickness` in the OpenSCAD file.

## Speedrun chassis plate (wide)
* **Author:** [@kleinnconrad](https://github.com/kleinnconrad)
* **Description:** Variant of the chassis plate v2 for speedruns with a widened middle section. The hole pattern, the countersinks, the window, the slot and both narrow ends are identical to the chassis plate v2.
* **Files:** `chassis_plate_T410R_speedrun_wide.step` (STEP AP214, one solid) and `chassis_plate_T410R_speedrun_wide.stl` (binary STL) in the directory `/chassis_v2`. This variant has no DXF, OpenSCAD, PDF or test print files and is not generated from the geometry data of version 2.

| Property | Chassis plate v2 | Speedrun chassis plate (wide) |
|:---|:---|:---|
| Size (width × length × thickness) | 99.98 × 325.6 × 2.0 mm | 199.98 × 325.6 × 2.0 mm |
| Holes | 36 through holes Ø3.2 mm, countersunk Ø6.2 mm × 90° on the bottom face | Identical |
| Cutouts | Window and slot | Identical |
| Volume | 49.4 cm³ | 80.7 cm³ |

The outline differs from the chassis plate v2 only between y = 55.3 mm and y = 246.5 mm (coordinate system as for the chassis plate v2, see [coordinate system](#coordinate-system)):

| Section | Position (y) | Width |
|:---|:---|:---|
| End with the 2 × 2 hole pattern | 0 to 55.3 mm | Identical to the chassis plate v2 |
| Transition, 30.3° to the cross direction | 55.3 to 85.5 mm | Increases from 100 to 200 mm |
| Wide section | 85.5 to 205.0 mm | 199.98 mm |
| Transition, 38.4° to the cross direction | 205.0 to 246.5 mm | Decreases from 200 to 100 mm |
| Opposite end | 246.5 to 325.6 mm | Identical to the chassis plate v2 |

* The values are taken from the STL file.
* The wide section is 10 mm wider than the width over the tires (190 mm, `spec_cartent410r.yaml`) and the body width (190 mm, `spec_body.yaml`). It protrudes by 5 mm per side. The clearance to the wheels and to the body has to be checked before manufacturing.
* The thickness of 2.0 mm is subject to the same open point as the chassis plate v2 (see [open points](#open-points)).

### Longer motor window for a 3660 motor
* **Author:** [@kleinnconrad](https://github.com/kleinnconrad)
* **Description:** Version of the speedrun chassis plate (wide) with a motor window that is 10 mm longer. The window is lengthened to fit a 3660 motor. The motor of the car (Hobbywing 3660SL G2) has a diameter of 36 mm and a length of 60 mm (`specs/electronics/brushless_combo/spec_brushless_combo.yaml`) and is 10 mm longer than a 3650 motor.
* **Status:** Not yet verified. The fit of the motor has to be checked before manufacturing.

![Top view of the wide chassis plate with the longer motor window and hole labels](chassis_v2/preview_speedrun_wide_motor10.png)

| Property | Speedrun chassis plate (wide) | Longer motor window |
|:---|:---|:---|
| Motor window (width × length) | 23.47 × 53.27 mm | 23.47 × 63.27 mm |
| Position of the window (x) | 16.59 to 40.06 mm | Identical |
| Position of the window (y) | 65.63 to 118.90 mm | 65.63 to 128.90 mm |
| Corner radius of the window | 3.0 mm | Identical |
| Volume | 80.7 cm³ | 80.2 cm³ |

* The window is extended only toward the end with the holes H34 to H36 (+y). The end edge at y = 65.63 mm is not moved.
* The outline, the slot, the 36 holes with the countersinks and the thickness are identical to the speedrun chassis plate (wide).
* The extension reduces the distance between the window and the countersink of hole H16 (Ø6.2 mm, bottom face) from 30.0 mm to 23.3 mm. The distances to the countersinks of the holes H07, H09, H10 and H13, which are closer to the window than H16, do not change.

| File | Format | Use |
|:---|:---|:---|
| `chassis_plate_T410R_speedrun_wide_motor10.step` | STEP (AP214) | Solid model for CAD programs (one solid) |
| `chassis_plate_T410R_speedrun_wide_motor10.stl` | STL (binary) | Complete part as triangle mesh |
| `chassis_plate_T410R_speedrun_wide_motor10.dxf` | DXF | 2D drawing for CNC manufacturing with the same layers as `chassis_plate_T410R_v2.dxf` |
| `chassis_plate_speedrun_wide_motor10_geometry.json` | JSON | Geometry data: outline, cutouts, holes, thickness and countersink parameters |
| `preview_speedrun_wide_motor10.png` | PNG | Top view with hole labels, the previous window (red, dashed) and the longer window |

* All files are stored in the directory `/chassis_v2`. The STEP, STL and DXF files are generated from the geometry data.
* The geometry data combines the outline of `chassis_plate_T410R_speedrun_wide.step` with the holes, cutouts and countersink parameters of `chassis_plate_v2_geometry.json`. Without the longer window, it reproduces `chassis_plate_T410R_speedrun_wide.step` exactly.

## 3D printed parts

### 1. Motor fan mount (`fan_mount.stl`)
* **Author:** [@kleinnconrad](https://github.com/kleinnconrad) (own design)
* **Description:** A 50 mm fan mount (60 x 50 x 18 mm, 40 mm air opening) for the **40 mm motor fan from hobbywing**. Designed for mounting in the Carten T410R for installation and cooling of the motor.
* **Status:** Not in use. The motor cooling was removed, since the motor does not heat up significantly during speedruns (ADR-007).

### 2. LiPo battery dummy (`lipo_mock.stl`)
* **Author:** [@kleinnconrad](https://github.com/kleinnconrad) (own design)
* **Description:** A placeholder object in the size of a **3S hardcase LiPo battery**. This model is used for planning installations, electronics and cable management in the Carten T410R. It replaces the physical battery during the design phase.

### 3. RC car maintenance stand (`stojan_3dprint_25.stl`)
* **Author:** [@Upgrade25](https://www.printables.com/@Upgrade25)
* **Description:** A maintenance stand for RC cars (scale 1:10). Intended for repairs, setup work or as a rest.

### 4. Rear diffuser (`T410R_DIFFUSOR_V2_2.stl`)
* **Author:** [3DMaxi](https://cults3d.com/en/users/3DMaxi/3d-models)
* **Description:** A rear diffuser for the Carten T410R (120 x 70 x 18 mm).
* **Status:** Printed and mounted on the car.
* **License:** Private use only (see [sources](#sources)).

---

## Sources

The RC maintenance stand (`stojan_3dprint_25.stl`) is not mine. The original files and all credits go to the original designer on printables:

* **Original model:** [RC car maintenance stand 1:10 on printables](https://www.printables.com/model/1200600-rc-car-maintenance-stand-110/files)
* **Designer profile:** [Upgrade25](https://www.printables.com/@Upgrade25)

The rear diffuser (`T410R_DIFFUSOR_V2_2.stl`) is not mine. The original file and all credits go to the original designer on Cults3D:

* **Designer profile:** [3DMaxi on Cults3D](https://cults3d.com/en/users/3DMaxi/3d-models)
* **License:** The license of the author covers private use only. The licenses of this repository (MIT, CC BY 4.0) do not apply to this file.
