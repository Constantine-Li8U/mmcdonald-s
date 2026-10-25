# -*- coding: utf-8 -*-
"""补充采集：针对候选稀少的门店追加关键词，结果追加到已有候选目录。"""
import json
import os
import subprocess
import time
import urllib.parse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(BASE, '_数据与评分', '候选图')
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')

EXTRA = {
    '丽都': dict(
        inc=['丽都'],
        exc=['复兴门', '北京丽都', '丽都饭店', '深圳', '郑州', '上海', '丽都酒店·'],
        queries=['麦当劳(丽都店)', '麦当劳丽都店', '丽都店 麦当劳 广州',
                 '麦当劳 北京路 老店 广州', '麦当劳 丽都大酒店 首层',
                 '北京路 麦当劳 甜品站', '麦当劳 大马站路', '麦当劳 永汉电影院']),
    '东风西': dict(
        inc=['东风西'],
        exc=['郑州', '东风路店', '深圳', '东风东路'],
        queries=['麦当劳(东风西路分店)', '麦当劳东风西路分店', '东风西路 麦当劳 店',
                 '麦当劳 东风西路店 广州', '麦当劳 流花湖 广州',
                 '麦当劳 东风西路 玻璃幕墙', '东风西路140号 麦当劳']),
    '江湾': dict(
        inc=['江湾壹号', '江湾新城', '阳光城'],
        exc=['江湾镇', '江湾三路', '江湾路', '江湾体育场', '五角场'],
        queries=['麦当劳(江湾壹号店)', '麦当劳江湾壹号店', '麦当劳 江湾新城 广州',
                 '麦当劳 沿江中路 广州', '广信江湾新城 麦当劳',
                 '麦当劳 阳光城江湾壹号', '沿江中路298号 麦当劳']),
    '总统': dict(
        inc=['总统大酒店', '总统店'],
        exc=['美国总统', '总统套房', '总统府'],
        queries=['麦当劳(总统大酒店店)', '麦当劳总统大酒店店', '麦当劳 南方电脑城',
                 '麦当劳 天河路 岗顶 广州', '总统大酒店 麦当劳 裙楼']),
    '广百': dict(
        inc=['广百'],
        exc=['茂名', '东汇城', '湛江', '肇庆'],
        queries=['麦当劳(广百广场店)', '麦当劳(广百新翼店)', '麦当劳 广百广场店 广州',
                 '麦当劳 西湖路 广州', '广百新翼 麦当劳 首层']),
}


def curl_json(url, tries=3):
    for i in range(tries):
        p = subprocess.run(['curl', '-s', '-m', '30', url,
                            '-H', 'User-Agent: ' + UA,
                            '-H', 'Referer: https://image.so.com/'],
                           capture_output=True)
        raw = p.stdout.decode('utf-8', 'ignore')
        if raw.strip().startswith('{'):
            try:
                return json.loads(raw)
            except Exception:
                pass
        time.sleep(6 * (i + 1))
    return {}


def download(url, path):
    subprocess.run(['curl', '-s', '-L', '-m', '40', url, '-o', path,
                    '-H', 'User-Agent: ' + UA,
                    '-H', 'Referer: https://www.dianping.com/'],
                   capture_output=True)
    return os.path.exists(path) and os.path.getsize(path) > 8000


def run(store):
    cfg = EXTRA[store]
    d = os.path.join(CAND, store)
    os.makedirs(d, exist_ok=True)
    ip = os.path.join(d, '_info.json')
    info = json.load(open(ip, encoding='utf-8')) if os.path.exists(ip) else []
    have = {x['img'] for x in info}
    n = max([int(x['file'].split('.')[0]) for x in info], default=0)
    added = 0
    for q in cfg['queries']:
        fresh = 0
        for sn in (0, 60, 120):
            url = ('https://image.so.com/j?q=%s&sn=%d&rn=30'
                   % (urllib.parse.quote(q), sn))
            for x in (curl_json(url).get('list') or []):
                t = (x.get('title') or '').strip()
                img = x.get('img') or ''
                try:
                    w, h = int(x.get('width') or 0), int(x.get('height') or 0)
                except Exception:
                    w = h = 0
                if not img or img in have or w < 500 or h < 400:
                    continue
                if not any(k in t for k in cfg['inc']):
                    continue
                if any(k in t for k in cfg['exc']):
                    continue
                have.add(img)
                n += 1
                fn = '%03d.jpg' % n
                fp = os.path.join(d, fn)
                if not download(img, fp):
                    if os.path.exists(fp):
                        os.remove(fp)
                    n -= 1
                    continue
                info.append(dict(title=t, img=img, w=w, h=h,
                                 page=(x.get('comm_purl') or x.get('dspurl') or ''),
                                 src=x.get('source') or '', q=q, file=fn))
                fresh += 1
                added += 1
            time.sleep(5)
        print('  [%s] +%d' % (q, fresh), flush=True)
    json.dump(info, open(ip, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('== %s 新增 %d，累计 %d' % (store, added, len(info)), flush=True)


if __name__ == '__main__':
    import sys
    for s in (sys.argv[1:] or list(EXTRA)):
        run(s)
