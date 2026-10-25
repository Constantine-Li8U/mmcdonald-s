# -*- coding: utf-8 -*-
"""生成 stores.json（唯一数据源）：合并评分结果与人工核实资料"""
import json, os, re, shutil

BASE = os.path.join(os.path.dirname(__file__), '..')
DATA = os.path.join(BASE, '_数据与评分')
top = json.load(open(os.path.join(DATA, 'TOP10.json'), encoding='utf-8'))
raw = json.load(open(os.path.join(DATA, '榜单原始抓取_20261024.json'), encoding='utf-8'))

TAB_SHORT = {
    '麦当劳_白领': '麦当劳榜·白领', '麦当劳_学生': '麦当劳榜·学生',
    '麦当劳_家庭': '麦当劳榜·家庭', '麦当劳_游客': '麦当劳榜·游客',
    '麦当劳_老年人': '麦当劳榜·老年人', '西式快餐_白领': '西式快餐榜·白领',
    '汉堡快餐_白领': '汉堡快餐榜·白领', '快餐简餐_白领': '快餐简餐榜·白领',
}

META = {
    '沙面': dict(area='沙面岛',
        short='沙面', folder='沙面店', title='麦当劳（沙面店）',
        alias='高德登记名「麦当劳(沙面分店)」；平台亦写作沙面分店 / 胜利宾馆店',
        address='荔湾区沙面大街 54 号胜利宾馆首层北面厅（店面朝沙面三街一侧，沙面三街 3 号）',
        addr_note='高德登记的「沙面大街 54 号」即胜利宾馆；探店报道写作「沙面三街 3 号」，是同一处建筑的临街门面。',
        opened='2020-01-23 开业（探店报道口径）；工商登记成立日期 2019-12-04',
        opened_src='★ 第三方探店报道 + 工商登记信息',
        sqm='未公开（探店口径：店内空间不大）', seats='未公开',
        identity='拥有广州最大的落地金拱门 M 招牌；沙面欧式复古门店，社交平台长期热门打卡点',
        hours='08:00–22:00（电话邦 / 点评口径）；Trip.com 记为 07:00–22:00，存在差异',
        phone='020-88501302',
        traffic='地铁 1 / 6 号线黄沙站 E 口，步行约 500 米；沙面岛北侧入口桥头',
        pros=['纯白欧式外立面配超大落地 M 招牌，白天、傍晚各有一版效果，出片率是全市门店里最高的一档',
              '麦咖啡与甜品站都齐备，是沙面岛上少有的「有座位、有咖啡、有空调」的落脚点',
              '沙面岛本身安静，工作日店内客流舒缓，适合久坐看书、办公，老外与亲子客群比例高'],
        cons=['店内面积小、座位少，探店与点评都反复提到「用餐位置不算很多」',
              '不少促销活动这家店不参与，套餐价格比市区普通门店略高',
              '白天门口拍照的人常排着队，想拍一张干净的 M logo 需要挑时段；节假日常需拼台'],
        scenes='拍照打卡 / 咖啡久坐 / 沙面岛半日游中继站',
        photo_src='网易号探店稿《这么复古的麦当劳，怎么能用来吃呢…》',
        photo_platform='网易号（用户上传）',
        photo_page='https://www.163.com/dy/article/F7T10MAK05421ZTT.html',
        credit='网络公开图片，版权归原作者所有，本档案仅作个人研究与非商业展示',
        pick=[('01', 'EXT'), ('02', 'EXT'), ('06', 'EXT'), ('09', 'EXT'), ('16', 'EXT'),
              ('03', 'SIGN'), ('07', 'SIGN'), ('08', 'SIGN'), ('14', 'SIGN'),
              ('04', 'CNT'), ('15', 'CNT'), ('05', 'ENV')],
        links=[('大众点评（门店页 / 用户相册）', 'https://www.dianping.com/review/240300543'),
               ('携程攻略（沙面店，含实拍评价）', 'https://hk.trip.com/restaurant/china/guangzhou/detail/city-81982772'),
               ('网易号探店稿（本文照片出处）', 'https://www.163.com/dy/article/F7T10MAK05421ZTT.html'),
               ('搜狐探店稿（同店另一组实拍）', 'https://www.sohu.com/a/382236522_391256')],
    ),
    '北京路丽都酒店店': dict(area='北京路步行街',
        short='丽都', folder='北京路丽都酒店店', title='麦当劳（北京路丽都酒店店）',
        alias='平台亦写作「麦当劳(丽都店)」「广州丽都大酒店分店」',
        address='越秀区北京路 182 号丽都大酒店首层、二层（近永汉电影院）',
        addr_note='一层为甜品站，堂食区在二层。',
        opened='不详（公开渠道未见确切开业年份；该店为北京路老店，近年重新装修）',
        opened_src='○ 未查到；仅能从平台点评时间线确认 2012 年已在营业',
        sqm='未公开', seats='未公开（点评口径：面积不大，高峰需拼台）',
        identity='北京路步行街路口 24 小时店，一层甜品站 + 二层堂食；二层整面玻璃可俯瞰步行街十字路口',
        hours='24 小时营业', phone='020-83330006',
        traffic='地铁 6 号线北京路站 B 口步行约 300 米；北京路与大马站路交界',
        pros=['24 小时营业，是北京路一带深夜少有的稳定选择',
              '二层靠窗位是一整面玻璃，能直接看到北京路十字路口人流，被不少点评称为「复古机位」',
              '老店重新装修后明亮干净，人工 / 自助机 / 小程序三种点餐方式都在，出餐快'],
        cons=['高峰期座位紧张，常需要拼台，临窗好位置难抢',
              '老客反映店内灯光偏暗、面积不大，环境评价一般',
              '有顾客反馈自助点餐出现过配错餐（要薯条给了麦乐鸡）的情况'],
        scenes='逛街歇脚 / 深夜宵夜 / 等人碰头 / 二层窗边拍照',
        photo_src='', photo_platform='', photo_page='', credit='', pick=[],
        links=[('开饭喇（相片 26 张、食记 13 篇）', 'https://www.openrice.com.cn/zh/guangzhou/r-%E9%BA%A5%E7%95%B6%E5%8B%9E-%E5%8C%97%E4%BA%AC%E8%B7%AF-%E8%A5%BF%E5%BC%8F-r8529688'),
               ('大众点评（284 条评论 / 用户相册）', 'https://www.dianping.com/review/240300543'),
               ('Trip.com（门店页与评价）', 'https://hk.trip.com/restaurant/china/guangzhou/detail/restaurant-11476708')],
    ),
    '东风西路': dict(area='西关 / 东风西路',
        short='东风西', folder='东风西路店', title='麦当劳（东风西路店）',
        alias='高德登记名「麦当劳(东风西路分店)」；注意与「金融大厦店（东风西路197-199号）」是两家不同门店',
        address='越秀区东风西路 140 号首层 103 铺（部位：自编 103A），流花湖公园对面',
        addr_note='同一条路上另有「金融大厦店」（东风西路 197-199 号广州国际金融大厦 B1），常被混淆，本档案指 140 号这家。',
        opened='不详（现址工商登记成立 2019-06-19，门店经营时间应早于此）',
        opened_src='★ 工商登记 + ○ 门店实际开业年份未查到',
        sqm='未公开', seats='未公开',
        identity='普通门店（无官方旗舰 / 首发身份）',
        hours='07:00–23:00', phone='020-81977551',
        traffic='东风西路主干道旁，正对流花湖公园；地铁 2 号线越秀公园站、5 号线西场站均需步行 10 分钟以上',
        pros=['在我们采集的 8 个高德榜单中，是唯一一家进入全部 4 个人群榜且都排第 1 的门店，评分 5.0',
              '自助电子屏点餐，出餐快，早餐时段排队短',
              '正对流花湖公园，早餐后可直接进公园散步，是这一带少见的「公园门口 M 记」'],
        cons=['第三方点评样本极少（Trip.com 仅 5 条评价），高分里有相当比例来自样本量小，需谨慎看待',
              '临城市主干道，无专属停车位，自驾不便',
              '门店规模未公开，无法判断堂食容量，高峰是否好找位缺乏可靠数据'],
        scenes='公园晨练后早餐 / 周边写字楼快午餐 / 途经快速解决',
        photo_src='', photo_platform='', photo_page='', credit='', pick=[],
        links=[('Trip.com（门店页与 5 条评价）', 'https://hk.trip.com/restaurant/china/guangzhou/detail/restaurant-118704573/'),
               ('高德地图门店页（评分与榜单来源）', 'https://www.amap.com/search?query=%E9%BA%A6%E5%BD%93%E5%8A%B3%20%E4%B8%9C%E9%A3%8E%E8%A5%BF%E8%B7%AF140%E5%8F%B7')],
    ),
    '总统大酒店店': dict(area='岗顶',
        short='总统', folder='总统大酒店店', title='麦当劳（总统大酒店店）',
        alias='高德登记名「麦当劳(总统大酒店店)」，因位于南方电脑城 2 层，平台亦写作「南方电脑城店」「天河路餐厅」',
        address='天河区天河路 518 号南方电脑城 2 层（总统大酒店裙楼，面向天河路主干道）',
        addr_note='同店在多个平台有 4 个以上别名，本档案统一用高德的「总统大酒店店」。',
        opened='不详（所在南方电脑城 2000 年代已运营；公开渠道未见确切开业年份）',
        opened_src='○ 未查到',
        sqm='未公开', seats='约 200 座（第三方生活服务平台 2012 年登记，未现场核实）',
        identity='普通门店，但为岗顶商圈 24 小时主力店；设夹层就餐区',
        hours='24 小时营业', phone='020-38788787',
        traffic='地铁 3 号线岗顶站 C 口向北步行 2–3 分钟；BRT 岗顶站下车步行约 200 米',
        pros=['24 小时营业，岗顶电脑城、中山三院、周边高校客群稳定，深夜仍有热食',
              '座位约 200 个，是本次入选门店里少数明确记载「座位多」的一家，还有夹层就餐区',
              '点餐到取餐流程成熟，非促销日常态下出餐很快'],
        cons=['促销活动日（如 5 元汉堡）人流量爆棚，有顾客等餐接近一小时',
              '人太多时难找座位，部分桌面清理不及时',
              '服务态度评价偏一般，有「叫了几次没人来收台」的吐槽'],
        scenes='电脑城逛街 / 医院陪诊等候 / 深夜宵夜 / 学生聚餐',
        photo_src='', photo_platform='', photo_page='', credit='', pick=[],
        links=[('百度百科（门店条目，含交通与营业信息）', 'https://baike.baidu.com/item/%E9%BA%A6%E5%BD%93%E5%8A%B3(%E6%80%BB%E7%BB%9F%E5%A4%A7%E9%85%92%E5%BA%97%E5%BA%97)/14275886'),
               ('大众点评（用户点评）', 'https://www.dianping.com/review/451002222'),
               ('8090 本地生活（座位数 / 别名登记）', 'https://life.city8090.com/guangzhou/s_768738')],
    ),
    '北京路广百广场店': dict(area='北京路步行街',
        short='广百', folder='北京路广百广场店', title='麦当劳（北京路广百广场店）',
        alias='平台亦写作「麦当劳(广百新翼商务中心店)」「北京路广百百货店」',
        address='越秀区西湖路至大马站路段 广百广场新翼首层及夹层',
        addr_note='另有平台登记为「北京路 295 号广百百货 M 层至 F1 层」并记座位约 200 个，疑为同一门店的不同登记口径，未现场核实。',
        opened='不详（公开渠道未见确切开业年份）',
        opened_src='○ 未查到',
        sqm='未公开', seats='约 200 座（开饭喇登记，未现场核实）',
        identity='普通门店；位于广百新翼首层+夹层，开放式店面',
        hours='07:00–23:00', phone='020-83384341（广百新翼）；020-83327929（广百百货）',
        traffic='地铁 6 号线北京路站 B 口；北京路步行街西侧，大马站路一侧进入',
        pros=['规模大、座位多，逛完北京路进来休息不容易没位置',
              '被点评形容为「闹中取静」，空调足、环境舒适',
              '早餐买优惠卡后性价比高，薯饼与麦满分系列口碑稳定'],
        cons=['位置在北京路算偏，在 2 楼（首层及夹层），不仔细看容易错过',
              '被反复提到「洋快餐越来越贵」，价格比国内同类快餐高一档',
              '豆浆为豆浆粉冲调，口感偏甜腻'],
        scenes='北京路逛街中途休息 / 亲子 / 早餐',
        photo_src='', photo_platform='', photo_page='', credit='', pick=[],
        links=[('开饭喇（相片 90 张、食记 130 篇）', 'https://www.openrice.com.cn/zh-cn/guangzhou/r-%E9%BA%A6%E5%BD%93%E5%8A%B3-%E5%8C%97%E4%BA%AC%E8%B7%AF-%E6%B1%89%E5%A0%A1%E5%8C%85-r42675'),
               ('携程攻略（465 条点评，4.5 分）', 'https://you.ctrip.com/food/ctripyouyoustar152/5326336-dianping.html'),
               ('Trip.com（门店页）', 'https://hk.trip.com/restaurant/china/guangzhou/detail/restaurant-11476708/')],
    ),
    '海珠广场店': dict(area='海珠广场 / 一德路',
        short='海珠广场', folder='海珠广场店', title='麦当劳（海珠广场店）',
        alias='高德登记名「麦当劳(海珠广场店)」；官方称「海珠广场餐厅」',
        address='越秀区起义路 1 号海印缤缤广场二层（一德路侧，近广州解放纪念雕像）',
        addr_note='麦当劳中国官网写「海印缤缤广场二层」；Trip.com 登记为「1 层」，以官网为准，现场有扶手电梯直达。',
        opened='1993 年开业（麦当劳进入广州的第二家餐厅）；2023-08-08 重装升级为广州首家童趣旗舰店',
        opened_src='★ 麦当劳中国官网新闻稿（2023-08-08）',
        sqm='超过 765 平方米，为广州麦当劳面积最大的餐厅', seats='未公开（点评口径：面积大但仍常坐满）',
        identity='广州首家童趣旗舰店；RAY 旗舰店设计风格；全国首发「开心小助手」智能机器人「小萌」；全国首发「四小福版」自助点餐机；儿童乐园全国首发设计',
        hours='24 小时营业（第三方实测口径）；Trip.com 记「全日开放」', phone='020-83359150',
        traffic='地铁 2 / 6 号线海珠广场站上盖；一德路、起义路交界',
        pros=['全市面积最大（765㎡+），座位容量在入选门店里最高一档',
              '二层落地大玻璃正对海珠广场与解放桥，晚上看夜景是这家店独有的体验',
              '2023 年重装后「四小福」巨型雕像、定制自助点餐机、全国首发儿童乐园与智慧机器人「小萌」全在这家，是一站式童趣打卡点；24 小时营业且有麦咖啡'],
        cons=['面积虽大，但常被坐满，中午需要排队等餐',
              '没有专属母婴室，带低龄宝宝换尿布不方便',
              '儿童乐园设施相对简单，餐食并非专为幼儿设计，更适合「顺路解决一餐」'],
        scenes='亲子遛娃 / 海珠广场与一德路逛街 / 夜景窗边位 / 24 小时应急',
        photo_src='麦当劳中国官网新闻稿（2023-08-08）官方配图',
        photo_platform='麦当劳中国官网',
        photo_page='https://www.mcdonalds.com.cn/news/20230808-Guangzhou-13-Family-Restaurant',
        credit='版权归麦当劳中国所有，本档案仅作个人研究与非商业展示',
        pick=[('01', 'EXT'), ('02', 'EXT'), ('06', 'EXT'), ('03', 'CNT'),
              ('07', 'SEAT'), ('08', 'SEAT'), ('04', 'KID')],
        links=[('麦当劳中国官网新闻稿（本文照片出处）', 'https://www.mcdonalds.com.cn/news/20230808-Guangzhou-13-Family-Restaurant'),
               ('Trip.com（9 条评价，4.5 分）', 'https://hk.trip.com/restaurant/china/guangzhou/detail/mcdonald-s-30963570/'),
               ('羊城晚报报道（同批官方图）', 'https://news.ycwb.com/2023-08/08/content_52126921.htm')],
    ),
    '阳光城·江湾壹号店': dict(area='沿江路',
        short='江湾', folder='阳光城江湾壹号店', title='麦当劳（阳光城·江湾壹号店）',
        alias='平台亦写作「麦当劳(江湾阳光天地店)」',
        address='越秀区沿江中路 298 号广信江湾新城东区裙楼二层 L2-6-1 号商铺',
        addr_note='入口在江湾阳光天地二层，从星巴克背后的小门进入。',
        opened='不详（所在江湾阳光天地为后期改造商业体，门店为较新开店）',
        opened_src='○ 未查到',
        sqm='未公开（点评口径：店不大，细长形）', seats='未公开',
        identity='普通门店；商业楼宇配套店，非街铺',
        hours='07:00–22:00',
        phone='020-87315179（Trip.com）；020-62790366（携程），平台登记不一致',
        traffic='沿江中路 298 号江湾阳光天地二层；地铁 6 号线团一大广场站步行约 10 分钟',
        pros=['靠窗位正对珠江，能一边吃一边看江景，是沿江路上性价比最高的「江景座位」之一',
              '出餐快、店员动作麻利，工作日午市效率高',
              '以商业楼宇客群为主，节假日反而人少，适合想安静坐一会儿的人'],
        cons=['店面不大、呈细长形，座位数量有限',
              '入口藏在星巴克后面的小门里，第一次来容易找不到',
              '节假日客流稀少，部分时段出品流转慢，薯条新鲜度不如高峰期'],
        scenes='江景窗边位 / 写字楼快午餐 / 沿江路散步中途休息',
        photo_src='', photo_platform='', photo_page='', credit='', pick=[],
        links=[('Trip.com（门店页与 5 条评价）', 'https://hk.trip.com/restaurant/china/guangzhou/detail/city-135091104'),
               ('携程攻略（门店信息与地图）', 'https://you.ctrip.com/food/guangzhou152/135091104-map.html')],
    ),
    '宜安广场': dict(area='建设六马路 / 淘金',
        short='宜安', folder='宜安广场店', title='麦当劳（宜安广场店）',
        alias='高德登记名「麦当劳(宜安广场分店餐厅)」',
        address='越秀区建设六马路 38 号宜安广场首层（实际需从广场正面右侧下楼梯，位于下层/负一层）',
        addr_note='门牌登记为首层，但多家点评都指出要下楼梯进入，实际在负一层位置。',
        opened='不详（公开渠道未见确切开业年份；2019 年前已在营业）',
        opened_src='○ 未查到',
        sqm='未公开（点评口径：店不大）', seats='未公开',
        identity='普通门店；以「自选配料 DIY 汉堡」为特色',
        hours='24 小时营业（Trip.com 记「全日开放」）', phone='020-83634339',
        traffic='建设六马路 38 号宜安广场；地铁 5 号线淘金站步行约 5 分钟',
        pros=['支持自选配料 DIY 汉堡，可以按自己口味搭，这在广州门店里不多见',
              '建设六马路一带外国人聚集，店内客群多元，氛围松弛',
              '就在宜安广场楼下，写字楼办事、逛街都能顺脚进来，近淘金地铁站'],
        cons=['店不大，周六下午茶时段也会爆满',
              '没有甜品站，买不到甜筒，只能点新地等杯装甜品',
              '入口要下楼梯、不在路边，第一次来不好找'],
        scenes='写字楼午市 / DIY 汉堡 / 建设六马路一带小坐',
        photo_src='', photo_platform='', photo_page='', credit='', pick=[],
        links=[('携程攻略（764 条点评，含 3 张门店照片）', 'https://you.ctrip.com/food/guangzhou152/5328549-food.html'),
               ('Trip.com（门店页与设施信息）', 'https://tw.trip.com/restaurant/china/guangzhou/detail/mcdonald-s-11478945/'),
               ('大众点评（405 条评论）', 'https://www.dianping.com/review/237209526')],
    ),
    '天字码头店': dict(area='沿江路 / 天字码头',
        short='天字码头', folder='天字码头店', title='麦当劳（天字码头店）',
        alias='官方称「沿江中路天字码头餐厅」',
        address='越秀区沿江中路 天字码头旁（北京南路路口，珠江夜游天字码头一侧）',
        addr_note='门牌未在公开稿中给出，位置描述以官方新闻稿为准。',
        opened='2026-01-04 开业，为麦当劳广州市场第 900 家餐厅',
        opened_src='★ 麦当劳中国官网新闻稿（2026-01-04）',
        sqm='未公开', seats='室内外合计超过 100 座',
        identity='全国首家「美味色谱 Classic Spectrum」设计风格餐厅；广州市场第 900 家餐厅',
        hours='未核实（开业不足一年，公开渠道未见稳定营业时间记录）', phone='未核实',
        traffic='沿江中路天字码头旁；地铁 6 号线北京路站、2 号线海珠广场站均需步行约 10 分钟',
        pros=['全国首家「美味色谱」设计门店：外立面做珠江「水波涟漪」造型，夜间灯光沿建筑线条流动，是沿江路新的夜景点位',
              '设室外休闲座区，直接面向珠江边步道开放，可以买完就坐在江边吃',
              '室内外 100+ 座位，配麦咖啡与麦乐送，覆盖早餐通勤到周末休闲'],
        cons=['开业不足一年，第三方评分样本几乎为零，口碑尚无稳定参考',
              '室外座位完全露天，下雨、暴晒或江风大时基本不可用',
              '作为新晋打卡点，开业期与周末客流集中，排队概率高于普通门店'],
        scenes='珠江边散步歇脚 / 夜景打卡 / 游客 / 亲子',
        photo_src='麦当劳中国官网新闻稿（2026-01-04）官方配图',
        photo_platform='麦当劳中国官网',
        photo_page='https://www.mcdonalds.com.cn/news/20260104-900-Restaurants-in-Guangzhou',
        credit='版权归麦当劳中国所有，本档案仅作个人研究与非商业展示',
        pick=[('03', 'EXT'), ('04', 'EXT'), ('02', 'EXT'), ('01', 'SEAT')],
        links=[('麦当劳中国官网新闻稿（本文照片出处）', 'https://www.mcdonalds.com.cn/news/20260104-900-Restaurants-in-Guangzhou'),
               ('广州日报新花城报道', 'https://huacheng.gz-cmc.com/pages/2026/01/07/dfe5724778704df383ec231e607221d9.html'),
               ('南方+ 报道', 'https://www.toutiao.com/w/1853467852371020/')],
    ),
    '白云CUBE旗舰店': dict(area='白云新城',
        short='CUBE', folder='白云CUBE旗舰店', title='麦当劳（白云 CUBE 旗舰店）',
        alias='官方称「云城南路餐厅」，位于白云万达广场旁',
        address='白云区云城南路 白云万达广场旁（上下两层独栋建筑）',
        addr_note='官方未给门牌号，公开稿均以「白云万达广场旁」「云城南路」定位。',
        opened='2023-04-03 开业',
        opened_src='★ 麦当劳中国官网新闻稿（2023-04-03）',
        sqm='超过 430 平方米（上下两层独栋）', seats='135 座',
        identity='广州首家、全国第五家 CUBE 风格旗舰餐厅；设计师梁志天主持设计；全国首发「开心魔力盒」；广州首家使用太阳能光伏板辅助照明的门店',
        hours='未核实（公开稿未给营业时间）', phone='未核实',
        traffic='白云万达广场旁，白云新城片区；地铁 2 号线飞翔公园站步行约 15 分钟',
        pros=['独栋两层 + 全透明落地玻璃，暖色方块堆叠出抽象产品图案，白天通透、夜晚灯光层次最明显',
              '全国首发「开心魔力盒」在二楼：3D 裸眼动画 + 「汉堡挑战赛」互动，旁边还有巨型「开心屋」和产品造型软包凳',
              '一楼子母环保充电单车、可无线充电餐桌、绿色再生塑料餐盘，是广州首批这类配置的门店'],
        cons=['位于白云新城，离市中心较远，专程过去一趟时间成本高',
              '亲子属性极强，周末儿童区拥挤、噪音大，不适合想安静坐的人',
              '周边商业体分散，除万达外可逛的内容有限'],
        scenes='亲子一站式遛娃 / 建筑与空间打卡 / 绿色门店体验',
        photo_src='麦当劳中国官网新闻稿（2023-04-03）官方配图',
        photo_platform='麦当劳中国官网',
        photo_page='https://www.mcdonalds.com.cn/news/20230403-Guangzhou-Cube-Grand-Opening',
        credit='版权归麦当劳中国所有，本档案仅作个人研究与非商业展示',
        pick=[('01', 'EXT'), ('02', 'EXT'), ('03', 'EXT'), ('04', 'SEAT'),
              ('07', 'SEAT'), ('05', 'KID'), ('06', 'KID')],
        links=[('麦当劳中国官网新闻稿（本文照片出处）', 'https://www.mcdonalds.com.cn/news/20230403-Guangzhou-Cube-Grand-Opening'),
               ('FoodTalks 探店稿（另一组实拍）', 'https://www.foodtalks.cn/news/43247'),
               ('南方+ 报道', 'https://static.nfnews.com/content/202304/04/c7529761.html')],
    ),
}

