# -*- coding: utf-8 -*-
"""渲染每店 Markdown + 总览 + README"""
import json, os, csv

BASE = os.path.join(os.path.dirname(__file__), '..')
stores = json.load(open(os.path.join(BASE, '_构建工具', 'stores.json'), encoding='utf-8'))
STAMP = '2026-10-24'

DECL = ('> **本档案不是销量排名。** 麦当劳中国不公开单店营业额，门店级销量属于商业机密，'
        '全网不存在「广州麦当劳销量前十」的权威榜单。本档案以高德地图公开榜单为主干，'
        '叠加门店规模、商圈能级、官方身份做加权估算，反映的是**公开可见度与讨论热度**，'
        '不代表实际销量或客流量。')

CODE_ORDER = ['EXT', 'CNT', 'SEAT', 'KID', 'SIGN', 'ENV']

def brief(x, n):
    for sep in ['（', '，', '；', '。']:
        x = str(x).split(sep)[0]
    return x[:n]



def rank_text(s):
    if not s['ranks']:
        return '未进入所采集的 8 个高德榜单'
    return '；'.join('%s 第 %d' % (r['tab'], r['rank']) for r in s['ranks'])


def md_store(s):
    d = '%02d_%s' % (s['no'], s['folder'])
    L = []
    L.append('# %s\n' % s['title'])
    L.append('**第 %d 名 · 综合指数 %.0f 分 · 入选通道：%s**\n' % (s['no'], s['score']['total'], s['score']['channel']))
    L.append('%s · %s · %s\n' % (s['district'], s['area'], s['scenes'].split(' / ')[0]))
    L.append('---\n')

    L.append('## 基本信息\n')
    L.append('| 项目 | 内容 |')
    L.append('| --- | --- |')
    rows = [
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
        ('交通', s['traffic']),
    ]
    for k, v in rows:
        L.append('| %s | %s |' % (k, v.replace('|', '｜')))
    L.append('')

    L.append('## 综合指数（满分 100）\n')
    sc = s['score']
    L.append('| 维度 | 得分 | 满分 | 说明 |')
    L.append('| --- | --- | --- | --- |')
    L.append('| A 高德榜单表现 | %d | 40 | 上榜次数 + 最好名次 |' % sc['A'])
    L.append('| B 门店规模 | %d | 20 | 面积 + 座位数 |' % sc['B'])
    L.append('| C 商圈能级 | %d | 20 | 城市级地标 20 / 一级商圈 15 / 区域中心 11 / 成熟社区 7 / 城郊园区 3 |' % sc['C'])
    L.append('| D 官方身份 | %d | 20 | 旗舰、首发、里程碑店型 |' % sc['D'])
    L.append('| **合计** | **%d** | 100 | %s |' % (sc['total'], '含推定项：' + sc['estimated'] if sc['estimated'] else '无推定项'))
    L.append('')

    L.append('## 门店与空间\n')
    L.append('- **面积 / 座位**：%s；%s' % (s['sqm'], s['seats']))
    L.append('- **店型与身份**：%s' % s['identity'])
    L.append('- **营业时间**：%s' % s['hours'])
    L.append('- **怎么去**：%s' % s['traffic'])
    L.append('')
    L.append('## 实拍\n')
    if s['photo_files']:
        L.append('共 %d 张，来源：%s（%s）。图片版权归原作者 / 品牌方所有。\n' % (
            len(s['photo_files']), s['photo_src'], s['photo_platform']))
        if s.get('photo_basis'):
            L.append('> 核验依据：%s\n' % s['photo_basis'])
        groups = {}
        for ph, fn in zip(s['photos'], s['photo_files']):
            groups.setdefault(ph['code'], []).append((ph['code_cn'], fn))
        for code in CODE_ORDER:
            if code not in groups:
                continue
            L.append('### %s（%s）\n' % (groups[code][0][0], code))
            for cn, fn in groups[code]:
                L.append('![%s](photos/%s)\n' % (fn, fn))
                L.append('*`%s`*\n' % fn)
        missing = [c for c in CODE_ORDER if c not in groups]
        if missing:
            name = {'EXT': '外立面 / 门头', 'CNT': '点餐前台', 'SEAT': '座位区',
                    'KID': '儿童区', 'SIGN': '招牌细节', 'ENV': '周边环境'}
            L.append('> 该店暂未找到公开可下载的：%s 实拍。\n' % '、'.join(name[c] for c in missing))
    else:
        L.append('**本店暂无公开可下载的实拍照片。**\n')
        if s.get('photo_absent_summary'):
            L.append('%s\n' % s['photo_absent_summary'])
        if s.get('photo_attempts'):
            L.append('逐渠道尝试记录：\n')
            for i, t in enumerate(s['photo_attempts'], 1):
                L.append('%d. %s' % (i, t))
            L.append('')
        L.append('按「只放可核验实拍、不伪造」的原则，本店不放任何示意图或占位图。下方提供平台相册直链，可自行查看完整照片：\n')
    L.append('### 照片来源\n')
    for name, url in s['links']:
        L.append('- %s：%s' % (name, url))
    if s['photo_files']:
        L.append('\n- 本店照片原始出处：%s（%s）' % (s['photo_src'], s['photo_page']))
        L.append('- 版权说明：%s' % s['credit'])
        L.append('- 明细见 `photos/_sources.csv`')
    L.append('')

    L.append('## 网上风评\n')
    L.append('### 好评\n')
    for i, p in enumerate(s['pros'], 1):
        L.append('%d. %s' % (i, p))
    L.append('')
    L.append('### 差评与短板\n')
    for i, c in enumerate(s['cons'], 1):
        L.append('%d. %s' % (i, c))
    L.append('')
    L.append('> 口碑内容整合自大众点评、开饭喇、携程 / Trip.com、新浪实测稿等公开页面。'
             '点评与开饭喇站点有反爬拦截，相关内容来自搜索引擎摘要，**未经页面原文逐条核对**；'
             '差评为归纳转述，非用户原话逐字引用。\n')

    L.append('## 适合什么场景\n')
    L.append(s['scenes'])
    L.append('')
    L.append('## 待核项与数据说明\n')
    if s['rating'] is None:
        L.append('- 高德未收录评分：该店未进入所采集的 8 个高德榜单，评分缺失。')
    if '不详' in s['opened'] or '未查到' in s['opened_src']:
        L.append('- 开业时间未查到确切来源，已如实标注「不详」，未做推测。')
    if '未公开' in s['sqm']:
        L.append('- 面积未公开，未按照片目测反推。')
    if '未公开' in s['seats']:
        L.append('- 座位数未公开。')
    if s['score']['estimated']:
        L.append('- 规模维度为推定值（%s），取候选池同维度中位档，已在此标注。' % s['score']['estimated'])
    if '未核实' in s['hours'] or '未核实' in s['phone']:
        L.append('- 营业时间 / 电话未核实，开业时间短或公开渠道未披露。')
    L.append('- 数据采集日期：%s。榜单与评分每日变动，以上仅为当日快照。' % STAMP)
    L.append('')
    L.append('---\n')
    L.append('*本文件为个人研究用途整理，图片版权归原作者 / 麦当劳中国所有，如有侵权请联系删除。*\n')
    return '\n'.join(L), d


