# CH9 视觉升级素材包

> 配套：《AlphaEarth CH9 古建筑天地一体预防性保护 PRD》《三体计算星座 × 古建筑保护 展台海报 v3》
> 生成日期：2026-09-08

---

## 一、先更正一个关键判断：`format: "png"` 不是根因

诊断里说「后端 `format` 不是 `png` 导致 GEE 返回实心背景色」——**这个结论是错的**，照着改不会修复任何东西。

**事实：**

1. GEE `getMapId()` 的 visParams **不接受 `format` 键**，传进去会被静默忽略。
2. GEE 瓦片**本来就是 PNG**，被 `updateMask` 掉的像元**本来就是全透明**的。

**真正的三个根因（按概率排序）：**

### ① 兜底分支返回了 `ee.Image.constant()` —— 这就是「黄色巨块」

CH8 原始代码里有这么一段，CH9 也继承了：

```python
try:
    insar_img = ee.Image(ASSET_ID)
except Exception:
    insar_img = ee.Image.constant(0).rename('velocity') \
                  .addBands(ee.Image.constant(1).rename('coherence'))
```

常量图在**全球每一个像元都有值**。后面 `coherence.gt(0.75)` → `constant(1) > 0.75` → **恒为真**；
`velocity.lt(-5).Or(velocity.gt(5))` 在 `constant(0)` 上恒为假 → 全掩掉（白屏）；
而 AEF 分支的 `prob.gt(0.72)` 在退化分类器上又可能**恒为真** → **满屏纯色块**。

一个 fallback，两种病症，正好对上你的两张截图。

> **Asset ID 没配 / 资产不存在 / 权限不足 → 必然触发。**

### ② `updateMask` 条件在退化图上恒为真
AEF 分类器如果训练样本资产缺失或样本量过小，输出会退化成近似常数，阈值过滤形同虚设。

### ③ `vis` 里 `min == max`，或 palette 只有一个颜色
所有像元映射到同一色 → 纯色块。

### 正确做法

**图层不可用时不要返回图层**，而不是返回一张假图：

```python
raise LayerUnavailable("Asset 不可访问", asset_id)
# → 后端返回 {"tileUrl": null, "available": false, "reason": ...}
# → 前端据此跳过 addImageryLayer，地球干干净净
```

`ch9_gee_layer_fix.py` 里还加了一道**覆盖率护栏**：掩膜后若仍覆盖 AOI 超过 92%（AEF 层 55%），
直接判定 mask 失效并拒绝出图 —— 宁可不显示，也不要糊住地球。

---

## 二、3D 模型：为什么是生成而不是下载

我没有去下载现成模型，而是写了一个**参数化生成器**（`gen_heritage_models.py`）。原因：

| | 网上下载的免费模型 | 本包生成的模型 |
|---|---|---|
| 版权 | CC-BY 需署名 / 部分不可商用 / 部分来源不明 | **脚本原创生成，无第三方版权** |
| 部位锚点 | 无，标签只能靠肉眼估位置 | **自带 40 个部位锚点**（屋脊/檐口/翼角/山墙/柱脚/台基），标签精确挂载 |
| 面数 | 常见 10 万–100 万面，Cesium 卡 | **2.5k–15k 面**，流畅 |
| 形制匹配 | 多为日式/泛东亚，或故宫式官式建筑 | 按江南民居形制调参，可派生 40+ 基本型 |
| 可扩展 | 改不了 | 改几个参数就出一个新变体，**直接对应风载荷知识库的基本型库** |

### 模型清单

| 文件 | 用途 | 三角面 | 尺寸 (面阔×进深×高, m) |
|---|---|---|---|
| `heritage_hall_xieshan.glb` | 通用中式厅堂 · 歇山顶。单体展示、通用替身 | 2,576 | 19.3 × 12.9 × 9.8 |
| `heritage_taimen_courtyard.glb` | 台门/三合院 · 门楼+正厅+两厢+院墙。**恒济台门形制** | 8,580 | 29.8 × 26.7 × 9.2 |
| `heritage_complex_multicourt.glb` | 多进院落建筑群 · 三进+厢廊。**卢宅形制** | 14,708 | 44.5 × 62.5 × 11.0 |

