from wien2_helper import *
from wien2k_connection import *
from wien2k_params import *
from wien2k_struct import *

import time, re, json, timeit
from datetime import datetime


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
        elif structure == "":
            # this is alright for just opening and empty instance for the CMD, SSH and SCP to use commands, but running lapw won't be possible
            pass
        else:
            raise Exception("No structure was given!")

    @staticmethod
    def open_empty_instance(credentials_json_path):
        MF = MaterialFolder(credentials_json_path, "", structure="")
        MF.open()
        return MF

    def open(self):
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
        self.cmd.cd(f"{self.material}")

    # ---------------- CLEANING AND EXITING ----------------
    def clean(self):
        self.cleanup_wien_scratch()

    def close(self):
        self.clean()

        self.ssh.disconnect()
        self.scp.disconnect()

        self.cmd.kill()

    # ---------------- WIEN SCRATCH ----------------
    def make_wien_scratch(self):
        # create wien2k scratch
        WS_basepath = "/home/sedlacek/"
        tmpdir_name = rng_string(16)
        self.WS_tmppath = WS_basepath + f"WS_{self.material}_{tmpdir_name}"

        self.cmd.type(f"mkdir {self.WS_tmppath}")
        self.cmd.type(f"export SCRATCH={self.WS_tmppath}")
        self.cmd.type(f"export EDITOR=nano")

    def cleanup_wien_scratch(self):
        self.cmd.home()
        self.cmd.type(f"rm {self.WS_tmppath} -rf")

    # ---------------- RUNNING SCF INTERNAL ----------------

    def _await_lapw_end(self, timeout=60, min_time=10 * 60):
        # set the start time:
        start_time = timeit.default_timer()
        print(
            "If the calculation finishes and the rest of the program is not able to recognise that, type 'manual_stop' into the ssh console to stop it manually and wait for the next check."
        )
        time.sleep(min_time)

        while True:
            # wait for some time
            time.sleep(timeout)

            try:
                # read the status of the screen
                lines = self.cmd.read_output(5)
                lines = "\n".join(lines)

                success_status = (
                    (f"{self.material}$" in lines)
                    and ("run_lapw" not in lines)
                    or ("> stop" in lines)
                )
                not_converged_status = "SCF NOT CONVERGED" in lines
                error_status = "stop error" in lines
                manual_stop_status = "manual_stop" in lines

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
                # in case of an error of the reading, continue chacking
                print("Error while waiting")
                pass

    def _run_safe(
        self,
        run_name,
        params: init_lapw_Parameters = None,
        params_so: init_so_lapw_Parameters = None,
        params_orb: UJ_Parameters = None,
    ):
        run_uid = "run_" + rng_string(16)

        # remove old files and upload the new struct file
        self.cmd.bring_forward()
        self.cmd.type(f"rm * -rf")

        # get and save the edited struct
        tmp_path = f"{rng_string(32)}.poscar"
        with open(tmp_path, "w") as f:
            f.write(self.structure.generate_poscar())

        # ulpoad poscar and remove temp file
        self.scp.upload_file(tmp_path, f"{self.material}.poscar")
        os.remove(tmp_path)

        # convert poscar to struct
        self.cmd.type(f"xyz2struct < {self.material}.poscar")
        while "be exactly" in "\n".join(self.cmd.read_output(2)):
            self.cmd.type("n")

        self.cmd.type(f"mv xyz2struct.struct {self.material}.struct")
        # TODO: add visual cehck for any questions

        # assess the high level location
        is_sp = params.raw_params["spin_polarized"]
        is_orb = params_orb != None
        is_so = params_so != None

        # run all init processes
        params.execute(self)
        if is_so:
            # inherit the sp and kpoints settings from init_lapw_Parameters
            params_so = params_so.reinstantiate(params)
            params_so.execute(self)
        if is_orb:
            params_orb.execute(self)

        self.cmd.type(
            f"run{'sp' if is_sp else ''}_lapw {'-so' if is_so else ''} {'-orb' if is_orb else ''}"
        )
        (runtime, status) = self._await_lapw_end()

        self._save_run_diagnostics(
            run_name, run_uid, status, runtime, params, params_so, params_orb
        )
        return run_uid

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
        last_lines = self.cmd.read_output(32)
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
            "completion_date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
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

    # ---------------- RUNNING SCF ----------------

    def manual_run(
        self,
        run_name,
        params: init_lapw_Parameters = None,
        params_so: init_so_lapw_Parameters = None,
        params_orb: UJ_Parameters = None,
        auto_confirm=False,
    ):
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
        self.cmd.cd(self.material)

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
            self._run_safe(run_name, params, params_so, params_orb)

        # return to the main material directory
        self.cmd.cd("../../..")

    # ---------------- PROCESSING ----------------

    @staticmethod
    def band_structure(run_detail_path):
        """
        Should be ran while in a directory with a finished run.
        """
        pass

    @staticmethod
    def DOS(
        run_detail_path, in_tetra, save_path, credentials_json_path="./credentials.json"
    ):
        """
        Calculates and collect DOS data of an already converged system.
        """

        MF = MaterialFolder.open_empty_instance(credentials_json_path)

        run_details = {}
        with open(run_detail_path, "r") as reader:
            run_details = json.load(reader)
        time_per_cycle = (
            run_details["diagnostics"]["runtime"] / run_details["diagnostics"]["cycles"]
        )

        MF.cmd.cd("")
        MF.cmd.cd(run_details["absolute_path"])
        # shift the .int file by the fermi energy and upload the .int file
        in_tetra.fermiShift(run_details["results"]["fermi_energy_eV"])
        in_tetra.execute(MF, run_details["inputs"]["material_name"])

        is_sp = run_details["inputs"]["init_lapw"]["spin_polarized"] == "y"
        is_so = run_details["inputs"]["init_so_lapw"] != {}
        is_orb = (
            run_details["inputs"]["UJ"]["U_eV"] != 0
            or run_details["inputs"]["UJ"]["J_eV"] != 0
        )

        # lapw1
        MF.cmd.type(
            f"x lapw1 {'-up' if is_sp else ''} {'-so' if is_so else ''} {'-orb' if is_orb else ''} -qtl",
            wait_after=time_per_cycle / 4,
        )
        if is_sp:
            MF.cmd.type(
                f"x lapw1 -dn {'-so' if is_so else ''} {'-orb' if is_orb else ''} -qtl",
                wait_after=time_per_cycle / 4,
            )

        # lapwso
        if is_so:
            MF.cmd.type(
                f"x lapw1 {'-up' if is_sp else ''} {'-orb' if is_orb else ''} -qtl",
                wait_after=time_per_cycle / 4,
            )
            if is_sp:
                MF.cmd.type(
                    f"x lapw1 -dn {'-orb' if is_orb else ''} -qtl",
                    wait_after=time_per_cycle / 4,
                )

        # lapw2
        MF.cmd.type(
            f"x lapw2 {'-up' if is_sp else ''} {'-so' if is_so else ''} -qtl",
            wait_after=time_per_cycle / 10,
        )
        if is_sp:
            MF.cmd.type(
                f"x lapw2 -dn {'-so' if is_so else ''} -qtl",
                wait_after=time_per_cycle / 10,
            )

        # run tetra
        MF.cmd.type(
            f"x tetra {'-up' if is_sp else ''} {'-so' if is_so else ''}",
            wait_after=time_per_cycle / 10,
        )

        # wait for all things to finish
        if "LEGAL END TETRA" not in MF.cmd.read_output(5):
            time.sleep(1)
            print("waiting for tetra to end")

        if is_sp:
            MF.cmd.type("clear")
            MF.cmd.type(
                f"x tetra -dn {'-so' if is_so else ''}",
                wait_after=time_per_cycle / 10,
            )

            if "LEGAL END TETRA" not in MF.cmd.read_output(5):
                time.sleep(1)
                print("waiting for tetra -dn to end")

        if is_sp:
            MF.scp.download_file(
                run_details["inputs"]["material_name"] + ".dos1evup",
                save_path + ".dos1evup",
            )
            MF.scp.download_file(
                run_details["inputs"]["material_name"] + ".dos1evdn",
                save_path + ".dos1evdn",
            )
        else:
            MF.scp.download_file(
                run_details["inputs"]["material_name"] + ".dos1ev",
                save_path + ".dos1ev",
            )

        MF.close()

    # ---------------- OPTIMISATIONS / AUTOMATIZATIONS ----------------


if __name__ == "__main__":
    crsb = StructureFile.load_materials_project(
        "https://legacy.materialsproject.org/materials/mp-1406/",  # load in mnte
        "credentials.json",
    )

    crsb.tweak_dimensions(4.103, 4.103, 5.463)
    crsb.tweak_atom(0, Z=24)
    crsb.tweak_atom(1, Z=51)
    print(crsb.atoms)

    mf = MaterialFolder("credentials.json", "CrSb", structure=crsb)
    mf.open()
    mf.manual_run(
        "CrSb_test_notSO",
        init_lapw_Parameters(
            kpoints=1000,
            spin_polarized=True,
            lstart_flag="ask",
            x_ask_flags_pattern=["u", "d"],
            calculation_method="LDA",
        ),
        auto_confirm=True,
    )

    mf.manual_run(
        "CrSb_test_SO",
        init_lapw_Parameters(
            kpoints=1000,
            spin_polarized=True,
            lstart_flag="ask",
            x_ask_flags_pattern=["u", "d"],
            calculation_method="LDA",
        ),
        params_so=init_so_lapw_Parameters(0, 0, 1, EMAX=10.0),
        auto_confirm=True,
    )
