# -*- coding: utf-8 -*-
"""下载候选图并按门店存放待核验区"""
import json, os, re, time, io
import urllib.request
from PIL import Image

BASE = os.path.join(os.path.dirname(__file__), '..')
cand = json.load(open(os.path.join(BASE, '_数据与评分', '照片候选.json'), encoding='utf-8'))
STAGE = os.path.join(BASE, '_数据与评分', '待核验图')
os.makedirs(STAGE, exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'

MAX_PER_STORE = 14
MIN_W, MIN_H = 500, 320


def safe(name):
    return re.sub(r'[\\/:*?"<>|]', '', name)


ok_all = {}
for store, items in cand.items():
    d = os.path.join(STAGE, safe(store))
    os.makedirs(d, exist_ok=True)
    kept, idx = [], 0
    for it in items:
        if len(kept) >= MAX_PER_STORE:
            break
        try:
            req = urllib.request.Request(it['murl'], headers={'User-Agent': UA, 'Referer': it.get('purl') or ''})
            raw = urllib.request.urlopen(req, timeout=20).read()
            if len(raw) < 30000:
                continue
            im = Image.open(io.BytesIO(raw))
            if im.width < MIN_W or im.height < MIN_H:
                continue
            if im.width / max(im.height, 1) > 3.0 or im.height / max(im.width, 1) > 3.0:
                continue
            idx += 1
            fn = '%02d.jpg' % idx
            rgb = im.convert('RGB')
            rgb.save(os.path.join(d, fn), 'JPEG', quality=88)
            rec = dict(file=fn, page=it.get('purl', ''), img=it['murl'],
                       title=it.get('title', ''), w=im.width, h=im.height)
            kept.append(rec)
        except Exception:
            continue
        time.sleep(0.15)
    ok_all[store] = kept
    print('%-14s 保留 %d' % (store, len(kept)))

json.dump(ok_all, open(os.path.join(BASE, '_数据与评分', '待核验清单.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
