# Stock parts of the Carten T410R
The files in this directory are models of stock parts of the Carten T410R. They are not part of the speedrun design and are not manufactured in this project. They are modelled for the completeness of the build: the assembly of the speedrun chassis contains them, so that the space around the speedrun parts can be checked.

* **`/pivot_block`**: Pivot blocks of the wishbones, long block (1 piece) and short block (3 pieces), STEP, STL and parameter file. Status: not verified, work in progress. Description and checks: see the [CAD readme](../readme.md#pivot-blocks-stock-parts-not-part-of-the-speedrun-design).
* **`/driveshaft`**: Centre driveshaft between the pinions of the two bulkheads, with the fixed metal pins, and the cup joints, STEP and STL; parameter file of all drive line parts. Status: not verified, work in progress.
* **`/rear_drive`**: Rear pinion shaft with flange, spur gear 72T 48DP and bearing 5x10x4 in the motor mount, STEP and STL. Status: not verified, work in progress.
* **`/motor_mount`**: Motor mount for 540 motors and its cap, STEP and STL. Status: not verified, work in progress.
* **`/diff_outdrive`**: Diff outdrive with the slots for the holding pin of the dogbones, STEP and STL. Status: not verified, work in progress.
* The parts of `/driveshaft`, `/rear_drive`, `/motor_mount` and `/diff_outdrive` are generated with `scripts/cad/generate_driveshaft.py`. Description and checks: see the [CAD readme](../readme.md#centre-driveshaft-stock-parts-not-part-of-the-speedrun-design).
