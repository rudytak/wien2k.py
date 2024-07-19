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

configs = {
    "F": ["u"] * 8 + ["n"] * 4,
    "Fi": ["d", "u", "u", "d"] * 2 + ["n"] * 4,
    "AF1": ["u"] * 4 + ["d"] * 4 + ["n"] * 4,
    "AF2": ["d", "u", "u", "u", "d", "d", "d", "u"] + ["n"] * 4,
    "AF3": ["d", "u", "u", "u", "u", "d", "d", "d"] + ["n"] * 4,
    "AF4": ["u", "u", "u", "d", "d", "d", "d", "u"] + ["n"] * 4,
    "AF5": ["d", "u"] * 4 + ["n"] * 4,
    "AF6": ["d", "u"] * 2 + ["u", "u", "d", "d"] + ["n"] * 4,
    "AF7": ["u", "u", "d", "u", "d", "u", "d", "d"] + ["n"] * 4,
    "AF8": ["d", "u"] * 2 + ["d", "d", "u", "u"] + ["n"] * 4,
    "AF9": ["d", "u"] * 2 + ["u", "d"] * 2 + ["n"] * 4,
    "AF10": ["u", "u", "d", "u", "d", "d", "u", "d"] + ["n"] * 4,
}

for key in configs.keys():
    mf.manual_run(
        key,
        init_lapw_Parameters(
            kpoints=1000,
            spin_polarized=True,
            lstart_flag="ask",
            x_ask_flags_pattern=configs[key],
        ),
        auto_confirm=True,
    )
mf.close()