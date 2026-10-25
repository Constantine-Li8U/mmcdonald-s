# -*- coding: utf-8 -*-
"""针对缺图门店，二次图片检索 + 下载 + 联系表"""
import re, json, os, io, time, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.join(os.path.dirname(__file__), '..')
OUTD = os.path.join(BASE, '_数据与评分', '待核验图2')
SHEET = os.path.join(BASE, '_数据与评分', '联系表2')
os.makedirs(OUTD, exist_ok=True)
os.makedirs(SHEET, exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36'

Q = {
    '丽都': ['麦当劳 丽都大酒店 北京路 二楼 窗边', '北京路182号 麦当劳 甜品站'],
    '东风西': ['麦当劳 东风西路 流花湖 广州', '东风西路140号 麦当劳'],
    '总统': ['麦当劳 总统大酒店 岗顶 广州', '南方电脑城 麦当劳 天河路'],
    '广百': ['麦当劳 北京路 广百 新翼', '广百新翼 麦当劳 二楼'],
    '江湾': ['麦当劳 江湾阳光天地 沿江中路', '江湾阳光天地 麦当劳 广州'],
    '宜安': ['麦当劳 宜安广场 建设六马路', '宜安广场 麦当劳 广州'],
}


def search(q):
    u = 'https://cn.bing.com/images/search?q=%s&qft=+filterui:photo-photo&form=IRFLTR' % urllib.parse.quote(q)
    h = urllib.request.urlopen(urllib.request.Request(
        u, headers={'User-Agent': UA, 'Accept-Language': 'zh-CN,zh'}), timeout=25).read().decode('utf-8', 'ignore')
    out = []
    for m in re.finditer(r'murl&quot;:&quot;(.*?)&quot;', h):
        seg = h[max(0, m.start() - 3500):m.start() + 2000]
        p = re.findall(r'purl&quot;:&quot;(.*?)&quot;', seg)
        out.append((m.group(1), p[-1] if p else ''))
    return out


FONT = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 22)
for store, qs in Q.items():
    d = os.path.join(OUTD, store)
    os.makedirs(d, exist_ok=True)
    seen, cand = set(), []
    for q in qs:
        try:
            for mu, pu in search(q):
                if mu in seen:
                    continue
                seen.add(mu)
                cand.append((mu, pu))
        except Exception as e:
            print(store, 'search fail', e)
        time.sleep(2.5)
    kept, n = [], 0
    for mu, pu in cand:
        if len(kept) >= 10:
            break
        try:
            raw = urllib.request.urlopen(urllib.request.Request(
                mu, headers={'User-Agent': UA, 'Referer': pu}), timeout=20).read()
            if len(raw) < 30000:
                continue
            im = Image.open(io.BytesIO(raw))
            if im.width < 480 or im.height < 320:
                continue
            n += 1
            fn = '%02d.jpg' % n
            im.convert('RGB').save(os.path.join(d, fn), 'JPEG', quality=88)
            kept.append((fn, pu, mu, im.width, im.height))
        except Exception:
            continue
        time.sleep(0.2)
    print(store, 'cand', len(cand), 'kept', len(kept))
    # 联系表
    files = sorted(f for f in os.listdir(d) if f.lower().endswith('.jpg'))
    CW, CH, COLS = 340, 255, 5
    rows = (len(files) + COLS - 1) // COLS or 1
    s = Image.new('RGB', (CW * COLS, CH * rows), 'white')
    dr = ImageDraw.Draw(s)
    for i, fn in enumerate(files):
        im = Image.open(os.path.join(d, fn)).convert('RGB')
        im.thumbnail((CW - 8, CH - 32))
        x, y = (i % COLS) * CW, (i // COLS) * CH
        s.paste(im, (x + 4, y + 28))
        dr.text((x + 6, y + 2), fn[:2], fill='black', font=FONT)
    s.save(os.path.join(SHEET, store + '.jpg'), 'JPEG', quality=82)
    json.dump([dict(file=a, page=b, img=c, w=dd, h=e) for a, b, c, dd, e in kept],
              open(os.path.join(d, '_info.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
