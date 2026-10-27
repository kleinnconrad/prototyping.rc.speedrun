# 1:10 onroad RC car for speeds over 100 km/h

This project covers the system architecture and configuration of an 1:10 scale on-road touring car with the design goal of a consistently repeatable top speed of over 100 km/h without risking the car to be damaged or destroyed. The focus is on maximizing drive power while ensuring reliability and cost efficiency.

The technical challenge primarily results from the chosen scale and the limited tire diameter of 64 millimeters. While vehicles from 1:8+ scale have strong physical advantages due to higher mass inertia, larger rolling circumferences, and a longer wheelbase, the 1:10 scale requires significantly higher rotor speeds. This leads to high mechanical stresses in the drivetrain. The low vehicle weight also requires precise aerodynamic and suspension tuning to ensure driving stability at high speeds.

The artefacts of this repository are:
* Architecture decision records (ADRs) in the `/architecture` directory
* System specification in the `specs/full_spec.yaml` file
* Vehicle setup configurations in the `/setup_sheets` directory

<table>
  <tbody>
    <tr>
      <td colspan="2"><img src="photos/rc_car.jpg" alt="RC car with clear body" width="100%"></td>
    </tr>
  </tbody>
  <tbody>
    <tr>
      <td><img src="photos/rc_car_chassis_front.jpg" alt="RC car chassis without body, front view" width="100%"></td>
      <td><img src="photos/rc_car_chassis_rear.jpg" alt="RC car chassis without body, rear view" width="100%"></td>
    </tr>
  </tbody>
</table>

