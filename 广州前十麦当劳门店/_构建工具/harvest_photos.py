# -*- coding: utf-8 -*-
"""从 360 图片搜索（image.so.com）采集缺失门店候选图。

要点：必须用 curl 发起请求，Python urllib 直连会被返回空列表。
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(BASE, '_数据与评分', '候选图')
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')

STORES = {
    '丽都': {
        'no': 2, 'short': '丽都',
        'inc': ['丽都'],
        'exc': ['复兴门', '丽都饭店', '丽都酒店·', '北京丽都', '深圳', '郑州', '上海'],
        'queries': ['麦当劳 丽都大酒店 广州', '麦当劳 丽都店 北京路',
                    '麦当劳 北京路182号', '麦当劳 北京路 永汉电影院',
                    '丽都大酒店 麦当劳 广州', '麦当劳 北京路步行街 二楼'],
    },
    '东风西': {
        'no': 3, 'short': '东风西',
        'inc': ['东风西'],
        'exc': ['郑州', '东风路店', '深圳', '东风东路'],
        'queries': ['麦当劳 东风西路', '麦当劳 东风西路分店',
                    '麦当劳 东风西路140号', '麦当劳 流花湖公园',
                    '麦当劳 广州 东风西路 越秀', '东风西路 麦当劳 首层'],
    },
    '总统': {
        'no': 4, 'short': '总统',
        'inc': ['总统大酒店', '总统店'],
        'exc': ['美国总统', '总统套房', '总统府'],
        'queries': ['麦当劳 总统大酒店 广州', '麦当劳 总统大酒店店',
                    '麦当劳 天河路518号', '麦当劳 岗顶 南方电脑城',
                    '麦当劳 岗顶 天河路 广州', '南方电脑城 麦当劳 二楼'],
    },
    '广百': {
        'no': 5, 'short': '广百',
        'inc': ['广百'],
        'exc': ['茂名', '东汇城', '湛江', '肇庆', '广百百货北京路店'],
        'queries': ['麦当劳 广百广场 广州', '麦当劳 广百新翼',
                    '麦当劳 西湖路 广百', '麦当劳 北京路 广百广场店',
                    '广百广场新翼 麦当劳', '麦当劳 北京路 夹层'],
    },
    '江湾': {
        'no': 7, 'short': '江湾',
        'inc': ['江湾壹号', '江湾新城', '阳光城'],
        'exc': ['江湾镇', '江湾三路', '江湾路', '江湾体育场', '五角场'],
        'queries': ['麦当劳 江湾壹号', '麦当劳 广信江湾新城',
                    '麦当劳 沿江中路298号', '麦当劳 阳光城 江湾',
                    '沿江中路 麦当劳 广州', '麦当劳 江湾壹号 广州 越秀'],
    },
    '宜安': {
        'no': 8, 'short': '宜安',
        'inc': ['宜安'],
        'exc': ['宜安广场 佛山', '宜安大厦'],
        'queries': ['麦当劳 宜安广场店', '麦当劳 宜安广场',
                    '麦当劳 建设六马路', '麦当劳 宜安广场 广州',
                    '建设六马路38号 麦当劳', '麦当劳 淘金 建设六马路'],
    },
}


def curl_json(url, referer, tries=3):
    for i in range(tries):
        p = subprocess.run(['curl', '-s', '-m', '30', url,
                            '-H', 'User-Agent: ' + UA,
                            '-H', 'Referer: ' + referer],
                           capture_output=True)
        raw = p.stdout.decode('utf-8', 'ignore')
        if raw.strip().startswith('{'):
            try:
                return json.loads(raw)
            except Exception:
                pass
        time.sleep(4 * (i + 1))
    return {}


def search(q, store_inc, store_exc):
    out = []
    for sn in (0, 60, 120, 180):
        url = ('https://image.so.com/j?q=%s&sn=%d&rn=30'
               % (urllib.parse.quote(q), sn))
        d = curl_json(url, 'https://image.so.com/')
        items = d.get('list') or []
        for x in items:
            t = (x.get('title') or '').strip()
            img = x.get('img') or ''
            try:
                w = int(x.get('width') or 0)
                h = int(x.get('height') or 0)
            except Exception:
                w = h = 0
            if not img or w < 500 or h < 400:
                continue
            if not any(k in t for k in store_inc):
                continue
            if any(k in t for k in store_exc):
                continue
            out.append(dict(title=t, img=img, w=w, h=h,
                            page=(x.get('comm_purl') or x.get('dspurl') or ''),
                            src=x.get('source') or '', q=q))
        time.sleep(4)
    return out


def download(url, path):
    p = subprocess.run(['curl', '-s', '-L', '-m', '40', url, '-o', path,
                        '-H', 'User-Agent: ' + UA,
                        '-H', 'Referer: https://www.dianping.com/'],
                       capture_output=True)
    return os.path.exists(path) and os.path.getsize(path) > 8000


def main(only=None):
    os.makedirs(CAND, exist_ok=True)
    seen_md5 = {}
    summary = {}
    for key, cfg in STORES.items():
        if only and key != only:
            continue
        d = os.path.join(CAND, key)
        os.makedirs(d, exist_ok=True)
        info_path = os.path.join(d, '_info.json')
        if os.path.exists(info_path) and os.path.getsize(info_path) > 10:
            old = json.load(open(info_path, encoding='utf-8'))
            if old:
                print('%s 已有 %d 张候选，跳过' % (key, len(old)))
                continue
        pool, seen_img = [], set()
        for q in cfg['queries']:
            try:
                got = search(q, cfg['inc'], cfg['exc'])
            except Exception as e:
                print('  query fail', q, e)
                continue
            new = 0
            for it in got:
                if it['img'] in seen_img:
                    continue
                seen_img.add(it['img'])
                pool.append(it)
                new += 1
            print('  [%s] +%d (累计 %d)' % (q, new, len(pool)))
        info = []
        n = 0
        for it in pool:
            n += 1
            fn = '%03d.jpg' % n
            fp = os.path.join(d, fn)
            if not download(it['img'], fp):
                if os.path.exists(fp):
                    os.remove(fp)
                continue
            it['file'] = fn
            info.append(it)
        json.dump(info, open(info_path, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        summary[key] = len(info)
        print('== %s 候选 %d 张' % (key, len(info)))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
