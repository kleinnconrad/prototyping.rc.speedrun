# Architecture Decision Records (ADRs)

This directory contains all fundamental architecture and hardware decisions for the RC100 project. **This file is generated automatically. Please do not edit manually.**

## Overview

| ID | Date | Title | Status | Decision |
| :--- | :--- | :--- | :--- | :--- |
| **ADR-001** | 2026-03-06 | Selection of the chassis platform and make-or-buy decision (100 km/h Benchmark) | 🟢 decided | MAKE - Carten T410R |
| **ADR-002** | 2026-03-06 | Selection of the brushless motor combo for 100 km/h speedruns | 🟢 decided | Hobbywing QuicRun WP10BL120 G2 Combo (3660SL 3700KV) |
| **ADR-003** | 2026-03-06 | Selection of the LiPo Battery for the 100 km/h Goal. | 🟢 decided | Absima GreenHorn Line V2 (3S / 5000mAh / 50C / Hardcase) |
| **ADR-004** | 2026-03-06 | Selection of the charger for 3S LiPo batteries | 🟢 decided | SkyRC S100neo |
| **ADR-005** | 2026-08-20 | Selection of the remote control system for 100 km/h speedruns | 🟢 decided | Konect X9S Radio + Mini Waterproof 4-Channel Receiver RG4CHWP |
| **ADR-006** | 2026-08-21 | Selection of the steering servo for precise high-speed control | 🟢 decided | Savöx SC-1252MG+ |
| **ADR-007** | 2026-10-27 | Selection of motor cooling for 3S speedruns | 🟢 decided | No dedicated motor cooling (stock setup) |
| **ADR-008** | 2026-10-05 | Selection of tires for 100 km/h speedruns | 🟢 decided | Team Corally C-14705-35 Attack Moosgummi Reifen - 1/10 GP Toerenwagen - 35 shore |
| **ADR-009** | 2026-03-12 | Selection of the aerodynamic body for 100 km/h speedruns | 🟢 decided | ZooRacing Hellcat (190 mm, 0.7mm thickness) |
| **ADR-010** | 2026-03-10 | Selection of the GPS measuring system to validate the 100 km/h mark | 🟢 decided | Ruddog GPS Performance Analyzer |
| **ADR-011** | 2026-08-30 | Selection of Gyro for vehicle stabilization | 🟢 decided | SkyRC GC301 Gyro |

---

## Detailed Logs

### ADR-001: Selection of the chassis platform and make-or-buy decision (100 km/h Benchmark)
**Status:** decided | **Date:** 2026-03-06

#### Context
For the 100 km/h speedrun project, a mechanically stable basis is required. 
The platform must withstand 
extreme loads (approx. 41,000 rpm at the motor, massive 
centrifugal forces on the axles). 
The fundamental architecture question (Make or Buy) compares the construction of an own budget kit ("Make") 

with the purchase of an expensive, pre-assembled high-end competition chassis ("Buy"
). 
A critical risk for 3S use are differential gears made of plastic/composite, 
which often cannot withstand the torque.


#### Decision
> **MAKE - Carten T410R**

#### Rationale
The decision is made in favor of the "Make" option with the Carten T410R 
(~ 180 €). 
It is the only kit in the benchmark field of this price class that 
combines the essential requirements 
for a 3S/100 km/h run out of the box: 
1. A stiff 2.25mm carbon bottom plate (prevents dangerous fluttering). 
2. A robust shaft drive (eliminates the risk of skipping belts). 
3. Differential gears made of sintered metal (solves the knockout criterion of shearing 
plastic diffs). 
The massive price advantage over the Xray X4 '24 fully justifies 
the increased manual setup effort.


#### Consequences
- The metal differentials of the T410R must be shimmed precisely to guarantee zero play.
- The central aluminum driveshaft must be checked for concentricity before installation, as strong vibrations can occur with shaft setups.


---

### ADR-002: Selection of the brushless motor combo for 100 km/h speedruns
**Status:** decided | **Date:** 2026-03-06

