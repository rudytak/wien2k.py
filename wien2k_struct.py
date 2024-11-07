from wien2_helper import *

import mendeleev
import numpy as np
import re, json

from mp_api.client import MPRester
from pyxtal.lattice import para2matrix, matrix2para
import copy, math

from time import perf_counter


class StructureAtom:
    symbol_to_number = {
        "H": 1,
        "He": 2,
        "Li": 3,
        "Be": 4,
        "B": 5,
        "C": 6,
        "N": 7,
        "O": 8,
        "F": 9,
        "Ne": 10,
        "Na": 11,
        "Mg": 12,
        "Al": 13,
        "Si": 14,
        "P": 15,
        "S": 16,
        "Cl": 17,
        "Ar": 18,
        "K": 19,
        "Ca": 20,
        "Sc": 21,
        "Ti": 22,
        "V": 23,
        "Cr": 24,
        "Mn": 25,
        "Fe": 26,
        "Co": 27,
        "Ni": 28,
        "Cu": 29,
        "Zn": 30,
        "Ga": 31,
        "Ge": 32,
        "As": 33,
        "Se": 34,
        "Br": 35,
        "Kr": 36,
        "Rb": 37,
        "Sr": 38,
        "Y": 39,
        "Zr": 40,
        "Nb": 41,
        "Mo": 42,
        "Tc": 43,
        "Ru": 44,
        "Rh": 45,
        "Pd": 46,
        "Ag": 47,
        "Cd": 48,
        "In": 49,
        "Sn": 50,
        "Sb": 51,
        "Te": 52,
        "I": 53,
        "Xe": 54,
        "Cs": 55,
        "Ba": 56,
        "La": 57,
        "Ce": 58,
        "Pr": 59,
        "Nd": 60,
        "Pm": 61,
        "Sm": 62,
        "Eu": 63,
        "Gd": 64,
        "Tb": 65,
        "Dy": 66,
        "Ho": 67,
        "Er": 68,
        "Tm": 69,
        "Yb": 70,
        "Lu": 71,
        "Hf": 72,
        "Ta": 73,
        "W": 74,
        "Re": 75,
        "Os": 76,
        "Ir": 77,
        "Pt": 78,
        "Au": 79,
        "Hg": 80,
        "Tl": 81,
        "Pb": 82,
        "Bi": 83,
        "Po": 84,
        "At": 85,
        "Rn": 86,
        "Fr": 87,
        "Ra": 88,
        "Ac": 89,
        "Th": 90,
        "Pa": 91,
        "U": 92,
        "Np": 93,
        "Pu": 94,
        "Am": 95,
        "Cm": 96,
        "Bk": 97,
        "Cf": 98,
        "Es": 99,
        "Fm": 100,
        "Md": 101,
        "No": 102,
        "Lr": 103,
        "Rf": 104,
        "Db": 105,
        "Sg": 106,
        "Bh": 107,
        "Hs": 108,
        "Mt": 109,
        "Ds": 110,
        "Rg": 111,
        "Cn": 112,
        "Nh": 113,
        "Fl": 114,
        "Mc": 115,
        "Lv": 116,
        "Ts": 117,
        "Og": 118,
    }
    number_to_symbol = {
        1: "H",
        2: "He",
        3: "Li",
        4: "Be",
        5: "B",
        6: "C",
        7: "N",
        8: "O",
        9: "F",
        10: "Ne",
        11: "Na",
        12: "Mg",
        13: "Al",
        14: "Si",
        15: "P",
        16: "S",
        17: "Cl",
        18: "Ar",
        19: "K",
        20: "Ca",
        21: "Sc",
        22: "Ti",
        23: "V",
        24: "Cr",
        25: "Mn",
        26: "Fe",
        27: "Co",
        28: "Ni",
        29: "Cu",
        30: "Zn",
        31: "Ga",
        32: "Ge",
        33: "As",
        34: "Se",
        35: "Br",
        36: "Kr",
        37: "Rb",
        38: "Sr",
        39: "Y",
        40: "Zr",
        41: "Nb",
        42: "Mo",
        43: "Tc",
        44: "Ru",
        45: "Rh",
        46: "Pd",
        47: "Ag",
        48: "Cd",
        49: "In",
        50: "Sn",
        51: "Sb",
        52: "Te",
        53: "I",
        54: "Xe",
        55: "Cs",
        56: "Ba",
        57: "La",
        58: "Ce",
        59: "Pr",
        60: "Nd",
        61: "Pm",
        62: "Sm",
        63: "Eu",
        64: "Gd",
        65: "Tb",
        66: "Dy",
        67: "Ho",
        68: "Er",
        69: "Tm",
        70: "Yb",
        71: "Lu",
        72: "Hf",
        73: "Ta",
        74: "W",
        75: "Re",
        76: "Os",
        77: "Ir",
        78: "Pt",
        79: "Au",
        80: "Hg",
        81: "Tl",
        82: "Pb",
        83: "Bi",
        84: "Po",
        85: "At",
        86: "Rn",
        87: "Fr",
        88: "Ra",
        89: "Ac",
        90: "Th",
        91: "Pa",
        92: "U",
        93: "Np",
        94: "Pu",
        95: "Am",
        96: "Cm",
        97: "Bk",
        98: "Cf",
        99: "Es",
        100: "Fm",
        101: "Md",
        102: "No",
        103: "Lr",
        104: "Rf",
        105: "Db",
        106: "Sg",
        107: "Bh",
        108: "Hs",
        109: "Mt",
        110: "Ds",
        111: "Rg",
        112: "Cn",
        113: "Nh",
        114: "Fl",
        115: "Mc",
        116: "Lv",
        117: "Ts",
        118: "Og",
    }

    @staticmethod
    def init_symbol_maps():
        for Z in range(1, 118 + 1):
            symb = mendeleev.element(Z).symbol
            StructureAtom.symbol_to_number[symb] = Z
            StructureAtom.number_to_symbol[Z] = symb

    def __init__(self, x, y, z, Z, mag_vec=0):
        self.x = x
        self.y = y
        self.z = z

        if StructureAtom.symbol_to_number == {} or StructureAtom.number_to_symbol == {}:
            StructureAtom.init_symbol_maps()

        self.Z = int(Z)
        self.symb = None
        self.get_symbol()

        if type(mag_vec) == type(1) or type(mag_vec) == type(1.0):
            self.mag_vec = (mag_vec, 0, 0)
        elif type(mag_vec) == type((1, 0, 0)) or type(mag_vec) == type([1, 0, 0]):
            self.mag_vec = (mag_vec[0], mag_vec[1], mag_vec[2])

    def get_symbol(self):
        self.symb = StructureAtom.number_to_symbol[self.Z]
        return self.symb

    def get_type_id(self):
        return f"<wien2k_struct.StructureAtom {self.Z} {self.mag_vec[0]} {self.mag_vec[1]} {self.mag_vec[2]}>"

    def copy(self):
        return StructureAtom(self.x, self.y, self.z, self.Z, self.mag_vec)

    def __repr__(self):
        return f"<wien2k_struct.StructureAtom {self.x} {self.y} {self.z} {self.get_symbol()}>"

    def __str__(self):
        return f"<wien2k_struct.StructureAtom {self.x} {self.y} {self.z} {self.get_symbol()}>"


