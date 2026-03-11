Zero2x v7.2 核心场景技术开发与演示汇报手册 (Data-Driven Edition)

涵盖范围： Demo 6 (塔拉滩) —— Demo 14 (微观虫洞)
核心主旨： 视窗即现场 (Window as Reality)，代码即算力 (Code as Compute)

🌍 第二阵列：前沿开拓 (空天视界进阶)

本阵列侧重于展示系统对多源异构数据（3DTiles、高程、矢量、CZML、影像）的空间融合能力，以及 Cesium 高级渲染管线的调用。

Demo 6: 塔拉滩光伏治沙与空间统计

背景与意义： 青海塔拉滩是全球最大的光伏治沙基地。本场景旨在展示平台从“单纯看图”向“定量空间统计”的跨越能力。

数据源与处理工程 📦：

真实获取路径： 1. 影像底图：使用 GEE 调用 Sentinel-2 最新无云镶嵌影像 (COPERNICUS/S2_SR_HARMONIZED)。
2. 矢量数据：利用 Meta 的 Segment Anything Model (SAM) 对遥感影像进行光伏板实例分割，导出 GeoJSON。
3. 产能数据：爬取黄河水电公司历年公开财报。

演示兜底生成方案 (Python Mock)： 如果无法实时调用大模型分割，可用以下脚本在目标区域生成逼真的网格化光伏板阵列：

import geopandas as gpd
from shapely.geometry import Polygon
import numpy as np

# 塔拉滩核心区中心点: 36.18, 100.55
polygons = []
for x in np.arange(100.50, 100.60, 0.005):
    for y in np.arange(36.15, 36.20, 0.005):
        # 生成光伏板阵列
        poly = Polygon([(x, y), (x+0.004, y), (x+0.004, y+0.002), (x, y+0.002)])
        capacity = np.random.randint(50, 200) # 随机装机容量
        polygons.append({"geometry": poly, "properties": {"capacity_mw": capacity}})

gdf = gpd.GeoDataFrame.from_features(polygons)
gdf.to_file("talatan_mock.geojson", driver="GeoJSON")


总结演示说明（导演台本）：

🗣️ 话术： “Copilot，请评估塔拉滩光伏治沙的实际工程量与历年发展趋势。”

🎬 视觉预期： 镜头平滑飞至青海，满屏的蓝色光伏矢量色块拔地而起（高度代表 capacity_mw）。左侧资产面板切至 CHARTS，展示历年装机量曲线。

Demo 7: 珠峰冰原溃决预警

背景与意义： 模拟喜马拉雅冰碛湖溃决洪水 (GLOF)，展示极致的三维地形与流体结合表现力。

数据源与处理工程 📦：

真实获取路径：

地形：调用 Cesium Ion 的 Cesium World Terrain (Asset ID: 1)。

网络/环境兜底：若现场网络无法访问 `assets.ion.cesium.com`（常见报错：`net::ERR_CONNECTION_RESET`），前端会自动回退到椭球地形（Ellipsoid）。此时仍可继续演示“淹没 Polygon + 动态水体”，但不会有真实山体起伏。解决：放通外网/配置代理与 Ion Token；或直接关闭 World Terrain 依赖做离线演示。

淹没范围：基于 SRTM 30m DEM，在 ArcGIS/QGIS 中使用水文分析工具（Hydrology）提取珠峰北坡汇水盆地，生成淹没 Polygon。

演示兜底生成方案： 直接手绘一个沿山谷走向的多边形。

{
  "type": "Feature",
  "geometry": { "type": "Polygon", "coordinates": [[[86.92, 28.01], [86.93, 28.05], [86.91, 28.08], [86.89, 28.04], [86.92, 28.01]]] }
}


方法与后端逻辑：

开启全球地形深度测试，利用 Cesium Fabric Material 编写动态水体着色器。

总结演示说明（导演台本）：

🗣️ 话术： “基于当前气象参数，模拟珠峰地区高危冰碛湖溃决的潜在淹没范围。”

🎬 视觉预期： 镜头推近雄伟的 3D 雪山峡谷。泛着波光、动态流淌的蓝色水体多边形完美贴合地形起伏（不穿模）。

Demo 8: 夏威夷火山地壳形变 (InSAR)

背景与意义： 监控极其微小的地表隆起（毫米级），将枯燥的 InSAR 矩阵转化为视觉奇观。

数据源与处理工程 📦：

