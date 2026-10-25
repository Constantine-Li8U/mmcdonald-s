# -*- coding: utf-8 -*-
"""解析高德榜单 HTML，输出结构化 JSON"""
import re, json, os, glob

RAW = os.path.join(os.path.dirname(__file__), '..', '_数据与评分', 'raw')
OUT = os.path.join(os.path.dirname(__file__), '..', '_数据与评分', '榜单原始抓取_20261024.json')


def body_text(html):
    b = html.split('</head>', 1)[1] if '</head>' in html else html
    t = re.sub(r'<script.*?</script>', '', b, flags=re.S)
    t = re.sub(r'<style.*?</style>', '', t, flags=re.S)
    t = re.sub(r'<[^>]+>', '|', t)
    t = re.sub(r'\|+', '|', t)
    return t


def parse(html):
    toks = [x.strip() for x in body_text(html).split('|')]
    items = []
    i = 0
    while i < len(toks) - 7:
        # 结构: 名次, 店名, 品类, '⭐', 评分, '📍', 区, 地址, [📌, 商圈], 品类
        if re.fullmatch(r'\d{1,2}', toks[i]) and toks[i + 3] == '⭐' and toks[i + 5] == '📍':
            rank = int(toks[i])
            name = toks[i + 1]
            cat = toks[i + 2]
            rating = toks[i + 4]
            dist = toks[i + 6]
            k = i + 7
            if k < len(toks) and toks[k] == '':
                k += 1
            addr = toks[k] if k < len(toks) else ''
            area = ''
            j = k + 1
            if j + 1 < len(toks) and toks[j] == '📌':
                area = toks[j + 1]
                j += 2
            if re.fullmatch(r'\d{1,2}', name) or not name:
                i += 1
                continue
            items.append(dict(rank=rank, name=name, category=cat,
                              rating=float(rating), district=dist,
                              address=addr, area=area))
            i = j
            continue
        i += 1
    # 去重保序
    seen, out = set(), []
    for it in items:
        k = (it['rank'], it['name'])
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out[:10]


def main():
    res = {}
    for fp in sorted(glob.glob(os.path.join(RAW, '*.html'))):
        key = os.path.basename(fp).replace('.html', '')
        html = open(fp, encoding='utf-8', errors='ignore').read()
        res[key] = {'source': 'https://ranks.amap.com/ranking/' + key,
                    'items': parse(html)}
    json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for k, v in res.items():
        print('##', k, len(v['items']))
        for it in v['items']:
            print(' ', it['rank'], it['name'], it['rating'], it['district'], it['address'], it['area'])


if __name__ == '__main__':
    main()
