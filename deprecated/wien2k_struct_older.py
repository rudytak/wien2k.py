from wien2_helper import *

import re, mendeleev, itertools
import numpy as np


class StructureFile:
    def __init__(self, filepath):
        self.filepath = filepath

        with open(self.filepath, "r+") as reader:
            self.original = reader.read()
            self.lines_original = self.original.split("\n")

        # TODO: more robust loading by just getting all the numbers??
        # ------------ CAN'T BE TWEAKED ------------
        self.unique_atom_count = re.findall(r"ATOM.*-\d:", self.original).__len__()
        self.atom_count = re.findall(r"X.*Y.*Z.*", self.original).__len__()

        # ------------ CAN BE TWEAKED ------------
        self.tweak_logs = []
        # get the a,b,c dimensions from the struct in bohr radii
        self.a, self.b, self.c, self.alpha, self.beta, self.gamma = lmap(
            lfilt(
                re.findall(r"((\d*\.\d* *){6})", self.original)[0][0].split(" "),
                lambda ch: ch != "",
            ),
            float,
        )

        # get all the atom info
        self.atoms = []
        atom_groups = re.findall(
            r"ATOM\s+-\d[\S\s]*?Z:\s+\d*\.\d*", self.original, flags=re.S
        )

        # get all the roatation matrices
        rot_matrices = re.findall(
            r"LOCAL ROT MATRIX:(?:(?:\s*\d*\.\d*\s*){3}){3}", self.original, re.S
        )
        # format them into 3D float arrays
        rot_matrices = lmap(
            rot_matrices,
            lambda rm: re.sub(
                r"[\\n]*\s+", ",", rm.replace("LOCAL ROT MATRIX:", "").strip()
            ),
        )
        rot_matrices = lmap(
            rot_matrices,
            lambda rm: np.asarray(lmap(rm.split(","), float)).reshape(3, 3).tolist(),
        )

        # go through each atom group
        for i in range(len(atom_groups)):
            group = atom_groups[i]
            atomic_number = int(re.findall(r"Z:\s+(\d*)", group)[0])
            rot_matrix = rot_matrices[i]
            symbol = mendeleev.element(atomic_number).symbol
            NPT = int(re.findall(r"NPT=\s*(\d*\.?\d*)", group)[0])
            R0 = float(re.findall(r"R0=\s*(\d*\.\d*)", group)[0])
            RMT = float(re.findall(r"RMT=\s*(\d*\.\d*)", group)[0])
            ISPLIT = int(re.findall(r"ISPLIT=\s*(\d*\.?\d*)", group)[0])

            # find all the atom positions in that group
            atoms_iter = re.finditer(
                r"X=(\d*\.\d*)\s+Y=(\d*\.\d*)\s+Z=(\d*\.\d*)", group
            )
            while True:
                try:
                    # and save an instance of each atom
                    m = next(atoms_iter)
                    self.atoms.append(
                        {
                            "x": float(m.group(1)),  # save the atom's position
                            "y": float(m.group(2)),
                            "z": float(m.group(3)),
                            "rot_matrix": rot_matrix,  # rotation
                            "atomic_number": atomic_number,  # and atomic number
                            "symbol": symbol,
                            "NPT": NPT,
                            "R0": R0,
                            "RMT": RMT,
                            "ISPLIT": ISPLIT,
                        }
                    )
                except:
                    break

    # --------------- TWEAKING ---------------
    # TODO: add more possible tweaks: lattice type, calc mode, symmetry operations

    def tweak_dimensions(
        self, a=None, b=None, c=None, alpha=None, beta=None, gamma=None
    ):
        """Change the structure dimensions (inputs in bohr radii)."""
        if a != None:
            self.tweak_logs.append(f"Cell dimension: a : {self.a} -> {a}")
            self.a = a
        if b != None:
            self.tweak_logs.append(f"Cell dimension: b : {self.b} -> {b}")
            self.b = b
        if c != None:
            self.tweak_logs.append(f"Cell dimension: c : {self.c} -> {c}")
            self.c = c
        if alpha != None:
            self.tweak_logs.append(f"Cell dimension: alpha : {self.alpha} -> {alpha}")
            self.alpha = alpha
        if beta != None:
            self.tweak_logs.append(f"Cell dimension: beta : {self.beta} -> {beta}")
            self.beta = beta
        if gamma != None:
            self.tweak_logs.append(f"Cell dimension: gamma : {self.gamma} -> {gamma}")
            self.gamma = gamma

    def tweak_atom(
        self,
        index,
        x=None,
        y=None,
        z=None,
        atomic_number=None,
        rot_matrix=None,
        NPT=None,
        R0=None,
        RMT=None,
        ISPLIT=None,
    ):
        if index >= len(self.atoms) or index < 0:
            raise Exception(
                "Atom index out of range (indexing is from 0 in the order as in the struct file)."
            )

        if x != None:
            self.tweak_logs.append(f"Atom {index}: x : {self.atoms[index]['x']} -> {sorted([0.0, x, 1.0])[1]}")
            self.atoms[index]["x"] = sorted([0.0, x, 1.0])[
                1
            ]  # clamp between 0-1 so that the atom is kep inside the cell
        if y != None:
            self.tweak_logs.append(f"Atom {index}: y : {self.atoms[index]['y']} -> {sorted([0.0, y, 1.0])[1]}")
            self.atoms[index]["y"] = sorted([0.0, y, 1.0])[
                1
            ]  # clamp between 0-1 so that the atom is kep inside the cell
        if z != None:
            self.tweak_logs.append(f"Atom {index}: z : {self.atoms[index]['z']} -> {sorted([0.0, z, 1.0])[1]}")
            self.atoms[index]["z"] = sorted([0.0, z, 1.0])[
                1
            ]  # clamp between 0-1 so that the atom is kep inside the cell
        if atomic_number != None:
            nsymb = mendeleev.element(atomic_number).symbol

            self.tweak_logs.append(f"Atom {index}: Z : {self.atoms[index]['atomic_number']} -> {atomic_number}")
            self.tweak_logs.append(f"Atom {index}: Symbol : {self.atoms[index]['symbol']} -> {nsymb}")

            self.atoms[index]["atomic_number"] = atomic_number
            self.atoms[index]["symbol"] = nsymb
        if rot_matrix != None:
            self.atoms[index]["rot_matrix"] = (
                np.asarray(rot_matrix).reshape(3, 3).tolist()
            )
        if NPT != None:
            if int(NPT) % 2 != 1:
                raise Exception(
                    "NPT is not odd. Check http://www.wien2k.at/reg_user/textbooks/usersguide.pdf page 43 for more info."
                )
            self.tweak_logs.append(f"Atom {index}: NPT : {self.atoms[index]['NPT']} -> {int(NPT)}")
            self.atoms[index]["NPT"] = int(NPT)
        if R0 != None:
            self.tweak_logs.append(f"Atom {index}: R0 : {self.atoms[index]['R0']} -> {int(R0)}")
            self.atoms[index]["R0"] = R0
        if RMT != None:
            self.tweak_logs.append(f"Atom {index}: RMT : {self.atoms[index]['RMT']} -> {int(RMT)}")
            self.atoms[index]["RMT"] = RMT
        if ISPLIT != None:
            if int(ISPLIT) not in [0, 1, 2, 3, 4, 5, 6, 7, 8, -2, 88, 99]:
                raise Exception(
                    "Invalid ISPLIT option. Check http://www.wien2k.at/reg_user/textbooks/usersguide.pdf page 43 for more info."
                )
            self.tweak_logs.append(f"Atom {index}: ISPLIT : {self.atoms[index]['ISPLIT']} -> {int(ISPLIT)}")
            self.atoms[index]["ISPLIT"] = int(ISPLIT)
        else:
            # nothing changed
            pass

        return self.atoms[index]

    # --------------- OUTPUT ---------------

    def get_text(self):
        # returns the .struct file with tweaks done to it
        # currently possible tweaks are:
        #   a,b,c dimensions
        #   atom types
        #   atom x,y,z positions (not accounting for rotation matrix)

        # create a copy of the structu file text
        copy = self.original

        # 1. CHANGE CELL DIMENSIONS
        # first get the line at which the cell dimensions are written
        copy, _ = nested_regex_replace(
            copy,
            [
                r".*(?:\d*\.\d* *){6}",  # find the row containing the cell parameters
                r"\d*\.\d*",  # find the individual numbers
            ],
            [self.a, self.b, self.c, self.alpha, self.beta, self.gamma],
        )

        # 2. CHANGE ATOMS

        # group the atoms by: atomic number, rotational matrix, NPT, R0, RMT, ISPLIT
        groups = {}

        for a in self.atoms:
            # createa a unique string identifiedr representing all the grouping values
            g_uid = ";".join(
                lmap(
                    [
                        "rot_matrix",
                        "atomic_number",
                        "symbol",
                        "NPT",
                        "R0",
                        "RMT",
                        "ISPLIT",
                    ],
                    lambda key: str(a[key]),
                )
            )

            # create a group if didn't exist yet
            if g_uid not in groups:
                groups[g_uid] = []

            # save the atom to the group
            groups[g_uid].append(a)

        total_atom_text = ""
        g_num_id = 0
        for g_uid in groups.keys():
            g_num_id += 1
            group = groups[g_uid]
            repre = group[0]

            # create a template for the atom group and put in some basic values
            template = "\n".join(
                [
                    f"""ATOM  -{g_num_id}: X=0.00000000 Y=0.00000000 Z=0.00000000
          MULT= 0          ISPLIT= 0""",
                    "\n".join(
                        [
                            f"      -{g_num_id}: X=0.00000000 Y=0.00000000 Z=0.00000000"
                            for a in group[1:]
                        ]
                    ),
                    f"""{repre["symbol"]}         NPT=  000  R0=0.00000000 RMT= 2.50000     Z:  {int(repre["atomic_number"])}.00000
LOCAL ROT MATRIX:    0.0000000 0.0000000 0.0000000
                     0.0000000 0.0000000 0.0000000
                     0.0000000 0.0000000 0.0000000""",
                ]
            ).replace("\n\n", "\n")

            # now put in the rest of the values using nested regex
            # atom positions
            template, _ = nested_regex_replace(
                template,
                [
                    r"ATOM\s+-\d*[\S\s]*?Z:\s+\d*\.\d*",  # find the atom group
                    r"X=(?:\d*\.\d*)\s+Y=(?:\d*\.\d*)\s+Z=(?:\d*\.\d*)",  # find the row with x, y, z
                    r"\d*\.\d*",  # find the individual numbers
                ],
                list(
                    itertools.chain.from_iterable(
                        lmap(group, lambda a: [a["x"], a["y"], a["z"]])
                    )
                ),  # flatten all the atom positions
            )

            template, _ = nested_regex_replace(
                template,
                [
                    r"LOCAL ROT MATRIX:(?:(?:\s*\d*\.\d*\s*){3}){3}",  # find rotation matrix
                    r"\d*\.\d*",  # find the individual numbers
                ],
                list(
                    itertools.chain.from_iterable(repre["rot_matrix"])
                ),  # flatten the matrix
            )

            # NPT, R0, RMT, ISPLIT, MULT
            template, _ = nested_regex_replace(
                template, [r"NPT=\s*(?:\d*\.?\d*)", r"\d+\.?\d*"], [repre["NPT"]]
            )
            template, _ = nested_regex_replace(
                template, [r"R0=\s*(?:\d*\.\d*)", r"\d*\.\d*"], [f"{repre['R0']:.99f}"[1:]]
            )
            template, _ = nested_regex_replace(
                template, [r"RMT=\s*(?:\d*\.\d*)", r"\d*\.\d*"], [repre["RMT"]]
            )
            template, _ = nested_regex_replace(
                template, [r"ISPLIT=\s*(?:\d*\.?\d*)", r"\d+\.?\d*"], [repre["ISPLIT"]]
            )
            template, _ = nested_regex_replace(
                template, [r"MULT=\s*(?:\d*\.?\d*)", r"\d+\.?\d*"], [len(group)]
            )

            total_atom_text += template + "\n"

        # save the whole atom block to the copied file structure
        copy, _ = nested_regex_replace(
            copy,
            [
                r".*(?:\d*\.\d* *){6}[\S\s]*NUMBER OF SYMMETRY OPERATIONS",  # find the row containing the cell parameters
                r"$[\S\s]*^",  # find the individual numbers,
            ],
            [f"\n{total_atom_text}\n"],
            keep_len=False,
        )

        # MORE CHANGES COMING LATER
        # TODO: add more possible tweaks: lattice type, calc mode, symmetry operations

        return copy
    
    def get_logs(self, do_print = True):
        if do_print:
            print(self.get_logs(do_print=False))
        return "\n".join(self.tweak_logs)
