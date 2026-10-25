# McDONALD'S · 像素 3D 点餐台（Demo v6）

三页一体的像素点餐闭环：**进入页（选堂食 / 外卖）→ 堂食点餐台（3D 门店）或 外卖到家工作台**。
无卡片像素风；门店、菜单、优惠券、积分、营养、活动、订单均来自**麦当劳 MCP 真实数据**。

## 运行

```bash
cd 线上点餐台
python -m http.server 8899
# 进入页：http://127.0.0.1:8899/entry.html     ← 建议从这里开始
# 堂食台：http://127.0.0.1:8899/index.html?mode=dinein
# 外卖台：http://127.0.0.1:8899/delivery.html
```

自测（结果写入页面标题，`PASS xxx | FAIL xxx`）：

| 页面 | 入口 | 项数 |
| --- | --- | --- |
| 进入页 | `entry.html?selftest=1` | 19 |
| 堂食台 | `index.html?selftest=1` | 28 |
| 外卖台 | `delivery.html?selftest=1` | 26 |

`index.html` 无 `mode` 参数时会自动跳到进入页（`?selftest=1` 例外，方便回归）。
深链 `?store=<storeCode>` 直接选中门店（不弹欢迎窗）。

必须走 HTTP（GLB 加载受 CORS 限制），不能双击 file:// 打开。

调试参数（仅自测用，页面无任何昼夜开关）：`?qa_day=1` 强制日间、`?qa_night=1` 强制夜间、
`?welcome=1` 强制弹一次欢迎提示（`?welcome=<毫秒>` 可加长便于截图）。

## 进入页 entry.html

画面正中是**品牌海报 + 两个等尺寸主入口**，功能入口排在海报下方与主按钮同宽（720px），形成一条单列视觉流。

| 模块 | 位置 | 内容 |
| --- | --- | --- |
| 品牌海报 | 正中偏上 | 红底 + 双层点阵 + 45° 金色斜块；金黄拱门 SVG + `McDONALD'S` 黄色大字（`clamp(40px,5.7vw,80px)`）+ `i'm lovin' it 我就喜欢` |
| 主入口 ×2 | 画面正中，等尺寸并列 | 左「堂食 / DINE IN」金色主按钮（带「推荐」角标，视觉优先级最高）；右「外卖到家 / DELIVERY」品牌红按钮 |
| 功能条 ×4 | 主按钮正下方 2×2 | 优惠券 3 张 / 积分 106.3 / 活动日历·抢先知 / 营养计算器（MCP） |

交互与状态：

- 点主按钮 → `pressed` 态 + 整页 `.leaving` 淡出 320ms → `location.href`：堂食 `index.html?mode=dinein`，外卖 `delivery.html`。
- 营养计算器：搜索 + 目标 kcal + 7 个分组 chips + 3 个快捷搭配；已选列表可 `−/+`，底部实时汇总热量/蛋白/脂肪/碳水/钠，并给出结论。数据 `data/nutrition.json`（158 项，来自 MCP `list-nutrition-foods`）。
- 活动日历：按日期分组，今天/明天/N 天后标签 + 返场日期，可按类型筛选。数据 `data/campaign.json`（15 场，MCP `campaign-calendar` 合并）。
- 优惠券 / 积分：复用点餐台的 `.coupon-card` / `.pts-hero`，只读展示。
- 顶栏：品牌、本地时钟、昼夜状态胶囊、可选门店数；全部中文文案 + CSS 色点（Zpix 缺 `☀/☾/◐` 等符号，会渲染成方块）。

## 外卖到家 delivery.html

**单页五区**，不做多页跳转：吸顶步骤条点击即 `scrollIntoView` 平滑滚动到对应区块。

| 区 | 功能 |
| --- | --- |
| 01 配送地址 | 列表**内联展开**表单（不弹层）：联系人 / 11 位手机号 / 区域 / 详细地址 / 家·公司·学校标签 / 设为默认；校验失败就地 toast；首个地址自动默认；单选默认约束；支持编辑、删除（删除二次确认） |
| 02 配送方式 | 标准配送（骑手直送 30–40 分钟）/ 无接触配送；立即送达 / 预约（time 选择器）；出餐门店（MCP 6 店）；餐具勾选 |
| 03 选餐 | 13 分类 chips + 4 列商品网格；快捷「+」加购，已加购项原位变 `− qty +` |
| 04 结算支付 | 行内数量增减、外送可用券选择（`到店专用` 券自动排除、空购物袋不放券）、商品小计 / 配送费 / 优惠 / 应付、3 种支付方式、提交订单 |
| 05 订单状态与历史 | 本页订单实时进度条（已支付 → 制作中 → 配送中 → 已送达，每 4.2s 推进）；历史订单 = 本地订单 + MCP `order-list` 7 条，按时间倒序，`本页下单` 绿色标签区分 |

