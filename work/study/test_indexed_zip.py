import io
import unittest
import zipfile
from indexed_zip import WindowFile,read_indexed_member,member_window

class IndexedZipTests(unittest.TestCase):
    def fixture(self,method=zipfile.ZIP_DEFLATED):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',compression=method) as archive:
            archive.writestr('predictions/confidence.json',b'{"score":0.7}')
        data=buffer.getvalue()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            info=archive.infolist()[0]
            row={'name':info.filename,'size':info.file_size,'compressed_size':info.compress_size,
                 'crc32':format(info.CRC,'08x'),'header_offset':info.header_offset,'flag_bits':info.flag_bits,
                 'compress_type':info.compress_type,'archive_size':len(data),'archive_url':'https://example.test/archive.zip'}
        return data,row
    def test_real_zip_round_trip(self):
        for method in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):
            data,row=self.fixture(method)
            result,proof=read_indexed_member(WindowFile(data,0,len(data)),row)
            self.assertEqual(result,b'{"score":0.7}')
            self.assertTrue(proof['crc32_verified'])
            self.assertFalse(proof['whole_archive_checksum_verified'])
    def test_mismatched_index_rejected(self):
        data,row=self.fixture()
        for key,value in [('name','wrong'),('crc32','00000000'),('size',1),('flag_bits',1)]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                read_indexed_member(WindowFile(data,0,len(data)),dict(row,**{key:value}))
    def test_bounded_decompression_and_window(self):
        data,row=self.fixture()
        with self.assertRaises(ValueError):read_indexed_member(WindowFile(data,0,len(data)),row,max_bytes=2)
        self.assertEqual(member_window([row]),(0,len(data)))
        with self.assertRaises(ValueError):member_window([row],max_span=2)
        with self.assertRaises(ValueError):member_window([row,dict(row,archive_url='other')])
    def test_corrupt_payload_rejected(self):
        data,row=self.fixture(zipfile.ZIP_STORED)
        mutated=bytearray(data)
        mutated[30+len(row['name'])]^=1
        with self.assertRaises(ValueError):read_indexed_member(WindowFile(bytes(mutated),0,len(data)),row)

if __name__=='__main__':unittest.main()
