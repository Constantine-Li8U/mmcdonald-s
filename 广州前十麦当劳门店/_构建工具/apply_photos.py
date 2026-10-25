# -*- coding: utf-8 -*-
"""把核验通过的候选图落进各门店 photos 目录，并回写 stores.json。"""
import csv
import json
import os
import shutil

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(BASE, '_数据与评分', '候选图')
STORE_JSON = os.path.join(BASE, '_构建工具', 'stores.json')

CODE_CN = {'EXT': '外立面 / 门头', 'CNT': '点餐前台', 'SEAT': '座位区',
           'KID': '儿童区', 'SIGN': '招牌细节', 'ENV': '周边环境'}
ORDER = ['EXT', 'CNT', 'SEAT', 'KID', 'SIGN', 'ENV']

# store key -> [(候选序号, 角度)]，均为逐张目视核验通过的门店空间照
PICKS = {
    '丽都': [('050', 'EXT'), ('053', 'EXT'), ('084', 'EXT'),
             ('023', 'CNT'), ('028', 'CNT'), ('060', 'CNT'),
             ('043', 'SEAT'), ('052', 'SEAT'), ('088', 'SEAT'), ('027', 'SEAT'),
             ('015', 'SIGN'), ('046', 'ENV')],
    '总统': [('003', 'EXT'), ('008', 'CNT'), ('002', 'SEAT')],
    '广百': [('009', 'EXT'), ('003', 'SIGN'),
             ('006', 'CNT'), ('011', 'CNT'), ('015', 'CNT'),
             ('007', 'SEAT'), ('010', 'SEAT'), ('013', 'SEAT'), ('016', 'SEAT'),
             ('012', 'ENV')],
    '宜安': [('003', 'EXT'), ('048', 'EXT'), ('006', 'EXT'),
             ('013', 'CNT'), ('010', 'CNT'), ('009', 'CNT'),
             ('004', 'SEAT'), ('014', 'SEAT'), ('007', 'SEAT'), ('012', 'SEAT'),
             ('040', 'SIGN'), ('034', 'ENV')],
}

PLATFORM = '大众点评（用户实拍，经 360 图片搜索索引）'
CREDIT = '图片版权归原作者所有，本档案仅作个人研究与非商业展示'


def main():
    stores = json.load(open(STORE_JSON, encoding='utf-8'))
    idx = {s['short']: s for s in stores}
    for key, picks in PICKS.items():
        s = idx[key]
        d = os.path.join(BASE, '%02d_%s' % (s['no'], s['folder']), 'photos')
        os.makedirs(d, exist_ok=True)
        info = {x['file']: x for x in json.load(
            open(os.path.join(CAND, key, '_info.json'), encoding='utf-8'))}
        picks = sorted(picks, key=lambda p: (ORDER.index(p[1]), p[0]))
        photos, files, rows = [], [], []
        cnt = {}
        for cand, code in picks:
            cnt[code] = cnt.get(code, 0) + 1
            fn = '%02d_%s_%s_%02d.jpg' % (s['no'], s['short'], code, cnt[code])
            src = os.path.join(CAND, key, cand + '.jpg')
            shutil.copy2(src, os.path.join(d, fn))
            meta = info.get(cand + '.jpg', {})
            photos.append(dict(code=code, code_cn=CODE_CN[code], src=cand))
            files.append(fn)
            rows.append([fn, PLATFORM, meta.get('page', ''), meta.get('img', ''),
                         '2026-10-24', CREDIT])
        with open(os.path.join(d, '_sources.csv'), 'w', encoding='utf-8-sig',
                  newline='') as f:
            w = csv.writer(f)
            w.writerow(['文件名', '平台', '来源页面', '图片直链', '抓取时间', '版权说明'])
            w.writerows(rows)
        s['photos'] = photos
        s['photo_files'] = files
        s['photo_src'] = '大众点评门店相册（用户实拍），经 360 图片搜索索引取得'
        s['photo_platform'] = '大众点评（用户实拍）'
        s['photo_page'] = 'https://www.dianping.com/guangzhou（原图直链见 photos/_sources.csv）'
        s['credit'] = CREDIT
        print('%02d %-6s 落图 %d 张' % (s['no'], key, len(files)))
    json.dump(stores, open(STORE_JSON, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('stores.json 已更新')


if __name__ == '__main__':
    main()
