import unittest
from types import SimpleNamespace
from audit_rnp_correspondence import role_chain_map


class CorrespondenceTests(unittest.TestCase):
    def test_entity_ids_not_alphabetical_or_nearest_chain(self):
        roles=[{'kind':'protein','sequence':'AAA','input_entity_id':'1'},
               {'kind':'ligand','input_entity_id':'2'}]
        atoms=[SimpleNamespace(chain='Z',entity='1'),SimpleNamespace(chain='A',entity='2')]
        self.assertEqual(role_chain_map('protenix',roles,atoms,{'Z':'AAA'}),['Z','A'])

    def test_repeated_entity_and_sequence_mismatch_rejected(self):
        roles=[{'kind':'protein','sequence':'AAA','input_entity_id':'1'},
               {'kind':'ligand','input_entity_id':'2'}]
        atoms=[SimpleNamespace(chain='Z',entity='1'),SimpleNamespace(chain='A',entity='1')]
        with self.assertRaises(ValueError):role_chain_map('protenix',roles,atoms,{'Z':'AAA'})
        atoms[-1].entity='2'
        with self.assertRaises(ValueError):role_chain_map('protenix',roles,atoms,{'Z':'AAG'})

    def test_boltz_explicit_ids_no_sorted_order_guess(self):
        roles=[{'kind':'ligand','declared_input_chain_id':'B'},
               {'kind':'protein','declared_input_chain_id':'A','sequence':'AAA'}]
        atoms=[SimpleNamespace(chain='A',entity='1'),SimpleNamespace(chain='B',entity='2')]
        self.assertEqual(role_chain_map('boltz2',roles,atoms,{'A':'AAA'}),['B','A'])
        atoms.append(SimpleNamespace(chain='B',entity='3'))
        with self.assertRaises(ValueError):role_chain_map('boltz2',roles,atoms,{'A':'AAA'})


if __name__=='__main__':unittest.main()
