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

💡 概念核心：什么是 Stub (存根) 与如何利用它？

释义： 什么是 Stub？在极高规格的 ToB 路演中，Stub 是一种“合法的智能替身”。例如，真实的高光谱体积解混（Hyperspectral Voxel Unmixing）在后端 PyTorch 集群上可能需要跑 30 分钟。在 3 分钟的汇报现场，这是不允许的。因此，系统会“佯装”执行完毕，并由 Copilot 直接调度一个预先生成好的、极具视觉冲击力的渲染结果（即 Stub）。它既能保障演示 100% 成功，也能完美传达产品的业务逻辑与技术远景。

高阶视觉演进 (Voxel Cloud)：
目前使用椭球体显得有些廉价。为了强化“深层数据体素”的质感，前端应渲染密集的**“发光体素点云”**作为 Stub。

前端 Stub 高阶渲染伪代码（基于 PointPrimitiveCollection）：

// 引擎层高阶地下锚点：生成赛博朋克风的高光谱体素点云
const points = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());
for(let i=0; i<5000; i++) {
    const lat = -22.3 + (Math.random() - 0.5) * 0.05;
    const lon = 118.7 + (Math.random() - 0.5) * 0.05;
    const depth = -3800.0 - Math.random() * 1000.0;
    points.add({
        position: Cesium.Cartesian3.fromDegrees(lon, lat, depth),
        color: Cesium.Color.fromCssColorString('#FF4D6D').withAlpha(0.8),
        pixelSize: 4.0, // 形成致密的点云矿脉
        disableDepthTestDistance: Number.POSITIVE_INFINITY
    });
}


总结演示说明（导演台本）：

🗣️ 话术： “对我们而言，地表已无秘密可言。剥离澳洲地壳，调用高光谱解混算子，直接透视地下4000米的隐伏锂矿分布层。”

🎬 视觉预期： 地球瞬间变成半透明玻璃态，镜头如钻探机般直降地下 -4500m。抬头仰望，漆黑深渊中悬浮着由数千个闪耀红光的高光谱数据点构成的庞大矿脉网络（高阶 Stub）。全场惊艳，秒杀传统平面 GIS。

🚀 第三阵列：极客炫技 (系统级架构张力)

🌟🌟🌟 Demo 13: 全球流体与 WebGPU 代码热生成 (架构巅峰)

背景与意义： 完美诠释“Code as Compute”。摒弃枯燥的噪点聚集，这次大模型将实时写出兼具“粒子生命周期 (Lifecycle)”与“无散度流函数 (Curl of Stream Function)”的工业级全管线 Shader，并在显卡上直接编译运行。

💡 究极演示方案：全管线接管 (Full Pipeline Override WGSL)
注：由于该脚本提供了完整的 @vertex 和 @fragment，引擎不再将其当作残缺片段，而是完全交出显卡控制权。
请将下方脚本置入 v7_copilot.py 中用于下发给编辑器：

// WGSL Full Pipeline: 宏观流体力学与生命周期管理
struct Camera { view: mat4x4<f32>, proj: mat4x4<f32> }
struct Particles { data: array<vec4<f32>> }
@group(0) @binding(0) var<storage, read_write> particles: Particles;
@group(0) @binding(3) var<storage, read> particles_ro: Particles;
@group(0) @binding(1) var<uniform> uCamera: Camera;
@group(0) @binding(2) var<uniform> uParams: vec4<f32>;

// 伪随机哈希，用于打散生命周期
fn hash(n: f32) -> f32 { return fract(sin(n) * 43758.5453123); }

// 三维流函数 (Stream Function) 叠加，导数即为无散度流场 (Divergence-Free)
fn stream(p: vec3<f32>, t: f32) -> f32 {
    var f = 0.0;
    f += sin(p.x * 4.0 + t) * cos(p.y * 4.0 - t) * 1.0;
    f += sin(p.y * 7.0 - t * 1.2) * cos(p.z * 7.0 + t * 0.8) * 0.5;
    f += sin(p.z * 12.0 + t * 1.5) * cos(p.x * 12.0 - t * 1.1) * 0.25;
    return f;
}