每个 `.glb` 配一个 `*_anchors.json`，含：
- `anchors_local_m`：部位锚点的**模型局部坐标**（米，Z-up）
- `size_m` / `triangles` / 坐标轴约定说明

### 屋顶做了什么

不是简单的三角棱柱，而是按中式屋面的三个特征参数化建模：

- **举折**：`z = z_ridge − (z_ridge − z_eave) · u^0.62`，指数 < 1 → 近脊陡、近檐缓，这是中式屋面的辨识特征
- **翼角起翘**：仅在 `|v| > 0.62` 的两端区间，抬升量随 `u²` 增长 → 檐角上扬
- **出翘**：翼角同时向外飘出，形成"如翚斯飞"的轮廓
- **正脊 + 鸱吻**：脊身两端微微上翘，端部加吻兽体块

配色沿用展台海报的语义色：青灰瓦面 `#4A525A`、朱红木柱 `#7A3A2A`、粉白墙 `#DED8CC`、石灰台基 `#C4BEB2`。

### 派生更多基本型

改 `build_hall()` 的参数即可：

```python
build_hall(W=16, D=10, ridge_frac=1.0, hip=False)   # 硬山顶（江南民居最常见）
build_hall(W=20, D=12, ridge_frac=0.0, hip=True)    # 攒尖/庑殿趋近
build_hall(W=12, D=8,  h_ridge=6.5, bays=3)         # 三开间小型厅堂
```

`ridge_frac=1.0 + hip=False` → 硬山；`0.5~0.7 + hip=True` → 歇山；越接近 0 越像庑殿。
配合 `corner_lift`（起翘高度）和 `curve_p`（举折陡缓）可以做地域差异——北方平缓、江南陡峭高翘。

---

## 三、L5 三维实现：三个关键修正

### 修正一：不要用 `ColorBlendMode.REPLACE`

`REPLACE` 会把模型材质**整个换成纯色** → 又变回"红色方块"，只是形状好看了一点。
必须用 **`MIX` + `colorBlendAmount ≈ 0.55`**，这样瓦面纹理、木柱色都还在，风险色是叠加上去的。

```js
color: colorProp,
colorBlendMode: Cesium.ColorBlendMode.MIX,
colorBlendAmount: 0.55,
silhouetteColor: base,      // 高危时再加一圈描边
silhouetteSize: 2.0,
```

### 修正二：废弃地面 2D 热力图，改屋面风场流线

诊断说得对——**风压作用在屋顶上，地面的红色热力图在物理逻辑上是错的**。
`addWindStreamlines()` 用 `PolylineGlowMaterialProperty` + `CallbackProperty` 在屋面上方画 9 条随时间流动的青蓝色流线，沿真实风向推进，中段随屋面拱起。呼应侧边栏的 FEA 云图，物理上也说得通。

### 修正三：锚点标签的深度测试要分开设

- **点（point）**：`disableDepthTestDistance: 0` → 参与深度测试，被屋顶挡住时自然隐藏，产生真实的空间纵深
- **文字（label）**：`disableDepthTestDistance: Infinity` → 始终可读

两者都设成 `Infinity` 会让标签"穿模"漂浮；都设 0 则文字会被遮挡看不清。分开设是关键。

另外每个锚点向下引一根 2.2 m 的短引线"钉"在部位上，视觉上标签就长在建筑上，不再悬空。

### 电影级打光

`applyCinematicLighting()` 一次性解决"侧边栏暗黑 vs 地图大白天"的割裂：

```js
globe.baseColor = "#0A1520";              // 无影像区不再刺眼
globe.atmosphereBrightnessShift = -0.32;  // 大气压暗
scene.light = new Cesium.DirectionalLight({ // 低角度冷调定向光
  direction: (0.28, -0.52, -0.81), intensity: 2.4 });
scene.fog.enabled = true; scene.fog.density = 0.00016;
scene.highDynamicRange = true;
scene.backgroundColor = "#060E16";
```

