"""Strictly bounded numeric/structured NPZ input inspection; never unpickle."""
import io
import math
from pathlib import Path
import zipfile
import numpy as np
from stream_inventory import safe_member

def read_npz_arrays(path,allowed_names,max_total_bytes=10_000_000,max_arrays=32):
    path=Path(path)
    if path.stat().st_size>max_total_bytes:raise ValueError('NPZ compressed file exceeds budget')
    result={}
    with zipfile.ZipFile(path) as archive:
        infos=archive.infolist()
        if len(infos)>max_arrays or sum(i.file_size for i in infos)>max_total_bytes:
            raise ValueError('NPZ decompressed size/count exceeds budget')
        for info in infos:
            if not safe_member(info.filename) or info.flag_bits&1 or info.is_dir():raise ValueError('Unsafe NPZ member')
            if not info.filename.endswith('.npy'):raise ValueError('Non-NPY member in input NPZ')
            name=info.filename[:-4]
            if name not in allowed_names:continue
            if name in result:raise ValueError('Duplicate named NPZ array')
            raw=archive.read(info)  # CRC checked by zipfile; size prechecked.
            stream=io.BytesIO(raw)
            version=np.lib.format.read_magic(stream)
            if version==(1,0):shape,fortran,dtype=np.lib.format.read_array_header_1_0(stream)
            elif version==(2,0):shape,fortran,dtype=np.lib.format.read_array_header_2_0(stream)
            else:raise ValueError('Unsupported NPY header version')
            if dtype.hasobject:raise ValueError('Object arrays/pickle are forbidden')
            if any(type(d) is not int or d<0 for d in shape):raise ValueError('Invalid NPY shape')
            size=math.prod(shape)*dtype.itemsize
            if size>max_total_bytes or stream.tell()+size!=len(raw):raise ValueError('NPY header/data size mismatch')
            array=np.load(io.BytesIO(raw),allow_pickle=False)
            result[name]=array
    return result
