## Drivetrain dashboard: Speed targets & thermal zones


## Table of contents
* [Drivetrain dashboard: Speed targets & thermal zones](#drivetrain-dashboard-speed-targets--thermal-zones)
  * [Reading guide for the dashboard:](#reading-guide-for-the-dashboard)
* [The "wheel load %" formula](#the-wheel-load--formula)
  * [The calculation](#the-calculation)
  * [The load zones (for 3650 motors / 4000kV on 3S)](#the-load-zones-for-3650-motors--4000kv-on-3s)


The following dashboard visualizes the physical limits of the **Carten T410R** in combination with the specified **3660 brushless motor (3700KV on 3S)**. 

It shows the direct correlation between the chosen pinion size, the resulting mechanical load (wheel load in %) and the achievable axle speed.

![Drivetrain dashboard with speed targets](https://github.com/kleinnconrad/prototyping.rc.speedrun/blob/main/photos/1772373437236.png)

### Reading guide for the dashboard:
* **The dashed lines (grayscale):** Mark the required axle speed for our milestones (100, 110, 120 and 130 km/h) with a tire diameter of 64 mm.
* **The red curve (axle speed):** Shows the theoretically applied speed of the wheels at full throttle per pinion. Where this curve intersects one of the dashed lines, the respective speed target is reached.
* **The blue curve (wheel load):** Shows the mechanical load of the motor. 
* **The colored zones (background):** Define the thermal tolerance limits of the 3660 motor.
  * 🟢 **safe zone (< 22 %):** Continuous load possible without problems.
  * 🟡 **sweet spot (22 % - 25 %):** optimal for speedruns, keep an eye on thermal limit.
  *  **Danger zone (> 25 %):** Acute risk of overheating, only for extreme short sprints.

**Conclusion of the visualization (68T spur gear):** The primary project goal of **100 km/h** is achieved from a **34T pinion**. The wheel load is at this point (20.2 %) in the green zone. Within the 25 % limit, the setup offers mechanical reserves up to approx. 121 km/h (41T pinion). The current setup with a **43T pinion** is at **25.6 %** wheel load and therefore in the danger zone. Test drives showed that the motor does not heat up significantly at this wheel load, even without dedicated motor cooling (ADR-007).


## The "wheel load %" formula

The **wheel load in percent** calculated in our scripts is an empirical indicator for the mechanical load on the motor. It is based on the reciprocal of the final drive ratio (FDR). 

The smaller the FDR (i.e. the "taller" the gear ratio), the less leverage the motor has. It must consequently apply more raw power to push the car against the exponentially increasing air resistance.

### The calculation
1. **Calculate final drive ratio (FDR):**
   FDR = (spur gear / motor pinion) * internal ratio
   *(On the Carten T410R, the internal ratio is 2.47)*

2. **Calculate wheel load factor:**
   Wheel load (%) = (1 / FDR) * 100

**Example:** With the 68T spur gear and the 43T pinion of the current setup, the FDR is `(68 / 43) * 2.47 = 3.91`.
The wheel load is thus `(1 / 3.91) * 100 = 25.6 %`.

### The load zones (for 3650 motors / 4000kV on 3S)
These zones have established themselves in practice as guide values for temperature and current monitoring:

* **< 19.0 % (green zone):** High leverage. optimal for twisty tracks, stop-and-go and long bashing. Electronics stay cool.
* **19.0 % - 22.0 % (yellow sweet spot):** Ideal balance for speedruns. The car reaches top speed, electronics get very warm, needs cooling down after 1-2 runs.
* **22.0 % - 25.0 % (red danger zone):** Extreme load. Exclusively suitable for short, linear acceleration races with active fan cooling.
* **> 25.0 % (heat death):** The leverage is no longer sufficient. The motor draws stalling currents, converts energy almost entirely into heat and risks the immediate destruction of ESC or rotor.
