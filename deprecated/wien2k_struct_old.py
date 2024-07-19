from wien2_helper import *

import mendeleev
import numpy as np
import re

from pyxtal.lattice import para2matrix
import spglib


class StructureSymmetryOperation:
    def __init__(self, rot_matrix, translation_vector):
        self.rot_matrix = np.asarray(rot_matrix).tolist()
        self.translation_vector = np.asarray(translation_vector).tolist()

    @staticmethod
    def generate_all_atoms_from_symmetries(
        unique_atoms, symmetry_operations, precision_pos=5, precision_mag=6, depth=1
    ):
        atom_collections = []

        def get_symmetrized_posmags(pos, mag, symmetry_operations):
            output = []
            for symm in symmetry_operations:
                pos_new = np.matmul(symm.rot_matrix, pos) + np.asarray(
                    symm.translation_vector
                )
                mag_new = np.matmul(symm.rot_matrix, mag)

                # normalize the position to the 0-1 range
                pos_new = lmap(pos_new, lambda coord: (coord + 100) % 1)

                output.append((pos_new, mag_new))

            return output

        for i in range(len(unique_atoms)):
            at = unique_atoms[i]
            atom_collections.append(set())

            pos = (at.x, at.y, at.z)
            mag = at.get_precise_magnetization()

            pos_mags = [(pos, mag)]
            for d in range(depth):
                for pos_mag in pos_mags:
                    new_possibilities = get_symmetrized_posmags(
                        pos_mag[0], pos_mag[1], symmetry_operations
                    )
                pos_mags += new_possibilities

            for pos_mag in pos_mags:
                pos_text = ",".join(
                    lmap(pos_mag[0], lambda coord: format(coord, f".{precision_pos}f"))
                )

                mag_text = ",".join(
                    lmap(pos_mag[1], lambda coord: format(coord, f".{precision_mag}f"))
                )
                atom_collections[i].add(f"{pos_text},{mag_text}")

        for i in range(len(atom_collections)):
            at = unique_atoms[i]

            def parse(pos_mag):
                x, y, z, mx, my, mz = lmap(pos_mag.split(","), float)
                return StructureAtom(
                    x,
                    y,
                    z,
                    at.Z,
                    at.rot_matrix,
                    at.NPT,
                    at.R0,
                    at.RMT,
                    at.ISPLIT,
                    [mx, my, mz],
                )

            atom_collections[i] = lmap(atom_collections[i], parse)

        return flatten(atom_collections)


class StructureAtom:
    def __init__(
        self,
        x,
        y,
        z,
        Z,
        rot_matrix=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        NPT=781,
        R0=0.00001,
        RMT=2.4,  # TODO: automatically determine default RMT for each atom from a table
        ISPLIT=8,
        magnetization_vector=None,
        magnetization_precise_magnitude=None,
    ):
        self.x = x
        self.y = y
        self.z = z

        self.rot_matrix = np.asarray(rot_matrix).reshape(3, 3).tolist()

        self.Z = Z
        self.NPT = NPT
        self.R0 = R0
        self.RMT = RMT
        self.ISPLIT = ISPLIT

        # magnetization parsing
        self.magnetization_vector = np.asarray(magnetization_vector)

        # magnitude stting
        if magnetization_precise_magnitude != None:
            self.magnetization_magnitude = magnetization_precise_magnitude
        else:
            if (
                magnetization_vector != None
                and np.linalg.norm(self.magnetization_vector) != 0
            ):
                self.magnetization_magnitude = np.linalg.norm(self.magnetization_vector)
            else:
                self.magnetization_magnitude = 0

        # unit vector setting
        if (
            magnetization_vector != None
            and np.linalg.norm(self.magnetization_vector) != 0
        ):
            self.magnetization_unit_vector = self.magnetization_vector / np.linalg.norm(
                self.magnetization_vector
            )
        else:
            self.magnetization_unit_vector = [1, 0, 0]

    def get_symbol(self):
        return mendeleev.element(int(self.Z)).symbol

    def get_precise_magnetization(self):
        return np.asarray(self.magnetization_unit_vector) * self.magnetization_magnitude

    def get_uid(self):
        return ";".join(
            lmap(
                ["rot_matrix", "Z", "NPT", "R0", "RMT", "ISPLIT"],
                lambda key: str(getattr(self, key)),
            )
        )

    def __repr__(self):
        return f"<wien2k_struct.StructureAtom {self.x} {self.y} {self.z} {self.Z}>"

    def __str__(self):
        return f"<wien2k_struct.StructureAtom {self.x} {self.y} {self.z} {self.Z}>"


