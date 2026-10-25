# -*- coding: utf-8 -*-
"""候选池合并、去重、过滤与 A 维度（榜单表现）计算"""
import json, os, re
from collections import defaultdict

BASE = os.path.join(os.path.dirname(__file__), '..', '_数据与评分')
data = json.load(open(os.path.join(BASE, '榜单原始抓取_20261024.json'), encoding='utf-8'))

GZ = ['越秀区', '荔湾区', '海珠区', '天河区', '白云区', '黄埔区', '番禺区',
      '花都区', '南沙区', '从化区', '增城区']
BAD = ['佛山', '南海', '顺德', '东莞', '中山', '清远', '肇庆']


def norm(name):
    """标准化店名：取括号内核心名，去城市名与「分店/餐厅/店」后缀"""
    core = re.sub(r'^麦当劳', '', name).strip()
    m = re.search(r'[（(]([^）)]*)[）)]', core)
    base = (m.group(1) if m else core).strip()
    base = base.replace('广州', '', 1) if base.startswith('广州') else base
    base = re.sub(r'(分店餐厅|分店|餐厅)$', '', base).strip()
    return base or core or name


pool = {}
for tab, v in data.items():
    for it in v['items']:
        if not it['name'].startswith('麦当劳'):
            continue
        if it['district'] not in GZ:
            continue
        if any(b in it['address'] for b in BAD):
            continue
        key = norm(it['name']) or it['address'][:12]
        p = pool.setdefault(key, {'key': key, 'raw_name': it['name'], 'district': it['district'],
                                  'address': it['address'], 'area': it['area'],
                                  'rating': it['rating'], 'hits': []})
        p['hits'].append((tab, it['rank']))
        if it['rating'] > p['rating']:
            p['rating'] = it['rating']
        if not p['area'] and it['area']:
            p['area'] = it['area']

# 地标候选（公开报道确认，不依赖榜单）
LANDMARK = {
    '天字码头店': dict(district='越秀区', address='沿江中路 天字码头（北京南路路口）', area='沿江路'),
    '海珠广场店': dict(district='越秀区', address='海珠广场 海印缤缤广场二层', area='海珠广场'),
    '白云CUBE旗舰店': dict(district='白云区', address='白云万达广场旁', area='白云新城'),
    '正佳广场店': dict(district='天河区', address='天河路228号正佳广场', area='天河路'),
}
for k, v in LANDMARK.items():
    if k not in pool:
        pool[k] = {'key': k, 'raw_name': '麦当劳(%s)' % k, 'district': v['district'],
                   'address': v['address'], 'area': v['area'], 'rating': 0.0, 'hits': [],
                   'landmark': True}

for p in pool.values():
    best = min([r for _, r in p['hits']], default=99)
    p['hit_count'] = len(p['hits'])
    p['best_rank'] = best if best != 99 else None
    p['best_tab'] = [t for t, r in p['hits'] if r == best][0] if p['hits'] else ''

out = sorted(pool.values(), key=lambda x: (-x['hit_count'], x['best_rank'] or 99))
json.dump(out, open(os.path.join(BASE, '候选池.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print('候选池门店数：', len(out))
for p in out:
    print('%-22s %-5s 命中%d 最佳第%s(%s) %-6s %s' % (
        p['key'], p['district'], p['hit_count'], p['best_rank'], p['best_tab'],
        '%.1f' % p['rating'] if p['rating'] else '—', p['address'][:34]))
