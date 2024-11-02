import numpy as np
from amcheck import is_altermagnet

symmetry_operations = [(np.array([[-1,  0,  0],
                                  [ 0, -1,  0],
                                  [ 0,  0, -1]],
                                 dtype=int),
                       np.array([0.0, 0.0, 0.0])),
                       # for compactness reasons,
                       # other symmetry operations are omitted
                       # from this example
                       ]

# positions of atoms in NiAs structure: ["Ni", "Ni", "As", "As"]
positions = np.array([[0.00, 0.00, 0.00],
                      [0.00, 0.00, 0.50],
                      [1/3., 2/3., 0.25],
                      [2/3., 1/3., 0.75]])

equiv_atoms  = [0, 0, 1, 1]

chem_symbols = ["Mn", "Mn", "Te", "Te"]
spins = ["u", "d", "n", "n"]
print(is_altermagnet(symmetry_operations, positions, equiv_atoms,
                     chem_symbols, spins))