#### Context
In order to accelerate a 1/10 touring car (Carten T410R) to 100 km/h, 
the gearing must be very 'tall' (high wheel load > 22 %). A 
classic 3650 motor (50 mm length) operates 
here at its thermal 
load limit. A drivetrain is absolutely required 
that delivers enough mechanical torque (motor size 3660) at 3S voltage 
(11.1V) and 
whose electronic speed controller (ESC) can safely handle the high stall currents during acceleration 
(min. 120A).


#### Decision
> **Hobbywing QuicRun WP10BL120 G2 Combo (3660SL 3700KV)**

#### Rationale
The decision is made in favor of the Hobbywing QuicRun G2 Combo. It eliminates 
the risk of failure of 
no-name motors and offers an optimally coordinated architecture (firmware of ESC 
and motor timing are optimally interlocked). 
The 3660 motor delivers the perfect 
rpm with its 3700KV on 3S 
(approx. 41,000 rpm) and has enough torque due to the longer rotor 
to confidently handle 
the calculated wheel load of approx. 25.6 % (43T pinion / 68T spur gear). 
The combo is the safest and most efficient solution on a budget under 100 €. 
Note: 25.6 % is slightly above the 25 % guide value of the load model; 
thermal problems have not occurred in the tests so far.


#### Consequences
- Packaging (Installation space): The 3660 motor is 10 mm longer than the standard size. The ESC and the receiver must be placed correspondingly further back in the T410R chassis.
- Pinion bore (IMPORTANT): Hobbywing usually delivers the 3660SL G2 with a 5.0 mm shaft (verify specifications with the dealer finally before ordering the pinion). A 48dp pinion with a 5 mm bore (e.g. Robinson Racing) is absolutely required.
- Power supply: The system voltage is strictly limited to 3S LiPo. A 4S operation would exceed the maximum permissible rotor speed of the motor.


---

### ADR-003: Selection of the LiPo Battery for the 100 km/h Goal.
**Status:** decided | **Date:** 2026-03-06

#### Context
In order to accelerate the RC100 project to over 100 km/h, the power source must be optimally 
matched to the 3700kV motor and the 120A ESC (Hobbywing QuicRun). 
A 2S LiPo (7.4V) would only deliver approx. 27,400 rpm, which is not sufficient for 100 km/h 
with a normal gear ratio. Therefore, a 3S LiPo (11.1V) is absolutely necessary to 
reach the calculated ~41,000 rpm. In addition, the battery must be able to briefly 
deliver extreme currents without dropping in voltage (voltage sag), and must be physically 
protected in the event of a crash at high speed.


#### Decision
> **Absima GreenHorn Line V2 (3S / 5000mAh / 50C / Hardcase)**

#### Rationale
The decision is made in favor of the Absima GreenHorn V2 3S LiPo. With a 50C 
discharge rate, it offers 
enough buffer for the massive current peaks when accelerating 
the 43T/68T gearing (pinion/spur gear). 
The hardcase is a safety requirement for speedruns, as an impact at 100 km/h 
would immediately destroy and ignite a softcase LiPo. The pre-assembled XT60 connector 
guarantees a 
low contact resistance for the high currents.


#### Consequences
- Chassis modification: Since 3S hardcase batteries are approx. 35mm high, the upper carbon battery brace in the Carten T410R must be raised with 10mm spacers and longer M3 screws.
- Connector compatibility: The Hobbywing controller must absolutely be soldered with a matching XT60 connector (no Tamiya connectors at these currents!).
- Safety: Charging and storing the battery (55.5 Wh) may only be done under supervision in a Bat-Safe or a fireproof LiPo bag.


---

### ADR-004: Selection of the charger for 3S LiPo batteries
**Status:** decided | **Date:** 2026-03-06

