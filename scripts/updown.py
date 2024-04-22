from functools import partial
import os
import os.path as osp
import shutil
import sys
import cv2
from tqdm import tqdm


def _process_selected(updir, sel, func, procname, quality, testmode, backup=True):
    """A generic function that backups `sel` files to 'orig_<procname>' folder,
    then applies `func` to every image and overwrites originals with JPG `quality`
    - or, if `testmode` is `True`, instead of overwriting saves the results to
    backup folder as well (so you can do side-by-side comparison with originals).
    
    """
    if backup:
        bud = osp.join(updir, 'orig_' + procname)
        os.makedirs(bud, exist_ok=True)
        for fn in sel:
            pt = osp.join(updir, fn)
            dst = osp.join(bud, osp.basename(fn).replace('.', '_orig.'))
            shutil.copy(pt, dst)
        print('backed up %d files to %s' % (len(sel), bud))
    for fn in tqdm(sel, procname):
        pt = osp.join(updir, fn)
        im = cv2.imread(pt)
        if testmode:
            pt = osp.join(bud, osp.basename(fn).replace('.', '_%s.' % procname))
        cv2.imwrite(pt, func(im), [int(cv2.IMWRITE_JPEG_QUALITY), quality])

def _downscale_one(im, maxdim):
    h, w = im.shape[:2]
    scale = maxdim / max(h, w)
    new_size = (round(w * scale), round(h * scale))
    return cv2.resize(im, new_size, interpolation=cv2.INTER_AREA)
    return im

def downscale(updir, files, dims, maxdim, quality, testmode=False):
    sel = [fn for fn, (w, h) in zip(files, dims) if w > maxdim or h > maxdim]
    func = partial(_downscale_one, maxdim=maxdim)
    _process_selected(updir, sel, func, 'downscale', quality, testmode)

def compress(updir, files, maxkb, quality, testmode=False):
    """a.k.a resave with lower quality"""
    kbs = [round(osp.getsize(osp.join(updir, f)) / 1024) for f in tqdm(files, 'read sizes')]
    sel = [fn for fn, kb in zip(files, kbs) if kb > maxkb]
    _process_selected(updir, sel, lambda x: x, 'compress', quality, testmode)

def upscale(updir, files, dims, mindim, quality, upscaler, testmode=False):
    assert upscaler in ['cugan', 'esrgan', 'both']
    sel = [fn for fn, (w, h) in zip(files, dims) if w < mindim and h < mindim]
    #git clone https://github.com/bilibili/ailab.git
    #gdown 1jAJyBf2qKe2povySwsGXsVMnzVyQzqDD --folder -O ailab/Real-CUGAN/weights_v3
    if upscaler in ['cugan', 'both']:
        libp = osp.join(os.getcwd(), 'ailab', 'Real-CUGAN')
        if libp not in sys.path:
            sys.path.append()
        from upcunet_v3 import RealWaifuUpScaler
        pt = 'ailab/Real-CUGAN/weights_v3/up2x-latest-no-denoise.pth'
        modelCU = RealWaifuUpScaler(2, pt, half=False, device='cpu')
        func = partial(modelCU, tile_mode=5, cache_mode=2, alpha=1)
        _process_selected(updir, sel, lambda x: func(x)[:, :, ::-1], 'cugan', quality, testmode)
    #pip install basicsr
    #git clone https://github.com/xinntao/Real-ESRGAN.git
    #wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth -P Real-ESRGAN/weights
    #cd Real-ESRGAN && python setup.py develop
    if upscaler in ['esrgan', 'both']:
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer
        pt = '/weights/RealESRGAN_x4plus_anime_6B.pth'
        modelESR = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=4)
        wrapper = RealESRGANer(scale=2, model_path=pt, model=modelESR)
        func = partial(wrapper.enhance, outscale=2)
        _process_selected(updir, sel, lambda x: func(x)[0], 'esrgan', quality, testmode, backup=upscaler!='both')


if __name__ == '__main__':
    from utils import list_files, read_dimensions
    updir = 'D:/Data/AniCharDetSet/anime'
    files = list_files(updir, excl_sub='del')
    dims = read_dimensions(updir, files)
    downscale(updir, files, dims, maxdim=1920, quality=75)
    compress(updir, files, maxkb=700, quality=80)