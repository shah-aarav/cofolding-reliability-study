import io
from pathlib import Path
import tempfile
import unittest
import zipfile
import numpy as np
from safe_npz import read_npz_arrays

class SafeNPZTests(unittest.TestCase):
    def test_numeric_arrays_and_allowlist(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.npz'
            np.savez_compressed(path,bonds=np.array([[1,2,1]]),ignored=np.arange(4))
            arrays=read_npz_arrays(path,{'bonds'})
            self.assertEqual(set(arrays),{'bonds'})
            self.assertEqual(arrays['bonds'].tolist(),[[1,2,1]])
            with self.assertRaises(ValueError):read_npz_arrays(path,{'bonds'},max_total_bytes=10)
    def test_pickle_array_rejected_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.npz'
            np.savez(path,unsafe=np.array([{'anything':'object'}],dtype=object))
            with self.assertRaises(ValueError):read_npz_arrays(path,{'unsafe'})
    def test_header_cannot_allocate_a_giant_array(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.npz'
            raw=io.BytesIO()
            np.lib.format.write_array_header_1_0(raw,{'descr':'<f8','fortran_order':False,'shape':(10**12,)})
            with zipfile.ZipFile(path,'w') as archive:archive.writestr('atoms.npy',raw.getvalue())
            with self.assertRaises(ValueError):read_npz_arrays(path,{'atoms'})

if __name__=='__main__':unittest.main()
