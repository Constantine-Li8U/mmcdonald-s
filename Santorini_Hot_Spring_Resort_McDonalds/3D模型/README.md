# 广州圣托利温泉庄园店：照片级建筑三维模型

本项目对象为 **广州圣托利温泉庄园店（McDonald's Santorini Hot Spring Resort）**，城市为 **广州市**。地址按照片与可核对公开信息记录为：**广州市从化区温泉镇圣托利温泉庄园内**；照片和现有资料未提供可可靠核实的街道门牌号，精确地址需现场确认。

## 建模主体与尺寸

模型主体是门店所在的白色仿圣托里尼 / 欧式度假建筑，包括中央三层拱券钟楼、铜钟、人物雕像、蓝色高拱窗、左侧玻璃电梯塔、入口四柱门廊、蓝色半圆玻璃雨篷、玻璃门、入口台阶和麦当劳 / 圣托利庄园标识。人物、车辆、树木、道路标线、广告牌和未经照片支持的环境物不建模。

单位为米，`+Z` 向上，主立面朝 `-Y`，建筑向 `+Y` 延伸，首层地坪为 `Z=0`。

| 项目 | 基准尺寸 |
|---|---:|
| 主体宽度 | 34.0 m |
| 主体进深 | 18.0 m |
| 主体檐口高度 | 9.0 m |
| 中央钟楼最高点 | 17.8 m |
| 入口宽 × 高 | 5.4 m × 3.4 m |
| 主立面宽深比 | 1.889 |
| 交付几何整体包络（含前伸构件） | 36.77 m × 21.145 m × 18.90 m |

所有尺寸均为 **L1 照片推定**，不是现场测量；背面、屋顶和照片不可见的连接处为简化推定，不可用于施工图、结构计算、消防设计或工程测量。

## 层级结构与命名

交付集合如下：

- `01_HOST_SHELL`：主体体量与屋顶阶梯
- `02_FACADE_STONE`：白色墙体、檐口、柱、装饰构件
- `03_ARCHITECTURAL_ARCHES`：拱券、钟楼、钟、雕像、拱形装饰
- `04_GLAZING_AND_DOORS`：蓝色拱窗、玻璃电梯塔、玻璃门、门框
- `05_SIGNAGE`：麦当劳、McCafé、圣托利庄园和城市标识
- `06_ENTRANCE_STEPS`：入口台阶与铺装
- `07_LIGHTING_STORE`：门店暖色点光
- `90_PREVIEW_STUDIO_EXCLUDED_FROM_EXPORT`：仅用于预览的地面、相机、三点光，不进入 GLB 等交付模型
- `99_REFERENCE_METADATA`：照片来源与建模证据元数据，不进入交付模型

对象名使用 ASCII 的部位 / 构件 / 序号风格；材质使用 `类别_用途` 风格。文件名使用 ASCII snake / Pascal 风格，便于 Blender、WebGL 和 DCC 软件交换。

## 可调参数与重建

编辑 `src/santorini_config.json` 可调整：主体宽度、进深、主体高度、钟楼高度、中央塔宽度、窗洞宽高、入口尺寸、转角半径、材质颜色、渲染分辨率和采样数。使用项目配套 Blender 4.5.3 重建：

```powershell
& "C:\Users\Stan Li\WorkBuddy\吃吃麦当劳\.tools\blender-4.5.3-windows-x64\blender.exe" --background --python "src\build_santorini.py"
```

脚本会重建场景、保存 BLEND、导出 GLB / OBJ+MTL / FBX、生成四张预览图和 `model_manifest.json`。

## 最终输出

- `models/Santorini_Hot_Spring_Resort_McDonalds.blend`：可编辑 Blender 场景，含集合、相机、灯光、材质和场景元数据
- `models/Santorini_Hot_Spring_Resort_McDonalds.glb`：WebGL、实时引擎和 `viewer.html` 使用；不含预览工作室集合
- `models/Santorini_Hot_Spring_Resort_McDonalds.obj` + `.mtl`：通用静态网格交换
- `models/Santorini_Hot_Spring_Resort_McDonalds.fbx`：DCC / 游戏引擎交换
- `models/model_manifest.json`：尺寸、包络、集合、照片来源与导出清单
- `models/validation_report.json`：自动验证结果
- `previews/Santorini_01_front.png`、`02_oblique.png`、`03_detail.png`、`04_night.png`：四张预览
- `previews/Santorini_preview_board.jpg`：2×2 汇总板
- `viewer.html`：加载 GLB 的拖拽旋转、缩放、固定视角与自动旋转查看器

模型用于建筑展示、实时查看和视觉研究；L1 照片推定精度不代表测绘成果。
