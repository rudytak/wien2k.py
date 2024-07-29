from wien2k import *
import asyncio


async def Mn2As_mag_permutations():
    # calculating magnetic orientation energies as per:
    # doi: 10.1021/ic3024716

    mn2as = StructureFile.load_materials_project(
        "https://next-gen.materialsproject.org/materials/mp-610522",
        "credentials.json",
    )
    mn2as.tweak_cell_multiples(c=2)

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

    async def prepMF(_mf, name, init_lapw):
        await _mf.open()
        await _mf.manual_run(
            name, init_lapw,
            auto_confirm=True,
        )
        await _mf.close()

    coroutines = []
    for key in configs.keys():
        coroutines.append(prepMF(
            MaterialFolder("credentials.json", "Mn2As", structure=mn2as),
            key,
            init_lapw_Parameters(
                kpoints=1000,
                spin_polarized=True,
                lstart_flag="ask",
                x_ask_flags_pattern=configs[key],
            )
        ))

    await asyncio.gather(coroutines)

async def Cr2As_mag_permutations():
    # calculating magnetic orientation energies as per:
    # doi: 10.1021/ic3024716

    cr2as = StructureFile.load_materials_project(
        "https://next-gen.materialsproject.org/materials/mp-20552",
        "credentials.json",
    )
    cr2as.tweak_cell_multiples(c=2)

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

    async def prepMF(_mf, name, init_lapw):
        await _mf.open()
        await _mf.manual_run(
            name, init_lapw,
            auto_confirm=True,
        )
        await _mf.close()

    coroutines = []
    for key in configs.keys():
        coroutines.append(prepMF(
            MaterialFolder("credentials.json", "Cr2As", structure=cr2as),
            key,
            init_lapw_Parameters(
                kpoints=1000,
                spin_polarized=True,
                lstart_flag="ask",
                x_ask_flags_pattern=configs[key],
            )
        ))

    await asyncio.gather(*coroutines)

asyncio.run(
    wien2k_main(
        [
            Cr2As_mag_permutations()
        ]
    )
)