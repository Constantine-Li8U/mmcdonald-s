# 吃吃麦当劳 · 麦当劳门店档案与像素 3D 点餐台

围绕麦当劳门店做的两个方向的工作，放在同一个仓库里：

1. **门店档案库** —— 广州人气 TOP10 门店的图文档案，以及若干海外/地标门店的 3D 建筑模型。
2. **线上点餐台** —— 一个像素风的三页一体点餐 Demo，门店 / 菜单 / 优惠券 / 营养 / 订单全部接麦当劳 MCP 真实数据。

> 说明：所有「人气排名」类内容都是基于公开数据的**综合指数估算**，麦当劳不公开单店营业额，因此**不是销量榜**。

## 目录结构

| 目录 | 内容 |
| --- | --- |
| [`广州前十麦当劳门店/`](广州前十麦当劳门店/) | 广州 TOP10 门店档案：总览报告 + 10 个门店文件夹（说明文档 md/docx、实拍照片、3D 模型）、`_数据与评分/` 原始数据、`_构建工具/` 生成脚本 |
| [`线上点餐台/`](线上点餐台/) | 像素 3D 点餐 Demo：`entry.html` 进入页 → `index.html` 堂食 3D 点餐台 / `delivery.html` 外卖工作台 |
| [`富士山下的麦当劳门店/`](富士山下的麦当劳门店/) | 富士山店门店档案 + 3D 模型（含昼 / 夜两版资产） |
| [`Santorini_Hot_Spring_Resort_McDonalds/`](Santorini_Hot_Spring_Resort_McDonalds/) | 圣托里尼门店 3D 模型 |
| [`United_Kingdom_Hotel_McDonalds/`](United_Kingdom_Hotel_McDonalds/) | 英国酒店门店 3D 模型 |

各子目录内的 `README.md`（广州总览、线上点餐台、各店 `3D模型/README.md`）是该部分的详细说明：运行方式、文件清单、建模依据与免责声明。

## 快速开始

### 线上点餐台

纯静态页面，无需构建：

```bash
python -m http.server 8899 --directory 线上点餐台
# 进入页   http://127.0.0.1:8899/entry.html
# 堂食台   http://127.0.0.1:8899/index.html?mode=dinein
# 外卖台   http://127.0.0.1:8899/delivery.html
```

各页面带自测开关 `?selftest=1`，结果写入页面标题（`PASS n | FAIL n`）。

### 门店档案生成

档案的 md 与 docx 由同一份数据渲染，**不要手改产物**：

```bash
cd 广州前十麦当劳门店/_构建工具
python build_stores.py     # stores.json 由原始抓取数据生成
python render_md.py        # 渲染 Markdown
python render_docx.py      # 渲染 Word
```

脚本依赖 `python-docx` 与 `Pillow`，建议用虚拟环境安装，不要污染全局环境。

### 3D 模型

每个门店的 `3D模型/` 目录下包含可编辑源文件与导出格式：

- `models/*.blend` —— Blender 4.5 LTS 可编辑源文件
- `models/*.glb` —— 单文件交换格式，Web 查看器与多数 3D 软件可直接打开
- `models/*.obj` + `.mtl`、`models/*.fbx` —— 通用网格与跨软件编辑
- `src/build_*.py` + `*_config.json` —— 参数化重建脚本（尺寸、材质、光照参数都在配置里）
- `viewer.html` —— 本地直接双击即可旋转查看

系列建模的统一流程、材质、光照、命名与验收标准见
[`广州前十麦当劳门店/01_沙面店/3D模型/docs/系列门店建模风格规范.md`](广州前十麦当劳门店/01_沙面店/3D模型/docs/系列门店建模风格规范.md)。

## 数据与版本说明

- 档案库的唯一数据源是 `广州前十麦当劳门店/_构建工具/stores.json`；改数据只改它，再重渲染产物。
- 照片来源、抓取时间与版权说明记录在各店 `photos/_sources.csv` 与 `_数据与评分/照片来源总表.csv`。
- 3D 模型尺寸为**以门高为视觉标尺的照片推定值，非实测**，不可用于施工、结构、消防、改造报价或工程测量。

## 不纳入版本库的内容

| 排除项 | 原因 |
| --- | --- |
| `.tools/`（Blender 便携版）、`.venv/` | 工具与依赖，体积大、可重建 |
| `.workbuddy/`、`.tmp/`、`_temp_fuji/` | 会话数据与临时工作目录 |
| `*.blend1` | Blender 自动备份副本（`.blend` 已保留） |
| `~$*.docx`、`*.待替换.docx` | Office/WPS 锁文件与渲染降级产物 |
| `bing.html`、`bk.html`、`mdp.html` | 抓取过程中的临时网页快照（Bing 搜索页、百度验证页等） |
| `__pycache__/`、`*.pyc` | Python 字节码 |
