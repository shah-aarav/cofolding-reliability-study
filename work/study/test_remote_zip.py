import io
import unittest
import zipfile
from remote_zip import RangeFile,bounded_member

class Response(io.BytesIO):
    def __init__(self,data,status,content_range):
        super().__init__(data)
        self.status=status
        self.headers={'Content-Range':content_range}

class RemoteZipTests(unittest.TestCase):
    def setUp(self):
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('predictions/confidence.json','{"ranking_score": 0.7}')
            z.writestr('large.bin',b'x'*10000)
        self.data=output.getvalue()

    def opener(self,request,timeout):
        spec=request.headers['Range'].split('=')[1]
        start,end=map(int,spec.split('-'))
        return Response(self.data[start:end+1],206,f'bytes {start}-{end}/{len(self.data)}')

    def test_zipfile_can_seek_and_verify_selected_member(self):
        with RangeFile('https://example.invalid/fixture.zip',len(self.data),opener=self.opener) as stream,zipfile.ZipFile(stream) as z:
            self.assertEqual(bounded_member(z,'predictions/confidence.json'),b'{"ranking_score": 0.7}')
            with self.assertRaises(RuntimeError):bounded_member(z,'large.bin',100)

    def test_server_ignoring_range_is_rejected_before_body(self):
        def opener(request,timeout):return Response(b'should-not-be-read',200,None)
        with RangeFile('https://example.invalid/fixture.zip',100,opener=opener) as stream:
            with self.assertRaises(RuntimeError):stream.read(10)
            self.assertEqual(stream.network_bytes,0)

    def test_network_cap_and_invalid_seeks(self):
        with RangeFile('https://example.invalid/fixture.zip',len(self.data),max_network_bytes=5,opener=self.opener) as stream:
            with self.assertRaises(RuntimeError):stream.read(6)
            with self.assertRaises(ValueError):stream.seek(-1)
            with self.assertRaises(ValueError):stream.seek(len(self.data)+1)

    def test_truncated_transfer_retry_remains_strict_and_budgeted(self):
        calls=[]
        def opener(request,timeout):
            calls.append(1)
            response=self.opener(request,timeout)
            if len(calls)==1:return Response(self.data[:1],response.status,response.headers['Content-Range'])
            return response
        with RangeFile('https://example.invalid/fixture.zip',len(self.data),max_network_bytes=20,max_attempts=3,retry_delay=0,opener=opener) as stream:
            self.assertEqual(stream.read(10),self.data[:10])
            self.assertEqual(stream.network_bytes,19)
            self.assertEqual(stream.requests,2)
        calls.clear()
        with RangeFile('https://example.invalid/fixture.zip',len(self.data),max_network_bytes=10,max_attempts=3,retry_delay=0,opener=opener) as stream:
            with self.assertRaises(RuntimeError):stream.read(10)
            self.assertEqual(stream.network_bytes,10)

if __name__=='__main__':unittest.main(verbosity=2)
