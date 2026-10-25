# -*- coding: utf-8 -*-
"""渲染每店 docx + 总览 docx"""
import json, os, csv
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

BASE = os.path.join(os.path.dirname(__file__), '..')
stores = json.load(open(os.path.join(BASE, '_构建工具', 'stores.json'), encoding='utf-8'))
STAMP = '2026-10-24'
FONT = '微软雅黑'
CODE_ORDER = ['EXT', 'CNT', 'SEAT', 'KID', 'SIGN', 'ENV']

def brief(x, n):
    for sep in ['（', '，', '；', '。']:
        x = str(x).split(sep)[0]
    return x[:n]


DECL = ('本档案不是销量排名。麦当劳中国不公开单店营业额，门店级销量属于商业机密，'
        '全网不存在「广州麦当劳销量前十」的权威榜单。本档案以高德地图公开榜单为主干，'
        '叠加门店规模、商圈能级、官方身份做加权估算，反映的是公开可见度与讨论热度，'
        '不代表实际销量或客流量。')


def styled(doc):
    st = doc.styles['Normal']
    st.font.name = FONT
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
    st.paragraph_format.line_spacing = 1.45
    st.paragraph_format.space_after = Pt(4)
    for i, sz in [(1, 20), (2, 14), (3, 11.5)]:
        h = doc.styles['Heading %d' % i]
        h.font.name = FONT
        h.font.size = Pt(sz)
        h.font.bold = True
        h.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
        h.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
        h.paragraph_format.space_before = Pt(14 if i == 1 else 10)
        h.paragraph_format.space_after = Pt(6)


def para(doc, text, size=10.5, bold=False, italic=False, color=None, align=None, space_after=4):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = FONT
    r.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    if color:
        r.font.color.rgb = RGBColor(*color)
    if align:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    return p


def table(doc, rows, widths=None, size=9.5, header=True):
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci, val in enumerate(row):
            cells[ci].text = ''
            p = cells[ci].paragraphs[0]
            r = p.add_run(str(val))
            r.font.name = FONT
            r.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
            r.font.size = Pt(size)
            if header and ri == 0:
                r.bold = True
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.2
    if widths:
        for ci, w in enumerate(widths):
            for row in t.rows:
                row.cells[ci].width = Cm(w)
    return t


def rank_text(s):
    if not s['ranks']:
        return '未进入所采集的 8 个高德榜单'
    return '；'.join('%s 第 %d' % (r['tab'], r['rank']) for r in s['ranks'])