#### Context
Charging the 3S LiPo battery defined in ADR-003 (11.1V, 5000mAh, 55.5 
Wh) requires a 
safe and powerful charger. To gently charge the battery 
with 1C (5 Amps), 
a charging power of at least 63 Watts 
(5 Amps * 12.6V end-of-charge voltage) is required. 
In addition, the charger must 
exactly monitor the cell voltages (balancing) and be able to measure the internal 
resistance of the cells to prevent fire hazards. The connector must 
be able to safely transmit the 
high currents via an XT60 plug.


#### Decision
> **SkyRC S100neo**

#### Rationale
The decision is made in favor of the SkyRC S100neo. It optimally covers the "sweet spot" 
between safety, 
performance and budget. The 100 Watts of internal power (AC) are more than sufficient 
to gently fully charge the 3S 5000mAh LiPo in about an 
hour. Particularly advantageous is 
the XT60 connector firmly integrated into the front panel, which makes dangerous and error-prone 
adapter cables 
superfluous. This fits perfectly with the architecture decision of the Absima battery.


#### Consequences
- Safety during charging: In addition to the XT60 main connector, the white JST-XH balancer cable of the battery must strictly be plugged into the port of the charger, otherwise the individual cells will not be monitored.
- Cable minimalism: No additional charging cables are required (battery is plugged directly into the device).
- Cooling: The charger has an active fan. During charging, ensure a safe stand and free air supply.


---

### ADR-005: Selection of the remote control system for 100 km/h speedruns
**Status:** decided | **Date:** 2026-08-20

#### Context
An RC car traveling at 100 km/h (approx. 27.7 meters per second) covers 
enormous distances in a few seconds. 
The remote control (transmitter) 
and the receiver 
must therefore absolutely have a stable radio connection 
and an absolutely reliable fail-safe 
so that the vehicle does not get out of control at the end 
of the acceleration stretch. 
A balance must be struck 
between maximum range incl. gyro support and a 
robust, 
failsafe MVP approach (Minimum Viable Product) that reduces the complexity in 
the setup.


#### Decision
> **Konect X9S Radio + Mini Waterproof 4-Channel Receiver RG4CHWP**

#### Rationale
The tests with the Carson Reflex Wheel X1 showed insufficient steering precision, as the servo did not reproducibly return to the neutral position depending on the steering angle. To increase steering precision, the Konect X9S remote control was purchased in combination with the RG4CHWP receiver for 152 €.


#### Consequences
- Receiver installation: The RG4CHWP receiver is installed and the fail-safe must absolutely be programmed to brake/neutral.
- Interface compatibility: The operating voltage of the receiver must be matched with the BEC output voltage of the motor controller.
- Steering angle limitation: The steering deflections (Dual Rate) are adapted to the requirements of high-speed driving.


---

### ADR-006: Selection of the steering servo for precise high-speed control
**Status:** decided | **Date:** 2026-08-21

#### Context
At speeds of 100 km/h, enormous aerodynamic and mechanical forces act on the front wheels of the Carten T410R. A minimal jitter, play or a too slow reaction time of the steering servo can immediately lead to loss of control and total failure. In addition, space in a 1:10 touring car chassis is limited. The servo must hold the straight line precisely, return reproducibly to the neutral position and execute the counter-steering commands of the steering gyro (ADR-011) without delay. A low-profile servo with metal gears (robustness), high speed and a precise neutral return is required.


#### Decision
> **Savöx SC-1252MG+**

#### Rationale
Test drives with the MVP servo (JX PDI-4409MG) showed that the required steering precision was not reached, as the servo did not reproducibly return to the neutral position. The change to the Savöx SC-1252MG+ (52.72 €) was necessary to reach an appropriate steering precision. It offers a speed of 0.07s, a torque of 7 kg and a precise return to the neutral position. In addition, the mechanical resistance in the steering caused by overtightened C-hub mounting screws was eliminated (error log no. 14). Since test drive 13, corrective steering maneuvers can be executed effectively.


