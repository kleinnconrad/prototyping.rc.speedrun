# Hobbywing QuicRun 120A ESC


## Table of contents
* [1. Throttle range calibration](#1-throttle-range-calibration)
  * [1.1 preparation of the transmitter](#11-preparation-of-the-transmitter)
  * [1.2 performing the calibration](#12-performing-the-calibration)
* [2. Parameterization of the "punch" (start mode) via LED program card](#2-parameterization-of-the-punch-start-mode-via-led-program-card)
  * [2.1 connecting the program card](#21-connecting-the-program-card)
  * [2.2 setting the parameter](#22-setting-the-parameter)
* [3. Ensure correct polarity of the motor](#3-ensure-correct-polarity-of-the-motor)
* [4. ESC programming](#4-esc-programming)


## 1. Throttle range calibration

### 1.1 preparation of the transmitter
* Set the throttle trim to the value 0 (neutral).
* Set end point adjustment (EPA) for throttle and brake to 100%.
* ABS braking functions must be disabled.
* Check throttle channel inversion (usually "REV" for futaba systems, "NOR" for other manufacturers).
* Turn on the transmitter.

### 1.2 performing the calibration
1. Connect the drive battery to the switched-off ESC.
2. Press and hold the SET button on the ESC.
3. Turn on the ESC using the main switch.
4. As soon as the red status LED starts flashing, release the SET button immediately.
5. **Neutral point:** Leave the throttle trigger in the neutral position. Press the SET button once. The green LED flashes once for confirmation.
6. **Full throttle endpoint:** Pull the throttle trigger to the maximum forward position (full throttle) and hold it at the mechanical stop. Press the SET button once. The green LED flashes twice.
7. **Full brake endpoint:** Push the throttle trigger to the maximum reverse position (full brake) and hold it at the mechanical stop. Press the SET button once. The green LED flashes three times.
8. Return the throttle trigger to the neutral position. The ESC completes the initialization process after approx. three seconds and is ready for operation.

---

## 2. Parameterization of the "punch" (start mode) via LED program card

### 2.1 connecting the program card
1. Make sure the ESC is turned off.
2. Plug the connection cable of the program card into the dedicated PRG port (3-pin) of the ESC.
3. Strictly observe polarity: The ground cable (black/brown) must be connected to the negative pole (-), the signal cable (white/orange) to the signal pole (S/P).
4. Connect the opposite end of the cable to the program card.

### 2.2 setting the parameter
1. Connect the drive battery and turn on the ESC. The numeric segment display of the program card is activated.
2. Iteratively press the **ITEM** button until the parameter for "start mode / punch" (menu item 3) is displayed on the left display field.
3. Press the **VALUE** button to specify the numeric value.
   * *Note for the present high-load gear ratio (43/68):* Value must absolutely be set to **1 (soft)** to minimize critical inrush currents (stall currents) and prevent triggering of the overcurrent protection circuit.
4. Press the **OK** button to write the changed value into the non-volatile memory of the ESC. (Motor usually gives an acoustic confirmation signal).
5. Turn off the ESC and disconnect the physical connection to the program card.

## 3. Ensure correct polarity of the motor
The fit of the motor in the Carten requires an inverse polarity compared to the standard so that technical and physical direction of movement are congruent. The technical directions of rotation are controlled differently, so that purely inverting on the remote control is not sufficient.

## 4. ESC programming

| Item | programmable items | option 1 | option 2 | option 3 | option 4 | option 5 | option 6 | option 7 | option 8 | option 9 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | running mode | forward with brake | **(forward / reverse with brake)** | forward with reverse | | | | | | |
| 2 | cutoff voltage | disabled | 2.6V/cell | 2.8V/cell | **(3.0V/cell)** | 3.2V/cell | 3.4V/cell | | | |
| 3 | punch | **(level 1)** | level 2 | level 3 | level 4 | level 5 | level 6 | level 7 | level 8 | level 9 |
| 4 | drag brake force | **(0%)** | 5% | 10% | 20% | 40% | 60% | 80% | 100% | |
| 5 | max. Brake force* | **(25%)** | 50% | 75% | 100% | disabled | | | | |
| 6 | max. Reverse force | **(25%)** | 50% | 75% | 100% | | | | | |
| 7 | neutral range | 6% | **(9%)** | 12% | | | | | | |
| 8 | timing | 0° | 3.75° | 7.5° | **(11.25°)** | 15° | 18.75° | 22.5° | 26.25° | |
| 9 | LiPo cells* | **(auto)** | 2S | 3S | 4S | 5S | 6S | | | |
| 10 | BEC voltage | **(6.0V)** | 7.4V | | | | | | | |

![Program card ESC](https://github.com/kleinnconrad/prototyping.rc.speedrun/blob/main/photos/PXL_20260319_093605867.jpg)