费用规则：配送费 ¥9，满 ¥39 免（`deliveryFee(raw)`）；应付 = 小计 − 券 + 运费。
下单：校验地址与购物袋 → 900ms 模拟支付网关 → 生成 `D+时间戳` 订单 → 支付成功弹窗 2.6s 自动消失 → 进度自动推进。

响应式：桌面三列（信息 / 菜单 / 结算 sticky）→ ≤1240px 双列 → ≤900px 单列 + 固定底部结算条（购物袋件数 / 应付 / 去结算）→ ≤620px 顶栏收窄、单列配送方式、菜单 2 列。

数据与限制（页面上也有标注）：

- MCP `delivery-query-addresses` 当前返回**空列表**，地址存 `localStorage`（`mcd.dl.addresses`），仅本浏览器可见。
- `calculate-price` 需要真实 `addressId → beCode` 才能调用，因此结算按**菜单价 + 配置费率本地试算**；真实交易链路未接。
- 演示订单存 `localStorage`（`mcd.dl.orders`）；自测模式（`?selftest=1`）下 `persist()/restore()` 直接 return，不污染真实数据。

## 堂食点餐台 index.html：布局与交互（对照设计要求）

| 要求 | 实现 |
| --- | --- |
| 不使用卡片、3D 与点餐不分割 | 全页无卡片：2px 粗线 + 虚线分区；模型区透明底、无边框容器，靠 `.hero-right:before/:after` 底色渐隐 + `model-viewer` 双轴 `mask-image` 与页面融为一体 |
| 点餐区在下方 | `.order-zone` 固定在视口下方 300px 通栏：分类 Tab + 横向商品滑轨 |
| 3D 在右上角 | `.hero-right` 占右上，透明背景、无描边，模型与地面阴影自然落在页面底色上 |
| 左侧英文大字标题 | 像素字体堆叠大标题 `McDONALD'S PIXEL WORLD.` + 门店名 / 介绍 / 档案 |
| 3D 不可缩放 | `disable-zoom disable-pan`，且 `min/max-camera-orbit` 半径锁死（富士山 64m / 沙面 29m），仅可环绕旋转（俯仰 12°–88°） |
| MCP 门店选择 | 顶栏下拉列出 MCP `query-nearby-stores` 门店（含 3D 分组）；选中已建模门店加载对应 GLB，未建模门店自动轮播实景照片 |
| 无模型门店 | `.photo-carousel` 3.2s 循环轮播该店实景照；无照片时用品牌色像素占位幻灯片，并在左下角标注「该店暂无 3D 模型」 |
| 欢迎弹窗 | 选定门店即弹「欢迎来到xxx店，麦门永存！」，店名由门店全名去前缀/去括号生成，切换门店同步更新；**无按钮，1.6s 自动消失**（底部像素倒计时条），也可点击空白处立即关闭 |
| 像素字体 | 全站 Zpix（中文像素字体，本地 `assets/fonts/zpix.woff2`，中英文/数字统一像素风） |
| 自动昼夜（无开关） | 依据访问者设备本地时间判定（18:00–次日 06:00 为夜），每 30s 校时 |

## 购物袋数据链路

`state.cart` 是唯一数据源，菜单加购、购物袋、结算、下单全部只读它：

- 行结构 `{ code, opts, qty, lineId, price(单价), name, image }`；同商品 + 同规格再点一次只累加 `qty`，不重复插行。
- `price` = 商品单价 + 加料/升级差价，保证详情页「加入购物袋 · ¥47.00」与袋内金额一致。
- 快捷「+」等价于该商品的**默认搭配**，与详情页默认选中项完全相同，因此两条入口加的是同一行。
- 注意：`data/menu.json` 的菜品对象不带 `code`，编码是 `meals` 的键；`loadData()` 会回填 `m.code`，
  否则渲染出的 `data-add` 全是 `undefined`，会出现「点了加购、提示成功、袋里却没有」。

## 昼夜：双模型交叉淡化

