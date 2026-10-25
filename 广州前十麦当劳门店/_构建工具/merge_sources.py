# -*- coding: utf-8 -*-
"""汇总所有门店的照片来源"""
import os, glob, csv

BASE = os.path.join(os.path.dirname(__file__), '..')
rows = [('门店', '文件名', '平台', '来源页URL', '图片直链', '抓取时间', '版权说明')]
for d in sorted(os.listdir(BASE)):
    fp = os.path.join(BASE, d, 'photos', '_sources.csv')
    if not os.path.isfile(fp):
        continue
    with open(fp, encoding='utf-8-sig') as f:
        for r in csv.reader(f):
            if r and r[0] != '文件名':
                rows.append([d] + r)
with open(os.path.join(BASE, '_数据与评分', '照片来源总表.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    csv.writer(f).writerows(rows)
print('总表 %d 条' % (len(rows) - 1))
