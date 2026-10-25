# United Kingdom Hotel / McDonald's Kew 3D 模型

## 生成与写实设定

本模型按 6.1 Ultra 级别的照片理解与参数化建模工作流整理，目标是还原可见的建筑主体、Streamline Moderne 轮廓、砖墙/石材/玻璃/金属材质差异，以及门店檐下暖光、玻璃反射和接触阴影。模型为 Blender 4.5.3 LTS 场景，采用米制、AgX 色彩管理、AgX Medium High Contrast，预览输出为 1500 × 1200 PNG；交付集合与预览摄影棚集合分开管理。

## 对象

澳大利亚墨尔本 Kew 区 **McDonald's Kew** 所在的历史建筑，原名 **United Kingdom Hotel**，位于 **261-267 High Street, Kew VIC 3101, Australia**。本项目以 1937—1938 年建筑和现状门店照片为视觉依据，制作可编辑的 Streamline Moderne 建筑展示模型。

## 精度与坐标

- 精度等级：**L1 照片推定**，非实测、非测绘、不可用于施工。
- 单位：米；Z 轴向上；主立面朝 `-Y`，建筑向 `+Y` 延伸。
- 建筑宽度：26.0 m；进深：15.0 m；主体高度：8.4 m；中央塔楼：14.2 m；含招牌约 17.7 m。
- 立面/进深比例：1.733；所有尺寸均服务于照片比例和展示用途。

## 目录

```text
3D模型/
├── README.md
├── viewer.html
├── models/
│   ├── United_Kingdom_Hotel_McDonalds.blend
│   ├── United_Kingdom_Hotel_McDonalds.glb
│   ├── United_Kingdom_Hotel_McDonalds.obj
│   ├── United_Kingdom_Hotel_McDonalds.mtl
│   ├── United_Kingdom_Hotel_McDonalds.fbx
│   ├── model_manifest.json
│   └── validation_report.json
├── previews/
│   ├── United_Kingdom_Hotel_01_front.png
│   ├── United_Kingdom_Hotel_02_oblique.png
│   ├── United_Kingdom_Hotel_03_detail.png
│   ├── United_Kingdom_Hotel_04_night.png
│   └── United_Kingdom_Hotel_preview_board.jpg
├── references/
├── src/
│   ├── united_kingdom_hotel_config.json
│   └── build_united_kingdom_hotel.py
└── docs/
    ├── 照片分析与建模记录.md
    ├── 门店介绍.md
    └── 模型验证报告.md
```

## 集合与导出边界

`01_HOST_SHELL`、`02_FACADE_STONE`、`03_ARCHITECTURAL_ARCHES`、`04_GLAZING_AND_DOORS`、`05_SIGNAGE`、`06_ENTRANCE_STEPS` 和 `07_LIGHTING_STORE` 为建筑与门店交付集合。`90_PREVIEW_STUDIO_EXCLUDED_FROM_EXPORT` 只包含预览地面、相机和棚灯；`99_REFERENCE_METADATA` 只保存照片来源说明，两者不进入 GLB、OBJ 或 FBX 模型导出。

## 可调参数

编辑 `src/united_kingdom_hotel_config.json` 后运行：

```powershell
& "C:\Users\Stan Li\WorkBuddy\吃吃麦当劳\.tools\blender-4.5.3-windows-x64\blender.exe" --background --python src/build_united_kingdom_hotel.py
```

可调项包括建筑宽度、进深、主体高度、塔楼尺寸、层高、转角半径、雨篷投影、阳台深度、入口宽度与高度、材质色值、渲染分辨率和采样数。脚本会重新生成 `.blend`、`.glb`、`.obj/.mtl`、`.fbx`、预览图和 `model_manifest.json`。

主要参数位于 `src/united_kingdom_hotel_config.json`：

- 建筑体量：`building.width`、`building.depth`、`building.main_height`、`building.tower_height`、`building.corner_radius`
- 立面构件：`building.awning_projection`、`building.balcony_depth`、`building.entrance_width`、`building.entrance_height`
- 材质外观：`materials.brick`、`materials.stone_gold`、`materials.glass`、`materials.metal`、`materials.awning` 等颜色参数
- 图像输出：`render.resolution_x`、`render.resolution_y`、`render.samples`；相机和灯光位置在 `src/build_united_kingdom_hotel.py` 的 `CAMS`、`point_light` 和 `area` 配置中调整

修改 JSON 后重新运行构建脚本即可更新全部交付文件。若需要更高的离线照片级质量，可将脚本中的 `BLENDER_EEVEE_NEXT` 改为 Cycles，并提高采样数，同时保留相同的单位、集合和文件命名规则。

## 输出格式

- **BLEND**：保留集合、相机、灯光、材质、可编辑文本和参数化建模上下文。
- **GLB**：适合 Web、实时引擎和模型查看器；只包含 01—07 交付集合。
- **OBJ + MTL**：通用静态网格交换格式，材质由 MTL 引用。
- **FBX**：适合 DCC 和游戏引擎之间的网格交换。
- **PNG/JPG**：四个固定视角和一张 2×2 预览汇总板。

## 相关文档

- `docs/门店介绍.md`：历史沿革、建筑风格与更新利用观点。
- `docs/照片分析与建模记录.md`：照片证据、构件取舍、尺寸推定与材质灯光记录。
- `docs/模型验证报告.md`：文件完整性、导出边界和预览检查结果。