@compute @workgroup_size(256)
fn cs_main(@builtin(global_invocation_id) gid: vec3<u32>) {
    let i = gid.x;
    if (i >= arrayLength(&particles.data)) { return; }

    let t = uParams.x * 0.15; // 全局时钟
    let dt = max(0.001, uParams.y * 0.016);
    var p = particles.data[i];

    // 核心进化 1：粒子寿命衰减 (p.w 从 1.0 降至 0.0)
    p.w -= dt * (0.1 + hash(f32(i)) * 0.2);

    // 核心进化 2：生死轮回 (Respawn)，产生源源不断的流线感
    if (p.w <= 0.0 || length(p.xyz) < 1.0) {
        p.w = 1.0;
        let seed = f32(i) + t;
        let phi = hash(seed) * 6.2831853;
        let costheta = hash(seed * 1.5) * 2.0 - 1.0;
        let theta = acos(costheta);
        p.x = sin(theta) * cos(phi);
        p.y = sin(theta) * sin(phi);
        p.z = cos(theta);
        p.xyz = normalize(p.xyz) * 20000000.0;
    }

    let pos = normalize(p.xyz);

    // 数值求偏导获取旋度 (Curl)，确保粒子绝对顺滑流动，不扎堆
    let eps = 0.02;
    let dx = stream(pos + vec3(eps,0.,0.), t) - stream(pos - vec3(eps,0.,0.), t);
    let dy = stream(pos + vec3(0.,eps,0.), t) - stream(pos - vec3(0.,eps,0.), t);
    let dz = stream(pos + vec3(0.,0.,eps), t) - stream(pos - vec3(0.,0.,eps), t);
    var vel = cross(pos, vec3<f32>(dx, dy, dz) / (2.0 * eps)); 

    // 叠加纬向急流 (Zonal Jet Stream)
    let jet = cross(vec3<f32>(0.,0.,1.), pos) * cos(pos.z * 6.0) * 1.5;
    vel = vel + jet;

    // 切线平流并固化在球壳表面
    p.xyz = normalize(p.xyz + vel * (dt * 15.0)) * 20000000.0;
    particles.data[i] = p;
}

struct VSOut {
    @builtin(position) pos: vec4<f32>,
    @location(0) color: vec4<f32>
}

@vertex
fn vs_main(@builtin(vertex_index) vid: u32) -> VSOut {
    // NOTE: Vertex stage must not read RW storage buffers.
    // Use the engine-provided read-only alias at binding(3).
    let p = particles_ro.data[vid];
    var out: VSOut;
    out.pos = uCamera.proj * uCamera.view * vec4<f32>(p.xyz, 1.0);

    // 核心进化 3：基于寿命的淡入淡出，消除屏幕闪烁噪点
    let alpha = smoothstep(0.0, 0.2, p.w) * smoothstep(1.0, 0.8, p.w);

    // 核心进化 4：空间色彩映射 (赤道青色，极地紫红)
    let lat = abs(normalize(p.xyz).z);
    let cWarm = vec3<f32>(0.0, 0.95, 1.0);
    let cCool = vec3<f32>(0.6, 0.1, 0.9);
    out.color = vec4<f32>(mix(cWarm, cCool, lat), alpha * 0.8);
    return out;
}

@fragment
fn fs_main(in: VSOut) -> @location(0) vec4<f32> { return in.color; }


总结演示说明（导演台本）：

🗣️ 话术： “Copilot，请通过 WebGPU 计算着色器，构建具备无散度流函数与生命周期管理算法的全球气象流场。”

🎬 视觉预期 (极其震撼)：

镜头拉远。编辑器瞬间被极其专业的 WGSL 全管线代码 填满。此时暂停，指着代码解释：“看，这不是调用动画 API，这是大模型实时推演出的 GPU 底层物理矩阵”。

按下 ▶ RUN SCRIPT。整个屏幕瞬间安静，紧接着，十万级带有彗星拖尾的荧光粒子流从无到有逐渐涌现。赤道区域呈现明亮的青色急流，高纬度区域盘绕着紫色的庞大涡旋。粒子生生灭灭，形成令人窒息的流体力学之美。

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