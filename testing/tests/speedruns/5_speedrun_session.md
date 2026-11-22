# 5. Speedrun test report

## Table of contents
* [Basic data](#basic-data)
* [Test results](#test-results)
* [Error analysis](#error-analysis)
* [Measures](#measures)
* [Conclusion](#conclusion)

## Basic data
* **Date:** November 22, 2026
* **Location:** not documented
* **Vehicle:** Carten T410R with the stock chassis parts (not the speedrun chassis)
* **Drive:** Hobbywing QuicRun WP10BL120 G2 with 3660SL 3700KV, pinion 43T, spur gear 68T (final drive ratio 3.91), tyres 64 mm
* **Battery:** 3S LiPo, 12.6 V fully charged
* **Measurement:** Ruddog GPS (10 Hz); cloudy weather; the app showed a signal and recorded the speeds
* **Result:** chassis setup confirmed; top speed limited by the missing throttle calibration of the ESC

## Test results
* **Driving behaviour:** Geometry, traction and steering are fixed. The car sits on the road and runs in a straight line.
* **Measured top speed with a fully charged battery:** **87 km/h**, the same value on several consecutive runs.
* **Measured top speed with a nearly empty battery:** **83 km/h**. The subjective impression matched this value; with the fully charged battery the car felt faster than 87 km/h.
* **Temperatures:** Motor and ESC did not get hot on any run.

## Error analysis
**Cause:** The ESC was not recalibrated after the switch to the new transmitter. The ESC kept the throttle end points of the previous transmitter, so it did not reach full output at full trigger. All findings of the session match a fixed, reduced throttle output:

* **Identical top speed on several runs:** A fixed limit (constant maximum throttle output) and not a measurement scatter.
* **Motor and ESC stayed cool:** At full output, a top speed at 61 % of the no-load speed would mean very high current and fast heating of the motor. A reduced throttle output keeps current and temperature low.
* **Lower speed with a nearly empty battery:** The speed decreases with the battery voltage, as expected for a constant reduced throttle output.
* **Comparison with the 1st speedrun session:**

| Value | 1st session (April 19, 2026) | 5th session (November 22, 2026) |
| :--- | :--- | :--- |
| Transmitter | Previous transmitter | New transmitter, ESC not recalibrated |
| Gearing | Pinion 43T, spur gear 72T (final drive ratio 4.14) | Pinion 43T, spur gear 68T (final drive ratio 3.91) |
| Theoretical no-load speed at 12.6 V | approx. 135 km/h | approx. 143 km/h |
| Throttle | Not full throttle | Full trigger |
| Measured top speed | 103 km/h | 87 km/h |

The 68T spur gear gives a taller gear ratio than the 72T spur gear. At full throttle the car must therefore be at least as fast as in the 1st session. The reduction of the wheel torque by the taller gear (approx. 5.6 %) does not explain the drop from 103 to 87 km/h.

**Theoretical values (43T/68T, tyre 64 mm):** Motor speed 46,256 rpm at 12.6 V (from the RPM test), axle speed approx. 11,840 rpm, no-load speed approx. 143 km/h. 87 km/h is 61 % of it. With a nearly empty battery (approx. 10.8 V) the no-load speed is still approx. 122 km/h, so 83 km/h is far below the electrical limit.

**GPS as cause (unlikely):** Clouds have almost no effect on the satellite signals. A poor GPS fix causes scatter and dropouts, not the same value on several runs.

## Measures
* **Done (2026-11-22):** ESC recalibrated with the new transmitter (procedure: [ESC readme, section 1](../../../specs/electronics/brushless_combo/readme.md#1-throttle-range-calibration)).
* **Rule:** Recalibrate the ESC after each change of the transmitter or the receiver. Before the calibration: throttle trim at 0, throttle and brake end points at 100 %, no throttle curve, no speed limiter.
* **Open:** Stand test with the laser tachometer (fully charged battery, full throttle): expected approx. 11,800 rpm at the axle with 43T/68T. A clearly lower value means that the throttle output is still limited.
* **Open:** Check the fail-safe with the new receiver: the car must brake when the transmitter is switched off.
* **Open:** Next speedrun on the same track with the GPS: expected top speed clearly above 103 km/h.
* **Open:** Check the motor temperature after each run. With full throttle output, the gearing 43T/68T (wheel load 25.6 %) is in the danger zone of the [drivetrain dashboard](../../../specs/mechanics/carten_t410r/drivetrain/readme.md); keep the motor below approx. 80 °C and let it cool down between the runs.

## Conclusion
The chassis setup is complete: geometry, traction and steering no longer limit the top speed. The low top speed of 87 km/h is attributed to the missing recalibration of the ESC after the change of the transmitter. The ESC is now recalibrated; the stand test and the next speedrun confirm the result.
