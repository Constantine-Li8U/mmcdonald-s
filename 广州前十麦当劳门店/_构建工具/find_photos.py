# -*- coding: utf-8 -*-
"""按门店抓取图片搜索候选直链"""
import re, json, os, time, urllib.parse, urllib.request

BASE = os.path.join(os.path.dirname(__file__), '..')
OUT = os.path.join(BASE, '_数据与评分', '照片候选.json')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'

QUERIES = {
    '天字码头': ['麦当劳 天字码头 广州 外立面', '麦当劳 沿江中路 天字码头 餐厅', '麦当劳 美味色谱 广州'],
    '海珠广场': ['麦当劳 海珠广场 童趣旗舰店', '麦当劳 海印缤缤广场 广州', '麦当劳 四小福 广州 海珠广场'],
    '白云CUBE': ['麦当劳 CUBE 旗舰店 广州 白云', '麦当劳 小立方体 广州 白云万达'],
    '沙面': ['麦当劳 沙面 广州 门店', '麦当劳 沙面大街 金拱门'],
    '北京路丽都': ['麦当劳 北京路 丽都大酒店 广州', '麦当劳 丽都酒店 北京路 甜品站'],
    '东风西路': ['麦当劳 东风西路 广州 门店', '麦当劳 东风西路140号'],
    '总统大酒店': ['麦当劳 总统大酒店 岗顶 广州', '麦当劳 南方电脑城 天河路518号'],
    '北京路广百': ['麦当劳 广百新翼 北京路 广州', '麦当劳 北京路 广百广场'],
    '江湾阳光天地': ['麦当劳 江湾阳光天地 沿江中路', '麦当劳 广信江湾新城'],
    '宜安广场': ['麦当劳 宜安广场 建设六马路 广州'],
}


def fetch(q):
    url = 'https://cn.bing.com/images/search?q=%s&form=HDRSC2&first=1' % urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    html = urllib.request.urlopen(req, timeout=25).read().decode('utf-8', 'ignore')
    items = []
    for m in re.finditer(r'murl&quot;:&quot;(.*?)&quot;', html):
        murl = m.group(1)
        seg = html[max(0, m.start() - 4000):m.start() + 3000]
        p = re.findall(r'purl&quot;:&quot;(.*?)&quot;', seg)
        t = re.findall(r't&quot;:&quot;(.*?)&quot;', seg)
        items.append({'murl': murl,
                      'purl': p[-1] if p else '',
                      'title': t[-1] if t else ''})
    return items


def main():
    res = {}
    for store, qs in QUERIES.items():
        seen, got = set(), []
        for q in qs:
            try:
                for it in fetch(q):
                    if it['murl'] in seen:
                        continue
                    seen.add(it['murl'])
                    it['query'] = q
                    got.append(it)
            except Exception as e:
                print(store, q, 'FAIL', e)
            time.sleep(1.2)
        res[store] = got
        print('%-14s %d' % (store, len(got)))
    json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