富士山店是**按黄昏照明建模**的场景资产（墙面/沥青为夜色材质 + 门店射灯）。只调曝光无法做出可信的「白天」，
因此改为一套几何、两版材质与灯光，由构建脚本 `--theme day|night` 分别导出：

| 文件 | 状态 | 灯光 |
| --- | --- | --- |
| `Fuji_McDonalds_day.glb` | 日间石材/玻璃/沥青配色，招牌自发光为 0 | 无 punctual 灯（纯 neutral 环境光，与沙面/丽都口径一致） |
| `Fuji_McDonalds.glb` | 夜色配色 | 招牌射灯 + 室内暖光 + 黄昏环境光（强度已按 Web 端校准） |

页面里两个 `<model-viewer>` 叠放（`#mvDay` / `#mvNight`），切主题时同步机位后交叉淡化 1.4s，
不重新加载、不闪烁；曝光与投影强度同样 1.4s 平滑过渡。

> 关键坑：glTF 的 `KHR_lights_punctual` 会把 Blender 瓦特换算成 cd/lux（×683 量级），而 three.js 直接当光强用。
> 不缩放的话整场景会严重过曝成白屏——`build_fuji.py` 里用 `LS = 0.02` 统一缩放。

## 3D 门店模型

| storeCode | 门店 | 模型 |
| --- | --- | --- |
| 19541 | 富士山下麦当劳（场景特辑，非中国 MCP） | `Fuji_McDonalds.glb`（夜）+ `Fuji_McDonalds_day.glb`（日） |
| 1400477 | 麦当劳广州沙面餐厅 | `Shamian_McDonalds.glb` |
| 1400099 | 麦当劳广州丽都大酒店餐厅 | `Lido_McDonalds.glb` |

每家模型在 `data/store.json → models` 中声明 GLB（可含 `glbDay` / `glbNight`）、锁定半径、默认机位与视角预设。
视角预设共用同一锁定半径，只改方位/俯仰与观察点，因此不会违反「不可缩放」。

## 数据（MCP 真实数据）

- 门店列表：`query-nearby-stores`（广州·北京路商圈 5 店 + 沙面商圈 5 店，到店自取，2026-10-25）→ `data/store.json`
- 菜单 13 分类 / 100+ 商品：`query-meals`（沙面店 1400477）→ `data/menu.json`
- 优惠券 3 张 / 积分：`query-my-coupons` / `query-my-account` → `data/store.json`
- 营养 158 项：`list-nutrition-foods`（去重后按 汉堡/小食/甜品/饮品咖啡/汽水/早餐/套餐 分组）→ `data/nutrition.json`
- 活动 15 场：`campaign-calendar`（含返场日期）→ `data/campaign.json`
- 外卖：`delivery-query-addresses`（空）/ `order-list`（7 条真实订单，含整单退款状态）→ `data/delivery.json`（另含配送费、免运门槛、ETA、配送方式与支付方式配置）

Demo 下单为模拟闭环（真实交易需 `calculate-price` → `create-order`）。

## 目录

```
线上点餐台/
├── entry.html              # 进入页：品牌海报 + 堂食/外卖双入口 + 4 个功能入口
├── index.html              # 堂食点餐台（顶栏 + 左标题右3D + 底部点餐条）
├── delivery.html           # 外卖到家工作台（单页五区）
├── assets/
│   ├── style.css           # 像素风无卡片样式 + 昼夜自动主题（三页共用）
│   ├── gate.css / gate.js  # 进入页样式与交互（营养计算器 / 活动日历 / 优惠券 / 积分）
│   ├── delivery.css/.js    # 外卖页样式与五区逻辑（地址 / 配送 / 选餐 / 结算 / 订单）
│   ├── app.js              # 门店选择 / 3D 锁定环绕 / 昼夜双模型 / 轮播 / 点餐链路
│   ├── fonts/zpix.woff2    # Zpix 像素字体（中英文）
│   ├── stores/*.jpg        # 无 3D 门店的实景照片（广百 / 海珠广场）
│   └── models/             # 门店 GLB + 预览图
└── data/
    ├── menu.json           # MCP 菜单
    ├── store.json          # 模型注册表 + MCP 门店列表 + 优惠券 + 积分
    ├── nutrition.json      # MCP 营养库（进入页营养计算器）
    ├── campaign.json       # MCP 活动日历
    └── delivery.json       # 外卖配置 + MCP 地址/订单
```