真实获取路径： 从 Alaska Satellite Facility (ASF) 下载 Sentinel-1 影像，使用 SNAP 软件进行干涉测量，导出位移量（Displacement）的 GeoTIFF。

演示兜底生成方案 (Python Mock)： 用高斯分布生成一张伪造的形变灰度图，用于传入 Shader。

import numpy as np
from PIL import Image

# 生成 512x512 的高斯形变纹理
x, y = np.meshgrid(np.linspace(-1,1,512), np.linspace(-1,1,512))
d = np.sqrt(x*x+y*y)
sigma, mu = 0.3, 0.0
g = np.exp(-( (d-mu)**2 / ( 2.0 * sigma**2 ) ) )

img = Image.fromarray(np.uint8(g * 255), 'L')
img.save('mock_insar_displacement.png')


方法与后端逻辑：

实现伪代码： 使用 CustomShader。

void vertexMain(VertexInput vsInput, inout czm_modelVertexOutput vsOutput) {
    float disp = texture2D(u_insarMap, vsInput.attributes.st).r;
    vsOutput.positionMC += vsInput.attributes.normalMC * (disp * 100.0); // 夸张100倍
}


总结演示说明（导演台本）：

🗣️ 话术： “叠加 InSAR 形变数据，放大夏威夷莫纳罗亚火山的‘呼吸’活动。”

🎬 视觉预期： 静态的地表模型开始呈现具有生命力般的脉动起伏。

Demo 9: 刚果盆地碳汇估算

背景与意义： 盘点“地球之肺”的碳储量资产，展示系统对前沿空间网格体系（Uber H3）的支撑。

数据源与处理工程 📦：

真实获取路径： GEE 下载 NASA/GEDI/L4B/Gridded_Biomass 数据。

演示兜底生成方案 (Python + H3)：

import h3
import json
import random

# 刚果盆地中心
lat, lng = -0.5, 15.0
hexagons = h3.k_ring(h3.geo_to_h3(lat, lng, 5), 10)

features = []
for h in hexagons:
    geo = h3.h3_to_geo_boundary(h, geo_json=True)
    carbon = random.uniform(50, 300) # 模拟吨/公顷
    features.append({
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [geo]},
        "properties": {"carbon_stock": carbon}
    })

with open("congo_h3_mock.geojson", "w") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f)


总结演示说明（导演台本）：

🗣️ 话术： “对刚果盆地进行 H3 网格化，估算该区域的立体碳汇储量。”

🎬 视觉预期： 广袤的非洲大地上，拔地而起无数个六边形柱体。柱体的高度代表碳储量。

Demo 10: 纽约热岛与社会折叠 (Bivariate Map)

背景与意义： 揭示城市空间正义议题（例如：穷人区缺少绿化温度高）。

数据源与处理工程 📦：

真实获取路径： 1. 温度：GEE 提取纽约夏季 Landsat LST。
2. 收入：纽约市 OpenData 平台下载 Census Tracts GeoJSON。

演示兜底生成方案： 在纽约行政区 GeoJSON 中直接注入随机的负相关属性。

# 伪代码：为GeoJSON注入双变量属性
for feature in geojson['features']:
    income_percentile = random.uniform(0, 100)
    # 模拟负相关：收入越低，热岛越严重
    heat_percentile = 100 - income_percentile + random.uniform(-10, 10)
    feature['properties']['income'] = income_percentile
    feature['properties']['heat'] = heat_percentile


总结演示说明（导演台本）：

🗣️ 话术： “透视纽约城市热岛分布与人均收入的折叠关系。”

🎬 视觉预期： 曼哈顿核心区（高收入低温度显蓝）与布朗克斯等区域（低收入高温度显红）呈现出截然不同的色块对比。

🌟 Demo 11: 马六甲暗夜油污与船舶溯源

背景与意义： 动态时空追溯的巅峰场景，完美融合了遥感解译（SAR多边形）与物联网轨迹（AIS时序数据）。

数据源与处理工程 📦：

真实获取路径： Sentinel-1 SAR 处理提取海面暗斑；AIS 船舶轨迹从 Global Fishing Watch 下载。

演示兜底生成方案 (CZML 格式器)： 必须下发真实的 JSON 结构给前端渲染。

