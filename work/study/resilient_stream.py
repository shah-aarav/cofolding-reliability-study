"""Sequential compressed HTTP stream with exact-offset reconnection.

Keeps the caller's live decompressor intact through a dropped connection. It
CANNOT restore gzip state after a process has already exited. No archive cache.
"""
import hashlib
import http.client
import time
import urllib.error
import urllib.request


class ReconnectingStream:
    def __init__(self,url,size,cutoff,max_reconnects=8,opener=None):
        if size<=0 or not 0<=max_reconnects<=16:raise ValueError('Invalid source size/retry cap')
        self.url=url;self.size=size;self.cutoff=cutoff
        self.opener=opener or urllib.request.urlopen
        self.max_reconnects=max_reconnects
        self.position=0;self.reconnects=0;self.response=None
        self.md5=hashlib.md5();self.sha256=hashlib.sha256()

    def _open(self):
        if time.time()>=self.cutoff:raise TimeoutError('Acquisition cutoff reached')
        start=self.position
        request=urllib.request.Request(self.url,headers={
            'Range':f'bytes={start}-{self.size-1}','Accept-Encoding':'identity',
            'User-Agent':'ProteinLigandReliabilityResearch/0.1 reconnecting-stream'})
        response=self.opener(request,timeout=min(60,max(1,self.cutoff-time.time())))
        expected=f'bytes {start}-{self.size-1}/{self.size}'
        if response.status!=206 or response.headers.get('Content-Range')!=expected:
            response.close();raise ValueError('Exact stream continuation range not honored')
        encoding=response.headers.get('Content-Encoding')
        if encoding not in (None,'identity'):
            response.close();raise ValueError('Unexpected HTTP content transformation')
        self.response=response

    def close(self):
        if self.response is not None:self.response.close();self.response=None

    def _retry(self):
        self.close()
        if self.reconnects>=self.max_reconnects:raise IOError('Compressed stream reconnect cap reached')
        self.reconnects+=1

    def read(self,size=-1):
        if type(size) is not int or not 0<=size<=16_000_000:raise ValueError('Unbounded/oversized stream read forbidden')
        size=min(size,self.size-self.position)
        parts=[];remaining=size
        while remaining:
            if time.time()>=self.cutoff:raise TimeoutError('Acquisition cutoff reached')
            try:
                if self.response is None:self._open()
                try:chunk=self.response.read(remaining)
                except http.client.IncompleteRead as error:chunk=error.partial
                if len(chunk)>remaining:raise ValueError('Oversized compressed response')
                if chunk:
                    parts.append(chunk);self.position+=len(chunk);remaining-=len(chunk)
                    self.md5.update(chunk);self.sha256.update(chunk)
                if remaining:self._retry()
            except (OSError,urllib.error.URLError):
                # No returned bytes are committed; reread from the last exact
                # committed offset. Never continue from an assumed socket offset.
                if self.reconnects>=self.max_reconnects:raise
                self._retry()
        return b''.join(parts)

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