def main():
    for s in stores:
        txt, d = md_store(s)
        path = os.path.join(BASE, d)
        os.makedirs(path, exist_ok=True)
        fn = os.path.join(path, '%02d_%s.md' % (s['no'], s['folder']))
        open(fn, 'w', encoding='utf-8').write(txt)
        print('md', fn)

    # 观察名单
    obs = []
    with open(os.path.join(BASE, '_数据与评分', '候选池评分明细.csv'), encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if not r['最终名次']:
                obs.append(r)
    obs = obs[:5]

    L = []
    L.append('# 广州麦当劳人气 TOP10 门店总览\n')
    L.append('采集日期：%s　|　样本：广州 11 区麦当劳门店　|　框架：8 个高德公开榜单\n' % STAMP)
    L.append('---\n')
    L.append('## 一、先说清楚：这不是销量榜\n')
    L.append(DECL + '\n')
    L.append('麦当劳从未公开单店销量，任何声称「广州麦当劳销量前十」的名单都不具备数据基础。'
             '本档案改用可追溯的公开信号做加权估算，并把方法、权重、缺失值处理全部摊开，方便你复核和推翻。\n')

    L.append('## 二、方法\n')
    L.append('### 1. 榜单来源\n')
    L.append('从高德地图榜单页抓取 8 个榜（2026-10-24 快照）：\n')
    L.append('- 品牌榜 5 个：麦当劳 · 广州 · 白领 / 学生 / 家庭 / 游客 / 老年人')
    L.append('- 品类榜 3 个：西式快餐 · 汉堡快餐 · 快餐简餐（均取白领维度）\n')
    L.append('高德榜单基于用户真实出行与评价数据排序，是目前最接近「客流热度」的公开指标。\n')
    L.append('### 2. 加权模型（满分 100）\n')
    L.append('| 维度 | 权重 | 打分规则 |')
    L.append('| --- | --- | --- |')
    L.append('| A 高德榜单表现 | 40 | 上榜次数 0/1/2/3/≥4 → 0/10/18/26/34 分；最好名次 1–2 名 +6、3–5 名 +4、6–10 名 +2 |')
    L.append('| B 门店规模 | 20 | 面积：≥700㎡ 12 / 500–699 10 / 350–499 8 / 250–349 6 / <250 4；座位：≥150 8 / 100–149 6 / 70–99 4 / <70 2 |')
    L.append('| C 商圈能级 | 20 | 城市级地标 20 / 一级商圈 15 / 区域中心 11 / 成熟社区 7 / 城郊园区 3 |')
    L.append('| D 官方身份 | 20 | 全国概念首发 20 / 全国或大区旗舰、特殊店型 18 / 城市里程碑 14 / 官方称旗舰 10 / 无 0 |\n')
    L.append('### 3. 缺失值处理\n')
    L.append('面积、座位这类数据绝大多数门店不公开。**缺失项一律取候选池该维度的中位档，绝不计 0 分**，'
             '否则新开旗舰店会被系统性低估。所有推定值在单店文档的得分卡里都标了「含推定项」。\n')
    L.append('### 4. 双通道入选（这条规则决定了名单长什么样）\n')
    L.append('- **榜单通道 7 席**：在高德各榜命中 ≥2 次的门店中，按总分取前 7 名。')
    L.append('- **地标通道 3 席**：剩余门店按「官方身份 > 规模 > 商圈」取前 3 名。')
    L.append('- 合并后按总分重新排名，每店标注入选通道。\n')
    L.append('为什么要地标通道：天字码头店、海珠广场店、白云 CUBE 旗舰店这类门店在榜单里几乎全部缺席——'
             '新店评分样本少，高德榜单又偏向日常高频复购的街坊客群。如果纯按分数排，'
             '「全国首发设计门店」「全市面积最大门店」会集体落榜，名单会变成一份纯街坊食堂榜。'
             '这条规则是为了纠正这个偏差，不是为了让名单好看，**代价是牺牲了 1 席纯榜单门店**。\n')

    L.append('## 三、TOP10 总表\n')
    L.append('| 名次 | 门店 | 区 / 商圈 | 总分 | A | B | C | D | 高德评分 | 最好榜单名次 | 面积 | 座位 | 官方身份 | 通道 |')
    L.append('| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |')
    for s in stores:
        best = ('第 %d 名（%s）' % (s['ranks'][0]['rank'], s['ranks'][0]['tab'])) if s['ranks'] else '未上榜'
        ident = brief(s['identity'], 26)
        L.append('| %d | %s | %s / %s | **%d** | %d | %d | %d | %d | %s | %s | %s | %s | %s | %s |' % (
            s['no'], s['title'].replace('麦当劳（', '').replace('）', ''), s['district'], s['area'],
            s['score']['total'], s['score']['A'], s['score']['B'], s['score']['C'], s['score']['D'],
            ('%.1f' % s['rating']) if s['rating'] else '—', best,
            brief(s['sqm'], 12), brief(s['seats'], 10), ident, s['score']['channel']))
    L.append('')

    L.append('## 四、分维度小榜\n')
    byA = sorted(stores, key=lambda x: -x['score']['A'])[:3]
    byB = sorted(stores, key=lambda x: -x['score']['B'])[:3]
    byC = sorted(stores, key=lambda x: -x['score']['C'])[:5]
    byD = [s for s in sorted(stores, key=lambda x: -x['score']['D']) if s['score']['D'] > 0]
    L.append('- **榜单之王（A 维度）**：%s' % '、'.join('%s %d 分' % (s['short'], s['score']['A']) for s in byA))
    L.append('- **体量最大（B 维度）**：%s' % '、'.join('%s %d 分' % (s['short'], s['score']['B']) for s in byB))
    L.append('- **地段最贵（C 维度，20 分档）**：%s' % '、'.join(s['short'] for s in byC if s['score']['C'] == 20))
    L.append('- **身份最特殊（D 维度）**：%s' % '、'.join('%s %d 分' % (s['short'], s['score']['D']) for s in byD))
    L.append('')

    L.append('## 五、差一点入选（11–15 名）\n')
    L.append('| 名次 | 门店 | 区 | 总分 | 落选原因 |')
    L.append('| --- | --- | --- | --- | --- |')
    reasons = {
        '国际大厦': '总分 51 排第 8，但榜单通道只取 7 席；原址是 1993-02-20 广州第一家麦当劳（当天交易 14129 次创当时全球纪录），但首店已于 2010 年因租约结业，现店为后续重开，不构成「城市里程碑」身份，故未加分',
        '今日广场店': '天河路商圈、评分 4.8，但只命中 2 个榜、最佳第 2，A 维度不足以挤进榜单通道前 7',
        '动漫星城店': '公园前地铁出入口旁，客流极强，但仅命中 2 个榜，规模数据缺失',
        '恩宁路': '永庆坊一带，命中 2 个榜（游客榜第 3），无官方身份加分',
        '宝华路': '恒宝广场地库店，命中 2 个榜，商圈评为一级（15 分）拖累总分',
    }
    for i, r in enumerate(obs, 11):
        L.append('| %d | %s | %s | %s | %s |' % (i, r['门店'], r['行政区'], r['总分'], reasons.get(r['门店'], '总分不足')))
    L.append('')
    L.append('> 特别说明：**正佳广场、天河城、天环等天河路核心商场店全部落榜**。'
             '这不是漏查，而是高德榜单的真实结果——天河路商场店的评分被大量游客与一次性客流稀释，'
             '普遍在 4.3–4.5 区间，进不了前列。数据如此，我没有为了「看起来合理」去调权重。\n')

    L.append('## 六、照片覆盖情况\n')
    L.append('| 门店 | 照片数 | 已覆盖角度 | 核验结论 |')
    L.append('| --- | --- | --- | --- |')
    cn = {'EXT': '外立面', 'CNT': '前台', 'SEAT': '座位', 'KID': '儿童区',
          'SIGN': '招牌', 'ENV': '环境'}
    for s in stores:
        codes = []
        for p in s['photos']:
            if p['code'] not in codes:
                codes.append(p['code'])
        concl = '已核对：店名与画面双重确认' if s['photo_files'] else '无可用实拍，原因见核对报告'
        L.append('| %s | %d | %s | %s |' % (
            s['title'].replace('麦当劳（', '').replace('）', ''),
            len(s['photo_files']), '、'.join(cn[c] for c in codes) or '—', concl))
    L.append('')
    L.append('共 **%d 张**实拍，覆盖 **%d 家**门店；**%s** 没有可确认的实拍图，'
             '已在该店文档中逐条列出渠道与失败原因，并汇总到根目录 `照片核对报告.md`。\n' % (
                 sum(len(s['photo_files']) for s in stores),
                 sum(1 for s in stores if s['photo_files']),
                 '、'.join(s['short'] for s in stores if not s['photo_files'])))
    L.append('> 收录规则：只要门店空间照（外立面 / 门头 / 点餐前台 / 座位区 / 招牌 / 周边），不收菜品特写；'
             '异地同名店（上海江湾镇、上海唐镇阳光城、合肥恒生阳光城、佛山江湾三路等）一律排除；不放示意图或占位图。\n')

    L.append('## 七、数据缺口（必须知道）\n')
    L.append('| 字段 | 缺失情况 | 处理方式 |')
    L.append('| --- | --- | --- |')
    L.append('| 单店销量 / 营业额 | 100% 缺失，永不公开 | 改用高德榜单做代理指标 |')
    L.append('| 面积 | 10 家中仅 3 家有公开数据 | 缺失取候选池中位档并标注「推定」 |')
    L.append('| 座位数 | 10 家中仅 2 家有公开数据 | 同上 |')
    L.append('| 开业年份 | 4 家未查到 | 如实标注「不详」，不推测 |')
    L.append('| 高德评分 | 3 家未收录 | 标注「未收录」，不计 0 分 |')
    L.append('| 实拍照片 | %d 家有可下载实拍（共 %d 张），%d 家无 | 无图门店逐条列出失败渠道，只附平台相册直链，不放示意图 |' % (
        sum(1 for s in stores if s['photo_files']),
        sum(len(s['photo_files']) for s in stores),
        sum(1 for s in stores if not s['photo_files'])))
    L.append('| 用户评论原文 | 点评 / 开饭喇有反爬拦截 | 只取搜索摘要，标注「未经原文核对」 |')
    L.append('')

    L.append('## 八、局限与可能的误读\n')
    L.append('1. **榜单≠客流≠销量。** 高德榜单综合了评分与出行数据，高评分的小店可能排在高客流大店之前。')
    L.append('2. **新店系统性吃亏。** 开业不足一年的门店评分样本太少，几乎不可能进榜，地标通道只能部分补偿。')
    L.append('3. **老城区被高估。** 越秀、荔湾的街坊店复购率高、评分稳定，在榜上占绝对优势；这不等于它们的营业额最高。')
    L.append('4. **推定值会传导误差。** 规模维度大面积使用中位推定，若真实面积与推定差异大，排名可能变动 1–2 位。')
    L.append('5. **快照有时效。** 所有名次、评分均为 %s 当日数据，榜单每日更新。\n' % STAMP)

    L.append('## 九、怎么复核\n')
    L.append('- 原始榜单页面：`https://ranks.amap.com/ranking/麦当劳/广州市/白领`（把「白领」换成 学生 / 家庭 / 游客 / 老年人 即其余 4 个榜）')
    L.append('- 原始抓取留档：`_数据与评分/榜单原始抓取_20261024.json`（8 个榜的完整解析结果，含原始 HTML 在 `raw/`）')
    L.append('- 全量打分：`_数据与评分/候选池评分明细.csv`（42 家候选门店逐项分数、推定标记、入选通道）')
    L.append('- 榜单命中矩阵：同名目录下可按店名检索上榜情况')
    L.append('- 照片出处：各店 `photos/_sources.csv`\n')
    L.append('---\n')
    L.append('*本档案为个人研究与非商业展示用途整理。图片版权归原作者 / 麦当劳中国所有，如有侵权请联系删除。*')
    open(os.path.join(BASE, '00_广州麦当劳人气TOP10总览.md'), 'w', encoding='utf-8').write('\n'.join(L))
    print('md 总览')

    # README
    R = []
    R.append('# 广州前十麦当劳门店\n')
    R.append('采集日期：%s\n' % STAMP)
    R.append('**先读这个：这不是销量排名。** 麦当劳不公开单店销量，本档案是「人气综合指数」估算榜，'
             '方法、权重、缺失值处理全部写在 `00_广州麦当劳人气TOP10总览.md` 里。\n')
    R.append('## 目录\n')
    for s in stores:
        R.append('%d. [%s](%02d_%s/) — %s · %s · 综合指数 %.0f · 照片 %d 张' % (
            s['no'], s['title'], s['no'], s['folder'], s['district'], s['area'],
            s['score']['total'], len(s['photo_files'])))
    R.append('')
    R.append('## 每个门店文件夹里有什么\n')
    R.append('- `NN_门店名.md` / `NN_门店名.docx`：说明文档，含基本信息表、得分卡、面积座位、正负风评、实拍、照片来源链接')
    R.append('- `photos/`：该店实拍照片，命名规则 `序号_简称_角度_序号.jpg`')
    R.append('- `photos/_sources.csv`：每张图的平台、来源页、抓取时间、版权说明\n')
    R.append('## 角度代码\n')
    R.append('| 代码 | 含义 |')
    R.append('| --- | --- |')
    for c, n in [('EXT', '外立面 / 门头'), ('CNT', '点餐前台 / 甜品站'), ('SEAT', '座位区 / 堂食区'),
                 ('KID', '儿童区 / 游乐区'), ('SIGN', '招牌细节 / 品牌元素'), ('ENV', '周边环境')]:
        R.append('| %s | %s |' % (c, n))
    R.append('')
    R.append('## 照片核对\n')
    R.append('- `照片核对报告.md` / `.docx`：逐店照片核对结论、清晰度核查、仍无法补充照片的门店及原因')
    R.append('- `_数据与评分/照片覆盖核对表.csv`：10 家门店逐行的照片数 / 角度 / 清晰度 / 核验结论')
    R.append('- `_数据与评分/照片审计.json`：每张图的宽高、体积、锐度、哈希')
    R.append('- `_数据与评分/候选图/`：采集到的候选与弃用留档（含原始标题、图片直链）\n')
    R.append('## 支撑材料\n')
    R.append('- `_数据与评分/候选池评分明细.csv` — 42 家候选门店逐项打分')
    R.append('- `_数据与评分/榜单原始抓取_20261024.json` — 8 个高德榜的原始解析结果')
    R.append('- `_数据与评分/照片来源总表` — 见各店 `photos/_sources.csv`')
    R.append('- `_构建工具/` — 抓取与渲染脚本，可复现')
    R.append('')
    R.append('---\n')
    R.append('*个人研究与非商业用途。图片版权归原作者 / 麦当劳中国所有，如有侵权请联系删除。*')
    open(os.path.join(BASE, 'README.md'), 'w', encoding='utf-8').write('\n'.join(R))
    print('md README')


if __name__ == '__main__':
    main()
