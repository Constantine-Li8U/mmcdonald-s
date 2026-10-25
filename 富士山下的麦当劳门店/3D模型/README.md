# 富士山下的麦当劳 · 3D 黄昏场景模型

日本山梨县富士吉田市 · 国道 139 号沿线麦当劳（139富士見バイパス店 / 139富士吉田店一带的黄昏场景意象）。

**本模型为系列首个「场景型」交付**：按用户指令，富士山与整体风景（云海带、远山、针叶树、湿地面前景）是模型的**指定不可移除部分**（集合 `08_ENVIRONMENT_FUJI`，随 GLB 导出），构图、色彩与细节以用户提供的黄昏参考照片（`references/REF_USER_黄昏参考照片.jpg`）为准。

## 查看方式

- 交互预览：直接打开 `viewer.html`（model-viewer，含参考照片构图 / 门店正视 / 三分之四 / 立柱招牌特写 / 富士山全景 5 个固定视角）。
- 静帧对比：`previews/` 下 6 张渲染（`Fuji_01_hero.png` 为与参考照片构图匹配的主视图）。

## 文件清单

```text
3D模型/
├── README.md
├── viewer.html
├── models/
│   ├── Fuji_McDonalds.blend     # 全集合 + 可编辑文字 + 相机
│   ├── Fuji_McDonalds.glb       # 交互查看（含 KHR_lights_punctual 灯光、雾墙贴图）
│   ├── Fuji_McDonalds.obj/.mtl
│   ├── Fuji_McDonalds.fbx
│   └── model_manifest.json
├── previews/                    # 6 张黄昏预览（AgX）
├── references/                  # 用户参考照片
├── src/
│   ├── build_fuji.py            # 参数化建模脚本（Blender 4.5 后台执行）
│   ├── fuji_config.json         # 全部尺寸 / 色板 / 灯光 / 相机参数
│   └── mist_gradient.png        # 云海竖直渐变 alpha 贴图
└── docs/
    └── 富士山店_照片分析与建模记录.md
```

## 模型组织

| 集合 | 内容 | 导出 |
| --- | --- | --- |
| 01_HOST_SHELL | 屋面板 / 檐口带 / 端墙 / 地坪 | 是 |
| 02_FACADE_CLADDING | 踢脚 / 左端实墙板 | 是 |
| 04_GLAZING_AND_DOORS | 幕墙 / 竖梃 / 门 / 室内暖光与家具剪影 | 是 |
| 05_SIGNAGE | 屋顶横匾 / 右端小 M 牌 / 立柱牌全套 | 是 |
| 07_LIGHTING_STORE | 门店与黄昏灯光（spot / point / sun） | 是 |
| 08_ENVIRONMENT_FUJI | 富士山三段锥体 / 云海雾墙 / 远山 / 针叶树 / 湿地坪 | 是 |
| 90_PREVIEW_STUDIO | 相机与预览地面 | 否 |

## 复建

```bash
blender --background --python src/build_fuji.py            # 构建 + 导出 + 渲染
blender --background --python src/build_fuji.py -- --no-render
```

## 诚实声明

- 全部尺寸为**照片推定**，非实测，不可用于施工或工程测量。
- 参考照片为艺术化透视：富士山相对门店的视角比例无法物理自洽，模型按「构图视觉匹配」处理（山体半角约 25.6° 接近照片观感，山距 2600m / 可见高 442m），不是地理真实比例。
- 立柱牌「OPEN 24 HOURS」来自参考照片；日本麦当劳官网对 19541 店的实际口径为 7:00–23:00（临时月曜 7:00–21:00），出行以官方页为准。
- 室内仅做暖光背板与家具剪影，无人物；灯位全部可追溯到参考照片（v1.1 规范）。