#### Consequences
- Servo horn: To minimize play in the steering system, a rigid aluminum lever (ALU CLAMP SERVO HORN - FUTABA, SAVÖX - 3-HOLE - 25T, item HUD293409) is mounted without a servo saver.
- BEC voltage: The BEC output voltage of the controller is configured to 6.0V.
- Dual-Rate: The maximum steering angle is limited on the remote control to ensure stability at 100 km/h.


---

### ADR-007: Selection of motor cooling for 3S speedruns
**Status:** decided | **Date:** 2026-10-27

#### Context
The targeted goal of 100 km/h requires the use of a 3700kV motor (Hobbywing QuicRun 3660SL G2) on a 3S LiPo (11.1V), which leads to motor speeds of approx. 41,000 rpm and a tall final drive ratio (43T pinion / 68T spur gear, FDR 3.91, wheel load 25.6 %). Under these conditions, a high thermal load of the motor was expected. Excessive motor temperatures can demagnetize the rotor or damage the winding insulation. The cooling concept must therefore match the thermal load observed in test drives.


#### Decision
> **No dedicated motor cooling (stock setup)**

#### Rationale
Test drives showed that the motor does not heat up significantly during speedruns. The motor drives the final drive ratio of 3.91 (43T pinion / 68T spur gear) without problems. The active and passive cooling (Hobbywing fan with cooling fins, HW86080120) that was selected initially as a precaution proved to be obsolete and was removed. Thus, the decision was revised to operate the motor without dedicated cooling. A fan that is mounted on the motor for visual reasons is not part of the cooling concept.


#### Consequences
- Receiver slot: The motor cooling does not require a receiver slot.
- Weight and wiring: Without a fan, the vehicle weight and the number of cables that must be secured in the chassis are reduced.
- Decorative fan: A fan is mounted on the motor for visual reasons only. It is not required for cooling and can be removed without consequences for the motor temperature.
- Re-evaluation: The decision applies to the current final drive ratio (3.91) on 3S. A taller gear ratio, a higher battery voltage or a different motor requires a re-evaluation of the motor cooling.


---

### ADR-008: Selection of tires for 100 km/h speedruns
**Status:** decided | **Date:** 2026-10-05

#### Context
At a target speed of 100 km/h and the associated high 
speeds 
of the wheels, standard rubber tires expand massively in the middle due to centrifugal force 
(the so-called "pizza cutter effect" or "ballooning"
). This leads to an immediate 
loss of control and often to the tire bursting. 
Pre-glued tires 
on rims with a 12mm hex hub 
(suitable for the Carten T410R chassis) are required, 
which retain their shape 100% under high centrifugal forces 
and whose rubber compound 
withstands the high friction heat on rough 
asphalt. 
In addition, the real track conditions (not 
dust-free normal asphalt vs. 
cleanly prepared race track) must be considered when choosing 
the tire tread (slick vs. grooved). 



#### Decision
> **Team Corally C-14705-35 Attack Moosgummi Reifen - 1/10 GP Toerenwagen - 35 shore**

#### Rationale
While belted tires avoid ballooning, they do not provide sufficient stability and grip for speedruns. Changing to foam rubber tires significantly improves both stability and grip at high speeds. Thus, the decision was revised to use the Team Corally 35 shore foam tires.

#### Consequences
- Pre-check: Even factory pre-glued tires must absolutely be checked for manufacturing defects on the glue seam before the first run (pull briefly on the tire sidewall).
- Balancing: Since the smallest imbalances destabilize the chassis at 100 km/h, the wheels should ideally be balanced with an RC tire balancer and putty lead.
- Temperature window: In order to build up maximum mechanical grip, the 35 shore foam tires must be warmed up by 1-2 slow laps before the actual speedrun.


---

### ADR-009: Selection of the aerodynamic body for 100 km/h speedruns
**Status:** decided | **Date:** 2026-03-12

