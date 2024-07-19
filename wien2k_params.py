from wien2_helper import *

import os, time

class init_lapw_Parameters:
    CALC_METHOD_DICT = {
        "GGA-PBE": 13,
        "LDA": 5,
        "GGA-WC": 11,
        "GGA-PBESOL": 19,
    }

    DEFAULTS = {
        "reduction_percentage": 0,
        "scheme": "N",
        "accept_radii": "a",
        "nearest_neighbor": 2,
        "lstart_flag": "up",
        "x_ask_flags_pattern": ["u"],
        "calculation_method": "GGA-PBE",
        "separation_energy_eV": -6.0,
        "kpoints": 1000,
        "x_kdensity": 0.1,
        "kshift": False,
        "spin_polarized": True,
        "x_antiferromagnetic": False,
    }

    @staticmethod
    def manual_init():
        # TODO: allow manual parameter creation
        pass

    def __init__(
        self,
        reduction_percentage: int = None,
        scheme=None,
        accept_radii=None,
        nearest_neighbor: int = None,
        lstart_flag=None,
        x_ask_flags_pattern=None,  # any apttern of u/d/n that will be repeated for the all the atoms in a given structure
        calculation_method=None,  # one of these options: GGA-PBE/LDA/GGA-WC/GGA_PBESOL or a number 13/5/11/19
        separation_energy_eV: float = None,
        kpoints: int = None,
        x_kdensity: float = None,
        kshift: bool = None,
        spin_polarized: bool = None,
        x_antiferromagnetic: bool = None,
    ) -> None:
        # save copies of everything
        self.reduction_percentage = reduction_percentage
        self.scheme = scheme
        self.accept_radii = accept_radii
        self.nearest_neighbor = nearest_neighbor
        self.lstart_flag = lstart_flag
        self.x_ask_flags_pattern = x_ask_flags_pattern
        self.calculation_method = calculation_method
        self.separation_energy_eV = separation_energy_eV
        self.kpoints = kpoints
        self.x_kdensity = x_kdensity
        self.kshift = kshift
        self.spin_polarized = spin_polarized
        self.x_antiferromagnetic = x_antiferromagnetic

        args = locals()

        # the defaulted raw parameters
        self.raw_params = {}
        # the stringified parameters (except for x_ask_flags_pattern)
        self.text_params = {}

        for k in args:
            # use the default param values if nothing else was specified
            if args[k] == None:
                self.raw_params[k] = init_lapw_Parameters.DEFAULTS[k]
            else:
                self.raw_params[k] = args[k]

        for k in self.raw_params:
            # handle floats
            if k in ["separation_energy_eV", "x_kdensity"]:
                self.text_params[k] = str(float(self.raw_params[k]))

            # handle ints
            if k in ["nearest_neighbor", "kpoints", "reduction_percentage"]:
                self.text_params[k] = str(int(self.raw_params[k]))

            # handle 0/1 bools
            if k in ["kshift"]:
                if self.raw_params[k]:
                    self.text_params[k] = "1"
                else:
                    self.text_params[k] = "0"

            # handle y/n bools
            if k in ["spin_polarized", "x_antiferromagnetic"]:
                if self.raw_params[k]:
                    self.text_params[k] = "y"
                else:
                    self.text_params[k] = "n"

            # handle calculation methods:
            if k in ["calculation_method"]:
                # the calculation option is passed in as a number
                if type(self.raw_params[k]) == type(int()):
                    if self.raw_params[k] not in [13, 5, 11, 19]:
                        # if the passed in number is not a valid computational method, set it to the default value
                        self.text_params[k] = str(
                            init_lapw_Parameters.CALC_METHOD_DICT[
                                init_lapw_Parameters.DEFAULTS["calculation_method"]
                            ]
                        )
                    else:
                        # it is a valid method represented by an integer
                        self.text_params[k] = str(self.raw_params[k])
                # the calculation option is passed in as a string
                elif type(self.raw_params[k]) == type(str()):
                    if self.raw_params[k] not in [
                        "GGA-PBE",
                        "LDA",
                        "GGA-WC",
                        "GGA_PBESOL",
                    ]:
                        # if the passed in string is not a valid computational method, set it to the default value
                        self.text_params[k] = str(
                            init_lapw_Parameters.CALC_METHOD_DICT[
                                init_lapw_Parameters.DEFAULTS["calculation_method"]
                            ]
                        )
                    else:
                        # it is a valid method represented by an string
                        self.text_params[k] = str(
                            init_lapw_Parameters.CALC_METHOD_DICT[self.raw_params[k]]
                        )
                else:
                    # invalid type (neither an int or a string)
                    # set to default
                    self.text_params[k] = str(
                        init_lapw_Parameters.CALC_METHOD_DICT[
                            init_lapw_Parameters.DEFAULTS["calculation_method"]
                        ]
                    )

            # handle _ask_flag_pattern
            if k in ["x_ask_flags_pattern"]:
                self.text_params[k] = self.raw_params[k]

            # handle lstart_flags (up/dn/nm/ask)
            if k in ["lstart_flag"]:
                if self.raw_params[k] not in [
                    "up",
                    "dn",
                    "nm",
                    "ask",
                    "-up",
                    "-dn",
                    "-nm",
                    "-ask",
                ]:
                    # revert to the default flag
                    self.text_params[k] = (
                        "-" + str(init_lapw_Parameters.DEFAULTS[k])
                    ).replace("--", "-")
                else:
                    # set the correct flag with the dash in the front
                    self.text_params[k] = ("-" + str(self.raw_params[k])).replace(
                        "--", "-"
                    )

            # handle scheme
            if k in ["scheme"]:
                if str(self.raw_params[k]).lower() in ["o", "old"]:
                    # old scheme
                    self.text_params[k] = "o"
                elif str(self.raw_params[k]).lower() in ["n", "new"]:
                    # new scheme
                    self.text_params[k] = "N"
                else:
                    # set to default
                    self.text_params[k] = str(init_lapw_Parameters.DEFAULTS[k])

            # handle accepting radii
            if k in ["accept_radii"]:
                if str(self.raw_params[k]).lower() in ["a", "accept"]:
                    # old scheme
                    self.text_params[k] = "a"
                elif str(self.raw_params[k]).lower() in ["d", "discard"]:
                    # new scheme
                    self.text_params[k] = "d"
                # elif str(self.raw_params[k]).lower() in ["r", "rerun"]:
                #     # new scheme
                #     self.text_params[k] = "r"
                else:
                    # set to default
                    self.text_params[k] = str(init_lapw_Parameters.DEFAULTS[k])

    def execute(self, MF, do_restart = False):
        MF.cmd.type(f"init_lapw -m", 1)

        if(do_restart):
            MF.cmd.type("r", 0.5)

        MF.cmd.type(self.text_params["reduction_percentage"], 0.5)
        MF.cmd.type(self.text_params["scheme"], 0.5)
        MF.cmd.type(self.text_params["accept_radii"], 0.5)
        MF.cmd.type(self.text_params["nearest_neighbor"], 0.5)
        MF.cmd.type("^X", 1, do_ENTER=False)

        if "DO YOU WANT TO USE THE NEW" in "\n".join(MF.cmd.read_output(10)):
            MF.cmd.type("n", 0.5)

            # TODO: get this working for cell simplification
            # MF.cmd.type("y", 0.5)
            # MF.cmd.type(self.text_params["nearest_neighbor"], 0.5)
            # MF.cmd.type("^X", 1, do_ENTER=False)

        MF.cmd.type("c", 1)
        MF.cmd.type("^X", 1, do_ENTER=False)
        MF.cmd.type("c", 1)
        MF.cmd.type("^X", 1, do_ENTER=False)
        MF.cmd.type("c", 1)

        if "STOP: YOU MUST MOVE THE ORIGIN OF THE UNIT CELL" in "\n".join(MF.cmd.read_output(10)):
            # TODO: moving around cell origin if necessary
            pass

        MF.cmd.type(self.text_params["lstart_flag"], 0.5)
        if self.text_params["lstart_flag"] == "-ask":
            for i in range(MF.structure.non_eq_count):
                MF.cmd.type(
                    self.text_params["x_ask_flags_pattern"][
                        i % self.text_params["x_ask_flags_pattern"].__len__()
                    ],
                    0.2,
                )
        MF.cmd.type(self.text_params["calculation_method"], 0.5)
        MF.cmd.type(self.text_params["separation_energy_eV"], 0.5)
        MF.cmd.type("^X", 1, do_ENTER=False)
        MF.cmd.type("c", 1)
        MF.cmd.type("^X", 1, do_ENTER=False)
        MF.cmd.type("^X", 1, do_ENTER=False)

        MF.cmd.type(self.text_params["kpoints"], 0.5)
        if self.text_params["kpoints"] == "-1":
            MF.cmd.type(self.text_params["x_kdensity"], 0.5)
        MF.cmd.type(self.text_params["kshift"], 0.5)
        MF.cmd.type("^X", 1, do_ENTER=False)
        MF.cmd.type("c", 1)
        MF.cmd.type("^X", 1, do_ENTER=False)

        MF.cmd.type(self.text_params["spin_polarized"], 0.5)
        MF.cmd.type("^X", 1, do_ENTER=False)
        MF.cmd.type("^X", 1, do_ENTER=False)
        if self.text_params["spin_polarized"] == "y":
            MF.cmd.type(self.text_params["x_antiferromagnetic"], 0.5)


