from wien2_helper import *
from wien2k_connection import *
from wien2k_params import *
from wien2k_struct import *

import time, re, json, timeit
from datetime import datetime

from typing import Tuple


class MaterialFolder:
    def __init__(
        self, credentials_json_path, material_name, struct_filepath=None, structure=None
    ) -> None:
        # handle connection credentails
        self.credentials_path = credentials_json_path

        self.material = material_name

        if struct_filepath != None:
            self.structure = StructureFile.load(struct_filepath)
        elif structure != None:
            self.structure = structure
        else:
            raise Exception("No structure was given!")

    def open(self) -> asyncio.Future:
        # connect to the server
        self.cmd = CMD_Window()
        self.scp = SCP_Connection(self.cmd, self.credentials_path)
        self.scp.connect_twohop()
        self.ssh = dSSH_Connection(self.cmd, self.credentials_path)
        self.ssh.connect()

        # make a new scratch folder
        self.make_wien_scratch()

        # make the material folder (if that folder already exists, it'll just be automatically ignored)
        self.cmd.home()
        self.cmd.type(f"mkdir {self.material}")
        return self.cmd.cd(f"{self.material}")

    # ---------------- CLEANING AND EXITING ----------------
    def clean(self) -> asyncio.Future:
        return self.cleanup_wien_scratch()

    def close(self) -> asyncio.Future:
        self.clean()

        self.ssh.disconnect()
        self.scp.disconnect()

        return self.cmd.kill()

    # ---------------- WIEN SCRATCH ----------------
    def make_wien_scratch(self) -> asyncio.Future:
        # create wien2k scratch
        WS_basepath = "/home/sedlacek/"
        tmpdir_name = rng_string(16)
        self.WS_tmppath = WS_basepath + f"WS_{self.material}_{tmpdir_name}"

        self.cmd.type(f"mkdir {self.WS_tmppath}")
        self.cmd.type(f"export SCRATCH={self.WS_tmppath}")
        return self.cmd.type(f"export EDITOR=nano")

    def cleanup_wien_scratch(self) -> asyncio.Future:
        self.cmd.home()
        return self.cmd.type(f"rm {self.WS_tmppath} -rf")

    # ---------------- RUNNING SCF INTERNAL ----------------

    async def _await_lapw_end(self, timeout=15) -> Tuple[float, str]:
        # set the start time:
        start_time = timeit.default_timer()
        print(
            "If the calculation finishes and the rest of the program is not able to recognize that, type 'manual_stop' into the ssh console to stop it manually and wait for the next check."
        )

        while True:
            # wait for some time
            await asyncio.sleep(timeout)

            try:
                # read the status of the screen
                lines = await self.cmd.read_output(5)
                lines = "\n".join(lines)

                success_status = (
                    does_text_contain(f"{self.material}$", lines, 85)
                    and not does_text_contain("run_lapw", lines, 85)
                    and not does_text_contain("runsp_lapw", lines, 85)
                ) or does_text_contain("> stop", lines, 80)
                not_converged_status = does_text_contain("SCF NOT CONVERGED", lines, 80)
                error_status = does_text_contain("stop error", lines, 80)
                manual_stop_status = does_text_contain("manual_stop", lines, 80)

                if any(
                    [
                        success_status,
                        not_converged_status,
                        error_status,
                        manual_stop_status,
                    ]
                ):
                    status = "unknown"
                    if manual_stop_status:
                        status = "manual_stop"
                    elif not_converged_status:
                        status = "not_converged"
                    elif error_status:
                        status = "error"
                    elif success_status:
                        status = "success"
                    self.cmd.cd(".")
                    self.cmd.type("^C", do_ENTER=False)
                    self.cmd.cd(".")

                    end_time = timeit.default_timer()
                    return (round(end_time - start_time, 2), status)
            except:
                # in case of an error of the reading, continue checking
                print("Error while waiting")
                pass

    def _save_run_diagnostics(
        self, run_name, run_uid, status, runtime, params, params_so, params_orb
    ):
        """
        This function should be called in the directory where a run has finished.
        This function is automatically called after _run_safe.
        """

        # assess the high level location
        is_sp = params.raw_params["spin_polarized"]
        is_orb = params_orb != None
        is_so = params_so != None

        # save run diagnostics
        last_lines = self.cmd._read_output(32)
        stack = "\n".join(last_lines[::-1])

        def cycles_find(l):
            finds = re.findall(r"in cycle (\d*)", l)
            if len(finds) == 0:
                return -1
            else:
                return int(finds[0])

        cycles = max(lmap(last_lines, cycles_find))

        # save results to some local database
        # downlaod the SCF file
        self.scp.download_file(f"{self.material}.scf", f"{self.material}.scf")
        with open(f"{self.material}.scf", "r") as f:
            content = f.read()
        os.remove(f"{self.material}.scf")

        # extract important data
        fer_Ry = float(re.findall(r":FER.+(\d*\.\d*)", content)[-1])
        ene_Ry = float(re.findall(r":ENE[\D]+([- ]\d*\.\d*)", content)[-1])
        gap_Ry = float(re.findall(r":GAP.+(\d*\.\d*).+(\d*\.\d*)", content)[-1][0])

        run_details = {
            "name": run_name,
            "run_uid": run_uid,
            "competion_date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "absolute_path": self.cmd.curr_dir,
            "inputs": {
                "material_name": self.material,
                "struct": {
                    "plaintext": self.structure.generate_poscar(),
                    "tweaks_log": self.structure.get_logs(),
                },
                "init_lapw": params.text_params,
                "init_so_lapw": params_so.text_params if is_so else {},
                "UJ": {
                    "U_eV": params_orb.U if is_orb else 0,
                    "J_eV": params_orb.J if is_orb else 0,
                    "atoms": params_orb.atoms_complete if is_orb else [],
                },
            },
            "diagnostics": {
                "cycles": cycles,
                "runtime": runtime,
                "status": status,
                "end_stack": stack,
            },
            "results": {
                "fermi_energy_eV": fer_Ry * Constants.Ry_to_eV,
                "energy_tot_eV": ene_Ry * Constants.Ry_to_eV,
                "energy_per_cell_eV": ene_Ry
                * Constants.Ry_to_eV
                / self.structure.get_mutliples_count(),
                "gap_eV": gap_Ry * Constants.Ry_to_eV,
                "fermi_energy_Ry": fer_Ry,
                "energy_tot_Ry": ene_Ry,
                "energy_per_cell_Ry": ene_Ry / self.structure.get_mutliples_count(),
                "gap_Ry": gap_Ry,
                "MM_tot": float(
                    re.findall(r":MMTOT.+([- ]\d*\.\d*)", content)[-1]
                ),  # all in bohr magneton
                "MM_intersticial": float(
                    re.findall(r":MMINT.+([- ]\d*\.\d*)", content)[-1]
                ),
                "MM_atoms": lmap(
                    re.findall(r":MMI\d{3}\d*\d\d*([- ]\d*\.\d*)", content)[
                        -self.structure.non_eq_count :
                    ],
                    float,
                ),
            },
        }

        # save the json data on the server
        with open(f"_{run_uid}_details.json", "w") as f:
            json.dump(run_details, f)
        self.scp.upload_file(f"_{run_uid}_details.json", f"_{run_uid}_details.json")

        # TODO: output file structuring

    async def _run_safe(
        self,
        run_name,
        params: init_lapw_Parameters = None,
        params_so: init_so_lapw_Parameters = None,
        params_orb: UJ_Parameters = None,
    ) -> asyncio.Future:
        run_uid = "run_" + rng_string(16)

        # remove old files and upload the new struct file
        self.cmd.bring_forward()
        await self.cmd.type(f"rm * -rf")

        # get and save the edited struct
        tmp_path = f"{rng_string(32)}.poscar"
        with open(tmp_path, "w") as f:
            f.write(self.structure.generate_poscar())

        # ulpoad poscar and remove temp file
        self.scp.upload_file(tmp_path, f"{self.material}.poscar")
        os.remove(tmp_path)

        # convert poscar to struct
        self.cmd.type(f"xyz2struct < {self.material}.poscar 1e-9")
        while await does_console_contain("be exactly", self.cmd, 2, 80):
            self.cmd.type(f"n")

        self.cmd.type(f"mv xyz2struct.struct {self.material}.struct")
        # TODO: add visual check for any questions

        # assess the high level location
        is_sp = params.raw_params["spin_polarized"]
        is_orb = params_orb != None
        is_so = params_so != None

        # run all init processes
        # use await to ensure that the initialization is finished before running "run_lapw"
        await params.execute(self)
        if is_so:
            # inherit the sp and kpoints settings from init_lapw_Parameters
            # use await to ensure that the initialization is finished before running "run_lapw"
            params_so = params_so.reinstantiate(params)
            await params_so.execute(self)
        if is_orb:
            params_orb.execute(self)

        await self.cmd.type(
            f"run{'sp' if is_sp else ''}_lapw {'-so' if is_so else ''} {'-orb' if is_orb else ''}"
        )
        (runtime, status) = await self._await_lapw_end()

        self._save_run_diagnostics(
            run_name, run_uid, status, runtime, params, params_so, params_orb
        )

    # ---------------- RUNNING SCF ----------------

    async def manual_run(
        self,
        run_name,
        params: init_lapw_Parameters = None,
        params_so: init_so_lapw_Parameters = None,
        params_orb: UJ_Parameters = None,
        auto_confirm=False,
    ) -> asyncio.Future:
        if params == None:
            # ask if they want to put in the parameters manually
            decision = Mbox(
                "Parameter issue",
                "No init_lapw_Params object was passed in. Would you like to perform the initialization yourself? If not, the default parameters will be used.",
                4,
            )

            # 6 stands for the yes button, 7 for the no button
            if decision == 6:
                Mbox(
                    "Manual initialization",
                    "Continue with the manual initalization in the console. After that is done, the process will continue on it's own.",
                    0,
                )
                # do the manual initialization in the control console
                # TODO: finish the manual init
                params = init_lapw_Parameters.manual_init()
                print("init_lapw_Parameters manual initialization succesfull")
            else:
                print("Default parameters will be used in the calculation.")
                # create the default params
                params = init_lapw_Parameters()

        # assess the high level location
        is_sp = params.raw_params["spin_polarized"]
        is_orb = params_orb != None
        is_so = params_so != None

        # make the final directory where the
        sp_so_orb_path = f"sp{'1' if is_sp else '0'}_so{'1' if is_so else '0'}_orb{'1' if is_orb else '0'}"
        self.cmd.type(f"mkdir {sp_so_orb_path}")
        self.cmd.cd(sp_so_orb_path)

        self.cmd.type(f"mkdir {run_name}")
        self.cmd.cd(run_name)

        self.cmd.type(f"mkdir {self.material}")
        await self.cmd.cd(self.material)

        # here only remove old files and add a question before doing so
        if not auto_confirm:
            decision = Mbox(
                "Run",
                "Do you wish to proceed with the initialization process? This action will clear any files from old initializations.",
                4,
            )
        else:
            decision = 6

        if decision == 6:
            await self._run_safe(run_name, params, params_so, params_orb)

        # return to the main material directory
        return self.cmd.cd("../../..")

    # ---------------- PROCESSING ----------------

    def band_structure():
        """
        Should be ran while in a directory with a finished run.
        """
        pass

    def DOS():
        """
        Calculates and collect DOS data of an already converged system.
        Should be ran while in a directory with a finished run.
        """
        pass

    # ---------------- OPTIMISATIONS / AUTOMATIZATIONS ----------------