def doc_store(s, target=None):
    doc = Document()
    styled(doc)
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.4)
    sec.top_margin = sec.bottom_margin = Cm(2.2)

    para(doc, s['title'], size=21, bold=True, space_after=2)
    para(doc, '第 %d 名 · 综合指数 %.0f 分 · 入选通道：%s · %s %s' % (
        s['no'], s['score']['total'], s['score']['channel'], s['district'], s['area']),
        size=10, color=(0x77, 0x77, 0x77), space_after=2)
    para(doc, '数据采集日期：%s　|　个人研究用途整理' % STAMP, size=9,
         color=(0x99, 0x99, 0x99), space_after=10)

    doc.add_heading('基本信息', 2)
    rows = [('项目', '内容'),
            ('门店全称', s['title']),
            ('别名 / 平台写法', s['alias']),
            ('地址', s['address']),
            ('地址备注', s['addr_note']),
            ('行政区 / 商圈', '%s / %s' % (s['district'], s['area'])),
            ('高德评分', ('%.1f' % s['rating']) if s['rating'] else '未收录（开业时间短或样本不足）'),
            ('高德榜单表现', rank_text(s)),
            ('开业 / 成立时间', s['opened']),
            ('时间来源', s['opened_src']),
            ('面积', s['sqm']),
            ('座位数', s['seats']),
            ('店型 / 官方身份', s['identity']),
            ('营业时间', s['hours']),
            ('电话', s['phone']),
            ('交通', s['traffic'])]
    table(doc, rows, widths=[3.6, 12.6], size=9)

    doc.add_heading('综合指数（满分 100）', 2)
    sc = s['score']
    table(doc, [('维度', '得分', '满分', '说明'),
                ('A 高德榜单表现', sc['A'], 40, '上榜次数 + 最好名次'),
                ('B 门店规模', sc['B'], 20, '面积 + 座位数'),
                ('C 商圈能级', sc['C'], 20, '地标 20 / 一级 15 / 区域中心 11 / 成熟社区 7 / 城郊 3'),
                ('D 官方身份', sc['D'], 20, '旗舰、首发、里程碑店型'),
                ('合计', sc['total'], 100, ('含推定项：' + sc['estimated']) if sc['estimated'] else '无推定项')],
          widths=[4.2, 2.2, 2.2, 7.6], size=9)

    doc.add_heading('门店与空间', 2)
    for line in ['面积 / 座位：%s；%s' % (s['sqm'], s['seats']),
                 '店型与身份：%s' % s['identity'],
                 '营业时间：%s' % s['hours'],
                 '怎么去：%s' % s['traffic']]:
        p = doc.add_paragraph(style='List Bullet')
        r = p.add_run(line)
        r.font.name = FONT
        r.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
        r.font.size = Pt(10)

    doc.add_heading('实拍', 2)
    if s['photo_files']:
        para(doc, '共 %d 张，来源：%s（%s）。版权归原作者 / 品牌方所有。' % (
            len(s['photo_files']), s['photo_src'], s['photo_platform']), size=9.5,
            color=(0x55, 0x55, 0x55))
        if s.get('photo_basis'):
            para(doc, '核验依据：%s' % s['photo_basis'], size=9, italic=True,
                 color=(0x55, 0x55, 0x55))
        groups = {}
        for ph, fn in zip(s['photos'], s['photo_files']):
            groups.setdefault(ph['code'], []).append((ph['code_cn'], fn))
        for code in CODE_ORDER:
            if code not in groups:
                continue
            doc.add_heading('%s（%s）' % (groups[code][0][0], code), 3)
            for cn, fn in groups[code]:
                fp = os.path.join(BASE, '%02d_%s' % (s['no'], s['folder']), 'photos', fn)
                if os.path.exists(fp):
                    doc.add_picture(fp, width=Cm(14))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                    para(doc, fn, size=8, italic=True, color=(0x88, 0x88, 0x88),
                         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8)
        missing = [c for c in CODE_ORDER if c not in groups]
        if missing:
            name = {'EXT': '外立面 / 门头', 'CNT': '点餐前台', 'SEAT': '座位区',
                    'KID': '儿童区', 'SIGN': '招牌细节', 'ENV': '周边环境'}
            para(doc, '该店暂未找到公开可下载的：%s 实拍。' % '、'.join(name[c] for c in missing),
                 size=9, italic=True, color=(0x88, 0x88, 0x88))
    else:
        para(doc, '本店暂无公开可下载的实拍照片。', bold=True)
        if s.get('photo_absent_summary'):
            para(doc, s['photo_absent_summary'], size=9.5)
        if s.get('photo_attempts'):
            para(doc, '逐渠道尝试记录：', size=9.5, bold=True)
            for i, t in enumerate(s['photo_attempts'], 1):
                para(doc, '%d. %s' % (i, t), size=9)
        para(doc, '按「只放可核验实拍、不伪造」的原则，本店不放任何示意图或占位图。'
                  '下方提供平台相册直链，可自行查看完整照片。', size=9.5)

    doc.add_heading('照片来源与出处', 2)
    for name, url in s['links']:
        para(doc, '· %s：%s' % (name, url), size=9)
    if s['photo_files']:
        para(doc, '· 本店照片原始出处：%s（%s）' % (s['photo_src'], s['photo_page']), size=9)
        para(doc, '· 版权说明：%s' % s['credit'], size=9)
        para(doc, '· 逐张明细见 photos/_sources.csv', size=9)

    doc.add_heading('网上风评', 2)
    doc.add_heading('好评', 3)
    for p_ in s['pros']:
        p = doc.add_paragraph(style='List Number')
        r = p.add_run(p_)
        r.font.name = FONT
        r.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
        r.font.size = Pt(10)
    doc.add_heading('差评与短板', 3)
    for c_ in s['cons']:
        p = doc.add_paragraph(style='List Number')
        r = p.add_run(c_)
        r.font.name = FONT
        r.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
        r.font.size = Pt(10)
    para(doc, '口碑内容整合自大众点评、开饭喇、携程 / Trip.com、新浪实测稿等公开页面。'
              '点评与开饭喇站点有反爬拦截，相关内容来自搜索引擎摘要，未经页面原文逐条核对；'
              '差评为归纳转述，非用户原话逐字引用。', size=8.5, italic=True, color=(0x88, 0x88, 0x88))

    doc.add_heading('适合什么场景', 2)
    para(doc, s['scenes'])

    doc.add_heading('待核项与数据说明', 2)
    items = []
    if s['rating'] is None:
        items.append('高德未收录评分：该店未进入所采集的 8 个高德榜单。')
    if '不详' in s['opened']:
        items.append('开业时间未查到确切来源，如实标注「不详」，未做推测。')
    if '未公开' in s['sqm']:
        items.append('面积未公开，未按照片目测反推。')
    if '未公开' in s['seats']:
        items.append('座位数未公开。')
    if s['score']['estimated']:
        items.append('规模维度为推定值（%s），取候选池同维度中位档。' % s['score']['estimated'])
    if '未核实' in s['hours'] or '未核实' in s['phone']:
        items.append('营业时间 / 电话未核实，开业时间短或公开渠道未披露。')
    items.append('数据采集日期 %s，榜单与评分每日变动，以上仅为当日快照。' % STAMP)
    for it in items:
        p = doc.add_paragraph(style='List Bullet')
        r = p.add_run(it)
        r.font.name = FONT
        r.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
        r.font.size = Pt(9)

    para(doc, '本文件为个人研究与非商业展示用途整理，图片版权归原作者 / 麦当劳中国所有，如有侵权请联系删除。',
         size=8.5, italic=True, color=(0x99, 0x99, 0x99))

    fn = target or os.path.join(BASE, '%02d_%s' % (s['no'], s['folder']),
                                '%02d_%s.docx' % (s['no'], s['folder']))
    doc.save(fn)
    return fn