#### Context
At a target speed of 100 km/h (approx. 27.7 m/s), the body is 
no longer a purely visual component, but the primary aerodynamic protective layer. 
A classic, boxy body 
traps air under the front apron, 
which inevitably leads to a 'blow-over' (lifting off due to 
dynamic pressure). At the same time, 
the air resistance (drag coefficient) must not unnecessarily slow down the motor. 
The Carten T410R chassis requires a width of 190 mm. The material thickness is 
critical: 
Thin lexan (< 0.5 mm) deforms massively at 100 km/h.


#### Decision
> **ZooRacing Hellcat (190 mm, 0.7mm thickness)**

#### Rationale
The decision is made in favor of the ZooRacing Hellcat in the 0.7mm standard thickness. 
It represents the 
optimal compromise between minimum air resistance (for 
reaching 100 km/h) and safe 
downforce (prevention of blow-overs). Unlike very flat LMP bodies, 
it fits easily over 
the shock towers of the Carten T410R. The material thickness of 0.7mm 
guarantees 
that the body withstands the massive dynamic pressure at top speed and does not 
start to vibrate or rub against the tires.


#### Consequences
- Assembly: The included rear wing must be screwed on very rigidly. The body holes must be precisely machined with lexan scissors and a body reamer.
- Chassis preparation: The foam bumper on the front of the Carten T410R must sit exactly flush with the inside of the front apron to prevent it from being pushed in at high speed.


---

### ADR-010: Selection of the GPS measuring system to validate the 100 km/h mark
**Status:** decided | **Date:** 2026-03-10

#### Context
The calculated mathematical models (axle speed, rolling resistance, 
voltage drop) 
must be validated in reality ('integration test' on the street) 
by hard telemetry data. 
Since the vehicle often only holds the top speed of 100 km/h for a time window 
of 2 to 3 seconds, a very high sampling rate (update frequency) of the 
measuring device is absolutely required. 
At the same time, the module must not 
negatively affect the vehicle weight (CG) 
and the aerodynamics.


#### Decision
> **Ruddog GPS Performance Analyzer**

#### Rationale
The decision is made in favor of the Ruddog GPS Performance Analyzer. It is 
the perfect 'fit-for-purpose' 
tool for this project. The 10Hz sampling rate 
guarantees that the exact top speed 
is recorded, even if 
it is only applied for a fraction of a second. The low weight 
of 38g does not change the driving behavior of the Carten T410R, and the Bluetooth app interface 
saves a heavy, readable display directly on the vehicle.


#### Consequences
- Signal constraint: The GPS signal easily passes through lexan bodies, but is massively blocked by carbon fibers. The module must not be mounted directly *under* the carbon upper deck in the Carten T410R. The optimal position is on the foam bumper in the front.
- Mounting: The device must be fixed very securely (e.g. with strong velcro or 3M Dual Lock) so that it does not fly away as a projectile in the event of a rollover at 100 km/h.


---

### ADR-011: Selection of Gyro for vehicle stabilization
**Status:** decided | **Date:** 2026-08-30

#### Context
At high speeds of up to 100 km/h, the RC vehicle requires electronic stabilization to maintain a straight trajectory and prevent spin-outs. A gyro sensor detects unwanted rotational movements and automatically applies counter-steering via the steering servo. The selection of a gyro must balance reliability and cost. High-end gyros offer advanced features but exceed the current project budget.

#### Decision
> **SkyRC GC301 Gyro**

#### Rationale
The decision is made in favor of the SkyRC GC301 Gyro. The primary factor is cost. The Futaba and Power HD alternatives exceed the project budget. The SkyRC GC301 provides a cost-effective method to implement electronic stabilization for initial testing. If the performance of the GC301 proves insufficient during high-speed tests, a budget increase for a higher-tier gyro can be considered in a future iteration.

#### Consequences
- Installation: The gyro must be mounted aligned with the longitudinal axis of the chassis to function correctly.
- Calibration: The gyro gain must be adjusted. High gain causes steering oscillation, low gain provides insufficient stabilization.
- Testing: Initial low-speed tests are required to verify the correct direction of the counter-steering before attempting high-speed runs.


---
