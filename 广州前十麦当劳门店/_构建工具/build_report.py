# -*- coding: utf-8 -*-
"""生成照片覆盖核对表（csv）与照片核对报告（md + docx）。"""
import json
import os

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAMP = '2026-10-24'
FONT = '微软雅黑'

stores = json.load(open(os.path.join(BASE, '_构建工具', 'stores.json'), encoding='utf-8'))
audit = json.load(open(os.path.join(BASE, '_数据与评分', '照片审计.json'), encoding='utf-8'))

CODE_CN = {'EXT': '外立面', 'CNT': '前台', 'SEAT': '座位', 'KID': '儿童区',
           'SIGN': '招牌', 'ENV': '环境'}

VERDICT = {
    '沙面': '通过。同一探店稿多角度实拍，可见沙面胜利宾馆首层临街店面与落地 M 招牌；清晰度最高的一批（946–1080 宽）。',
    '丽都': '通过。点评「麦当劳(丽都店)」相册，外立面 / 前台 / 座位 / 招牌 / 街景齐；画面为一层甜品站 + 二层堂食，与门店描述一致。',
    '东风西': '未通过。13 组关键词与 8 个渠道（含唯一有效的新渠道 360 图片搜索）均无可确认的本店实拍，唯一同名条目是甜筒特写（菜品图，按规则排除）。',
    '总统': '通过。点评「麦当劳(总统大酒店店)」相册；前台照自带水印「麦当劳(总统大酒店店) 2020.04.17」，店名与门店直接对应。',
    '广百': '通过。点评「麦当劳(广百店)」相册；外立面照可读到「广百新翼商务」招牌，与所在商场一致。',
    '海珠广场': '通过。麦当劳中国官网 2023-08-08 家庭主题店新闻稿配图，画面与外立面 / 前台 / 座位 / 儿童区描述一致；分辨率 640 宽，压缩较重。',
    '江湾': '未通过。命中的全部是异地同名门店（上海唐镇阳光城 / 合肥恒生阳光城 / 佛山江湾三路），无一张可确认属本店。',
    '宜安': '通过。点评「麦当劳(宜安广场店)」相册；外立面照可见宜安广场招牌与下沉楼梯，与「首层需下楼梯」的描述一致。',
    '天字码头': '通过。麦当劳中国官网 2026-01-04 第 900 家店新闻稿配图；4 张，其中 1 张仅 320×320。',
    'CUBE': '通过。麦当劳中国官网 2023-04-03 CUBE 旗舰店开业稿配图；7 张，其中 1 张仅 320×320。',
}

SHORT = {
    '沙面': '通过（探店稿多角度，画面可辨沙面店）',
    '丽都': '通过（点评「丽都店」相册，一层甜品站+二层堂食）',
    '东风西': '未通过（无本店实拍）',
    '总统': '通过（前台照自带「总统大酒店店」水印）',
    '广百': '通过（外立面可见「广百新翼商务」招牌）',
    '海珠广场': '通过（官网家庭主题店稿配图）',
    '江湾': '未通过（命中全为异地同名店）',
    '宜安': '通过（外立面可见宜安广场招牌与下沉楼梯）',
    '天字码头': '通过（官网第 900 家店稿配图）',
    'CUBE': '通过（官网 CUBE 旗舰店开业稿配图）',
}

ABSENT = {
    '东风西': '360 图片搜索 13 组关键词全为无关结果（唯一同名条目是甜筒特写，属菜品图）；点评/美团滑块验证、开饭喇 http=000、官网无门店相册、携程无 POI、百度/搜狗/Bing/马蜂窝接口均不可用。',
    '江湾': '11 组关键词命中的 11 张全部为异地同名店（上海唐镇阳光城、合肥恒生阳光城、佛山江湾三路、上海江湾镇），「麦当劳 江湾壹号」「麦当劳 江湾新城」直接 0 条；其余渠道同东风西路。',
}


def stats(store_short):
    rows = [r for r in audit['rows'] if r['store'].startswith('%02d' % next(
        s['no'] for s in stores if s['short'] == store_short))]
    g = {'清晰': 0, '一般': 0, '偏低': 0}
    for r in rows:
        if r.get('grade'):
            g[r['grade']] += 1
    return g


