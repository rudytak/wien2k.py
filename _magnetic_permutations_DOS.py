from wien2k import *
from wien2k_params import *

for u in [0, 2, 3, 4]:
    for run in os.listdir(f"./execs/mn2as_mag_permuts_results_U={u}"):
        run_details = {}
        with open(f"./execs/mn2as_mag_permuts_results_U={u}/{run}", "r") as reader:
            run_details = json.load(reader)

        MaterialFolder.DOS(
            f"./execs/mn2as_mag_permuts_results_U={u}/{run}",
            input_TETRA(
                -7.0,
                5.0,
                [
                    input_TETRA.DOS_case("total", "all"),
                    input_TETRA.DOS_case(1, "d"),
                    input_TETRA.DOS_case(4, "d"),
                    input_TETRA.DOS_case(8, "p"),
                    input_TETRA.DOS_case(8, "d"),
                ],
                0.0272,
                0.0408
            ),
            f"./execs/mn2as_DOS/mn2as_DOS_U={u}_{run_details['name']}",
        )
