# Laser tachometer test


## Table of contents
* [Validation & findings](#validation--findings)
* [Theoretical speed](#theoretical-speed)


**Component:** Digital laser tachometer (optical speed measurement)
**Date:** 2026-03-16
**Status:** Verified / ready for use

## Validation & findings

* **Measurement method:** The laser tachometer was tested in RPM mode (revolutions per minute) for validation.
* **Reference test run:** To verify the accuracy of the measurement, the test was performed on a known, already existing RC car. To capture the optical laser signal, a reflection strip was applied to the outer flank of the wheel.
* **Plausibility check:** The recorded RPM value and the resulting speed are plausible. The measuring device provides data and is thus approved for data acquisition on the Carten T410R speedrun project.

## Theoretical speed

v = (d * π * rpm * 60) / 1000²

**Test calculation with the recorded values:**
* Wheel diameter (d): 64 mm
* Measured RPM (rpm): 2340.2

v = (64 * 3.14159 * 2340.2 * 60) / 1,000,000
**v ≈ 28.23 km/h**

<img src="https://github.com/kleinnconrad/prototyping.rc.speedrun/blob/main/photos/PXL_20260316_115617586.MP.jpg" alt="laser tachometer test setup" width="50%">