PHOTO_DIR = {'沙面': '沙面', '海珠广场店': '海珠广场', '天字码头店': '天字码头', '白云CUBE旗舰店': '白云CUBE'}
CODE_CN = {'EXT': '外立面 / 门头', 'CNT': '点餐前台 / 甜品站', 'SEAT': '座位区 / 堂食区',
           'KID': '儿童区 / 游乐区', 'SIGN': '招牌细节 / 品牌元素', 'ENV': '周边环境'}


def ranks_for(key):
    out = []
    for tab, v in raw.items():
        for it in v['items']:
            if it['name'].startswith('麦当劳') and it['district'] in [
                    '越秀区', '荔湾区', '海珠区', '天河区', '白云区', '黄埔区', '番禺区',
                    '花都区', '南沙区', '从化区', '增城区']:
                n = re.sub(r'[（(][^）)]*[）)]', '', it['name'])
                n2 = re.search(r'[（(]([^）)]*)[）)]', it['name'])
                base = (n2.group(1) if n2 else n).replace('麦当劳', '')
                base = re.sub(r'(分店餐厅|分店|餐厅)$', '', base.strip())
                if base == key:
                    out.append({'tab': TAB_SHORT.get(tab, tab), 'rank': it['rank']})
    return sorted(out, key=lambda x: x['rank'])


