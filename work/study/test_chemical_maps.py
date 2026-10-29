import unittest
from rdkit import Chem
from chemical_maps import checked_template,template_coordinates,exact_symmetry_maps,stereochemistry_flags
from structure_io import Atom

def template(smiles,names=None):
    molecule=Chem.MolFromSmiles(smiles)
    return checked_template(molecule,names or [f'a{i}' for i in range(molecule.GetNumAtoms())],'synthetic input')

class ChemicalMapTests(unittest.TestCase):
    def test_reordered_graph_and_symmetry(self):
        first=template('c1ccccc1')
        second=template('c1ccccc1')
        maps=exact_symmetry_maps(first,second)
        self.assertEqual(len(maps),12)
        with self.assertRaises(ValueError):exact_symmetry_maps(first,second,max_maps=11)
        self.assertEqual(len(exact_symmetry_maps(template('CCO'),template('OCC'))),1)
    def test_stereo_charge_and_isotope_are_not_erased(self):
        for first,second in [('N[C@H](C)O','N[C@@H](C)O'),('CC(=O)O','CC(=O)[O-]'),('CC','[13CH3]C')]:
            with self.subTest(first=first),self.assertRaises(ValueError):exact_symmetry_maps(template(first),template(second))
    def test_coordinate_order_is_template_order(self):
        molecule=template('CO',['carbon','oxygen'])
        a=Atom('B','B','2','LIG','1','1','carbon','C',(1,0,0),1)
        b=Atom('B','B','2','LIG','1','1','oxygen','O',(2,0,0),1)
        self.assertEqual(template_coordinates(molecule,[b,a]).tolist(),[[1,0,0],[2,0,0]])
        with self.assertRaises(ValueError):template_coordinates(molecule,[a,a])
        with self.assertRaises(ValueError):template_coordinates(molecule,[a])
    def test_ambiguity_and_invalid_template(self):
        self.assertEqual(stereochemistry_flags(template('NC(C)O'))['unassigned_tetrahedral_centers'],1)
        with self.assertRaises(ValueError):checked_template(Chem.MolFromSmiles('CO'),['same','same'],'source')
        with self.assertRaises(ValueError):checked_template(Chem.AddHs(Chem.MolFromSmiles('C')),['x']*5,'source')

if __name__=='__main__':unittest.main()
