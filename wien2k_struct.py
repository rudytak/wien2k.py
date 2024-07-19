from wien2_helper import *

import mendeleev
import numpy as np
import re, json

from mp_api.client import MPRester
from pyxtal.lattice import para2matrix


class StructureAtom:
    def __init__(
        self,
        x,
        y,
        z,
        Z,
    ):
        self.x = x
        self.y = y
        self.z = z

        self.Z = Z

    def get_symbol(self):
        return mendeleev.element(int(self.Z)).symbol

    def __repr__(self):
        return f"<wien2k_struct.StructureAtom {self.x} {self.y} {self.z} {self.Z}>"

    def __str__(self):
        return f"<wien2k_struct.StructureAtom {self.x} {self.y} {self.z} {self.Z}>"


class StructureFile:

    # --------------- CREATION ---------------
    # all in angstroms

    def __init__(
        self,
        title,
        atoms,
        a,
        b=None,
        c=None,
        alpha=90.0,
        beta=90.0,
        gamma=90.0,
    ):
        # file load variables
        self.filepath = ""
        self.original = None

        # log of all tweaks done
        self.tweak_logs = []

        # general info
        self.title = title

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
        self.non_eq_count = 0

    def get_mutliples_count(self):
        return self.cell_multiples["a"] * self.cell_multiples["b"] * self.cell_multiples["c"]

    @staticmethod
    def load_poscar(filepath):
        pass

    @staticmethod
    def load_cif(filepath):
        # TODO ??
        pass

    def load_materials_project(url, credentials_path):
        with open(credentials_path) as json_reader:
            credentials = json.load(json_reader)

        material = None
        with MPRester(credentials["MP_API_key"]) as mpr:
            docs = mpr.summary.search(material_ids=re.findall(r"mp-\d+", url))
            material = docs[0]

        return StructureFile(
            material.formula_pretty,
            lmap(
                material.structure.sites,
                lambda site: StructureAtom(site.a, site.b, site.c, site.specie.number),
            ),
            material.structure.lattice.a,
            material.structure.lattice.b,
            material.structure.lattice.c,
            material.structure.lattice.alpha,
            material.structure.lattice.beta,
            material.structure.lattice.gamma,
        )

    # --------------- TWEAKING ---------------

    def add_tweak_message(self, message):
        self.tweak_logs.append(message)

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

    def tweak_cell_multiples(self, a=1, b=1, c=1):
        old = self.cell_multiples
        self.cell_multiples = {
            "a": 1 if int(a) < 1 else int(a),
            "b": 1 if int(b) < 1 else int(b),
            "c": 1 if int(c) < 1 else int(c),
        }
        self.add_tweak_message(
            f"Cell multiples: ({old['a']},{old['b']},{old['c']}) -> ({self.cell_multiples['a']},{self.cell_multiples['b']},{self.cell_multiples['c']})"
        )

    def tweak_atom(
        self,
        index,
        x=None,
        y=None,
        z=None,
        atomic_number=None,
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
        else:
            # nothing changed
            pass

        return self.atoms[index]

    # --------------- OUTPUT ---------------

    def generate_poscar(self):
        # returns the .poscar file with tweaks done to it
        text = f"{self.title}\n"
        text += f"1.0 Ang\n"

        # cell multiples
        aa = self.cell_multiples["a"]
        bb = self.cell_multiples["b"]
        cc = self.cell_multiples["c"]

        # generate the lattice matrix
        lattice_matrix = para2matrix(
            (self.a * aa, self.b * bb, self.c * cc, self.alpha, self.beta, self.gamma),
            False,
        )

        # write the lattice matrix
        text += f"{lattice_matrix[0][0]:.16f} {lattice_matrix[0][1]:.16f} {lattice_matrix[0][2]:.16f}\n"
        text += f"{lattice_matrix[1][0]:.16f} {lattice_matrix[1][1]:.16f} {lattice_matrix[1][2]:.16f}\n"
        text += f"{lattice_matrix[2][0]:.16f} {lattice_matrix[2][1]:.16f} {lattice_matrix[2][2]:.16f}\n"

        # copy and sort atoms by atomic number
        sorted_atoms = []
        for _a in range(aa):
            for _b in range(bb):
                for _c in range(cc):
                    sorted_atoms += [
                        StructureAtom(
                            (a.x + _a) / aa, (a.y + _b) / bb, (a.z + _c) / cc, a.Z
                        )
                        for a in list(self.atoms)
                    ]
        sorted_atoms.sort(key=lambda a: a.Z)

        # count the occurences
        counts = {}
        for a in sorted_atoms:
            if a.Z not in counts:
                counts[a.Z] = 0
            counts[a.Z] += 1

        # atom types/symbols
        for atom_number in counts.keys():
            text += f"{mendeleev.element(int(atom_number)).symbol} "
        text += "\n"

        # atom counts
        for atom_number in counts.keys():
            text += f"{counts[atom_number]} "
        text += "\n"


        text += "Direct\n"

        # write out all atom positions
        for a in sorted_atoms:
            text += f"{a.x:.16f} {a.y:.16f} {a.z:.16f} {mendeleev.element(int(a.Z)).symbol}\n"
        self.non_eq_count = len(sorted_atoms)

        return text

    def get_logs(self, do_print=True):
        if do_print:
            print(self.get_logs(do_print=False))
        return "\n".join(self.tweak_logs)
