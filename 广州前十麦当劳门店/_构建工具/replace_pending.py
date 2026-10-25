# -*- coding: utf-8 -*-
"""WPS / Word 释放占用后，把 .待替换.docx 替换成正式文件名。"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
done = 0
for d in os.listdir(BASE):
    p = os.path.join(BASE, d)
    if not os.path.isdir(p) or not d[:2].isdigit():
        continue
    for f in os.listdir(p):
        if not f.endswith('.待替换.docx'):
            continue
        src = os.path.join(p, f)
        dst = os.path.join(p, f.replace('.待替换', ''))
        try:
            os.replace(src, dst)
            print('已替换', dst)
            done += 1
        except Exception:
            print('仍被占用，请先关闭', dst)
print('完成', done, '个')