class init_so_lapw_Parameters:
    DEFAULTS = {
        "h": 0,
        "k": 0,
        "l": 1,
        "ignored_atoms": [],
        "EMAX": 5.0,
        "RLOs": "n",
        "x_chosen_RLOs_pattern": [],
        "spin_polarized": init_lapw_Parameters.DEFAULTS["spin_polarized"],
        "x_use_SO_structure": True,
        "x__kpoints": init_lapw_Parameters.DEFAULTS["kpoints"],
        "init_lapw_params": init_lapw_Parameters(),
    }

    def __init__(
        self,
        h: int = None,
        k: int = None,
        l: int = None,
        ignored_atoms=None,
        EMAX: float = None,
        RLOs=None,
        x_chosen_RLOs_pattern=None,
        spin_polarized: bool = None,
        x_use_SO_structure: bool = None,
        x__kpoints: int = None,
        init_lapw_params: init_lapw_Parameters = None,
    ):
        # save copies of everything
        self.h = h
        self.k = k
        self.l = l
        self.ignored_atoms = ignored_atoms
        self.EMAX = EMAX
        self.RLOs = RLOs
        self.x_chosen_RLOs_pattern = x_chosen_RLOs_pattern
        self.spin_polarized = spin_polarized
        self.x_use_SO_structure = x_use_SO_structure
        self.x__kpoints = x__kpoints
        self.init_lapw_params = init_lapw_params

        args = locals()

        # the defaulted raw parameters
        self.raw_params = {}
        # the stringified parameters (except for x_ask_flags_pattern)
        self.text_params = {}

        for key in args:
            # use the default param values if nothing else was specified
            if args[key] == None:
                self.raw_params[key] = init_so_lapw_Parameters.DEFAULTS[key]
            else:
                self.raw_params[key] = args[key]

        # transfer sp init_lapw_params
        if init_lapw_params == None:
            if spin_polarized == None:
                self.raw_params["spin_polarized"] = init_so_lapw_Parameters.DEFAULTS[
                    "spin_polarized"
                ]
            else:
                self.raw_params["spin_polarized"] = spin_polarized
        else:
            self.raw_params["spin_polarized"] = init_lapw_params.raw_params[
                "spin_polarized"
            ]

        # transfer kpoints from init_lapw_params
        if init_lapw_params == None:
            if x__kpoints == None:
                self.raw_params["x__kpoints"] = init_so_lapw_Parameters.DEFAULTS[
                    "x__kpoints"
                ]
            else:
                self.raw_params["x__kpoints"] = x__kpoints
        else:
            self.raw_params["x__kpoints"] = init_lapw_params.raw_params["kpoints"]

        for key in self.raw_params:
            # handle floats
            if key in ["EMAX"]:
                self.text_params[key] = str(float(self.raw_params[key]))

            # handle ints
            if key in ["h", "k", "l", "x__kpoints"]:
                self.text_params[key] = str(int(self.raw_params[key]))

            # handle y/n bools
            if key in ["x_use_SO_structure", "spin_polarized"]:
                if self.raw_params[key]:
                    self.text_params[key] = "y"
                else:
                    self.text_params[key] = "n"

            # handle array concat
            if key in ["ignored_atoms"]:
                self.text_params[key] = ",".join(self.raw_params[key])

            # handle array
            if key in ["x_chosen_RLOs_pattern"]:
                self.text_params[key] = lmap(
                    self.raw_params[key],
                    lambda v: ("y" if v in [True, "y", "Y"] else "n"),
                )

            # RLOs
            if key in ["RLOs"]:
                if self.raw_params[key] in ["none", "n", "None", "N"]:
                    self.text_params[key] = "n"
                if self.raw_params[key] in ["all", "a", "All", "A"]:
                    self.text_params[key] = "a"
                if self.raw_params[key] in ["choose", "c", "Choose", "C"]:
                    self.text_params[key] = "c"

    def reinstantiate(self, replacement_init_lapw_params: init_lapw_Parameters):
        return init_so_lapw_Parameters(
            self.h,
            self.k,
            self.l,
            self.ignored_atoms,
            self.EMAX,
            self.RLOs,
            self.x_chosen_RLOs_pattern,
            self.spin_polarized,
            self.x_use_SO_structure,
            self.x__kpoints,
            init_lapw_params=replacement_init_lapw_params,
        )

    def execute(self, MF):
        MF.cmd.type(f"init_so_lapw", 1)

        MF.cmd.type(
            f"{self.text_params['h']} {self.text_params['k']} {self.text_params['l']}",
            0.5,
        )
        MF.cmd.type(self.text_params["ignored_atoms"], 0.5)
        MF.cmd.type(self.text_params["EMAX"], 0.5)
        MF.cmd.type(self.text_params["RLOs"], 0.5)

        if self.text_params["RLOs"] == "c":
            for i in range(MF.structure.non_eq_count):
                MF.cmd.type(
                    self.text_params["x_chosen_RLOs_pattern"][
                        i % self.text_params["x_chosen_RLOs_pattern"].__len__()
                    ],
                    0.2,
                )
        MF.cmd.type("^X", 1, do_ENTER=False)
        MF.cmd.type("^X", 1, do_ENTER=False)

        MF.cmd.type(self.text_params["spin_polarized"], 0.5)
        if self.text_params["spin_polarized"] == "y":
            MF.cmd.type("^X", 1, do_ENTER=False)
            MF.cmd.type(self.text_params["x_use_SO_structure"], 0.5)

            if self.text_params["x_use_SO_structure"] == "y":
                MF.cmd.type(self.text_params["x__kpoints"], 0.5)
                MF.cmd.type("^X", 1, do_ENTER=False)
                MF.cmd.type("n", 0.5)


