"""Read individual public ZIP members through strict bounded HTTP Range requests."""
import io
import http.client
import time
import urllib.error
import urllib.request
import zipfile

class RangeFile(io.RawIOBase):
    def __init__(self,url,size,max_network_bytes=160_000_000,max_read_bytes=128_000_000,opener=None,max_attempts=1,retry_delay=.5):
        super().__init__()
        self.url=url
        self.size=int(size)
        self.position=0
        self.max_network_bytes=max_network_bytes
        self.max_read_bytes=max_read_bytes
        self.network_bytes=0
        self.requests=0
        self.opener=opener or urllib.request.urlopen
        if type(max_attempts) is not int or not 1<=max_attempts<=3:raise ValueError('Invalid retry budget')
        self.max_attempts=max_attempts
        self.retry_delay=retry_delay

    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=io.SEEK_SET):
        if whence==io.SEEK_SET:position=offset
        elif whence==io.SEEK_CUR:position=self.position+offset
        elif whence==io.SEEK_END:position=self.size+offset
        else:raise ValueError('Invalid seek mode')
        if position<0 or position>self.size:raise ValueError('Remote seek outside archive')
        self.position=int(position)
        return self.position

    def read(self,n=-1):
        if self.closed:raise ValueError('Read on closed remote archive')
        if n<0:n=self.size-self.position
        n=min(n,self.size-self.position)
        if n==0:return b''
        if n>self.max_read_bytes or self.network_bytes+n>self.max_network_bytes:
            raise RuntimeError('Remote ZIP network/read budget exceeded')
        start=self.position
        end=start+n-1
        data=bytearray()
        for attempt in range(self.max_attempts):
            remaining=n-len(data)
            current=start+len(data)
            if self.network_bytes+remaining>self.max_network_bytes:raise RuntimeError('Remote ZIP retry network budget exceeded')
            request=urllib.request.Request(self.url,headers={'Range':f'bytes={current}-{end}','User-Agent':'ProteinLigandReliabilityResearch/0.1','Accept-Encoding':'identity'})
            self.requests+=1
            try:
                with self.opener(request,timeout=90) as response:
                    expected=f'bytes {current}-{end}/{self.size}'
                    if response.status!=206 or response.headers.get('Content-Range')!=expected:
                        raise RuntimeError('Server did not honor the exact requested byte range; body not consumed')
                    # Reserve even a truncated response's full requested bytes.
                    self.network_bytes+=remaining
                    chunk=response.read(remaining+1)
                    if len(chunk)>remaining:raise IOError('Oversized range body rejected')
                    data.extend(chunk)
                    if len(data)!=n:raise IOError(f'Truncated range response: expected tail {remaining}, received {len(chunk)}, range {current}-{end}, Content-Length {response.headers.get("Content-Length")}, encoding {response.headers.get("Content-Encoding")}')
                break
            except (OSError,urllib.error.URLError,http.client.IncompleteRead):
                if attempt+1==self.max_attempts:raise
                time.sleep(self.retry_delay*(attempt+1))
        self.position+=n
        return bytes(data)

def bounded_member(archive,name,max_bytes=5_000_000):
    info=archive.getinfo(name)
    if info.is_dir() or info.flag_bits&1:raise ValueError('Directory or encrypted member is ineligible')
    if info.file_size>max_bytes or info.compress_size>max_bytes:raise RuntimeError('Member exceeds decompression budget')
    # ZipFile.read also verifies the member CRC. A partial archive read does not
    # verify the entire archive MD5, and must not be described as doing so.
    data=archive.read(info)
    if len(data)!=info.file_size:raise IOError('Member size mismatch')
    return data