def build_rows():
    out = []
    for s in stores:
        codes, seen = [], set()
        for p in s['photos']:
            if p['code'] not in seen:
                seen.add(p['code'])
                codes.append(CODE_CN[p['code']])
        g = stats(s['short'])
        out.append(dict(
            no=s['no'], name=s['title'], short=s['short'],
            addr=s['address'], n=len(s['photo_files']),
            angles='、'.join(codes) if codes else '—',
            grade=('清晰 %d / 一般 %d / 偏低 %d' % (g['清晰'], g['一般'], g['偏低'])) if s['photo_files'] else '—',
            short_v=SHORT[s['short']],
            src=s['photo_platform'] or '—',
            verdict=VERDICT[s['short']],
            reason=ABSENT.get(s['short'], ''),
        ))
    return out


def write_csv(rows):
    import csv
    p = os.path.join(BASE, '_数据与评分', '照片覆盖核对表.csv')
    with open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['名次', '门店', '地址', '照片数', '已覆盖角度', '清晰度分布',
                    '来源平台', '核验结论', '缺失原因'])
        for r in rows:
            w.writerow([r['no'], r['name'], r['addr'], r['n'], r['angles'],
                        r['grade'], r['src'], r['verdict'], r['reason']])
    print('csv ->', p)
    return p


def write_md(rows):
    total = sum(r['n'] for r in rows)
    filled = [r for r in rows if r['n']]
    empty = [r for r in rows if not r['n']]
    L = []
    L.append('# 照片核对报告\n')
    L.append('核对日期：%s ｜ 对象：广州麦当劳人气 TOP10 十家门店 ｜ 结论：**%d 家有实拍（共 %d 张），%d 家无**\n'
             % (STAMP, len(filled), total, len(empty)))
    L.append('---\n')

    L.append('## 一、逐店核对总表\n')
    L.append('| 名次 | 门店 | 照片 | 覆盖角度 | 清晰度分布 | 核验结论 |')
    L.append('| --- | --- | --- | --- | --- | --- |')
    for r in rows:
        L.append('| %d | %s | %d | %s | %s | %s |' % (
            r['no'], r['name'].replace('麦当劳（', '').replace('）', ''), r['n'],
            r['angles'], r['grade'], r['short_v']))
    L.append('')

    L.append('## 二、仍无法补充照片的门店（%d 家）\n' % len(empty))
    for r in empty:
        L.append('### %d. %s\n' % (r['no'], r['name']))
        L.append('- **地址**：%s' % r['addr'])
        L.append('- **结论**：%s' % r['verdict'])
        L.append('- **逐渠道结果**：%s\n' % r['reason'])
    L.append('> 这两家门店并非「没有认真找」，而是把能用的公开渠道都试过一遍：'
             '360 图片搜索（大众点评图床索引，本次唯一有效的新增渠道）、大众点评 / 美团网页端、'
             '开饭喇、麦当劳中国官网、携程 / Trip.com、百度图片、搜狗图片、百度地图、Bing 图片、马蜂窝。'
             '东风西路是本次榜单第 1 名（高德 5.0 分），江湾壹号是沿江路商圈店——'
             '**榜单热度高、网络照片沉淀少**，这是公开数据的真实分布，不是漏查。\n')

    L.append('## 三、全库照片质量核查（含本次新增）\n')
    L.append('| 门店 | 数量 | 清晰 | 一般 | 偏低 | 问题说明 |')
    L.append('| --- | --- | --- | --- | --- | --- |')
    notes = {
        '沙面': '质量最好的一批，946–1080 宽、锐度 20–52，无重复。',
        '丽都': '分辨率 525–700 宽（点评图床原图上限），画质中等但角度齐全。',
        '总统': '仅 3 张（外立面 / 前台 / 座位），受公开图源数量限制。',
        '广百': '700 宽为主，1 张 1080×1620 招牌特写；画质均匀。',
        '海珠广场': '官网 640 宽配图，压缩较重（单张 90–260KB），细节一般。',
        '宜安': '575–700 宽；`CNT_03` 仅 575×430，是本次唯一偏低的补图。',
        '天字码头': '`EXT_01` 仅 320×320，为官网缩略尺寸；其余 640 宽。',
        'CUBE': '`EXT_02` 仅 320×320；`SEAT_02` 为 640×210 长条构图，展示效果一般。',
    }
    for r in rows:
        if not r['n']:
            continue
        g = stats(r['short'])
        L.append('| %s | %d | %d | %d | %d | %s |' % (
            r['name'].replace('麦当劳（', '').replace('）', ''), r['n'],
            g['清晰'], g['一般'], g['偏低'], notes.get(r['short'], '')))
    L.append('')
    L.append('判定口径：长边 ≥1000 且锐度 ≥12 记「清晰」；长边 ≥600 且锐度 ≥7 记「一般」；'
             '其余记「偏低」（锐度 = 800px 缩略图上的边缘强度标准差）。'
             '全库 %d 张图未检出近似重复（16×16 均值哈希，汉明距离 ≤12 判重）。\n' % total)

    L.append('## 四、收录与排除规则\n')
    L.append('1. **只要门店空间照**：外立面 / 门头 / 点餐前台 / 座位区 / 儿童区 / 招牌 / 周边，菜品与包装特写一律不收。')
    L.append('2. **必须能确认是本店**：店名精确匹配（如「麦当劳(总统大酒店店)」）或画面可读到本店专属标识'
             '（水印、商场招牌、下沉楼梯等）。判不准的按弃用处理。')
    L.append('3. **异地同名店一律排除**：上海江湾镇店、上海唐镇阳光城店、合肥恒生阳光城店、佛山江湾三路店、'
             '郑州东风路店、北京丽都／复兴门店等。')
    L.append('4. **不放示意图 / 占位图 / AI 生成图**，缺就写缺。')
    L.append('5. 图片仅作个人研究与非商业展示，版权归原作者；每张图的平台、来源页、原始直链记在各店 `photos/_sources.csv`。\n')

    L.append('## 五、复核方式\n')
    L.append('- 逐店照片与直链：`NN_门店名/photos/` + `_sources.csv`')
    L.append('- 逐张分辨率与锐度：`_数据与评分/照片审计.json`')
    L.append('- 本次核对表（机器可读）：`_数据与评分/照片覆盖核对表.csv`')
    L.append('- 候选与弃用留档：`_数据与评分/候选图/`（含每张图的原始标题与直链）\n')
    L.append('---\n')
    L.append('*个人研究与非商业用途。图片版权归原作者 / 麦当劳中国所有，如有侵权请联系删除。*')
    p = os.path.join(BASE, '照片核对报告.md')
    open(p, 'w', encoding='utf-8').write('\n'.join(L))
    print('md ->', p)
    return p