## Table of contents
* [Repository structure](#repository-structure)
* [Artefacts (ADR, specs, setup sheets)](#artefacts-adr-specs-setup-sheets)
* [Calculation models for drivetrain design](#calculation-models-for-drivetrain-design)
* [Learnings & modifications](#learnings--modifications)
* [Repository automation](#repository-automation)
* [Follow-up project: Telemetry system](#follow-up-project-telemetry-system)
* [Licensing](#licensing)

## Repository structure
* **`/architecture`**: Documentation of basic system designs
* **`/docs`**: Static web dashboard for visualizing the latest setup configurations
* **`/photos`**: Central directory for all image files
* **`/project`**: General project information
  * **`/costs`**: Cost tracking
  * **`/follow_up_projects`**: Documentation of related follow-up projects
* **`/scripts`**: Automation scripts
  * **`/calc`**: Calculation scripts
  * **`/plots`**: Plot scripts
* **`/setup_sheets`**: Vehicle setup configurations
* **`/specs`**: Specifications of the vehicle components
  * **`/electronics`**: Selection and specification of electronic components such as motors, electronic speed controllers, and batteries
  * **`/mechanics`**: Chassis design, construction data, and specification of physical components
* **`/testing`**: Test results and performance measurement data
  * **`/error_list`**: Error logs and their resolutions
  * **`/tests`**: Logs and data of test drives

## Artefacts (ADR, specs, setup sheets)
The documentation of architecture decisions (ADRs), the specifications of all mechanical and electronic components, and the vehicle setup configurations are consistently maintained as structured YAML files (`.yml` or `.yaml`). The formal hierarchical structure of these artefacts is standardized as follows:

```mermaid
classDiagram
    class adr {
        +id: String
        +title: String
        +status: String
        +date: Date
        +context: Text
        +decision: String
        +rationale: Text
        +consequences: List
    }
    class adr_alternative {
        +option_id: Integer
        +name: String
        +type: String
        +evaluation: Text
    }
    adr *-- adr_alternative : considered_alternatives
    
    class spec {
        +properties: Object
        +integration_notes: Object
    }
    class spec_meta {
        +brand: String
        +model: String
        +type: String
    }
    spec *-- spec_meta : meta

    class setup {
    }
    class setup_meta {
        +date: Date
        +description: String
        +version: String
        +top_speed_kmh: Float
    }
    class setup_properties {
        +suspension_and_geometry: Object
        +drivetrain: Object
        +electronics_and_control: Object
    }
    setup *-- setup_meta : meta
    setup *-- setup_properties : properties
```

## Calculation models for drivetrain design
To avoid thermal or mechanical overload of the electronic components, custom-developed calculation models are used:
* **Gearing calculator (`scripts/calc/gearing_calc.py`)**: Simulates the mechanical wheel load for the motor based on tire diameter and target speed, depending on available motor pinions. Setups are categorized into load zones for the defined drive system.
* **Limit calculator (`scripts/calc/max_speed.py`)**: Calculates the achievable top speed considering specific motor data, battery voltage, and defined thermal tolerance limits based on physical hardware specifications.

## Learnings & modifications
This section documents the findings from previous tests & speedruns in 1:10 scale as well as the resulting modifications to the vehicle. Each area can be expanded.

| Area | Learnings | Modifications |
|:---|---:|---:|
| Driving operation & environment | 4 | 0 |
| Suspension & geometry | 1 | 4 |
| Drivetrain | 3 | 3 |
| Electronics & control | 5 | 0 |
| Chassis & assembly | 5 | 2 |
| **Total** | **18** | **9** |

<details>
<summary><b>Driving operation & environment</b></summary>

| Type | Topic | Finding |
|:---|:---|:---|
| ![learning][badge-learning] | Track selection | A suitable track is crucial for success. Clean asphalt is absolutely necessary. The track should preferably not be bordered by walls or curbs. A minimum width of 8 meters is required. |
| ![learning][badge-learning] | Weather | The weather is also important. Ensure there is no wind and conditions are dry. |
| ![learning][badge-learning] | Safety | If the conditions are not right and you don't have a good feeling, no speedrun should be undertaken. |
| ![learning][badge-learning] | Driving practice | You must learn to drive. It is necessary to familiarize yourself with the vehicle and the acceleration curve. It is important to steer the vehicle smoothly when it is far away. |

</details>

<details>
<summary><b>Suspension & geometry</b></summary>

| Type | Topic | Finding |
|:---|:---|:---|
| ![modification][badge-modification] | Dampers & springs | Very viscous shock oil was used and spring preload maximized. Stiff suspension is absolutely necessary to prevent loss of control due to diving. |
| ![modification][badge-modification] | Suspension geometry | Rear toe-in of 2.5 degrees and 0 degrees camber. Front 0 degrees toe-in and 0 degrees camber. No experiments should be made here. |
| ![modification][badge-modification] | Sway bars | The sway bars were removed. They are unnecessary for speedruns and pose a potential source of error. |
| ![modification][badge-modification] | Droop screws | The droop screws were removed. Since the track is not manually cleaned, further lowering is not constructive. The screws are unnecessary for the regular 1:10 speedrun. |
| ![learning][badge-learning] | Weight distribution | Care must be taken to ensure an even left/right weight distribution. Furthermore, the front must not be too light. |

</details>

<details>
<summary><b>Drivetrain</b></summary>

| Type | Topic | Finding |
|:---|:---|:---|
| ![learning][badge-learning] | Motorization | Sufficient motorization is less of a problem than often assumed. You shouldn't invest too much here. |
| ![modification][badge-modification] | Motor & gearing | Use of a 3660 motor with a tall gear ratio instead of the usual 3650 motor. The motorization must be adapted to the available track. |
| ![modification][badge-modification] | Differential (front) | A front spool was installed. During straight-line running at maximum speed, diff-out must be absolutely avoided; speed compensation is not desired. |
| ![learning][badge-learning] | Differential (rear) | Making the rear differential stiffer is not necessary. The front spool is sufficient. |
| ![learning][badge-learning] | Thermal management | Problems with ESC and motor temperature have not occurred yet. The problem is apparently overrated. |
| ![modification][badge-modification] | Motor cooling | The motor cooling was removed. The motor does not heat up significantly during speedruns and drives the final drive ratio of 3.91 without problems. A fan is mounted for visual reasons only and is not required for cooling. |

</details>

<details>
<summary><b>Electronics & control</b></summary>

| Type | Topic | Finding |
|:---|:---|:---|
| ![learning][badge-learning] | Control components | **Do not skimp on the remote control and servo**. Lack of precision makes steering corrections a game of chance. You must invest in a remote control with hall sensors and a decent digital servo. |
| ![learning][badge-learning] | Assistance systems | **Using a gyro really makes a difference** and is highly recommended. |
| ![learning][badge-learning] | Steering mechanics | The steering mechanism must move without resistance when disconnected from the servo. Mechanical resistance prevents the servo from returning precisely to the neutral position during slow steering inputs. In this state, the servo stops visibly but continues to draw current, indicated by audible noise, as it attempts to reach the neutral position. |
| ![learning][badge-learning] | `Steering Exponential Curve` (cubic polynomial) | The steering exponential curve requires precise configuration. A setting of approximately -30 is recommended. |
| ![learning][badge-learning] | `Throttle Exponential Curve` (cubic polynomial) | The throttle exponential curve requires precise configuration. A setting of approximately -40 is recommended. |

</details>

<details>
<summary><b>Chassis & assembly</b></summary>

| Type | Topic | Finding |
|:---|:---|:---|
| ![learning][badge-learning] | Material selection | Not all plastic parts should be replaced with aluminum. You must consider which parts are allowed to be destroyed in a crash. If easily replaceable plastic parts are replaced with aluminum, the impact energy finds more unfavorable paths. |
| ![learning][badge-learning] | Threadlocker | Loctite on metal connections is absolutely mandatory. |
| ![learning][badge-learning] | Body | The body should not be painted. A clear body allows a necessary view of the technology at all times. |
| ![learning][badge-learning] | Aerodynamics | A wedge shape of the vehicle is necessary for efficient aerodynamics. To achieve this, the front body posts must be shortened as much as possible. |
| ![modification][badge-modification] | C-hub assembly | The mounting screws of the C-hubs were loosened to eliminate mechanical resistance. Excessive tightening prevents the steering from moving freely, resulting in the previously described issue of an inaccurate servo neutral return. |
| ![modification][badge-modification] | Servo saver | The servo saver was removed and an aluminum servo horn was mounted directly. This increases the risk of damage to the servo in the event of a crash. The servo saver was identified as a source of failure (steering oscillation) during speedruns. |
| ![learning][badge-learning] | Tires | Belted tires avoid ballooning but do not provide sufficient stability and grip for speedruns. The use of foam rubber tires increases stability and grip. |

</details>

[badge-learning]: https://img.shields.io/badge/learning-0e8a16?style=flat-square
[badge-modification]: https://img.shields.io/badge/modification-b60205?style=flat-square

## Repository automation
Maintaining the specifications, architecture decisions and setup sheets formatted as YAML files triggers automated processes:
* **Aggregation of specifications**: Individual hardware specifications are merged into the central specification file `specs/full_spec.yaml`.
* **Decision log**: Architecture decisions are automatically compiled into an overview sorted by ID (`architecture/README.md`).
* **Setup dashboard**: The latest setup sheet is converted to `docs/latest_setup.json` and deployed to GitHub Pages.

The bill of materials (`project/costs`) is maintained manually.

## Follow-up project: Telemetry system
This project is followed by an independent project concerned with the development of a telemetry data system based on an ESP32 microcontroller. The goal is the sensory recording and transmission of driving dynamics parameters of the RC vehicle.

[![GitHub repo](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/kleinnconrad/embedded.rc.telemetry)

## Licensing
* The source code of the calculation models is subject to the MIT license.
* The hardware design, documentation, specifications, and test results are released under the Creative Commons attribution 4.0 international license. Own adaptations and commercial use are permitted, provided authorship is acknowledged.
