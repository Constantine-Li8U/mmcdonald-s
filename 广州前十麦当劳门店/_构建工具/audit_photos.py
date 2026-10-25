# -*- coding: utf-8 -*-
"""审计交付照片：分辨率、体积、清晰度、跨店/同店近似重复。只读不修改。"""
import glob
import hashlib
import json
import os

from PIL import Image, ImageFilter, ImageStat

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ahash(im, n=16):
    g = im.convert('L').resize((n, n), Image.LANCZOS)
    px = list(g.getdata())
    avg = sum(px) / len(px)
    return ''.join('1' if p > avg else '0' for p in px)


def ham(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def sharpness(im):
    """边缘强度标准差，数值越高越锐利（同尺寸下可比）。"""
    g = im.convert('L')
    w, h = g.size
    if max(w, h) > 800:
        s = 800 / max(w, h)
        g = g.resize((int(w * s), int(h * s)), Image.LANCZOS)
    e = g.filter(ImageFilter.FIND_EDGES)
    return round(ImageStat.Stat(e).stddev[0], 2)


def grade(w, h, sh):
    long_edge = max(w, h)
    if long_edge >= 1000 and sh >= 12:
        return '清晰'
    if long_edge >= 600 and sh >= 7:
        return '一般'
    return '偏低'


def main():
    rows = []
    for fp in sorted(glob.glob(os.path.join(BASE, '[0-9][0-9]_*', 'photos', '*.jpg'))):
        store = os.path.basename(os.path.dirname(os.path.dirname(fp)))
        try:
            im = Image.open(fp)
            w, h = im.size
            sh = sharpness(im)
            ah = ahash(im)
        except Exception as e:
            rows.append(dict(store=store, file=os.path.basename(fp), error=str(e)))
            continue
        rows.append(dict(
            store=store, file=os.path.basename(fp), w=w, h=h,
            kb=round(os.path.getsize(fp) / 1024),
            md5=hashlib.md5(open(fp, 'rb').read()).hexdigest(),
            ahash=ah, sharp=sh, grade=grade(w, h, sh),
        ))

    # 近似重复检测
    dups = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            if 'ahash' not in a or 'ahash' not in b:
                continue
            d = ham(a['ahash'], b['ahash'])
            if d <= 12:
                dups.append(dict(a='%s/%s' % (a['store'], a['file']),
                                 b='%s/%s' % (b['store'], b['file']),
                                 dist=d, same_store=a['store'] == b['store']))

    out = dict(total=len(rows), rows=rows, dups=dups)
    json.dump(out, open(os.path.join(BASE, '_数据与评分', '照片审计.json'), 'w',
                        encoding='utf-8'), ensure_ascii=False, indent=1)

    cur = None
    for r in rows:
        if r['store'] != cur:
            print('\n## %s' % r['store'])
            cur = r['store']
        if 'error' in r:
            print('  %-36s ERROR %s' % (r['file'], r['error']))
        else:
            print('  %-36s %4dx%-4d %4dKB 锐度%-6s %s'
                  % (r['file'], r['w'], r['h'], r['kb'], r['sharp'], r['grade']))
    print('\n合计 %d 张' % len(rows))
    for g in ('清晰', '一般', '偏低'):
        print('  %s: %d' % (g, sum(1 for r in rows if r.get('grade') == g)))
    if dups:
        print('\n近似重复 %d 组：' % len(dups))
        for d in dups[:15]:
            print('  %s <-> %s (距离%d)' % (d['a'], d['b'], d['dist']))
    else:
        print('\n无近似重复')


if __name__ == '__main__':
    main()