配合模型的 `lightColor: (1.25, 1.30, 1.38)` 冷调补光，整体色温与海报 P1 一致。

### 镜头：L5 绝不用 −90°

```js
L5_BUILDING: { height: 620, pitch: -32 }   // ★ 垂直俯视 = 丧失 3D 感
```

诊断这一条完全正确，已写进 `LAYER_LEVELS` 常量。

---

## 四、文件清单与集成路径

```
frontend/public/assets/models/
├── heritage_hall_xieshan.glb                 →  modelKey: "hall"
├── heritage_hall_xieshan_anchors.json
├── heritage_taimen_courtyard.glb             →  modelKey: "taimen"   （恒济台门）
├── heritage_taimen_courtyard_anchors.json
├── heritage_complex_multicourt.glb           →  modelKey: "complex"  （卢宅）
└── heritage_complex_multicourt_anchors.json

frontend/src/scenes/
└── ch9_cesium_l5.js          →  L5 模块（打光/模型/锚点/风场/镜头/安全图层）

backend/
└── ch9_gee_layer_fix.py      →  合并进 gee_service.py，替换现有 CH9 分支

tools/
├── gen_heritage_models.py    →  重新生成 / 派生新基本型
└── *_preview.jpg             →  三个模型的渲染预览
```

**集成三步：**

1. `.glb` 与 `_anchors.json` 拷到 `frontend/public/assets/models/`
2. `gee_service.py` 里 CH9 三个分支替换成 `ch9_gee_layer_fix.py` 的实现；前端改成读 `available` 字段决定是否 `addImageryLayer`
3. 进入 L5 时调 `playDrilldown(viewer, ctx)`，参数见 `ch9_cesium_l5.js` 末尾的使用示例

---

## 五、如果后续要换成更精细的真实模型

本包的通用模型定位是**"高质量替身"**，够撑展台。若中期要上真实倾斜摄影/精模，合规来源如下：

| 来源 | 许可 | 适用 | 备注 |
|---|---|---|---|
| **Sketchfab CC0 专区** | CC0 公共领域，可商用免署名 | 通用中式建筑、四合院 | 检索时**务必筛 CC0**；CC-BY 需署名，部分标注 NC 不可商用 |
| **Sketchfab 文化遗产公共领域计划** | CC0 | 博物馆扫描的遗产模型 | 由博物馆机构主动发布，来源可靠 |
| **中试基地 3D Max 基本型库** | 内部资产 | **40+ 地区性基本型** | ★ **优先走这条**——形制准确、与风载荷知识库同源，转 glTF 即可用 |
| 无人机倾斜摄影 | 自采 | 卢宅、越城重点单体 | 精度最高，成本最高；建议只对国宝级建筑做 |

> **强烈建议**：中试基地既然已有 40+ 基本型的 3D Max 资产，且**风载荷知识库就是基于这批模型跑的有限元**，直接把它们批量导出 glTF 才是最优解——模型与仿真结果同源，薄弱点位置天然对齐，不存在"模型和数据对不上"的问题。本包的生成器可以作为过渡方案和补位。

---

## 六、待办

| # | 事项 | 影响 |
|---|---|---|
| 1 | 确认恒济台门 / 卢宅的**真实建筑朝向**（heading）与轮廓尺寸 | 模型 scale 与 heading 参数 |
| 2 | 中试基地 3D Max 基本型库能否批量导出 glTF | 决定是否替换本包通用模型 |
| 3 | 风载荷知识库返回的薄弱点，是否带**部位编码** | 若带，可与 anchors key 直接映射；若不带需人工建映射表 |
| 4 | Cesium 版本号 | `ColorBlendMode`、`DirectionalLight` API 在旧版本（<1.60）不可用 |
| 5 | 前端是否已按 `available` 字段跳过图层 | 决定黄块 bug 是否真正根治 |
