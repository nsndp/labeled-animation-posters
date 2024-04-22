import os
import os.path as osp
import struct
from tqdm import tqdm

IMG_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.ppm', '.bmp', '.pgm', '.tif', '.tiff', '.webp')

def is_image(e):
    return e.is_file() and e.name.lower().endswith(IMG_EXTENSIONS)

def list_files(root_dir, incl_sub='all', excl_sub=None):
    files = [e.name for e in os.scandir(root_dir) if is_image(e)]
    if incl_sub:
        sub = [e.name for e in os.scandir(root_dir) if e.is_dir()]
        sub = [d for d in sub if incl_sub == 'all' or d in incl_sub.split(',')]
        sub = [d for d in sub if excl_sub is None or d not in excl_sub.split(',')]
        for d in sub:
            files.extend([osp.join(d, e.name) for e in os.scandir(osp.join(root_dir, d)) if is_image(e)])
    return files

def read_dimensions(root_dir, files):
    dims = []
    for fn in tqdm(files, 'reading dimensions'):
        pt = osp.join(root_dir, fn)
        dims.append(read_imsize_binary(pt))
    return dims
    
def read_imsize_binary(path):
    """Extracts the width and height of an image located at ``path``
    without reading all data by analyzing the beginning as raw bytes.
    
    Sources:
    https://github.com/scardine/image_size/blob/master/get_image_size.py
    JPG: https://stackoverflow.com/a/63479164
    JPG: https://stackoverflow.com/a/35443269
    PNG: https://stackoverflow.com/a/5354562
    """
    w, h = None, None
    with open(path, 'rb') as f:
        start = f.read(2)
        if start == b'\xFF\xD8': # JPEG
            b = f.read(1)
            while (b and ord(b) != 0xDA):
                while (ord(b) != 0xFF): b = f.read(1)
                while (ord(b) == 0xFF): b = f.read(1)
                if (ord(b) == 0x01 or ord(b) >= 0xD0 and ord(b) <= 0xD9):
                    b = f.read(1)
                elif (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                    f.read(3)
                    h, w = struct.unpack('>HH', f.read(4))
                    break
                else:
                    seg_len = int(struct.unpack(">H", f.read(2))[0])
                    f.read(seg_len - 2)
                    b = f.read(1)
        elif start == b'\x89\x50': # PNG
            f.read(14)
            w, h = struct.unpack(">LL", f.read(8))
    return w, h
    
def check_if_valid_jpgs(files, updir):
    sizes = []
    fails = []
    for ff in tqdm(files):
        pth = osp.join(updir, ff)
        w, h = read_imsize_binary(pth)
        if w is None or h is None:
            fails.append(ff)
        else:
            sizes.append((w, h))
    return fails, sizes