class UJ_Parameters:

    @staticmethod
    def atom(index, orbitals=[], r_id=0, l_s_id=0):
        return {
            "index": index,
            "orbitals": orbitals,
            "r_index": r_id,
            "l_s_index": l_s_id,
        }

    def __init__(self, U, J, atoms, nsic=1, cutoff_energy=-12.0):
        # atoms = [
        #     {
        #         index: int,
        #         orbitals: ["s", "p", "d", "f", "g", "h", "i"] # if none are given, only the highest available for that atom will be picked
        #         r_index: int # 0 by default
        #         l_s_index: int # 0 by default
        #     } ...
        # ]

        self.U = U
        self.J = J
        self.atoms = atoms
        self.nsic = nsic
        self.cutoff_energy = cutoff_energy

        self.atoms_complete = []
        for atom in self.atoms:
            orbs = atom["orbitals"]
            if len(atom["orbitals"]) == 0:
                # TODO: if none are given, only the highest available for that atom will be picked
                # for that use this:
                # https://mendeleev.readthedocs.io/en/stable/notebooks/electronic_configuration.html
                orbs = []
                pass

            self.atoms_complete.append(
                {
                    "index": int(atom["index"]),
                    "orbitals": orbs,
                    "r_index": sorted([0, int(atom["r_index"]), 3])[1],
                    "l_s_index": sorted([0, int(atom["l_s_index"]), 5])[1],
                }
            )

        parsed_atoms = []
        for atom in self.atoms_complete:
            parsed_atoms.append(
                {
                    "index": str(atom["index"]),
                    "orbitals": lmap(
                        orbs,
                        lambda orb: str(
                            int(["s", "p", "d", "f", "g", "h", "i"].index(orb))
                        ),
                    ),
                    "r_index": str(atom["r_index"]),
                    "l_s_index": str(atom["l_s_index"]),
                }
            )

        self.inorb_text = "\n".join(
            [
                f"  1  {len(parsed_atoms)}  0",
                "PRATT,1.0",
                "\n".join(
                    lmap(
                        parsed_atoms,
                        lambda at:  f'{at["index"]} {len(at["orbitals"])} {" ".join(at["orbitals"])}',
                    )
                ),
                f"  {nsic}",
                "\n".join(
                    lmap(
                        parsed_atoms,
                        lambda at:  f"{self.U * Constants.eV_to_Ry} {self.J * Constants.eV_to_Ry}             U J (Ry)",
                    )
                ),
            ]
        )

        self.indmc_text = "\n".join(
            [
                f"{self.cutoff_energy}",
                f" {len(parsed_atoms)}",
                "\n".join(
                    lmap(
                        parsed_atoms,
                        lambda at: f' {at["index"]}  {len(at["orbitals"])}  {" ".join(at["orbitals"])}',
                    )
                ),
                "\n".join(
                    lmap(
                        parsed_atoms,
                        lambda at: f' {at["r_index"]} {at["l_s_index"]}',
                    )
                ),
            ]
        )

    def execute(self, MF):
        inorb_path = f"{MF.material}{rng_string(16)}.inorb"
        with open(inorb_path, "w") as f:
            f.write(self.inorb_text)
        indmc_path = f"{MF.material}{rng_string(16)}.indmc"
        with open(indmc_path, "w") as f:
            f.write(self.indmc_text)

        MF.scp.upload_file(inorb_path, f"{MF.material}.inorb")
        MF.scp.upload_file(indmc_path, f"{MF.material}.indmc")

        time.sleep(1)

        os.remove(inorb_path)
        os.remove(indmc_path)
