import os.path as osp

import cv2
import numpy as np
import scipy.fftpack
from sklearn.metrics.pairwise import cosine_distances
from tqdm import tqdm

from .utils import read_imsize_binary


def calc_embeddings(rdir, files, method):
    emb = []
    for fn in tqdm(files):
        pt = osp.join(rdir, fn)
        im = cv2.imread(pt, cv2.IMREAD_GRAYSCALE)
        emb.append(_ahash(im))
    return np.stack(emb)
    

def calc_distances_total(rdir, files1, files2, emb1, emb2, method, rang, topk, chunk_size):
    ret = []
    # taking a very big number so that chunk_size=None is equal to "don't chunk, do all at once"
    c = chunk_size if (chunk_size is not None) else 2 ** 32
    with tqdm(total=len(files1)) as pbar:
        for i in range(0, len(files1), c):
            a = emb1[i:i+c]
            b = emb1[i:] if (emb2 is None) else emb2
            g1 = files1[i:i+c]
            g2 = files1[i:] if (files2 is None) else files2
            d = distance_matrix(a, b, method, emb2 is None)
            s = select_distances(d, g1, g2, rdir, rang, topk)
            ret.extend(s)
            pbar.update(len(a))
    ret = sorted(ret, key=lambda x: x[-1])
    return ret


def calc_distances_group(rdir, groups1, groups2, emb1, emb2, method, rang, topk):
    ret = []
    for id_, g1 in tqdm(groups1):
        if groups2 is None:
            g2 = g1
        else:
            if id_ not in groups2:
                continue
            g2 = groups2[id_]
        d = distance_matrix(emb1, emb2, method, groups2 is None)
        s = select_distances(d, g1, g2, rdir, rang, topk)
        ret.extend(s)
    ret = sorted(ret, key=lambda x: x[-1])
    return ret


def distance_matrix(a, b, method, with_self):
    if method == 'hamming':
        # e.g. (15, 64) (40, 64) => (15, 40)
        d = np.count_nonzero(a[:, None] != b, axis=-1).astype(np.uint8)
    elif method == 'cosine':
        d = cosine_distances(a, b)
        #an = a / np.linalg.norm(a, axis=1, keepdims=True)
        #bn = b / np.linalg.norm(b, axis=1, keepdims=True)
        #d = 1 - an @ bn.T
    if with_self:
        lotri = np.tri(d.shape[0])
        d[:, :d.shape[0]] += lotri.astype(d.dtype) * 100
    return d


def select_distances(d, g1, g2, root_dir, dist_range, topk):
    ret = []
    cond1, cond2, cond3 = True, True, True
    if topk:
        msk = np.zeros(d.shape, dtype=int)
        ind = np.argpartition(d, topk-1, axis=1)[:, :topk]
        np.put_along_axis(msk, ind, 1, axis=1)
        cond1 = d * msk > 0
    if dist_range:
        if not isinstance(dist_range, tuple):
            cond2 = d <= dist_range
        else:
            lo, hi = dist_range
            cond2 = d >= lo
            cond3 = d <= hi
    m = np.argwhere(cond1 & cond2 & cond3)
    for i, j in m:
        fn1, pt1 = g1[i], osp.join(root_dir, g1[i])
        fn2, pt2 = g2[j], osp.join(root_dir, g2[j])
        k1, wh1 = round(osp.getsize(pt1) / 1024), read_imsize_binary(pt1)
        k2, wh2 = round(osp.getsize(pt2) / 1024), read_imsize_binary(pt2)
        if k1 > k2 or k1 == k2 and wh1[0] * wh1[1] > wh2[0] * wh2[1]:
            ln = (fn1, fn2, d[i, j])
        else:
            ln = (fn2, fn1, d[i, j])
        ret.append(ln)
    return ret


def _ahash(img):
    tiny = cv2.resize(img, (8, 8))
    diff = tiny > np.mean(tiny)
    return 1 * diff.flatten()


def _phash(img, like_imagehash_lib=False):
    tiny = cv2.resize(img, (32, 32))
    dct = scipy.fftpack.dct(scipy.fftpack.dct(tiny, axis=0), axis=1)
    dct = dct[:8, :8]
    avg = np.median(dct) if like_imagehash_lib else (sum(dct) - dct[0, 0]) / 63
    diff = dct > avg
    return 1 * diff.flatten() #1* => True/False to 1/0


def _dhash(img):
    tiny = cv2.resize(img, (9, 8))
    diff = tiny[:, 1:] > tiny[:, :-1]
    return 1 * diff.flatten()