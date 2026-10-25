# -*- coding: utf-8 -*-
"""把候选图拼成带序号的联系表，供目视核验。"""
import glob
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(BASE, '_数据与评分', '候选图')
OUT = os.path.join(BASE, '_数据与评分', '联系表_候选')
FONT = 'C:/Windows/Fonts/msyh.ttc'


def sheet(store, cols=5, cw=340, ch=280, chunk=0):
    d = os.path.join(CAND, store)
    files = sorted(glob.glob(os.path.join(d, '*.jpg')))
    if not files:
        print('%s: 无候选' % store)
        return None
    if chunk and len(files) > chunk:
        outs = []
        for i in range(0, len(files), chunk):
            outs.append(sheet_files(store, files[i:i + chunk], cols, cw, ch,
                                    suffix='_%d' % (i // chunk + 1)))
        return outs
    return sheet_files(store, files, cols, cw, ch)


def sheet_files(store, files, cols=5, cw=340, ch=280, suffix=''):
    d = os.path.join(CAND, store)
    info = {}
    ip = os.path.join(d, '_info.json')
    if os.path.exists(ip):
        for it in json.load(open(ip, encoding='utf-8')):
            info[it.get('file')] = it
    rows = (len(files) + cols - 1) // cols
    s = Image.new('RGB', (cw * cols, ch * rows), 'white')
    dr = ImageDraw.Draw(s)
    f = ImageFont.truetype(FONT, 20)
    fs = ImageFont.truetype(FONT, 15)
    for i, fp in enumerate(files):
        fn = os.path.basename(fp)
        im = Image.open(fp).convert('RGB')
        w, h = im.size
        im.thumbnail((cw - 10, ch - 46))
        x, y = (i % cols) * cw, (i // cols) * ch
        s.paste(im, (x + 5, y + 40))
        dr.rectangle([x + 2, y + 2, x + cw - 2, y + ch - 2], outline='#cccccc')
        dr.text((x + 8, y + 4), '%s  %dx%d' % (fn.replace('.jpg', ''), w, h),
                fill='black', font=f)
        t = (info.get(fn, {}).get('title') or '')[:30]
        dr.text((x + 8, y + 24), t, fill='#666666', font=fs)
    os.makedirs(OUT, exist_ok=True)
    op = os.path.join(OUT, store + suffix + '.jpg')
    s.save(op, 'JPEG', quality=80)
    print('%s -> %s (%d 张)' % (store, op, len(files)))
    return op


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    chunk = 0
    for a in sys.argv[1:]:
        if a.startswith('--chunk='):
            chunk = int(a.split('=')[1])
    targets = args or sorted(os.listdir(CAND))
    for t in targets:
        if os.path.isdir(os.path.join(CAND, t)):
            sheet(t, chunk=chunk)
