from wien2k import *

# calculating magnetic orientation energies as per:
# doi: 10.1021/ic3024716

cr2as = StructureFile.load_materials_project(
    "https://next-gen.materialsproject.org/materials/mp-20552?formula=Cr2As",
    "credentials.json",
)
cr2as.tweak_cell_multiples(c=2)

mf = MaterialFolder("credentials.json", "Cr2As", structure=cr2as)
mf.open()

configs_old = {
    # "F": ["u"] * 8 + ["n"] * 4,
    "Fi": ["d", "u", "u", "d"] * 2 + ["n"] * 4,
    # "AF1": ["u"] * 4 + ["d"] * 4 + ["n"] * 4,
    # "AF2": ["d", "u", "u", "u", "d", "d", "d", "u"] + ["n"] * 4,
    # "AF3": ["d", "u", "u", "u", "u", "d", "d", "d"] + ["n"] * 4,
    # "AF4": ["u", "u", "u", "d", "d", "d", "d", "u"] + ["n"] * 4,
    "AF5": ["d", "u"] * 2 + ["n"] * 4,
    # "AF6": ["d", "u"] * 2 + ["u", "u", "d", "d"] + ["n"] * 4,
    # "AF7": ["u", "u", "d", "u", "d", "u", "d", "d"] + ["n"] * 4,
    # "AF8": ["d", "u"] * 2 + ["d", "d", "u", "u"] + ["n"] * 4,
    # "AF9": ["d", "u"] * 2 + ["u", "d"] * 2 + ["n"] * 4,
    # "AF10": ["u", "u", "d", "u", "d", "d", "u", "d"] + ["n"] * 4,
}

Cr2As_configs_double = {
    # "Fi": ["d", "d", "u", "u"] * 2 + ["n", "n"] * 2,
    "AF5": ["u", "d", "d", "u"] * 2
    + ["n", "n"] * 2,
}

Cr2As_configs_single = {
    "Fi": ["d", "d", "u", "u", "n", "n"],
    "AF5": ["u", "d", "d", "u", "n", "n"],
}

for u in [3]:
    for key in Cr2As_configs_double.keys():
        mf.manual_run(
            key + f"_double_cell",
            init_lapw_Parameters(
                kpoints=1000,
                spin_polarized=True,
                lstart_flag="ask",
                x_ask_flags_pattern=Cr2As_configs_double[key],
            ),
            # params_orb=UJ_Parameters(
            #     u,
            #     0,
            #     [
            #         UJ_Parameters.atom(1, ["d"]),
            #         UJ_Parameters.atom(2, ["d"]),
            #         UJ_Parameters.atom(3, ["d"]),
            #         UJ_Parameters.atom(4, ["d"]),
            #         UJ_Parameters.atom(5, ["d"]),
            #         UJ_Parameters.atom(6, ["d"]),
            #         UJ_Parameters.atom(7, ["d"]),
            #         UJ_Parameters.atom(8, ["d"]),
            #     ],
            # ),
            auto_confirm=True,
        )
mf.close()
