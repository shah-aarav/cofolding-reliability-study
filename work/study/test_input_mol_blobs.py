import pickle
from unittest.mock import patch
import unittest
from rdkit import Chem
from input_mol_blobs import templates_from_inert_cache_bytes

class InertMolBlobTests(unittest.TestCase):
    def fixture(self):
        molecule=Chem.MolFromSmiles('CO')
        for i,atom in enumerate(molecule.GetAtoms()):atom.SetProp('name',f'a{i}')
        blob=molecule.ToBinary(Chem.PropertyPickleOptions.AllProps)
        return pickle.dumps({'component':blob})
    def test_extracts_named_graph_without_pickle_execution(self):
        raw=self.fixture()
        with patch('pickle.loads',side_effect=AssertionError('Unpickling forbidden')):
            templates=templates_from_inert_cache_bytes(raw,'synthetic input cache')
        self.assertEqual(len(templates),1)
        self.assertEqual(templates[0].atom_names,('a0','a1'))
        self.assertEqual(Chem.MolToSmiles(templates[0].molecule),'CO')
        self.assertEqual(templates[0].molecule.GetNumConformers(),0)
    def test_executable_opcode_is_never_evaluated(self):
        # Valid pickle instructions describing a callable, but no RDKit data.
        raw=b'cos\nsystem\n(S"echo should-not-execute"\ntR.'
        with patch('os.system',side_effect=AssertionError('Must never execute')) as system:
            with self.assertRaises(ValueError):templates_from_inert_cache_bytes(raw,'synthetic adversarial fixture')
            system.assert_not_called()
    def test_resource_limits(self):
        with self.assertRaises(ValueError):templates_from_inert_cache_bytes(self.fixture(),'source',max_bytes=2)
        with self.assertRaises(ValueError):templates_from_inert_cache_bytes(self.fixture(),'source',max_ops=1)

if __name__=='__main__':unittest.main()
