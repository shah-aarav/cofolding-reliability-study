import gzip
import io
import time
import unittest
from resilient_stream import ReconnectingStream


class Response(io.BytesIO):
    def __init__(self,data,start,total):
        super().__init__(data);self.status=206
        self.headers={'Content-Range':f'bytes {start}-{total-1}/{total}'}


class ResilientStreamTests(unittest.TestCase):
    def test_live_gzip_survives_multiple_connection_truncations(self):
        expected=b'Input only synthetic data.'*500
        raw=gzip.compress(expected);starts=[]
        def opener(request,timeout):
            start=int(request.headers['Range'].split('=')[1].split('-')[0]);starts.append(start)
            return Response(raw[start:start+13],start,len(raw))
        with ReconnectingStream('https://example.invalid',len(raw),time.time()+30,max_reconnects=16,opener=opener) as stream:
            with gzip.GzipFile(fileobj=stream) as decoder:self.assertEqual(decoder.read(),expected)
            self.assertEqual(stream.position,len(raw))
            self.assertGreater(len(starts),1)

    def test_ignored_ranges_and_retry_budget_rejected(self):
        def ignored(request,timeout):
            response=Response(b'x',0,3);response.status=200;return response
        with ReconnectingStream('https://example.invalid',3,time.time()+30,opener=ignored) as stream:
            with self.assertRaises(ValueError):stream.read(3)
        def empty(request,timeout):return Response(b'',0,3)
        with ReconnectingStream('https://example.invalid',3,time.time()+30,max_reconnects=1,opener=empty) as stream:
            with self.assertRaises(OSError):stream.read(3)
            self.assertEqual(stream.position,0)


if __name__=='__main__':unittest.main()
