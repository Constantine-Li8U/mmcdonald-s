# -*- coding: utf-8 -*-
"""加权打分 + 双通道选榜"""
import json, os, csv

BASE = os.path.join(os.path.dirname(__file__), '..', '_数据与评分')
pool = json.load(open(os.path.join(BASE, '候选池.json'), encoding='utf-8'))

# 商圈能级（20/15/11/7/3）—— 依据地址与高德商圈标签人工判定
C_MAP = {
    '沙面': 20, '北京路丽都酒店店': 20, '北京路广百广场店': 20, '阳光城·江湾壹号店': 20,
    '今日广场店': 20, '动漫星城店': 20, '恩宁路': 20, '天字码头店': 20, '海珠广场店': 20,
    '正佳广场店': 20,
    '东风西路': 15, '总统大酒店店': 15, '宜安广场': 15, '国际大厦': 15, '宝华路': 15,
    '白云CUBE旗舰店': 15, '中泰国际广场店': 15,
    '人民中路店': 7, '交易广场店': 7, '小北路店': 7, '西村': 7, '聚龙慧谷店': 7,
    '立白中心店': 11, '大参林总部副中心': 3,
}
C_DEFAULT = 7

# 官方身份（D，最高 20）
D_MAP = {
    '天字码头店': 20,      # 全国首发「美味色谱」设计 + 广州市场第900家
    '海珠广场店': 18,      # 广州首家童趣旗舰店 + 全市面积最大 + 1993年第二家
    '白云CUBE旗舰店': 18,  # 全国第五家 / 广州首家 CUBE 旗舰
}
D_DEFAULT = 0
# 注：环市东路广东国际大厦店（原址为 1993-02-20 广州首家麦当劳）不额外加分——
# 该首店已于 2010 年因租约结业，现店为后续重开，与首店不是同一家，避免误导。

# 规模（B）：面积 12/10/8/6/4 + 座位 8/6/4/2
B_KNOWN = {
    '天字码头店': (None, 12, '室内外合计 100+ 座'),      # 面积未公开
    '海珠广场店': (765, None, '面积 765㎡，座位未公开'),
    '白云CUBE旗舰店': (430, 135, '面积 430㎡，135 座'),
    '正佳广场店': (None, 120, '座位 120（开饭喇），面积未公开'),
}
B_MEDIAN = 6  # 未知规模统一取中位档（250–349㎡），标注「推定」


def area_score(a):
    if a is None:
        return None
    if a >= 700: return 12
    if a >= 500: return 10
    if a >= 350: return 8
    if a >= 250: return 6
    return 4


def seat_score(s):
    if s is None:
        return None
    if s >= 150: return 8
    if s >= 100: return 6
    if s >= 70: return 4
    return 2


def a_score(k, best):
    base = {0: 0, 1: 10, 2: 18, 3: 26}.get(k, 34)
    bonus = 0
    if best is not None:
        if best <= 2: bonus = 6
        elif best <= 5: bonus = 4
        elif best <= 10: bonus = 2
    return base + bonus


rows = []
for p in pool:
    k = p['hit_count']
    best = p['best_rank']
    A = a_score(k, best)

    key = p['key']
    est = []
    if key in B_KNOWN:
        a_sqm, seats, note = B_KNOWN[key]
        sa, ss = area_score(a_sqm), seat_score(seats)
        if sa is None:
            sa = 6; est.append('面积')
        if ss is None:
            ss = 6; est.append('座位')
        B = sa + ss
    else:
        B = B_MEDIAN
        est.append('面积')
        est.append('座位')

    C = C_MAP.get(key, C_DEFAULT)
    D = D_MAP.get(key, D_DEFAULT)
    rows.append(dict(key=key, name=p['raw_name'], district=p['district'], address=p['address'],
                     area=p['area'], rating=p['rating'], hit_count=k, best_rank=best,
                     best_tab=p['best_tab'], A=A, B=B, C=C, D=D, total=A + B + C + D,
                     estimated='/'.join(est) if est else ''))

rows.sort(key=lambda r: (-r['total'], -r['A'], -r['D'], r['best_rank'] or 99))

# 双通道
rank_ch = [r for r in rows if r['hit_count'] >= 2][:7]
chosen_keys = {r['key'] for r in rank_ch}
rest = [r for r in rows if r['key'] not in chosen_keys]
land_ch = sorted(rest, key=lambda r: (-r['D'], -r['B'], -r['C']))[:3]
for r in rank_ch:
    r['channel'] = '榜单'
for r in land_ch:
    r['channel'] = '地标'

final = sorted(rank_ch + land_ch, key=lambda r: (-r['total'], -r['A'], -r['D'], r['best_rank'] or 99))
for i, r in enumerate(final, 1):
    r['final_rank'] = i

with open(os.path.join(BASE, '候选池评分明细.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['序号', '门店', '行政区', '商圈', '地址', '高德评分', '上榜次数', '最佳名次',
                '最佳榜', 'A榜单40', 'B规模20', 'C商圈20', 'D身份20', '总分', '推定项', '入选通道', '最终名次'])
    # 入选的排前面
    ordered = final + [r for r in rows if 'final_rank' not in r]
    for i, r in enumerate(ordered, 1):
        w.writerow([i, r['name'], r['district'], r['area'], r['address'],
                    r['rating'] or '', r['hit_count'], r['best_rank'] or '',
                    r['best_tab'], r['A'], r['B'], r['C'], r['D'], r['total'],
                    r['estimated'], r.get('channel', '未入选'), r.get('final_rank', '')])

json.dump(final, open(os.path.join(BASE, 'TOP10.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('=== 入选 TOP10 ===')
for r in final:
    print('%2d %-16s %-5s A%2d B%2d C%2d D%2d = %3d  [%s] 上榜%d 最佳%s' % (
        r['final_rank'], r['key'], r['district'], r['A'], r['B'], r['C'], r['D'],
        r['total'], r['channel'], r['hit_count'], r['best_rank']))
print('\n=== 落选（前8） ===')
for r in [x for x in rows if 'final_rank' not in x][:8]:
    print('   %-16s %-5s %3d  A%2d B%2d C%2d D%2d  上榜%d' % (
        r['key'], r['district'], r['total'], r['A'], r['B'], r['C'], r['D'], r['hit_count']))
