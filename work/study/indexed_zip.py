"""Bounded indexed ZIP member reads, without rereading a huge central directory.

Only stored and raw-DEFLATE members are supported. Index provenance is retained;
member CRC and SHA256 are checked, not the checksum of the entire remote ZIP.
"""
import hashlib
import struct
import zlib
from remote_zip import RangeFile

HEADER=struct.Struct('<4s5H3I2H')

def read_indexed_member(stream,row,max_bytes=5_000_000):
    size=int(row['size'])
    compressed=int(row['compressed_size'])
    offset=int(row['header_offset'])
    if min(size,compressed,offset)<0 or max(size,compressed)>max_bytes:
        raise ValueError('Member size/offset outside bounded policy')
    if row.get('directory') or row['flag_bits']&1:
        raise ValueError('Directory/encrypted member rejected')
    if row['compress_type'] not in (0,8):raise ValueError('Unsupported compression method')
    stream.seek(offset)
    header=stream.read(HEADER.size)
    if len(header)!=HEADER.size:raise IOError('Truncated local ZIP header')
    signature,version,flags,method,mtime,mdate,crc,csize,usize,nlen,xlen=HEADER.unpack(header)
    if signature!=b'PK\x03\x04':raise ValueError('Local ZIP signature mismatch')
    if flags!=row['flag_bits'] or method!=row['compress_type']:
        raise ValueError('Local ZIP metadata does not match central index')
    name=stream.read(nlen).decode('utf-8' if flags&0x800 else 'cp437')
    if name!=row['name']:raise ValueError('Local ZIP member name mismatch')
    # ZIP64 sizes may be in extra fields, and bit 3 may defer CRC/sizes to a
    # descriptor. The pinned central-directory values remain authoritative.
    if not flags&8:
        if crc!=int(row['crc32'],16):raise ValueError('Local CRC differs from central index')
        if csize not in (compressed,0xffffffff) or usize not in (size,0xffffffff):
            raise ValueError('Local sizes differ from central index')
    payload_offset=offset+HEADER.size+nlen+xlen
    if payload_offset+compressed>stream.size:raise ValueError('Member outside remote archive')
    stream.seek(payload_offset)
    packed=stream.read(compressed)
    if method==0:
        data=packed
    else:
        decoder=zlib.decompressobj(-15)
        data=decoder.decompress(packed,size+1)
        if len(data)>size or not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:
            raise ValueError('Invalid or oversized DEFLATE member')
    if len(data)!=size:raise ValueError('Decompressed size mismatch')
    if zlib.crc32(data)&0xffffffff!=int(row['crc32'],16):raise ValueError('Member CRC mismatch')
    return data,{'sha256':hashlib.sha256(data).hexdigest(),'crc32_verified':True,'whole_archive_checksum_verified':False}

class WindowFile:
    """Read-only adapter for one bounded contiguous archive range already in RAM."""
    def __init__(self,data,start,archive_size):
        self.data=data
        self.start=start
        self.size=archive_size
        self.position=start
    def seek(self,offset):
        if not self.start<=offset<=self.start+len(self.data):raise ValueError('Seek outside fetched window')
        self.position=offset
    def read(self,n):
        relative=self.position-self.start
        if n<0 or relative+n>len(self.data):raise ValueError('Read outside fetched window')
        value=self.data[relative:relative+n]
        self.position+=n
        return value

def member_window(rows,max_span=20_000_000):
    """Conservative ZIP header allowance, clipped by archive end."""
    if not rows:raise ValueError('Empty member group')
    archives={(r['archive_url'],r['archive_size']) for r in rows}
    if len(archives)!=1:raise ValueError('Cannot combine different archives')
    start=min(r['header_offset'] for r in rows)
    end=min(rows[0]['archive_size'],max(r['header_offset']+30+65535+65535+r['compressed_size'] for r in rows))
    if end-start>max_span:raise ValueError('Member group exceeds network window budget')
    return start,end