async def wien2k_main(coroutines_to_run=[]):
    await asyncio.gather(*coroutines_to_run, CMD_input.handler_loop())

if __name__ == "__main__":
    async def run():
        mn2as = StructureFile(
            "Mn2As",
            [
                StructureAtom(0.0, 0.0, 0.0, 25),
                StructureAtom(0.5, 0.5, 0.0, 25),
                StructureAtom(0.5, 0.0, 0.3528180000000001, 25),
                StructureAtom(0.0, 0.5, 0.6471819999999999, 25),
                StructureAtom(0.5, 0.0, 0.7383260000000001, 33),
                StructureAtom(0.0, 0.5, 0.2616739999999999, 33),
            ],
            3.615015000000000,
            3.615015000000000,
            6.334917000000000,
        )
        # mn2as.tweak_cell_multiples(c=2)

        mf1 = MaterialFolder("./credentials.json", "Mn2As_test1", structure=mn2as)
        mf2 = MaterialFolder("./credentials.json", "Mn2As_test2", structure=mn2as)
        mf3 = MaterialFolder("./credentials.json", "Mn2As_test3", structure=mn2as)
        mf4 = MaterialFolder("./credentials.json", "Mn2As_test4", structure=mn2as)
        mf5 = MaterialFolder("./credentials.json", "Mn2As_test5", structure=mn2as)
        mf6 = MaterialFolder("./credentials.json", "Mn2As_test6", structure=mn2as)

        corroutines = []

        async def f(_mf):
            await _mf.open()
            await _mf.manual_run(
                "F",
                init_lapw_Parameters(
                    kpoints=100,
                    spin_polarized=True,
                    lstart_flag="-ask",
                    x_ask_flags_pattern=["u"],
                ),
                auto_confirm=True,
            )
            await _mf.close()

        for mf in [mf1, mf2, mf3, mf4]:
            corroutines.append(f(mf))

        await asyncio.gather(*corroutines)

    asyncio.run(
        wien2k_main(
            [
                run()
            ]
        )
    )
