# 麦当劳（沙面店）3D 建筑模型

基于本店实拍制作的独立、可编辑、参数化建筑模型。仅包含建筑本体，不含人物、车辆、道路、绿化、购物车、互联网图标或周边场景。

## 快速查看

- **交互查看**：打开 `viewer.html`，可旋转、缩放，切换正立面、三分之四和首层细节视角。
- **预览汇总**：`previews/Shamian_preview_board.jpg`。
- **直接修改**：用 Blender 4.5 LTS 或更新版本打开 `models/Shamian_McDonalds.blend`。
- **跨软件查看**：优先使用 `models/Shamian_McDonalds.glb`；另附 OBJ+MTL 与 FBX。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `models/Shamian_McDonalds.blend` | 可编辑源文件，保留语义集合、文字、材质和预览相机 |
| `models/Shamian_McDonalds.glb` | 单文件三维交换格式，含材质，适合查看器与多数 3D 软件 |
| `models/Shamian_McDonalds.obj` + `.mtl` | 通用网格与材质格式 |
| `models/Shamian_McDonalds.fbx` | 跨软件编辑与资产管线 |
| `models/model_manifest.json` | 模型尺寸、网格统计、集合与来源记录 |
| `previews/` | 正立面、三分之四、首层细节和汇总预览 |
| `references/` | 实拍视觉依据联系表 |
| `src/shamian_config.json` | 推定尺寸、开间、拱、招牌与材质参数 |
| `src/build_shamian.py` | 可复建的 Blender 参数化脚本 |
| `docs/沙面店_照片分析与建模记录.md` | 本店照片依据、比例、细节取舍和制作过程 |
| `docs/系列门店建模风格规范.md` | 后续门店复用的统一流程、材质、光照、命名与验收标准 |

## 模型内容

- 三层宿主建筑体量，首层为沙面店临街立面。
- 四个半圆拱、浅灰石墙与水平分缝、层间线脚。
- 左侧甜品站、黑色 McDonald's 窗篷、落地金色 M。
- 右侧双扇玻璃入口、拉手、三级台阶。
- 上层 McDonald's 立体字、竖向 McCafé、矩形上层窗。
- 简化的侧墙、后墙、楼板、平屋顶与低女儿墙。

## 比例与使用边界

模型按米制组织，主体约 **18.0 m 宽 × 6.5 m 进深 × 10.2 m 高**。这些尺寸是以门高为视觉标尺的**照片推定值，非实测**；不可用于施工、结构、消防、改造报价或工程测量。

照片未展示的背立面、侧面与屋顶采用克制补全。室内仅表达玻璃与暖色纵深，不重建人物、家具或商品。

## 修改与复建

1. 直接修改 `.blend`：`01–06` 集合为建筑本体，`90` 为不导出的预览灯光与地面。
2. 修改 `src/shamian_config.json` 中的尺寸与色值。
3. 在 Blender 中运行：

```bash
blender --background --python src/build_shamian.py
```

只重建模型、不渲染：

```bash
blender --background --python src/build_shamian.py -- --no-render
```

`.blend` 中文字保持可编辑；导出格式中的文字已转网格，避免跨软件缺字。

## 来源与版权

视觉依据为门店档案中的 12 张实拍，原始出处与版权信息见 `../photos/_sources.csv`。照片版权归原作者与品牌方所有；本模型用于门店档案与建筑可视化研究，不是麦当劳官方模型，也不构成品牌授权。