class StructureFile:
    # --------------- LINE FORMATTING ---------------
    # A = any, I = integer, F = float, X = empty spaces
    LINE_FORMATS = [
        None,  # indexing from 1 offset
        "A80",  # 1: title line (any)
        "A4,23X,I3",  # 2: lattice type (??) and non-equivalent atoms count
        "13X,A4",  # 3: calculation mode (RELA/NREL)
        "6F10.6",  # 4: unit parameters a,b,c,alpha,beta,gamma
        "4X,I4,4X,F10.8,3X,F10.8,3X,F10.8",  # 5: atom index, x, y, z
        "15X,I2,17X,I2",  # 6: MULT, ISPLIT
        "A10,5X,I5,5X,F10.8,5X,F10.5,5X,F10.5",  # 7: atom symbol [3 for non-equiv number, 4-10 for other labeling], NPT, R0, RMT, Z
        "20X,3F10.7",  # 8: rotational matrix line 1
        "20X,3F10.7",  # 9: rotational matrix line 2
        "20X,3F10.7",  # 10: rotational matrix line 3
        "I4",  # 11: number of symmetry operations,
        "3I2,F10.7",  # 12: operation matrix line1, translation vector x
        "3I2,F10.7",  # 13: operation matrix line2, translation vector y
        "3I2,F10.7",  # 14: operation matrix line3, translation vector z
        "I8",  # 15: above symmetry operation index
        "F16.14,1X,F16.14,1X,F16.14",  # 16: Precise positions (optional, free form)
    ]

    @staticmethod
    def apply_format(form, replaces):
        instructions = form.split(",")

        line = ""
        rid = 0
        for instruction in instructions:
            repetitions = 1
            try:
                repetitions = int(re.split(r"[AIFX]", instruction)[0])
            except:
                pass

            val_type = "X"
            char_count = 0
            precision = 0

            try:
                val_type = re.findall(r"[AIFX]", instruction)[0]
            except:
                pass
            try:
                _match = re.split(r"[AIFX]", instruction)[1]

                if "." in _match:
                    char_count = int(_match.split(".")[0])
                    precision = int(_match.split(".")[1])
                else:
                    char_count = int(_match)
            except:
                pass

            for r in range(repetitions):
                if val_type == "A":
                    line += (replaces[rid] + 100 * " ")[0:char_count]
                if val_type == "I":
                    line += (100 * " " + str(int(replaces[rid])))[-char_count:]
                if val_type == "F":
                    line += (100 * " " + format(replaces[rid], f".{precision}f"))[
                        -char_count:
                    ]
                if val_type == "X":
                    line += " "
                    rid -= 1
                    pass

                rid += 1

        return line + "\n"

    @staticmethod
    def parse_format(form, line):
        instructions = form.split(",")
        types = []

        _regex = "^"
        for instruction in instructions:
            repetitions = 1
            try:
                repetitions = int(re.split(r"[AIFX]", instruction)[0])
            except:
                pass

            val_type = "X"
            char_count = 0
            precision = 0

            try:
                val_type = re.findall(r"[AIFX]", instruction)[0]
            except:
                pass
            try:
                _match = re.split(r"[AIFX]", instruction)[1]

                if "." in _match:
                    char_count = int(_match.split(".")[0])
                    precision = int(_match.split(".")[1])
                else:
                    char_count = int(_match)
            except:
                pass

            if val_type == "X":
                _regex += f".{{{repetitions}}}"
            else:
                types += [val_type] * repetitions

                if val_type == "A":
                    _regex += f"(.{{0,{char_count}}})" * repetitions
                elif val_type == "I":
                    _regex += f"([-\s\d]{{{char_count}}})" * repetitions
                elif val_type == "F":
                    _regex += f"([-\s\d\.]{{{char_count}}})" * repetitions

        finds = re.findall(_regex, line)
        if len(types) > 1:
            finds = flatten(finds)

        output = []
        for i in range(len(finds)):
            find = finds[i].strip()
            if types[i] == "A":
                output.append(find)
            elif types[i] == "I":
                output.append(int(find))
            elif types[i] == "F":
                output.append(float(find))

        return output

    # --------------- CREATION ---------------

    def __init__(
        self,
        title,
        lattice_type,
        atoms,
        a,
        b=None,
        c=None,
        alpha=90.0,
        beta=90.0,
        gamma=90.0,
        calc_mode="RELA",
    ):
        # file load variables
        self.filepath = ""
        self.original = None

        # log of all tweaks done
        self.tweak_logs = []

        # general info
        self.title = title

        # lattice
        if lattice_type not in ["P", "F", "B", "CXY", "CYZ", "CXZ", "R", "H"]:
            raise Exception("Invalid lattice type")
        self.lattice_type = lattice_type

        # MODE:
        # RELA fully relativistic core and scalar relativistic valence
        # NREL non-relativistic calculation
        self.calc_mode = "RELA" if calc_mode.lower() == "rela" else "NREL"

        # dimensions
        self.a = a
        self.b = b if b is not None else a
        self.c = c if c is not None else a

        self.cell_multiples = {
            "a": 1,
            "b": 1,
            "c": 1,
        }

        # angles
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

        # atomic info
        self.atoms = atoms

        # TODO: actually figure out the symmetry operations sometime
        # write_symmetry_ops = False will keep the symmetrization process up to wien2k during initialization
        # getting symmetries will be attempted either way though
        self.write_symmetry_ops = False

        # symmetry operations
        self.non_eq_count = 0
        self.equivalent_atoms = []

        # spacegroup
        self.spacegroup_symbol = ""
        self.spacegroup_number = 0

        # symmtery operations
        # https://pyxtal.readthedocs.io/en/latest/Background.html#symmetry-operations
        self.symmetry_ops = []
        self.update_symmetry()

    @staticmethod
    def load(filepath):
        with open(filepath, "r+") as reader:
            original_text = reader.read()

        # TODO: loading in existing files
        lines = original_text.split("\n")

        [title] = StructureFile.parse_format(
            StructureFile.LINE_FORMATS[1], lines.pop(0)
        )
        [lattice_type, non_eq] = StructureFile.parse_format(
            StructureFile.LINE_FORMATS[2], lines.pop(0)
        )
        [calc_mode] = StructureFile.parse_format(
            StructureFile.LINE_FORMATS[3], lines.pop(0)
        )
        [a, b, c, alpha, beta, gamma] = StructureFile.parse_format(
            StructureFile.LINE_FORMATS[4], lines.pop(0)
        )

        unique_atoms = []
        for i in range(non_eq):
            [id, x, y, z] = StructureFile.parse_format(
                StructureFile.LINE_FORMATS[5], lines.pop(0)
            )
            [mult, ISPLIT] = StructureFile.parse_format(
                StructureFile.LINE_FORMATS[6], lines.pop(0)
            )

            atom_positions = []
            atom_positions.append((x, y, z))

            for j in range(mult - 1):
                [id, x, y, z] = StructureFile.parse_format(
                    StructureFile.LINE_FORMATS[5], lines.pop(0)
                )
                atom_positions.append((x, y, z))

            [symb, NPT, R0, RMT, Z] = StructureFile.parse_format(
                StructureFile.LINE_FORMATS[7], lines.pop(0)
            )

            rot_matrix = [
                StructureFile.parse_format(StructureFile.LINE_FORMATS[8], lines.pop(0)),
                StructureFile.parse_format(StructureFile.LINE_FORMATS[9], lines.pop(0)),
                StructureFile.parse_format(
                    StructureFile.LINE_FORMATS[10], lines.pop(0)
                ),
            ]

            for pos in atom_positions:
                unique_atoms.append(
                    StructureAtom(
                        pos[0], pos[1], pos[2], Z, rot_matrix, NPT, R0, RMT, ISPLIT
                    )
                )

        [symm_ops_count] = StructureFile.parse_format(
            StructureFile.LINE_FORMATS[11], lines.pop(0)
        )
        symm_ops = []

        for i in range(symm_ops_count):
            [m1, m2, m3, v1] = StructureFile.parse_format(
                StructureFile.LINE_FORMATS[12], lines.pop(0)
            )
            [m4, m5, m6, v2] = StructureFile.parse_format(
                StructureFile.LINE_FORMATS[13], lines.pop(0)
            )
            [m7, m8, m9, v3] = StructureFile.parse_format(
                StructureFile.LINE_FORMATS[14], lines.pop(0)
            )

            symm_ops.append(
                StructureSymmetryOperation(
                    [[m1, m2, m3], [m4, m5, m6], [m7, m8, m9]], [v1, v2, v3]
                )
            )

            symm_op_id = StructureFile.parse_format(
                StructureFile.LINE_FORMATS[15], lines.pop(0)
            )

        all_atoms = StructureSymmetryOperation.generate_all_atoms_from_symmetries(
            unique_atoms, symm_ops
        )

        # precise positions can be ignored for now
        # TODO: load precise positions??

        return StructureFile(
            title, lattice_type, all_atoms, a, b, c, alpha, beta, gamma, calc_mode
        )

    # --------------- TWEAKING ---------------

    def add_tweak_message(self, message):
        self.tweak_logs.append(message)

    def tweak_lattice_type(self, new_lattice_type):
        # lattice
        old_type = self.lattice_type
        if new_lattice_type not in ["P", "F", "B", "CXY", "CYZ", "CXZ", "R", "H"]:
            self.add_tweak_message(
                f"LATTICE TYPE : FAILED :  {old_type} -X-> {new_lattice_type}"
            )
            raise Exception("Invalid lattice type")
        self.lattice_type = new_lattice_type

        # add tweak message
        self.add_tweak_message(f"LATTICE TYPE : {old_type} -> {self.lattice_type}")

    def tweak_calculation_mode(self, new_mode):
        old_mode = self.calc_mode
        self.calc_mode = "RELA" if new_mode.lower() == "rela" else "NREL"

        # add tweak message
        self.add_tweak_message(f"CALC MODE : {old_mode} -> {self.calc_mode}")

    def tweak_dimensions(
        self, a=None, b=None, c=None, alpha=None, beta=None, gamma=None
    ):
        """Change the structure dimensions (inputs in bohr radii)."""
        if a != None:
            self.add_tweak_message(f"Cell dimension: a : {self.a} -> {a}")
            self.a = a
        if b != None:
            self.add_tweak_message(f"Cell dimension: b : {self.b} -> {b}")
            self.b = b
        if c != None:
            self.add_tweak_message(f"Cell dimension: c : {self.c} -> {c}")
            self.c = c
        if alpha != None:
            self.add_tweak_message(f"Cell dimension: alpha : {self.alpha} -> {alpha}")
            self.alpha = alpha
        if beta != None:
            self.add_tweak_message(f"Cell dimension: beta : {self.beta} -> {beta}")
            self.beta = beta
        if gamma != None:
            self.add_tweak_message(f"Cell dimension: gamma : {self.gamma} -> {gamma}")
            self.gamma = gamma

        self.update_symmetry()

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
            self.add_tweak_message(f"Atom {index}: FAILED : INVALID INDEX")
            raise Exception(
                "Atom index out of range (indexing is from 0 in the order as in the struct file)."
            )

        if x != None:
            self.add_tweak_message(
                f"Atom {index}: x : {self.atoms[index]['x']} -> {sorted([0.0, x, 1.0])[1]}"
            )
            self.atoms[index]["x"] = sorted([0.0, x, 1.0])[
                1
            ]  # clamp between 0-1 so that the atom is kep inside the cell
        if y != None:
            self.add_tweak_message(
                f"Atom {index}: y : {self.atoms[index]['y']} -> {sorted([0.0, y, 1.0])[1]}"
            )
            self.atoms[index]["y"] = sorted([0.0, y, 1.0])[
                1
            ]  # clamp between 0-1 so that the atom is kep inside the cell
        if z != None:
            self.add_tweak_message(
                f"Atom {index}: z : {self.atoms[index]['z']} -> {sorted([0.0, z, 1.0])[1]}"
            )
            self.atoms[index]["z"] = sorted([0.0, z, 1.0])[
                1
            ]  # clamp between 0-1 so that the atom is kep inside the cell
        if atomic_number != None:
            nsymb = mendeleev.element(atomic_number).symbol

            self.add_tweak_message(
                f"Atom {index}: Z : {self.atoms[index]['atomic_number']} -> {atomic_number}"
            )
            self.add_tweak_message(
                f"Atom {index}: Symbol : {self.atoms[index]['symbol']} -> {nsymb}"
            )

            self.atoms[index]["atomic_number"] = atomic_number
            self.atoms[index]["symbol"] = nsymb
        if rot_matrix != None:
            self.atoms[index]["rot_matrix"] = (
                np.asarray(rot_matrix).reshape(3, 3).tolist()
            )
        if NPT != None:
            if int(NPT) % 2 != 1:
                self.add_tweak_message(f"Atom {index}: FAILED : NPT : NPT NOT ODD")
                raise Exception(
                    "NPT is not odd. Check http://www.wien2k.at/reg_user/textbooks/usersguide.pdf page 43 for more info."
                )
            self.add_tweak_message(
                f"Atom {index}: NPT : {self.atoms[index]['NPT']} -> {int(NPT)}"
            )
            self.atoms[index]["NPT"] = int(NPT)
        if R0 != None:
            self.add_tweak_message(
                f"Atom {index}: R0 : {self.atoms[index]['R0']} -> {int(R0)}"
            )
            self.atoms[index]["R0"] = R0
        if RMT != None:
            self.add_tweak_message(
                f"Atom {index}: RMT : {self.atoms[index]['RMT']} -> {int(RMT)}"
            )
            self.atoms[index]["RMT"] = RMT
        if ISPLIT != None:
            if int(ISPLIT) not in [0, 1, 2, 3, 4, 5, 6, 7, 8, -2, 88, 99]:
                self.add_tweak_message(
                    f"Atom {index}: FAILED : ISPLIT : INVALID ISPLIT OPTION"
                )
                raise Exception(
                    "Invalid ISPLIT option. Check http://www.wien2k.at/reg_user/textbooks/usersguide.pdf page 43 for more info."
                )
            self.add_tweak_message(
                f"Atom {index}: ISPLIT : {self.atoms[index]['ISPLIT']} -> {int(ISPLIT)}"
            )
            self.atoms[index]["ISPLIT"] = int(ISPLIT)
        else:
            # nothing changed
            pass

        self.update_symmetry()

        return self.atoms[index]

    def tweak_cell_multiples(self, a=1,b=1,c=1):
        old = self.cell_multiples
        self.cell_multiples = {
            "a": 1 if int(a) < 1 else int(a),
            "b": 1 if int(b) < 1 else int(b),
            "c": 1 if int(c) < 1 else int(c),
        }
        self.add_tweak_message(f"Cell multiples: ({old['a']},{old['b']},{old['c']}) -> ({self.cell_multiples['a']},{self.cell_multiples['b']},{self.cell_multiples['c']})")

    # TODO: add ability to tweak atoms symmetrically
    def tweak_atom_symmetrically():
        pass

    # --------------- SYMMETRY ---------------

    def update_symmetry(self):
        # generate the lattice
        lattice = para2matrix(
            [
                self.a,
                self.b,
                self.c,
                np.radians(self.alpha),
                np.radians(self.beta),
                np.radians(self.gamma),
            ]
        )
        # generate cell
        cell = (
            lattice,
            lmap(self.atoms, lambda at: (at.x, at.y, at.z)),
            lmap(self.atoms, lambda at: at.Z),
            lmap(
                self.atoms,
                lambda at: at.get_precise_magnetization(),
            ),
        )

        # get space group symbol and number
        try:
            if self.write_symmetry_ops == False or not (
                self.cell_multiples["a"] == 1
                and self.cell_multiples["b"] == 1
                and self.cell_multiples["c"] == 1
            ):
                raise "Forcefully ignoring symmetry operations."

            space_group_info = spglib.get_spacegroup(cell, symprec=1e-5)
            self.spacegroup_symbol, self.spacegroup_number = space_group_info.split(
                "("
            )[0], int(space_group_info.split(")")[0].split("(")[1])

            # get all symmetry operations
            symmetry_ops = spglib.get_magnetic_symmetry(cell, symprec=1e-5)
            print(symmetry_ops["equivalent_atoms"])
            for i in range(len(symmetry_ops["rotations"])):
                self.symmetry_ops.append(
                    StructureSymmetryOperation(
                        symmetry_ops["rotations"][i], symmetry_ops["translations"][i]
                    )
                )

            # atom equivalence info
            self.equivalent_atoms = symmetry_ops["equivalent_atoms"]
            self.non_eq_count = len(set(self.equivalent_atoms))

            # add tweak message
            self.add_tweak_message(
                f"Update symmetry : {self.spacegroup_symbol} {self.spacegroup_number} : NONEQUIV {self.non_eq_count}"
            )
        except:
            # ignore symmetries
            self.write_symmetry_ops = False

            # make each passed in atom unique, so that wien2k can handle that itself
            self.non_eq_count = len(self.atoms)
            self.equivalent_atoms = list(range(0, self.non_eq_count))

            self.add_tweak_message(f"Update symmetry : ERROR")

            print("Error determining symmetry")

    def get_equivalent_atom_groups(self):
        groups = {}
        for i in range(len(self.equivalent_atoms)):
            g_id = self.equivalent_atoms[i]
            if g_id not in groups:
                groups[g_id] = []
            groups[g_id].append(self.atoms[i])

        return groups

    def get_unique_atom_instances(self):
        groups = self.get_equivalent_atom_groups()
        unique_atoms = []
        for k in groups:
            unique_atoms.append(groups[k][0])

        return unique_atoms

    # --------------- OUTPUT ---------------

    def get_text(self):
        # returns the .struct file with tweaks done to it
        text = ""

        # Title line
        text += StructureFile.apply_format(StructureFile.LINE_FORMATS[1], [self.title])
        text += StructureFile.apply_format(
            StructureFile.LINE_FORMATS[2],
            [
                self.lattice_type,
                self.non_eq_count
                * self.cell_multiples["a"]
                * self.cell_multiples["b"]
                * self.cell_multiples["c"],
            ],
        )
        text += StructureFile.apply_format(
            StructureFile.LINE_FORMATS[3], [self.calc_mode]
        )
        text += StructureFile.apply_format(
            StructureFile.LINE_FORMATS[4],
            [
                self.a * self.cell_multiples["a"],
                self.b * self.cell_multiples["b"],
                self.c * self.cell_multiples["c"],
                self.alpha,
                self.beta,
                self.gamma,
            ],
        )

        # equivalent atom groups
        unique = self.get_unique_atom_instances()
        cell_id = 0
        for _a in range(self.cell_multiples["a"]):
            for _b in range(self.cell_multiples["b"]):
                for _c in range(self.cell_multiples["c"]):
                    for i in range(len(unique)):
                        atom = unique[i]

                        # atoms
                        # we do not have to go through each atom, since the symmetry operations take care of that
                        group_id = (
                            (i + 1 + (cell_id) * len(unique))
                            if self.a == self.b and self.b == self.c
                            else -(i + 1 + (cell_id) * len(unique))
                        )

                        ###
                        text += StructureFile.apply_format(
                            StructureFile.LINE_FORMATS[5],
                            [
                                group_id,
                                (atom.x + _a) / self.cell_multiples["a"],
                                (atom.y + _b) / self.cell_multiples["b"],
                                (atom.z + _c) / self.cell_multiples["c"],
                            ],
                        )
                        # each atom has it's own equivalent group
                        text += StructureFile.apply_format(
                            StructureFile.LINE_FORMATS[6], [1, atom.ISPLIT]
                        )
                        ###

                        text += StructureFile.apply_format(
                            StructureFile.LINE_FORMATS[7],
                            [atom.get_symbol(), atom.NPT, atom.R0, atom.RMT, atom.Z],
                        )
                        # rot matrix
                        text += StructureFile.apply_format(
                            StructureFile.LINE_FORMATS[8], atom.rot_matrix[0]
                        )
                        text += StructureFile.apply_format(
                            StructureFile.LINE_FORMATS[9], atom.rot_matrix[1]
                        )
                        text += StructureFile.apply_format(
                            StructureFile.LINE_FORMATS[10], atom.rot_matrix[2]
                        )

                    cell_id += 1

        # symmetry operations
        if self.write_symmetry_ops:
            text += StructureFile.apply_format(
                StructureFile.LINE_FORMATS[11], [self.symmetry_ops.__len__()]
            )
            for i in range(len(self.symmetry_ops)):
                op = self.symmetry_ops[i]
                text += StructureFile.apply_format(
                    StructureFile.LINE_FORMATS[12],
                    op.rot_matrix[0] + [op.translation_vector[0]],
                )
                text += StructureFile.apply_format(
                    StructureFile.LINE_FORMATS[13],
                    op.rot_matrix[1] + [op.translation_vector[1]],
                )
                text += StructureFile.apply_format(
                    StructureFile.LINE_FORMATS[14],
                    op.rot_matrix[2] + [op.translation_vector[2]],
                )
                text += StructureFile.apply_format(
                    StructureFile.LINE_FORMATS[15], [i + 1]
                )
        else:
            text += StructureFile.apply_format(StructureFile.LINE_FORMATS[11], [0])

        text += "\n"
        # precise positions
        for _a in range(self.cell_multiples["a"]):
            for _b in range(self.cell_multiples["b"]):
                for _c in range(self.cell_multiples["c"]):
                    for atom in self.atoms:
                        text += StructureFile.apply_format(
                            StructureFile.LINE_FORMATS[16],
                            [
                                (atom.x + _a) / self.cell_multiples["a"],
                                (atom.y + _b) / self.cell_multiples["b"],
                                (atom.z + _c) / self.cell_multiples["c"],
                            ],
                        )

        return text

    def get_logs(self, do_print=True):
        if do_print:
            print(self.get_logs(do_print=False))
        return "\n".join(self.tweak_logs)