class StructureFile:

    # --------------- CREATION ---------------
    # all in angstroms
    # all atoms must be included

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
        self.atoms.sort(key=lambda a: a.Z)
        self.non_eq_count = 0

    def copy(self):
        return copy.deepcopy(self)

    def get_mutliples_count(self):
        return (
            self.cell_multiples["a"]
            * self.cell_multiples["b"]
            * self.cell_multiples["c"]
        )

    @staticmethod
    def load_poscar(filepath):
        # TODO:
        pass

    @staticmethod
    def parse_poscar(poscar_text):
        # start_time = perf_counter()

        lines = poscar_text.strip().split("\n")

        title = lines[0]
        matrix_scale = float(lines[1].strip().split(" ")[0])

        # set the unit to angstroms by default
        unit = "Ang"
        try:
            unit = lines[1].strip().split(" ")[1]
        except:
            # keep the unit as default
            pass

        a_vec = [matrix_scale * float(v) for v in re.split(r"[ \t]+", lines[2].strip())]
        b_vec = [matrix_scale * float(v) for v in re.split(r"[ \t]+", lines[3].strip())]
        c_vec = [matrix_scale * float(v) for v in re.split(r"[ \t]+", lines[4].strip())]

        (a, b, c, alpha, beta, gamma) = matrix2para([a_vec, b_vec, c_vec])
        alpha = alpha * 180 / math.pi
        beta = beta * 180 / math.pi
        gamma = gamma * 180 / math.pi

        atom_types = lines[5].strip().split(" ")
        atom_counts = [int(v) for v in lines[6].strip().split(" ")]
        are_atoms_direct = lines[7].strip().lower() == "direct"

        if not are_atoms_direct:
            raise NotImplementedError("Non-direct POSCAR files are not supported yet.")

        atoms = []
        ij = 0
        for i in range(len(atom_types)):
            at = atom_types[i]
            Z = mendeleev.element(at).atomic_number

            for j in range(atom_counts[i]):
                x, y, z = [
                    float(v) for v in re.split(r"[ \t]+", lines[8 + ij].strip())[0:3]
                ]
                atoms.append(StructureAtom(x, y, z, Z))
                ij += 1

        output = StructureFile(title, atoms, a, b, c, alpha, beta, gamma)

        # end_time = perf_counter()
        # print(f"Time took to parse POSCAR: {(end_time - start_time):.4f}s")

        return output

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

    def tweak_atom(self, index, x=None, y=None, z=None, Z=None, mag_vec=None):
        if index >= len(self.atoms) or index < 0:
            self.add_tweak_message(f"Atom {index}: FAILED : INVALID INDEX")
            raise Exception(
                "Atom index out of range (indexing is from 0 in the order as in the struct file)."
            )

        if x != None:
            self.add_tweak_message(
                f"Atom {index}: x : {self.atoms[index].x} -> {sorted([0.0, x, 1.0])[1]}"
            )
            self.atoms[index].x = sorted([0.0, x, 1.0])[
                1
            ]  # clamp between 0-1 so that the atom is kep inside the cell
        if y != None:
            self.add_tweak_message(
                f"Atom {index}: y : {self.atoms[index].y} -> {sorted([0.0, y, 1.0])[1]}"
            )
            self.atoms[index].y = sorted([0.0, y, 1.0])[
                1
            ]  # clamp between 0-1 so that the atom is kep inside the cell
        if z != None:
            self.add_tweak_message(
                f"Atom {index}: z : {self.atoms[index].z} -> {sorted([0.0, z, 1.0])[1]}"
            )
            self.atoms[index].z = sorted([0.0, z, 1.0])[
                1
            ]  # clamp between 0-1 so that the atom is kep inside the cell
        if Z != None:
            self.add_tweak_message(f"Atom {index}: Z : {self.atoms[index].Z} -> {Z}")

            self.atoms[index].Z = Z
        if mag_vec != None:
            if type(mag_vec) == type(1) or type(mag_vec) == type(1.0):
                new_mag_vec = (mag_vec, 0, 0)
            elif type(mag_vec) == type((1, 0, 0)) or type(mag_vec) == type([1, 0, 0]):
                new_mag_vec = (mag_vec[0], mag_vec[1], mag_vec[2])

            self.add_tweak_message(
                f"Atom {index}: mag_vec : {self.atoms[index].mag_vec} -> {new_mag_vec}"
            )
            self.atoms[index].mag_vec = new_mag_vec
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
                            (a.x + _a) / aa,
                            (a.y + _b) / bb,
                            (a.z + _c) / cc,
                            a.Z,
                            a.mag_vec,
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

    def generate_poscar_corresponding_lstart_pattern(self, lstart_pattern):
        # converts a lstart_pattern, that corresponds to the loaded poscar
        # into a different lstart_pattern, that will keep the same flags for the same atomic posittions in space
        # (this is due to the atoms getting sorted by the generate_poscar method)

        # cell multiples
        aa = self.cell_multiples["a"]
        bb = self.cell_multiples["b"]
        cc = self.cell_multiples["c"]

        # copy and sort atoms by atomic number
        sorted_atoms = []
        for _a in range(aa):
            for _b in range(bb):
                for _c in range(cc):
                    sorted_atoms += [
                        StructureAtom(
                            (a.x + _a) / aa,
                            (a.y + _b) / bb,
                            (a.z + _c) / cc,
                            a.Z,
                            a.mag_vec,
                        )
                        for a in list(self.atoms)
                    ]
        sorted_atoms.sort(key=lambda a: a.Z)

        # print(sorted_atoms)

        output_pattern = []
        for at in sorted_atoms:
            # find the corresponding atom in the original array
            for orig_at in self.atoms:
                if (
                    abs(orig_at.x - ((at.x * aa) % 1.00000000000001)) < 1e-5
                    and abs(orig_at.y - ((at.y * bb) % 1.00000000000001)) < 1e-5
                    and abs(orig_at.z - ((at.z * cc) % 1.00000000000001)) < 1e-5
                    and orig_at.Z == at.Z
                ):
                    o_ind = self.atoms.index(orig_at)
                    output_pattern.append(lstart_pattern[o_ind % len(lstart_pattern)])

        # print(lstart_pattern, output_pattern)
        return output_pattern

    def get_logs(self, do_print=True):
        if do_print:
            print(self.get_logs(do_print=False))
        return "\n".join(self.tweak_logs)

    # --------------- P,T,PT symmetry ---------------

    def determine_T_symmetry(self, eps=1e-4):
        pass

    def determine_P_symmetry(self, eps=1e-4):
        pass

    def determine_PT_symmetry(self, eps=1e-4):
        isPT = False
        centers = set()

        # generate all atoms that fit in the cell bounding box
        # and group them by equivalence
        atom_groups = {}

        for a in self.atoms:
            for x_off in [-1, 0, 1]:
                for y_off in [-1, 0, 1]:
                    for z_off in [-1, 0, 1]:
                        if (
                            a.x + x_off > 0.0 - eps
                            and a.x + x_off < 1.0 + eps
                            and a.y + y_off > 0.0 - eps
                            and a.y + y_off < 1.0 + eps
                            and a.z + z_off > 0.0 - eps
                            and a.z + z_off < 1.0 + eps
                        ):
                            if a.Z not in atom_groups:
                                atom_groups[a.Z] = []

                            new_a = StructureAtom(
                                a.x + x_off, a.y + y_off, a.z + z_off, a.Z, a.mag_vec
                            )
                            atom_groups[a.Z].append(new_a)

        #
        print(lmap(atom_groups.keys(), lambda k: (k, atom_groups[k].__len__())))

        # function to check if the atoms after a P_xyz around some origin and T transformations are the same:
        def PT_check(origin, _atoms):
            orig_atoms = _atoms
            transformed_atoms = lmap(
                _atoms,
                lambda a: StructureAtom(
                    (2 * origin[0] - a.x) % (1.0),  # P operator
                    (2 * origin[1] - a.y) % (1.0),
                    (2 * origin[2] - a.z) % (1.0),
                    a.Z,
                    (
                        a.mag_vec[0] * -1,  # T operator
                        a.mag_vec[1] * -1,
                        a.mag_vec[2] * -1,
                    ),
                ),
            )

            for at_orig in orig_atoms:
                at_match = None

                for at_trans in transformed_atoms:
                    if (
                        abs(at_orig.x - at_trans.x) < 2 * eps
                        and abs(at_orig.y - at_trans.y) < 2 * eps
                        and abs(at_orig.z - at_trans.z) < 2 * eps
                        and at_orig.Z == at_trans.Z
                        and abs(at_orig.mag_vec[0] - at_trans.mag_vec[0]) < 2 * eps
                        and abs(at_orig.mag_vec[1] - at_trans.mag_vec[1]) < 2 * eps
                        and abs(at_orig.mag_vec[2] - at_trans.mag_vec[2]) < 2 * eps
                    ):
                        at_match = at_trans

                if at_match == None:
                    # print("Wasn't able to find matching atom.")
                    return False
                else:
                    transformed_atoms.remove(at_match)

            if transformed_atoms.__len__() == 0:
                return True
            else:
                # print("Some atoms are left over.")
                return False

        for group_key in atom_groups.keys():
            group = atom_groups[group_key]

            for at1 in group:
                for at2 in group:
                    if at1 != at2:
                        possible_center = (
                            (at1.x + at2.x) / 2,
                            (at1.y + at2.y) / 2,
                            (at1.z + at2.z) / 2,
                        )

                        if PT_check(possible_center, self.atoms):
                            isPT = True
                            centers.add(possible_center)

        return (isPT, list(centers))

    # --------------- Equivalence ---------------

    def find_translation_vectors(self, other_struct, lim_count=-1):
        # attempts to find all teh translation vectors, that would give us other_struct from our struct
        # if no vectors are found, the two structures are not translationally equivalent/symmetric
        # if some vectors are found, the two structures are equivalent

        def check_translation_match(src_atoms, target_atoms, translation_vec):
            # check if the translation is valid for all other atoms as well
            is_valid = True
            for _at1 in src_atoms:
                p1 = (_at1.x, _at1.y, _at1.z)

                # we have to find some atom in the other structure that translationally corresponds
                has_corresponding_atom = False
                for _at2 in target_atoms:
                    p2 = (_at2.x, _at2.y, _at2.z)

                    _psum = np.add(p1, translation_vec)
                    _psum = lmap(_psum, lambda a: a % 1.00000000000001)

                    if _at1.Z == _at2.Z:
                        # check if the positions are close enough
                        if np.linalg.norm(np.subtract(p2, _psum)) < 1e-4:
                            has_corresponding_atom = True
                            break

                if not has_corresponding_atom:
                    # this translation vector is not valid
                    is_valid = False
                    break
            return is_valid

        translation_vecs = []

        for at1 in self.atoms:
            for at2 in other_struct.atoms:
                # make sure that the atoms have equivalent atomic numbers
                if at1.Z == at2.Z:
                    trans_vec = (at2.x - at1.x, at2.y - at1.y, at2.z - at1.z)

                    is_valid = check_translation_match(
                        self.atoms, other_struct.atoms, trans_vec
                    )
                    if is_valid:
                        translation_vecs.append(trans_vec)

                        if len(translation_vecs) >= lim_count and lim_count != -1:
                            return translation_vecs

        return translation_vecs

    def translational_equivalence_check(self, other_struct):
        # returns if two structures are translationally equivalent
        proof_of_equivalence = self.find_translation_vectors(other_struct, 1)
        are_equiv = len(proof_of_equivalence) > 0

        return are_equiv, proof_of_equivalence[0] if are_equiv else None

    # --------------- Magnetism ---------------