def doc_overview(obs):
    doc = Document()
    styled(doc)
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = sec.page_height, sec.page_width
    sec.left_margin = sec.right_margin = Cm(1.8)
    sec.top_margin = sec.bottom_margin = Cm(1.8)

    para(doc, '广州麦当劳人气 TOP10 门店总览', size=22, bold=True, space_after=2)
    para(doc, '采集日期 %s　|　样本：广州 11 区麦当劳门店　|　框架：8 个高德公开榜单' % STAMP,
         size=10, color=(0x77, 0x77, 0x77), space_after=12)

    doc.add_heading('一、先说清楚：这不是销量榜', 2)
    para(doc, DECL)
    para(doc, '麦当劳从未公开单店销量，任何声称「广州麦当劳销量前十」的名单都不具备数据基础。'
              '本档案改用可追溯的公开信号做加权估算，并把方法、权重、缺失值处理全部摊开，方便复核和推翻。')

    doc.add_heading('二、方法', 2)
    doc.add_heading('1. 榜单来源', 3)
    para(doc, '从高德地图榜单页抓取 8 个榜（2026-10-24 快照）：')
    para(doc, '· 品牌榜 5 个：麦当劳 · 广州 · 白领 / 学生 / 家庭 / 游客 / 老年人', size=10)
    para(doc, '· 品类榜 3 个：西式快餐 · 汉堡快餐 · 快餐简餐（均取白领维度）', size=10)
    para(doc, '高德榜单基于用户真实出行与评价数据排序，是目前最接近「客流热度」的公开指标。')

    doc.add_heading('2. 加权模型（满分 100）', 3)
    table(doc, [('维度', '权重', '打分规则'),
                ('A 高德榜单表现', 40, '上榜次数 0/1/2/3/≥4 → 0/10/18/26/34 分；最好名次 1–2 名 +6、3–5 名 +4、6–10 名 +2'),
                ('B 门店规模', 20, '面积 ≥700㎡ 12 / 500–699 10 / 350–499 8 / 250–349 6 / <250 4；座位 ≥150 8 / 100–149 6 / 70–99 4 / <70 2'),
                ('C 商圈能级', 20, '城市级地标 20 / 一级商圈 15 / 区域中心 11 / 成熟社区 7 / 城郊园区 3'),
                ('D 官方身份', 20, '全国概念首发 20 / 全国或大区旗舰、特殊店型 18 / 城市里程碑 14 / 官方称旗舰 10 / 无 0')],
          widths=[4.0, 2.0, 19.5], size=9)

    doc.add_heading('3. 缺失值处理', 3)
    para(doc, '面积、座位这类数据绝大多数门店不公开。缺失项一律取候选池该维度的中位档，绝不计 0 分，'
              '否则新开旗舰店会被系统性低估。所有推定值在单店文档的得分卡里都标了「含推定项」。')

    doc.add_heading('4. 双通道入选（这条规则决定了名单长什么样）', 3)
    for t in ['榜单通道 7 席：在高德各榜命中 ≥2 次的门店中，按总分取前 7 名。',
              '地标通道 3 席：剩余门店按「官方身份 > 规模 > 商圈」取前 3 名。',
              '合并后按总分重新排名，每店标注入选通道。']:
        p = doc.add_paragraph(style='List Bullet')
        r = p.add_run(t)
        r.font.name = FONT
        r.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
        r.font.size = Pt(10)
    para(doc, '为什么要地标通道：天字码头店、海珠广场店、白云 CUBE 旗舰店这类门店在榜单里几乎全部缺席——'
              '新店评分样本少，高德榜单又偏向日常高频复购的街坊客群。如果纯按分数排，「全国首发设计门店」'
              '「全市面积最大门店」会集体落榜，名单会变成一份纯街坊食堂榜。这条规则是为了纠正这个偏差，'
              '代价是牺牲了 1 席纯榜单门店。')

    doc.add_heading('三、TOP10 总表', 2)
    rows = [('名次', '门店', '区 / 商圈', '总分', 'A', 'B', 'C', 'D', '高德评分', '最好榜名次', '面积', '座位', '官方身份', '通道')]
    for s in stores:
        best = ('第%d（%s）' % (s['ranks'][0]['rank'], s['ranks'][0]['tab'].split('·')[0])) if s['ranks'] else '未上榜'
        rows.append((s['no'], s['title'].replace('麦当劳（', '').replace('）', ''), '%s/%s' % (s['district'], s['area']),
                     s['score']['total'], s['score']['A'], s['score']['B'], s['score']['C'], s['score']['D'],
                     ('%.1f' % s['rating']) if s['rating'] else '—', best,
                     brief(s['sqm'], 10), brief(s['seats'], 8),
                     brief(s['identity'], 20), s['score']['channel']))
    table(doc, rows, widths=[1.1, 4.3, 4.0, 1.2, 0.9, 0.9, 0.9, 0.9, 1.6, 2.9, 2.4, 2.2, 4.6, 1.3], size=8)

    doc.add_heading('四、分维度小榜', 2)
    byA = sorted(stores, key=lambda x: -x['score']['A'])[:3]
    byB = sorted(stores, key=lambda x: -x['score']['B'])[:3]
    byD = [x for x in sorted(stores, key=lambda x: -x['score']['D']) if x['score']['D'] > 0]
    for t in ['榜单之王（A 维度）：' + '、'.join('%s %d 分' % (x['short'], x['score']['A']) for x in byA),
              '体量最大（B 维度）：' + '、'.join('%s %d 分' % (x['short'], x['score']['B']) for x in byB),
              '地段最贵（C 维度 20 分档）：' + '、'.join(x['short'] for x in stores if x['score']['C'] == 20),
              '身份最特殊（D 维度）：' + '、'.join('%s %d 分' % (x['short'], x['score']['D']) for x in byD)]:
        p = doc.add_paragraph(style='List Bullet')
        r = p.add_run(t)
        r.font.name = FONT
        r.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
        r.font.size = Pt(10)

    doc.add_heading('五、差一点入选（11–15 名）', 2)
    reasons = {
        '国际大厦': '总分 51 排第 8，但榜单通道只取 7 席；原址是 1993-02-20 广州第一家麦当劳（当日交易 14129 次创当时全球纪录），但首店 2010 年因租约结业，现店为后续重开，不构成城市里程碑身份',
        '今日广场店': '天河路商圈、4.8 分，但只命中 2 个榜、最佳第 2，A 维度不足以挤进前 7',
        '动漫星城店': '公园前地铁出入口旁，客流极强，但仅命中 2 个榜，规模数据缺失',
        '恩宁路': '永庆坊一带，命中 2 个榜（游客榜第 3），无官方身份加分',
        '宝华路': '恒宝广场地库店，命中 2 个榜，商圈评为一级（15 分）拖累总分',
    }
    rows = [('名次', '门店', '区', '总分', '落选原因')]
    for i, r in enumerate(obs, 11):
        rows.append((i, r['门店'], r['行政区'], r['总分'], reasons.get(r['门店'], '总分不足')))
    table(doc, rows, widths=[1.3, 4.0, 2.0, 1.5, 16.7], size=8.5)
    para(doc, '特别说明：正佳广场、天河城、天环等天河路核心商场店全部落榜。这不是漏查，而是高德榜单的真实结果——'
              '天河路商场店的评分被大量游客与一次性客流稀释，普遍在 4.3–4.5 区间，进不了前列。'
              '数据如此，没有为了「看起来合理」去调权重。', size=9.5, color=(0x55, 0x55, 0x55))

    doc.add_heading('六、照片覆盖情况', 2)
    cnmap = {'EXT': '外立面', 'CNT': '前台', 'SEAT': '座位', 'KID': '儿童区',
             'SIGN': '招牌', 'ENV': '环境'}
    prow = [('门店', '照片数', '已覆盖角度', '核验结论')]
    for s in stores:
        codes = []
        for p in s['photos']:
            if p['code'] not in codes:
                codes.append(p['code'])
        prow.append((s['title'].replace('麦当劳（', '').replace('）', ''),
                     str(len(s['photo_files'])),
                     '、'.join(cnmap[c] for c in codes) or '—',
                     '已核对：店名与画面双重确认' if s['photo_files'] else '无可用实拍，原因见核对报告'))
    table(doc, prow, widths=[5.5, 2.2, 5.5, 8.3], size=8.5)
    para(doc, '共 %d 张实拍，覆盖 %d 家门店；%s 没有可确认的实拍图，已在该店文档中逐条列出渠道与失败原因，'
              '并汇总到根目录《照片核对报告》。' % (
                  sum(len(s['photo_files']) for s in stores),
                  sum(1 for s in stores if s['photo_files']),
                  '、'.join(s['short'] for s in stores if not s['photo_files'])),
         size=9.5, color=(0x55, 0x55, 0x55))
    para(doc, '收录规则：只要门店空间照（外立面 / 门头 / 点餐前台 / 座位区 / 招牌 / 周边），不收菜品特写；'
              '异地同名店（上海江湾镇、上海唐镇阳光城、合肥恒生阳光城、佛山江湾三路等）一律排除；不放示意图或占位图。',
         size=9, color=(0x88, 0x88, 0x88))

    doc.add_heading('七、数据缺口（必须知道）', 2)
    table(doc, [('字段', '缺失情况', '处理方式'),
                ('单店销量 / 营业额', '100% 缺失，永不公开', '改用高德榜单做代理指标'),
                ('面积', '10 家中仅 3 家有公开数据', '缺失取候选池中位档并标注推定'),
                ('座位数', '10 家中仅 2 家有公开数据', '同上'),
                ('开业年份', '4 家未查到', '如实标注「不详」，不推测'),
                ('高德评分', '3 家未收录', '标注「未收录」，不计 0 分'),
                ('实拍照片', '%d 家有可下载实拍（共 %d 张），%d 家无' % (sum(1 for s in stores if s['photo_files']), sum(len(s['photo_files']) for s in stores), sum(1 for s in stores if not s['photo_files'])), '无图门店逐条列出失败渠道，只附平台相册直链，不放示意图'),
                ('用户评论原文', '点评 / 开饭喇有反爬拦截', '只取搜索摘要，标注未经原文核对')],
          widths=[4.2, 9.0, 12.3], size=9)

    doc.add_heading('八、局限与可能的误读', 2)
    for i, t in enumerate([
        '榜单 ≠ 客流 ≠ 销量。高德榜单综合了评分与出行数据，高评分的小店可能排在高客流大店之前。',
        '新店系统性吃亏。开业不足一年的门店评分样本太少，几乎不可能进榜，地标通道只能部分补偿。',
        '老城区被高估。越秀、荔湾的街坊店复购率高、评分稳定，在榜上占绝对优势，但不等于营业额最高。',
        '推定值会传导误差。规模维度大面积使用中位推定，若真实面积与推定差异大，排名可能变动 1–2 位。',
        '快照有时效。所有名次、评分均为 %s 当日数据，榜单每日更新。' % STAMP], 1):
        p = doc.add_paragraph()
        r = p.add_run('%d. %s' % (i, t))
        r.font.name = FONT
        r.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
        r.font.size = Pt(10)

    doc.add_heading('九、怎么复核', 2)
    for t in ['原始榜单页面：https://ranks.amap.com/ranking/麦当劳/广州市/白领（把「白领」换成 学生 / 家庭 / 游客 / 老年人 即其余 4 个榜）',
              '原始抓取留档：_数据与评分/榜单原始抓取_20261024.json',
              '全量打分：_数据与评分/候选池评分明细.csv（42 家候选门店逐项分数、推定标记、入选通道）',
              '照片出处：各店 photos/_sources.csv']:
        p = doc.add_paragraph(style='List Bullet')
        r = p.add_run(t)
        r.font.name = FONT
        r.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
        r.font.size = Pt(9)

    para(doc, '本档案为个人研究与非商业展示用途整理。图片版权归原作者 / 麦当劳中国所有，如有侵权请联系删除。',
         size=8.5, italic=True, color=(0x99, 0x99, 0x99))

    fn = os.path.join(BASE, '00_广州麦当劳人气TOP10总览.docx')
    doc.save(fn)
    return fn


def main():
    locked = []
    for s in stores:
        try:
            print('docx', doc_store(s))
        except PermissionError:
            alt = os.path.join(BASE, '%02d_%s' % (s['no'], s['folder']),
                               '%02d_%s.待替换.docx' % (s['no'], s['folder']))
            doc_store(s, target=alt)
            locked.append(s['no'])
            print('!! %02d %s.docx 被占用，已写入 %s' % (s['no'], s['folder'], os.path.basename(alt)))
    obs = []
    with open(os.path.join(BASE, '_数据与评分', '候选池评分明细.csv'), encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if not r['最终名次']:
                obs.append(r)
    try:
        print('docx', doc_overview(obs[:5]))
    except PermissionError:
        locked.append(0)
        print('!! 总览 docx 被占用，已跳过')
    if locked:
        print('LOCKED:', locked)


if __name__ == '__main__':
    main()