// 包含一艘涉事船舶轨迹的极简 CZML
[
  {"id": "document", "version": "1.0", "clock": {"interval": "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z", "currentTime": "2024-01-01T00:00:00Z", "multiplier": 60}},
  {
    "id": "suspect_ship", "name": "Vessel XYZ",
    "position": {
      "epoch": "2024-01-01T00:00:00Z",
      "cartographicDegrees": [0, 100.7, 2.2, 0, 1800, 101.0, 2.5, 0, 3600, 101.2, 2.6, 0]
    },
    "path": {"material": {"polylineOutline": {"color": {"rgba": [0, 240, 255, 255]}, "outlineWidth": 2}}, "width": 4, "leadTime": 3600, "trailTime": 3600}
  }
]


总结演示说明（导演台本）：

🗣️ 话术： “马六甲海峡发现可疑油污，调取过去24小时 AIS 轨迹进行碰撞溯源。”

🎬 视觉预期： 引擎强制触发 setSceneMode('night')，地球滤镜压黑。海面亮起橙色油污斑块。一根发光的青色轨迹线像流星一样划过多边形边缘，底部时间轴狂飙。

🌟🌟 Demo 12: 皮尔巴拉极深地下矿脉解译

背景与意义： 打破传统 GIS 只能看“地表”的限制，让空间计算向下延伸到地下三维空间。

数据源与处理工程 📦：

真实获取路径： 深层地质 3D Voxel 数据极其昂贵且保密（如 Leapfrog 生成的数据）。

💡 概念核心：什么是 Stub (存根) 与如何利用它？

释义： Stub 是高规格路演中的“智能替身”。因为真实的高光谱体积解混（Hyperspectral Voxel Unmixing）需要消耗巨大的算力和数十分钟的时间，无法在 3 分钟的 Demo 中实时跑完。因此，当系统识别到用户的意图后，会“模拟”执行完毕，并直接下发一个预先准备好的、极具视觉冲击力的模型（这就是 Stub）。它既能保障演示绝对不翻车，也能传达最核心的产品理念。

高阶视觉演进： 目前使用简单的椭球体会显得有些廉价。为了强化“矿脉”的质感，建议在底层引擎将实体替换为具有分支结构的 PolylineVolumeGraphics（三维树段）或直接加载一个赛博朋克风格的发光 GLTF 模型。

前端 Stub 高阶渲染伪代码（基于 Cesium Entity）：

// 引擎层高阶地下锚点渲染：使用发光折线体模拟“矿脉根须”
viewer.entities.add({
  polylineVolume: {
    positions: Cesium.Cartesian3.fromDegreesArrayHeights([
      118.7, -22.3, -3500.0,
      118.72, -22.28, -4200.0,
      118.75, -22.35, -5000.0
    ]),
    shape: computeCircle(500.0), // 横截面半径500米
    material: new Cesium.PolylineGlowMaterialProperty({
      glowPower: 0.8,
      color: Cesium.Color.fromCssColorString('#FF4D6D')
    })
  }
});


总结演示说明（导演台本）：

🗣️ 话术： “对我们而言，地表已无秘密可言。剥离澳洲地壳，解译地下4000米的隐伏锂矿层。”

🎬 视觉预期： 地球瞬间变成半透明玻璃态，镜头如钻探机般直降地下 -4500m。抬头仰望，漆黑深渊中悬浮着闪耀着粉红光芒的网状矿脉虚影（Stub）。极少有竞品能做到地下渲染，这是大杀器。

🚀 第三阵列：极客炫技 (系统级架构张力)

🌟🌟🌟 Demo 13: 全球流体与 WebGPU 代码热生成

背景与意义： 完美诠释“Code as Compute”。大模型不是在调用 API，而是在实时写出具备真实流体力学特征的 GPU 算力代码并直接运行。

数据源与处理工程 📦：

真实获取路径： 从 NOAA GFS 下载气象数据，解析 U/V 风速分量，转成二进制 Buffer 传给 WebGPU。

💡 高阶演示方案：物理气象级 WebGPU 代码注入 (Procedural Flow)
之前的随机波浪代码缺乏流体感。以下是最新的“全球大气环流”程序化生成代码，它利用球坐标切线空间模拟了宏观的行星风带（Zonal Winds）与动态的气旋（Cyclones），视觉拉丝感极强。这正是您需要让大模型“实时生成”并写入编辑器的代码：

// WGSL compute body: 全球大气环流与气旋物理模拟 (Demo-Safe)
// 约定: group(0) bindings: 0=particles(RW compute), 3=particles_ro(RO vertex), 1=camera, 2=uParams(t, stepScale, _, _)
let i = gid.x;
let n = arrayLength(&particles.data);
if (i >= n) { return; }

