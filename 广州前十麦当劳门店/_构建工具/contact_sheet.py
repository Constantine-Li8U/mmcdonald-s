# -*- coding: utf-8 -*-
"""把待核验图拼成带编号的联系表，便于肉眼筛选"""
import os, glob
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.join(os.path.dirname(__file__), '..')
STAGE = os.path.join(BASE, '_数据与评分', '待核验图')
OUT = os.path.join(BASE, '_数据与评分', '联系表')
os.makedirs(OUT, exist_ok=True)

CELL_W, CELL_H, COLS = 360, 270, 4
FONT = None
for f in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/arial.ttf']:
    if os.path.exists(f):
        FONT = ImageFont.truetype(f, 22)
        break
if FONT is None:
    FONT = ImageFont.load_default()

for d in sorted(glob.glob(os.path.join(STAGE, '*'))):
    if not os.path.isdir(d):
        continue
    files = sorted(glob.glob(os.path.join(d, '*.jpg')))
    if not files:
        continue
    rows = (len(files) + COLS - 1) // COLS
    sheet = Image.new('RGB', (CELL_W * COLS, CELL_H * rows), 'white')
    dr = ImageDraw.Draw(sheet)
    for i, fp in enumerate(files):
        im = Image.open(fp).convert('RGB')
        im.thumbnail((CELL_W - 8, CELL_H - 34))
        x = (i % COLS) * CELL_W
        y = (i // COLS) * CELL_H
        sheet.paste(im, (x + 4, y + 30))
        dr.rectangle([x, y, x + CELL_W - 1, y + CELL_H - 1], outline='#cccccc')
        dr.text((x + 8, y + 4), os.path.basename(fp).replace('.jpg', ''), fill='black', font=FONT)
    name = os.path.basename(d) + '.jpg'
    sheet.save(os.path.join(OUT, name), 'JPEG', quality=80)
    print(name, sheet.size, len(files))