def main():
    stores = []
    for r in top:
        key = r['key']
        m = META[key]
        rk = ranks_for(key)
        stores.append(dict(
            no=r['final_rank'], key=key, title=m['title'], short=m['short'], folder=m['folder'],
            alias=m['alias'], district=r['district'], area=m['area'], address=m['address'],
            addr_note=m['addr_note'], rating=r['rating'] or None, ranks=rk,
            opened=m['opened'], opened_src=m['opened_src'], sqm=m['sqm'], seats=m['seats'],
            identity=m['identity'], hours=m['hours'], phone=m['phone'], traffic=m['traffic'],
            pros=m['pros'], cons=m['cons'], scenes=m['scenes'],
            score=dict(A=r['A'], B=r['B'], C=r['C'], D=r['D'], total=r['total'],
                       channel=r['channel'], estimated=r['estimated']),
            photo_src=m['photo_src'], photo_platform=m['photo_platform'],
            photo_page=m['photo_page'], credit=m['credit'],
            photos=[{'code': c, 'code_cn': CODE_CN[c], 'src': s} for s, c in m['pick']],
            links=m['links'],
        ))
    json.dump(stores, open(os.path.join(BASE, '_构建工具', 'stores.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    # 建目录 + 落图
    root = BASE
    for s in stores:
        d = os.path.join(root, '%02d_%s' % (s['no'], s['folder']))
        pd = os.path.join(d, 'photos')
        os.makedirs(pd, exist_ok=True)
        src_dir = os.path.join(DATA, '官方图', PHOTO_DIR.get(s['key'], ''))
        rows = []
        cnt = {}
        for ph in s['photos']:
            cnt[ph['code']] = cnt.get(ph['code'], 0) + 1
            fn = '%02d_%s_%s_%02d.jpg' % (s['no'], s['short'], ph['code'], cnt[ph['code']])
            sp = os.path.join(src_dir, ph['src'] + '.jpg')
            if os.path.exists(sp):
                shutil.copy2(sp, os.path.join(pd, fn))
                rows.append((fn, s['photo_platform'], s['photo_page'],
                             '', '2026-10-24', s['credit']))
        s['photo_files'] = [r[0] for r in rows]
        if rows:
            with open(os.path.join(pd, '_sources.csv'), 'w', encoding='utf-8-sig') as f:
                f.write('文件名,平台,来源页URL,图片直链,抓取时间,版权说明\n')
                for r in rows:
                    f.write(','.join('"%s"' % x for x in r) + '\n')
        print('%02d %-14s 照片 %d' % (s['no'], s['short'], len(rows)))

    json.dump(stores, open(os.path.join(BASE, '_构建工具', 'stores.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
