import os
import os.path as osp
import re

import numpy as np

import sys
topdir = osp.dirname(osp.dirname(osp.abspath(__file__)))
sys.path.append(topdir)

from tools.gui_comparer import DelCandidatesChecker
from tools.gui_explorer import GroupExplorer
from scripts.distance import calc_embeddings, calc_distances_total, calc_distances_group
from scripts.utils import list_files

def _get_groups(files, prefix='MAL'):
    g, ret = [], []
    i, s, prev = 0, 0, None
    while i < len(files):
        #f = files[i][0] if isinstance(files[i], tuple) else files[i]
        f = files[i]
        anid = re.search(prefix + '([0-9]{5})', f).groups()[0]
        if not prev or prev == anid:
            g.append(files[i])
        else:
            ret.append((int(prev), (s, i, g)))
            g = [files[i]]
            s = i
        prev = anid
        i += 1
    ret.append((int(prev), (s, len(files), g)))
    return ret


def _remove_chosen(root_dir, files_to_delete):
    ddir = osp.join(root_dir, 'del')
    if not osp.exists(ddir):
        os.mkdir(ddir)
    c = 0
    for fn in files_to_delete:
        src = osp.join(root_dir, fn)
        if osp.exists(src):
            dst = osp.join(ddir, osp.split(fn)[-1])
            os.rename(src, dst)
            c += 1
    print('%d files moved to "del" directory' % c)


def browse_groups(root_dir, start=0, stop=None):
    groups = _get_groups(list_files(root_dir))[start:stop]
    groups = [g[1][2] for g in groups if len(g[1]) > 1]
    #for g in groups: print(g)
    gui = GroupExplorer()
    gui.init_data(root_dir, groups)
    sel = gui.run()
    #_remove_chosen(root_dir, sel)
    #gui.root.destroy()
    return sel


def remove_duplicates(rdir, files1, files2, mode, emb, dist, rang=None,
                      topk=3, chunk_size=10):
    assert mode in ['total', 'group']
    assert dist in ['cosine', 'hamming']
    assert isinstance(emb, np.ndarray) or emb in ['vit', 'ahash', 'phash', 'dhash'] or emb.startswith('file')
    if isinstance(emb, np.ndarray):
        emb1 = emb
        emb2 = emb if files2 else None
    elif emb.startswith('file'):
        # expected format: 'file:<files1_emb.npy>[;<files2_emb.npy>]'
        emb1 = np.load(emb.split(':')[1].split(';')[0])[:len(files1)]
        emb2 = np.load(emb.split(':')[1].split(';')[1])[:len(files2)] if files2 else None
    else:
        print('Calculating embeddings')
        emb1 = calc_embeddings(rdir, files1, emb)
        emb2 = calc_embeddings(rdir, files2, emb) if files2 else None
    print('Calculating distances')
    if mode == 'total':
        cand = calc_distances_total(rdir, files1, files2, emb1, emb2, dist, rang, topk, chunk_size)
    else:
        groups1 = _get_groups(files1)
        groups2 = _get_groups(files2) if files2 else None
        cand = calc_distances_group(rdir, groups1, dict(groups2), emb1, emb2, dist, rang, topk)
    print('%d candidates found' % len(cand))
    if cand:
        gui = DelCandidatesChecker(delay=None)
        choices = gui(rdir, cand)
        sel = [ch for ch in choices if ch != 0 and ch != -1]
        #_remove_chosen(rdir, sel)
        #gui.root.destroy()
        return sel, cand
    
    
def match_sites_ids(folder, match_fn='ACDD/wa_anime_main.csv'):
    """Rename WA<world_art_id>_<number>.jpg -> MAL<mal_id>_<world_art_id>_<number>.jpg"""
    files = list_files(folder)
    with open(match_fn, encoding='utf-8') as f:
       matches = [ln.split(',')[:2] for ln in f.read().splitlines()[1:]]
       matches = [(int(m[0]), '' if m[1] == '""' else int(m[1])) for m in matches]
       matches = dict(matches)
    log, c1, c2 = [], 0, 0
    for fn in files:
        wid = int(fn.split(os.sep)[-1][2:7])
        mid = matches[wid]
        if mid:
            head, tail = osp.split(fn)
            fnnew = head + 'MAL%05d' % int(mid) + '_' + tail
            log.append((fn, fnnew))
            c1 += 1
            os.rename(osp.join(folder, fn), osp.join(folder, fnnew))
        else:
            log.append((fn, 'no mal_id'))
            c2 += 1
    print('%d files renamed' % c1)
    print('%d files skipped' % c2)
    return log