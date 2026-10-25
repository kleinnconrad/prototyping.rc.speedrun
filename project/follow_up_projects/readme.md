# Ideas for follow-up projects

**Sensors/telemetry** [![GitHub repo](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/kleinnconrad/embedded.rc.telemetry)
* Microcontroller/sensor solution for measuring ESC and motor temperature and the speed at the driveshaft. 

**IoT cloud data platform** [![GitHub repo](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/kleinnconrad/embedded.rc.telemetry)
* Setup of a real-time streaming pipeline (ESP32 via LTE) for GPS and ESC telemetry.
* Implementation of a cloud infrastructure for scalable storage and processing of vehicle data.
* Live dashboarding for real-time performance analysis during speedruns.

**Hardware scaling**
* Dual motor configuration for the Carten T410R chassis (CAD project).

**Data analytics (GPS and ESC telemetry)**
* Development of a regression model to estimate the real speed from ESC telemetry data.
* Structured evaluation of relevant experiments and speedrun test runs.
* Derivation of data-driven optimization approaches for maximum battery efficiency and absolute top speed.

**Assistance systems**
* Integration of hardware and software for assisted driving with the Carten T410R.

**Predictive maintenance**
* Development of a model for predicting thermal limits (motor/ESC) based on load profiles, RPM and ambient temperature.
* Long-term analysis of voltage sag under full load for data-driven evaluation of battery degradation (state of health).

**Computer vision & FPV systems**
* Integration of an FPV camera system with on-screen-display (OSD) for overlaying relevant live telemetry (speed, temperatures, battery level).
* Implementation of camera-based environment detection (e.g. via raspberry pi) to expand the assistance systems with lane detection and obstacle avoidance.