def write_docx(rows):
    doc = Document()
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = Cm(29.7), Cm(21)
    for m in ('left_margin', 'right_margin'):
        setattr(sec, m, Cm(1.8))

    def run_font(r, size=10.5, bold=False, color=None):
        r.font.name = FONT
        r.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
        r.font.size = Pt(size)
        r.bold = bold
        if color:
            r.font.color.rgb = RGBColor(*color)

    def para(text, size=10, bold=False, color=None, align=None, space=6):
        p = doc.add_paragraph()
        r = p.add_run(text)
        run_font(r, size, bold, color)
        p.paragraph_format.space_after = Pt(space)
        if align is not None:
            p.alignment = align

    def table(data, widths, size=8.5, header=True):
        t = doc.add_table(rows=len(data), cols=len(data[0]))
        t.style = 'Table Grid'
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, row in enumerate(data):
            for j, val in enumerate(row):
                c = t.cell(i, j)
                c.width = Cm(widths[j])
                c.text = ''
                p = c.paragraphs[0]
                r = p.add_run(str(val))
                run_font(r, size, header and i == 0)
        return t

    total = sum(r['n'] for r in rows)
    filled = [r for r in rows if r['n']]
    empty = [r for r in rows if not r['n']]

    h = doc.add_heading('广州麦当劳人气 TOP10 · 门店照片核对报告', 0)
    for r in h.runs:
        run_font(r, 22, True)
    para('核对日期：%s　｜　结论：%d 家有实拍（共 %d 张），%d 家无公开可确认实拍'
         % (STAMP, len(filled), total, len(empty)), 10.5, color=(0x55, 0x55, 0x55))

    doc.add_heading('一、逐店核对总表', 2)
    data = [('名次', '门店', '照片', '覆盖角度', '清晰度分布', '核验结论')]
    for r in rows:
        data.append((str(r['no']), r['name'], str(r['n']), r['angles'],
                     r['grade'], r['short_v']))
    table(data, [1.4, 6.2, 1.4, 4.6, 4.4, 8.2])

    doc.add_heading('二、仍无法补充照片的门店及原因', 2)
    for r in empty:
        para('%d. %s' % (r['no'], r['name']), 11, True)
        para('地址：%s' % r['addr'], 9.5)
        para('结论：%s' % r['verdict'], 9.5)
        para('逐渠道结果：%s' % r['reason'], 9.5, color=(0x33, 0x33, 0x33))
    para('这两家门店并非「没有认真找」：360 图片搜索（大众点评图床索引，本次唯一有效的新增渠道）、'
         '大众点评 / 美团网页端、开饭喇、麦当劳中国官网、携程 / Trip.com、百度图片、搜狗图片、'
         '百度地图、Bing 图片、马蜂窝——全部试过。东风西路是本次榜单第 1 名（高德 5.0 分），'
         '江湾壹号在沿江路商圈，属于「榜单热度高、网络照片沉淀少」的典型，这是公开数据的真实分布。',
         9.5, color=(0x55, 0x55, 0x55))

    doc.add_heading('三、全库照片质量核查（含本次新增）', 2)
    notes = {
        '沙面': '质量最好，946–1080 宽、锐度 20–52，无重复。',
        '丽都': '525–700 宽（点评图床原图上限），画质中等但角度齐全。',
        '总统': '仅 3 张（外立面 / 前台 / 座位），受公开图源数量限制。',
        '广百': '700 宽为主，1 张 1080×1620 招牌特写，画质均匀。',
        '海珠广场': '官网 640 宽，压缩较重（90–260KB/张），细节一般。',
        '宜安': '575–700 宽；CNT_03 仅 575×430，是本次唯一偏低的补图。',
        '天字码头': 'EXT_01 仅 320×320（官网缩略尺寸），其余 640 宽。',
        'CUBE': 'EXT_02 仅 320×320；SEAT_02 为 640×210 长条构图。',
    }
    d2 = [('门店', '数量', '清晰', '一般', '偏低', '问题说明')]
    for r in rows:
        if not r['n']:
            continue
        g = stats(r['short'])
        d2.append((r['name'], str(r['n']), str(g['清晰']), str(g['一般']),
                   str(g['偏低']), notes.get(r['short'], '')))
    table(d2, [5.4, 1.6, 1.6, 1.6, 1.6, 14.4])
    para('判定口径：长边 ≥1000 且锐度 ≥12 记「清晰」；长边 ≥600 且锐度 ≥7 记「一般」；其余「偏低」。'
         '锐度 = 800px 缩略图边缘强度标准差。全库 %d 张未检出近似重复（16×16 均值哈希，距离 ≤12 判重）。'
         % total, 9, color=(0x66, 0x66, 0x66))

    doc.add_heading('四、收录与排除规则', 2)
    for t in ['只要门店空间照（外立面 / 门头 / 点餐前台 / 座位区 / 儿童区 / 招牌 / 周边），菜品与包装特写不收。',
              '必须能确认是本店：店名精确匹配，或画面可读到本店专属标识（水印、商场招牌、下沉楼梯等）。',
              '异地同名店一律排除：上海江湾镇、上海唐镇阳光城、合肥恒生阳光城、佛山江湾三路、郑州东风路、北京丽都／复兴门等。',
              '不放示意图、占位图、AI 生成图；缺就写缺。',
              '图片仅作个人研究与非商业展示，版权归原作者；逐张来源见各店 photos/_sources.csv。']:
        para('· ' + t, 9.5)

    doc.add_heading('五、复核入口', 2)
    for t in ['逐店照片与直链：NN_门店名/photos/ 与 _sources.csv',
              '逐张分辨率与锐度：_数据与评分/照片审计.json',
              '机器可读核对表：_数据与评分/照片覆盖核对表.csv',
              '候选与弃用留档：_数据与评分/候选图/（含原始标题与图片直链）']:
        para('· ' + t, 9.5)

    p = os.path.join(BASE, '照片核对报告.docx')
    doc.save(p)
    print('docx ->', p)
    return p


if __name__ == '__main__':
    rows = build_rows()
    write_csv(rows)
    write_md(rows)
    write_docx(rows)
