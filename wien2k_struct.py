from wien2_helper import *

import mendeleev
import numpy as np
import re

from pyxtal.lattice import para2matrix
import spglib

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
    def load_poscar(filepath):
        pass

    @staticmethod
    def load_cif(filepath):
        pass

    def load_materials_project(url):
        pass

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
