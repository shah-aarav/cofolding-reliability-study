from dataclasses import replace
import unittest
import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem
from chemical_maps import checked_template
from structure_io import Atom
from validity import posed_template,coordinate_stereochemistry,strict_binary_report,reference_free_validity

class ValidityTests(unittest.TestCase):
    def test_missing_results_never_become_passes(self):
        report=strict_binary_report(pd.DataFrame({'a':[True],'b':[pd.NA]}),['a','b'])
        self.assertIsNone(report['all_checks_pass'])
        self.assertEqual(report['missing_checks'],['b'])
        with self.assertRaises(ValueError):strict_binary_report(pd.DataFrame(),['a'])
        with self.assertRaises(ValueError):strict_binary_report(pd.DataFrame({'a':[True]}),['a','b'])
    def test_geometry_is_preserved_and_mirror_stereo_rejected(self):
        molecule=Chem.AddHs(Chem.MolFromSmiles('N[C@H](C)O'))
        self.assertEqual(AllChem.EmbedMolecule(molecule,randomSeed=17),0)
        molecule=Chem.RemoveHs(molecule)
        template=checked_template(molecule,[f'a{i}' for i in range(molecule.GetNumAtoms())],'synthetic isomeric input')
        atoms=[Atom('B','B','2','LIG','1','1',f'a{i}',atom.GetSymbol().upper(),
                    tuple(molecule.GetConformer().GetAtomPosition(i)),1) for i,atom in enumerate(molecule.GetAtoms())]
        posed=posed_template(template,atoms)
        self.assertTrue(coordinate_stereochemistry(template,posed)['matches_specified_input_stereo'])
        mirrored=[replace(atom,position=(-atom.position[0],atom.position[1],atom.position[2])) for atom in atoms]
        self.assertFalse(coordinate_stereochemistry(template,posed_template(template,mirrored))['matches_specified_input_stereo'])
        np.testing.assert_allclose(posed.GetConformer().GetPositions(),molecule.GetConformer().GetPositions())
    def test_unspecified_stereo_is_not_claimed_valid(self):
        molecule=Chem.MolFromSmiles('CO')
        template=checked_template(molecule,['C1','O1'],'synthetic input')
        atoms=[Atom('B','B','2','LIG','1','1',name,element,point,1) for name,element,point in [('C1','C',(0,0,0)),('O1','O',(1.4,0,0))]]
        report=coordinate_stereochemistry(template,posed_template(template,atoms))
        self.assertIsNone(report['matches_specified_input_stereo'])

    def test_actual_reference_free_posebusters_has_complete_report(self):
        molecule=Chem.AddHs(Chem.MolFromSmiles('CCO'))
        AllChem.EmbedMolecule(molecule,randomSeed=17)
        molecule=Chem.RemoveHs(molecule)
        template=checked_template(molecule,['C1','C2','O1'],'synthetic input')
        atoms=[Atom('B','B','2','LIG','1','1',template.atom_names[i],atom.GetSymbol().upper(),
                    tuple(molecule.GetConformer().GetAtomPosition(i)),1) for i,atom in enumerate(molecule.GetAtoms())]
        environment=Chem.AddHs(Chem.MolFromSequence('AAAA'))
        AllChem.EmbedMolecule(environment,randomSeed=17)
        report=reference_free_validity(template,atoms,environment)
        self.assertEqual(len(report['checks']),22)
        self.assertEqual(report['missing_checks'],[])
        self.assertFalse(report['experimental_reference_used'])

if __name__=='__main__':unittest.main()