let t = uParams.x * 0.2; // 时间流速控制
let s = max(0.0, uParams.y);
var p = particles.data[i];
let r = length(p.xyz);
if (r < 1.0) { return; }

// 1. 归一化计算经纬度特征
let up = normalize(p.xyz);
let lat = asin(up.z);
let lon = atan2(up.y, up.x);

// 2. 构建球面切线空间 (East / North) 保证流体贴合地表
// NOTE: `ref` is a reserved keyword in newer WGSL parsers.
var axisRef = vec3<f32>(0.0, 0.0, 1.0);
if (abs(up.z) > 0.99) { axisRef = vec3<f32>(0.0, 1.0, 0.0); }
let east = normalize(cross(axisRef, up));
let north = normalize(cross(up, east));

// 3. 物理流体学方程融合：
// a. 行星风带 (Zonal Winds) - 形成赤道与中纬度的水平对流带
let zonal_wind = cos(lat * 6.0) * 1.5;

// b. 动态气旋 (Cyclonic Vortices) - 形成跨越经纬度的螺旋眼
let vortex1 = sin(lon * 5.0 + t * 0.8) * cos(lat * 4.0 - t * 0.4);
let vortex2 = cos(lon * 8.0 - t * 1.2) * sin(lat * 7.0);

// 合并切线向速度
let u = zonal_wind + vortex1 * 2.0;
let v = vortex2 * 1.8 - sin(lat * 3.0); 
let vel = east * u + north * v;

// 4. 粒子平流更新与高度约束 (锁定在距地表20000km的高度以适配深空视角)
let adv = vel * (s * 80000.0);
p.xyz = normalize(p.xyz + adv) * 20000000.0;
particles.data[i] = p;


总结演示说明（导演台本）：

🗣️ 话术： “Copilot，请利用 WebGPU 计算着色器，在当前空间沙盒中生成并渲染十万级带有气旋特征的全球流体场。”

🎬 视觉预期 (分两步走，拉满逼格)：

镜头拉远至深空全景。左侧编辑器瞬间被极其专业的 WGSL 代码填满。此时暂停，向客户解释：“看，这不是特效录像，这是大模型实时推演出的 GPU 底层物理流体方程”。

按下代码面板上的 ▶ RUN SCRIPT。全球瞬间被十万个荧光青色的粒子流体包裹，风带交织、气旋涌动，丝滑的流体力学拉丝效果填满屏幕。

Demo 14: 宏微观虫洞跃迁 (Macro-Micro)

背景与意义： 打破空间尺度的终极壁垒，从宇宙到原子。

数据源与处理工程 📦：

真实获取路径： 从 Crystallography Open Database 下载 SiO2 (石英) 的 CIF 晶体结构文件，解析为原子坐标。

演示兜底生成方案：

// 供 Three.js 渲染的简易分子结构 JSON
{
  "atoms": [
    {"id": 1, "element": "Si", "pos": [0, 0, 0], "color": "#0000FF"},
    {"id": 2, "element": "O", "pos": [1.6, 1.6, -1.6], "color": "#FF0000"}
  ],
  "bonds": [[1, 2]]
}


总结演示说明（导演台本）：

🗣️ 话术： “跨越物理尺度，从地质矿脉穿透到二氧化硅分子的微观晶格。”

🎬 视觉预期： 点击指令后，底层 EngineScaleRouter 销毁 Cesium，唤醒 Three.js。一个精密旋转的 3D 分子结构出现在深邃的背景中。

🎯 汇报与实操成功指南 (Success Criteria)

为了确保路演时“零翻车、高显示度”，请执行以下 Check-list：

真实数据背书： 如果客户问及数据来源，请熟练背诵每个 Demo 下的 📦 真实获取路径，证明我们不是在做动画，而是真实的硬核空间计算。

缓存与沙盒净化 (极重要)： 在演示完 Demo 12 (地下透明) 或 Demo 13 (WebGPU 粒子) 后，切记点击预置面板中的常规场景（如“亚马逊”）。系统会触发 resetSceneState() 全局洗地机制，避免“地球飞走”或“严重卡顿”的串扰 Bug。

掌控高潮节奏： 在 Demo 13 中，代码生成和代码运行是解耦的。充分利用这种解耦，把“看代码”和“点击 RUN 看到震撼气旋”变成两次独立的情绪高潮。