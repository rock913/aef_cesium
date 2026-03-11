Zero2x v7.2：Demo 6-13 核心场景实现与 WebGPU 引擎架构指南

更新时间：2026-03-10

## 当前状态（基于仓库实际落地）

已完成（✅）
- ✅ M0：Demo 11 基础能力与 Copilot tool_call → 引擎执行链路保持稳定。
- ✅ M1：Demo 12 最小闭环：`enable_subsurface_mode` 已打通（透明地球 + 关闭碰撞 + 可选下潜）。
- ✅ M2：Demo 13 最小沙盒骨架：`execute_dynamic_wgsl` 已打通（WGSL 写入编辑区 + WebGPU overlay + `scene.postRender` 同步 + `device.limits` 降级）。
- ✅ v7.2 可逆/清理：`disable_subsurface_mode`、`destroy_webgpu_sandbox` 已打通（退出地下模式、销毁 overlay）。
- ✅ Demo 13 进阶（最小 compute+render）：在 overlay 中增加了 demo-safe 的 compute+render 管线（若动态 WGSL 不兼容会自动回退到内置 WGSL/清屏）。
- ✅ 回归测试已覆盖：后端 `/api/v7/tools` 工具清单包含 v7.2 新工具；前端契约测试锁定 WebGPU overlay 与 postRender 同步策略。
- ✅ 0303 视觉表现力补强已落地：
  - Demo 11：night 模式基础影像可逆调色（Brightness↓、Contrast↑、Hue 冷偏），让轨迹/AI 图层更醒目。
  - Demo 13：stub 增加 `fly_to(~18,000km)`；粒子播种半径升级为 ~20,000km 全局分布；默认粒子颜色改为 Cyan。
  - Demo 12：补齐 `add_subsurface_model` 地下锚点；`fly_to` 支持 `pitch_deg`，并固定顺序 `enable_subsurface_mode` → 下潜 → 锚点。
- ✅ Demo 7（珠峰冰川湖溃决）：已具备“无资源依赖”闭环：`enable_3d_terrain` + `add_cesium_3d_tiles`（stub）+ `add_cesium_water_polygon`（动画洪水面）。
- ✅ Demo 6（塔拉滩光伏蓝海）：已具备“无资源依赖”闭环：后端 stub 下发 inline GeoJSON → `add_cesium_vector` 面元轮廓 + `add_cesium_extruded_polygons(height_property='panel_area')` 拉伸柱，同时下发 `show_chart` 作为统计占位。
- ✅ Demo 8（火山形变×热异常）：已具备“无资源依赖”闭环：后端 stub 发出 `fetch_insar_displacement` + `fetch_lst_anomaly` + `apply_custom_shader` + `generate_cesium_custom_shader`；前端提供 `applyCustomShader()`（优先 Cesium CustomShader，失败则 entity fallback），并会把 shader code 写入编辑区。
- ✅ Demo 9（全球碳汇三维估算）：已具备“无资源依赖”闭环：后端 stub 输出 inline GeoJSON（含 `carbon` 属性）→ 前端 `add_cesium_extruded_polygons(height_property='carbon')` 拉伸体素柱，同时下发 `show_chart` 做指标联动占位。
- ✅ Demo 10（纽约热岛×脆弱性）：已具备“无资源依赖”闭环：后端 stub 下发非空 bivariate grid（bounds/dims/palette/grid）；前端消费 `render_bivariate_map` 并在 Cesium 端绘制矩形网格 overlay（CustomDataSource + Rectangle.fromDegrees），同时 artifacts 侧仍保留 bivariate 占位。
- ✅ 0303 稳定性补强已落地：night 模式不启用物理光照（避免纯黑背光面）；场景切换会触发 resetSceneState（销毁 WebGPU/退出地下/移除 overlays/恢复默认时钟与碰撞），避免“卡顿/黑屏/状态串扰”。
- ✅ Cesium 初始化可靠性补强：修复 `DeveloperError: container is required`（组件在异步初始化途中被卸载/尺度切换导致容器 ref 变空）。策略：`nextTick()` 重试 + `disposed/container` 二次校验，未挂载时直接 abort 不再调用 `new Cesium.Viewer(...)`。
- ✅ 0303“扳机”补齐已落地：Unified Artifacts 的 CODE 面板提供 ▶ RUN SCRIPT 按钮；Workbench 会自动切到 Twin/Earth，并把编辑器内容按特征路由：WGSL → `execute_dynamic_wgsl`，GLSL → `apply_custom_shader`（best-effort），同时会把“未就绪/WebGPU 不可用/未挂载 earth twin”等原因写入报告区，避免无反馈。
  - WGSL 执行采用 WGSL-first：即使脚本只包含 compute（仅 `cs_main`，没有 `vs_main/fs_main`），引擎也会 best-effort 自动补齐最小渲染入口，若仍失败则回退到内置 demo-safe WGSL，避免“执行了但看不到”的假死。
  - 风场/粒子类脚本会走 `preset=wind`：粒子播种更贴近地表半径（surface-like），并提高默认 stepScale，让效果更容易被肉眼捕捉。
  - WebGPU overlay 与 Cesium 相机矩阵对齐：内置模板会自动把 WebGL-style clip space（z ∈ [-1,1]）转换到 WebGPU（z ∈ [0,1]），避免“管线 OK 但全被裁剪看不到”。
  - overlay canvas 默认启用 DPR 尺寸同步与窗口 resize 重配；报告区会显示 `mode/topology/pipeline/particles/verts`，便于定位是否真的在 draw。

下一步（🟡）
- ✅ Demo 13 进阶：已固化“LLM 输出 WGSL 模板”（compute body 可自动 wrap 成完整 WGSL module），让模型生成代码更稳定可执行。
- 🟡 M3：推进 Demo 6-10 场景组装（后续重点：把 stub 替换为真实数据源，并补齐样式与统计口径）。
  - Demo 6：优先接入真实 GeoJSON/Tile，并补齐面积/容量口径与图例。
  - ✅ Demo 10（纽约热岛×脆弱性）：已补齐“地图侧可视化骨架”，`render_bivariate_map` 同步驱动 Cesium overlay + artifacts。

分支与落地记录
- 分支：`patch/0303-v72-phase4`
- 已落地基础闭环提交：`e41fdcb`（v7.2 subsurface + WebGPU tools，TDD）
- 0303 视觉补强：`8bf07fb`（Demo 11/12/13 visual impact）
- Demo 7 竖切片：`bb63aec`（Everest water polygon slice）
- Demo 8 竖切片：`e6a5372`（Volcano custom shader slice + 工具链落地）

本文件作为 v7.2 主版本开发文档（source of truth）。以下规划会以当前仓库实现为基线：
- Workbench 已具备 Copilot tool_call → 前端引擎执行链路（Cesium Twin + 部分 Three Twin）。
- EngineRouter 已具备：夜景模式 `setSceneMode('night')`、CZML 播放 `playCzmlAnimation()`、透明地球 `setGlobeTransparency()`、3DTiles / ExtrudedPolygons 等。

---

0. v7.2 项目规划（结合当前项目现状）

目标：优先落地“高表现、低风险”的 Demo 11/12，并以最小可用沙盒打通 Demo 13 的 WebGPU 叠加框架（Event-Driven Overlay），确保演示稳定与可扩展。

M0（已具备/保持稳定）
- Demo 11 基础能力：夜景模式（赛博暗色底图：imageryLayers 调色；不启用物理光照）+ CZML 时空轨迹（CzmlDataSource + clock.shouldAnimate）。
- Copilot 执行链路：前端可消费 `/api/v7/tools` 工具定义，后端执行返回 events，前端按 tool_call 驱动引擎。

M1（本轮必须完成：Demo 12 “地下模式”最小闭环）
- 新增 Copilot 工具 `enable_subsurface_mode`：
  - 开启地球半透明（alpha-by-distance 或等效策略）
  - 关闭碰撞检测（允许相机穿透/下潜）
  - 可选：依据 `target_depth_meters` 做一次 best-effort 的下潜飞行
- 验收标准：
  - tool_call 能触发引擎进入“地下模式”，即使在缺少模型资源时也不报错、不黑屏。

M2（本轮必须完成：Demo 13 WebGPU 沙盒骨架 + 同步机制）
- 新增 Copilot 工具 `execute_dynamic_wgsl`：
  - 前端将 `wgsl_compute_shader` 写入 Workbench 的代码编辑区（Monaco/Code Stub 区）
  - 引擎挂载 WebGPU Canvas 作为 Cesium 之上的透明叠加层（pointer-events-none）
  - 通过 `viewer.scene.postRender` 做“事件级同步”（避免 rAF 轮询滑步）
  - 做硬件嗅探与平滑降级（device.limits），保证低配机不崩溃
- 验收标准：
  - 不要求立即实现百万粒子完整渲染；但必须保证：
    - 能创建/销毁 WebGPU overlay
    - postRender 同步回调能稳定挂载与解绑
    - 对 WebGPU 不可用环境给出可预期的 fail-safe

M3（后续迭代：逐步完成 Demo 6-10 的“高阶 Cesium 组装”）
- Demo 6：add_cesium_vector + extruded polygons + ECharts（已具备工具与 artifacts 管线，补业务数据与样式）。
- Demo 7/8：3DTerrain + 3DTiles + CustomShader（工具与底层接口已具备，按场景补资源与 shader 片段）。
- Demo 9/10：H3/双变量地图（先以 artifacts + 可视化 stub 交付，后续补真实计算/渲染）。

工具链门控（v7.2 新增）
- `enable_subsurface_mode(transparency, target_depth_meters)`：Demo 12
- `disable_subsurface_mode()`：Demo 12（退出地下模式）
- `execute_dynamic_wgsl(wgsl_compute_shader, particle_count)`：Demo 13
- `destroy_webgpu_sandbox()`：Demo 13（销毁 overlay + 解绑 postRender）

### Demo 13：LLM 输出 WGSL 模板约定（稳定优先）

引擎 `execute_dynamic_wgsl` 接受两种输入：
- ① 完整 WGSL module（包含 entryPoints：`cs_main`/`vs_main`/`fs_main`）
- ② 仅 compute body 片段（不包含 `@compute` / `fn cs_main`），引擎会自动 wrap 成稳定模板

稳定绑定布局（group(0)）：
- binding(0)：`particles`，`var<storage, read_write>`（Compute 用），`array<vec4<f32>>`
- binding(3)：`particles_ro`，`var<storage, read>`（Vertex 用，避免 RW storage 在 Vertex 阶段非法）
- binding(1)：`uCamera`，`var<uniform>`，`view`/`proj` 两个 `mat4x4<f32>`
- binding(2)：`uParams`，`var<uniform>`，`vec4<f32>`：`(t, stepScale, _, _)`

#### 风场 RUN SCRIPT：推荐 compute-only WGSL（可见优先）

说明：下面是一段“仅 compute body”的风场示例（不含 `vs_main/fs_main`）。在 v7.2 中它依然能直接运行：引擎会自动补齐最小渲染入口；若你的脚本不兼容会回退到内置 demo-safe WGSL，并在报告区显示 mode/fallback。

```wgsl
// WGSL compute body snippet: procedural wind on a sphere (demo-safe)
// Requires bindings (group(0)): particles (binding(0) storage rw vec4 array), particles_ro (binding(3) storage read vec4 array), uParams (binding(2) vec4: t, stepScale, _, _)
let i = gid.x;
let n = arrayLength(&particles.data);
if (i >= n) { return; }

let t = uParams.x;
let s = max(0.0, uParams.y);

var p = particles.data[i];
let r = length(p.xyz);
if (r < 1.0) { return; }

let up = normalize(p.xyz);
// NOTE: `ref` is a reserved keyword in newer WGSL parsers.
var axisRef = vec3<f32>(0.0, 0.0, 1.0);
if (abs(up.z) > 0.9) { axisRef = vec3<f32>(0.0, 1.0, 0.0); }
let east = normalize(cross(axisRef, up));
let north = normalize(cross(up, east));

let a = t * 0.55 + f32(i) * 0.00003;
let u = sin(a * 1.30 + up.x * 3.0 + up.y * 2.0);
let v = cos(a * 1.70 + up.y * 3.0 - up.z * 2.0);
let vel = east * u + north * v;

let adv = vel * (s * 40.0);
p.xyz = normalize(p.xyz + adv) * 6700000.0;
particles.data[i] = p;
```

实现约束（稳定优先）
- WebGPU 沙盒必须与 Cesium 渲染解耦（不侵入 Cesium 内部 WebGPU API）。
- 所有新能力必须可降级：WebGPU 不可用时不影响 Cesium 主渲染；地下模式不依赖外部模型也可演示。
- `enable_3d_terrain` 网络依赖说明：Cesium World Terrain 需要可访问 `assets.ion.cesium.com`（以及有效 Ion Token）。若出现 `net::ERR_CONNECTION_RESET`，前端会自动回退到 `EllipsoidTerrainProvider`（属预期兜底）。解决：放通外网/配置代理与 Token；或在离线/受限环境直接不配置 Token 以避免加载尝试与告警。

### 0303 Patch：视觉表现力验收标准（可演示优先）

Demo 11（马六甲暗夜 + 轨迹凸显）
- 验收：触发 `set_scene_mode('night')` 后，底图整体亮度显著压暗、对比度提升，轨迹/AI 图层在大屏上可一眼辨识。
- 实现建议：在 `EngineRouter.setSceneMode('night')` 中对 `viewer.imageryLayers` 做可逆调参（brightness/contrast/hue/saturation/gamma），并在切回 day 时恢复原值。

Demo 13（WebGPU 全局粒子宏大感）
- 验收：执行 Demo 13 预置后相机拉远到地球全景（~18,000km），粒子云覆盖全局且颜色高亮（Cyan），即使粒子数量自适应降级也能看到“包裹地球”的效果。
- 实现建议：后端 stub 在 `write_to_editor/execute_dynamic_wgsl` 前下发一次 `fly_to`；前端 `_seedParticles()` 改为基于球面随机方向的全局播种（半径约 20,000km），默认 shader 颜色改为 Cyan。

Demo 12（地下模式“下潜 + 锚点”）
- 验收：触发“皮尔巴拉/地下/矿脉”类指令后，先进入地下模式（透明地球 + 关闭碰撞），相机以可控仰俯角下潜到负高程，并在地下看到明显的发光锚点实体。
- 实现建议：后端 stub 工具序列固定为 `enable_subsurface_mode` → `fly_to(height<0, pitch_deg=...)` → `add_subsurface_model`；前端 Workbench 放行 `add_subsurface_model`，EngineRouter 以可清理的 entity stub 实现锚点。

---

### 0303 Data-Driven Edition：导演台本与成功指南（合并自 update_patch_0303.md）

本节用于“路演导演台本”，强调：**视窗即现场**、**代码即算力**。

#### Demo 6–10：前沿开拓（空天视界进阶）

Demo 6（塔拉滩光伏治沙与空间统计）
- 数据源（真实）：GEE Sentinel-2 镶嵌；SAM 分割导出 GeoJSON；历年产能统计（财报）。
- 兜底（Mock）：可用网格化多边形 + 随机 `capacity_mw` 的 GeoJSON。
- 导演台词："Copilot，请评估塔拉滩光伏治沙的实际工程量与历年发展趋势。"
- 视觉预期：飞至青海，蓝色面元/拉伸柱拔起；CHARTS 出现历年曲线。

Demo 7（珠峰冰原溃决预警）
- 数据源（真实）：Cesium World Terrain；基于 DEM 水文分析得到淹没 Polygon。
- 兜底（Mock）：手绘山谷走向 polygon。
- 导演台词："基于当前气象参数，模拟珠峰地区高危冰碛湖溃决的潜在淹没范围。"
- 视觉预期：雪山峡谷上出现动态水体多边形，贴地不穿模。

Demo 8（火山形变 × 热异常）
- 数据源（真实）：Sentinel-1 InSAR 位移（GeoTIFF/纹理）；LST 异常栅格。
- 兜底（Mock）：高斯纹理模拟形变。
- 导演台词："叠加 InSAR 形变数据，放大莫纳罗亚火山的‘呼吸’活动。"
- 视觉预期：地表模型出现可辨识的脉动起伏（CustomShader 或 entity fallback）。

Demo 9（全球碳汇三维估算）
- 数据源（真实）：GEDI biomass。
- 兜底（Mock）：H3 k_ring + 随机 `carbon_stock` 输出 GeoJSON。
- 导演台词："对刚果盆地进行 H3 网格化，估算该区域的立体碳汇储量。"
- 视觉预期：六边形柱体拔起，高度代表碳储量。

Demo 10（纽约热岛 × 社会折叠：双变量地图）
- 数据源（真实）：Landsat LST + NYC OpenData Census Tracts。
- 兜底（Mock）：注入负相关的 `income`/`heat` 百分位。
- 导演台词："透视纽约热岛分布与人均收入的折叠关系。"
- 视觉预期：Cesium 端矩形网格 overlay 出现清晰的双色矩阵分布。

#### Demo 11–14：极客炫技（系统级架构张力）

Demo 11（暗夜油污与船舶溯源）
- 数据源（真实）：Sentinel-1 SAR 暗斑；AIS 轨迹（GFW）。
- 兜底（Mock）：最小 CZML 结构（非空）驱动 path。
- 导演台词："马六甲海峡发现可疑油污，调取过去24小时 AIS 轨迹进行碰撞溯源。"
- 视觉预期：夜景压黑 + 橙色油污 + 青色轨迹 + 时间轴播放。

Demo 12（极深地下矿脉解译）
- 概念：Stub = 智能替身（路演稳定优先）。
- 导演台词："剥离澳洲地壳，解译地下4000米的隐伏锂矿层。"
- 视觉预期：半透明玻璃地球 + 相机下潜到负高程 + 地下发光“矿脉根须”锚点（可清理）。

Demo 13（全球流体 WebGPU 热生成）
- 数据源（真实）：NOAA GFS U/V 风速。
- 兜底（MVP）：procedural compute-body + 引擎模板 wrap；失败自动回退 demo-safe WGSL。
- 重要约定（与仓库实现一致）：
  - Vertex 阶段读取 `particles_ro`（group(0) binding(3)）以避免 RW storage 在 Vertex 阶段非法。
  - Debug 可用 `?wgpu_debug=tint|tri|all`，用来验证 overlay 可见性。
- 导演台词："利用 WebGPU 计算着色器，在当前沙盒生成并渲染十万级带气旋特征的全球流体场。"
- 视觉预期：深空全景 + 青色粒子风带/气旋拉丝。

Demo 14（宏微观虫洞跃迁：Macro-Micro）
- 目标：从 Earth → Macro → Micro 的尺度跃迁，强调“系统级架构张力”。
- 推荐工具序列（后端 stub / LLM 都可按此输出）：
  - `trigger_gsap_wormhole(target='micro')`（前端负责动画/过渡层）
  - `switch_scale(target='micro')`（挂载 ThreeTwin micro 场景）
  - `generate_molecular_lattice(type='sio2', count=...)`（触发 micro 场景重建/抖动，作为晶格演示兜底）
- 导演台词："跨越物理尺度，从地质矿脉穿透到二氧化硅分子的微观晶格。"
- 视觉预期：虫洞过渡后进入 micro，出现精密旋转的“分子晶格”风格结构。

#### 成功指南（Success Criteria / 演示 Check-list）

- 真实数据背书：客户追问数据来源时，能对应说明每个 demo 的“真实获取路径”。
- 缓存与沙盒净化（极重要）：演示完 Demo 12/13 后，切换到常规场景（如“亚马逊”）触发 `resetSceneState()`，避免状态串扰（透明地球/WebGPU overlay/碰撞等残留）。
- 高潮节奏控制：Demo 13 强调“看代码”和“运行结果”两段式高潮（生成与执行解耦）。

---

一、 核心底座升级：WebGPU 的引入必要性与双擎架构

在 Demo 1-5 中，我们主要依赖 CesiumJS 的数据加载和基本着色能力。但面对 Demo 12（极深地下体渲染）和 Demo 13（百万粒子流体力学），WebGL 的架构已达到瓶颈。

1.1 WebGPU 的核心必要性与 Cesium 原生适配分析

CesiumJS 的 WebGPU 现状分析：当前 CesiumJS 确实正在进行底层渲染器的重构并初步适配了 WebGPU。但这套底层 API（如 DrawCommand、ComputeCommand 等私有结构）对外部高度封闭且缺乏标准文档。

LLM 隔离沙盒理念 (Sandbox)：大语言模型（如 Qwen）生成图形代码时，最擅长的是输出标准规范的原生 WGSL 和标准的 WebGPU API 样板代码。若强行要求大模型适配 Cesium 未公开的底层 WebGPU 接口，幻觉率会极高，且一旦出错将直接导致整个数字地球引擎崩溃。

GPGPU 通用计算：为了满足 Demo 13 对百万气象粒子流体运动的算力要求，我们需要一套不依赖 Cesium 内部渲染管线的纯粹算力出口。

1.2 优化后的双擎融合架构 (Event-Driven Overlay)

基于上述分析，我们不直接在 Cesium 内部注入 WebGPU 代码，而是采用**“DOM 叠加 + 事件级渲染同步”**的优化沙盒方案：

底层由 Cesium 渲染地球（DOM 层级低），表层覆盖一个透明的独立 WebGPU Canvas（DOM 层级高）。优化点： 摒弃前端常规的 requestAnimationFrame 轮询，改用监听 Cesium 底层的 scene.postRender 事件进行相机矩阵注入。这样既保证了 LLM 运行环境的纯洁性和安全性，又实现了视觉上的“零延迟、无滑步”完美融合。

二、 Demo 6~11：空天视界的前沿开拓 (Cesium 原生进阶)

这一阵列主要挑战在于 Cesium 高级 API (3D Tiles, CustomShader, CZML) 的动态组装。

Demo 6: 塔拉滩光伏 (荒漠化治理与面积计算)

技术栈: Cesium GeoJSON + 面元拉伸 + 聚合计算。

实现细节:

Copilot 下发 add_cesium_vector({url: 'talatan.geojson', extruded: true})。

提取光伏板多边形，基于属性 panel_area 设定面元高度或颜色。

触发左侧 Unified Artifacts 挂载 ECharts 面板，展示历年装机容量折线图。

Demo 7: 冰原溃决预警 (珠峰)

技术栈: 3D Terrain + 高精度 3DTiles + 动态水体材质 (Fabric)。

实现细节:

// 伪代码：激活地形与水体材质
viewer.terrainProvider = await Cesium.createWorldTerrainAsync();
const tileset = await Cesium.Cesium3DTileset.fromUrl('path/to/everest.json');
viewer.scene.primitives.add(tileset);

// 创建动态流水面
const floodPolygon = viewer.entities.add({
  polygon: {
    hierarchy: Cesium.Cartesian3.fromDegreesArray([...]),
    material: new Cesium.Material({
      fabric: { type: 'Water', uniforms: { normalMap: 'waterNormals.jpg', frequency: 1000.0, animationSpeed: 0.05, amplitude: 10.0 } }
    })
  }
});


Demo 8: 地壳形变与火山预判 (夏威夷)

技术栈: Cesium CustomShader API (顶点位移)。

实现细节: 加载火山区域的 3DTiles，将 InSAR 形变数据作为纹理传入 Shader。在 Vertex Shader 中，沿法线方向动态拉伸顶点，让微小的形变在视觉上产生夸张效果。

const deformationShader = new Cesium.CustomShader({
  uniforms: { u_insarMap: { type: Cesium.UniformType.SAMPLER_2D, value: insarTexture } },
  vertexShaderText: `
    void vertexMain(VertexInput vsInput, inout czm_modelVertexOutput vsOutput) {
      float disp = texture2D(u_insarMap, vsInput.attributes.st).r;
      vsOutput.positionMC += vsInput.attributes.normalMC * (disp * 50.0); // 夸张50倍
    }
  `
});
tileset.customShader = deformationShader;


Demo 9: 全球碳汇三维估算 (刚果)

实现细节: 六边形网格 (H3) 聚合。利用 Cesium.Entity 批量生成六边形柱体，extrudedHeight 绑定碳储量估算值，使用绿-黄-红的色谱表示健康度。

Demo 10: 城市热岛与社会折叠 (纽约)

技术栈: 双变量地图 (Bivariate Choropleth)。

实现细节: Shader 中混合两个维度的数据（如温度和平均收入）。定义一个 3x3 的 Color Matrix，在 Fragment Shader 中根据两个归一化指标的相交点去矩阵中采样颜色。

Demo 11: 暗夜油污与船舶溯源 (马六甲)

技术栈: 夜景模式 + CZML 时空轨迹。

实现细节:

调用 `set_scene_mode('night')` 进入赛博暗夜模式：通过 `imageryLayers` 做可逆调参（brightness/contrast/hue/saturation/gamma），并保持 `viewer.scene.globe.enableLighting = false`（避免“背光面纯黑”）。

加载包含船舶 AIS 数据的 CZML（演示可直接用 stub CZML 数组，确保非空）。

唤起 v7.2 的底部动态时间轴 (TimelineWidget)，驱动 CZML 动画播放。

三、 Demo 12~13：极客炫技 (WebGPU 空间计算引入)

这里是 Zero2x 展现“代码即算力”肌肉的核心区域，依赖 Vue 组件动态挂载执行层。

Demo 12: 极深地下矿脉解译 (澳洲)

视觉目标: 地表半透明，向下透视看到树根般的矿脉模型或体素（Voxel）云。

技术路线: Cesium 地球半透明 + 地下深度渲染。

核心伪代码:

// 1. 开启地球透明度并消除背面剔除
viewer.scene.globe.translucency.enabled = true;
viewer.scene.globe.translucency.frontFaceAlphaByDistance = new Cesium.NearFarScalar(1000.0, 0.2, 50000.0, 1.0);
viewer.scene.screenSpaceCameraController.enableCollisionDetection = false; // 允许相机钻入地下

// 2. 加载矿脉模型 (glTF) 并放置在负海拔
const position = Cesium.Cartesian3.fromDegrees(120.0, -25.0, -5000.0); // 地下5公里
viewer.entities.add({
  position: position,
  model: { uri: 'mineral_veins.glb', color: Cesium.Color.GOLD.withAlpha(0.8) }
});


🌟 Demo 13: 气象流体力学代码热生成 (Global)

业务流: 用户输入指令 -> Copilot 使用 LLM 生成一段包含 Compute Shader 的逻辑 -> 写入左侧 Monaco Editor -> 系统动态挂载一个全屏 WebGPU Canvas 叠加在 Cesium 上并执行代码。

自适应硬件兼容策略 (Adaptive Degradation): 为了保证演示在各类设备（从轻薄本到搭载独立显卡的台式机）上的绝对稳定性，系统在初始化 WebGPU Device 时会嗅探硬件物理上限 (device.limits)。根据最大计算工作组容量和存储缓冲区限制，系统会动态切分并发任务，或将展示精度（如粒子并发数）平滑降级，确保大屏演示永不卡死。

优化后的严格同步框架 (Event-Driven WebGPU Overlay):

<!-- EngineRouter.vue -->
<template>
  <div class="relative w-full h-full">
    <CesiumBase id="cesium-container" />
    <!-- WebGPU 沙盒层 -->
    <canvas v-if="showWebGPU" ref="gpuCanvas" class="absolute inset-0 pointer-events-none z-30"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const showWebGPU = ref(false);
const gpuCanvas = ref(null);
let renderSyncCallback = null;

// 供 Copilot 调用的 API：注入热生成的 WGSL 代码并运行
async function executeHotGeneratedFluid(wgslCode) {
  showWebGPU.value = true;
  await nextTick();

  const adapter = await navigator.gpu.requestAdapter();

  // 🛡️ 硬件嗅探：尝试请求具有最佳性能的设备属性
  const device = await adapter.requestDevice();
  const context = gpuCanvas.value.getContext('webgpu');

  // 🛡️ 动态负载与降级计算 (Adaptive Limits)
  // 目标预设：渲染一百万个气象粒子
  let particleCount = 1000000; 
  const maxStorageBuffer = device.limits.maxStorageBufferBindingSize;
  const maxComputeInvocations = device.limits.maxComputeInvocationsPerWorkgroup;

  // 假设每个粒子包含 4个Float32 (pos, vel) = 16 bytes
  const requiredBufferSize = particleCount * 16; 

  // 如果设备显存 buffer 限制过小（常见于核显）或者工作组调用量受限，执行平滑降级
  if (requiredBufferSize > maxStorageBuffer || maxComputeInvocations < 256) {
      particleCount = Math.floor(maxStorageBuffer / 16 * 0.8); // 保留20%显存余量
      particleCount = Math.min(particleCount, 200000); // 设定硬上限为20万，保障核显帧率
      console.warn(`[Zero2x WebGPU Sandbox] 探测到轻量级 GPU，粒子并发量自适应降级为: ${particleCount}`);
  }

  // ... 根据调整后的 particleCount 配置 WebGPU Pipeline 与 Buffer 分配

  // 创建 Compute Pipeline (此处由 LLM 热生成的标准 WGSL 代码构成)
  const computeModule = device.createShaderModule({ code: wgslCode });
  // ...

    const viewer = window.cesiumViewer;

    // 关键优化：不使用 requestAnimationFrame，而是挂载到 Cesium 的原生渲染后置钩子
    // 确保两者的视角矩阵在同一帧完全咬合，避免拖拽时的滑步视觉差
    renderSyncCallback = viewer.scene.postRender.addEventListener(() => {
      const viewMatrix = viewer.camera.viewMatrix;
      const projMatrix = viewer.camera.frustum.projectionMatrix;

      // 更新 WebGPU 的 Uniform Buffer
      updateCameraUniforms(device, viewMatrix, projMatrix);

      // 触发 WebGPU Compute Pass (更新粒子) & Render Pass (绘制粒子)
      // executeWebGPUPass(device, context);
    });
  }

  // 清理逻辑
  function destroyWebGPUSandbox() {
    if (renderSyncCallback && window.cesiumViewer) {
      window.cesiumViewer.scene.postRender.removeEventListener(renderSyncCallback);
    }
    showWebGPU.value = false;
  }
  </script>


四、 整合：工具链门控 (Tool Definitions)

为了让 Qwen 大模型能够精确理解并触发这些复杂的混合渲染管线，需要将这些能力封装为结构化的 Tools。

// tools_registry.js (供 Qwen 调用的 Function Schema)

export const ZERO2X_TOOLS = [
  // ... 之前的 aef_compute_diff 等
  
  {
    type: "function",
    function: {
      name: "enable_subsurface_mode",
      description: "开启地下矿脉/地壳探测模式，使地表半透明并允许相机穿透。",
      parameters: {
        type: "object",
        properties: {
          transparency: { type: "number", description: "地表透明度 0.0-1.0" },
          target_depth_meters: { type: "number", description: "下潜深度" }
        }
      }
    }
  },
  {
    type: "function",
    function: {
      name: "execute_dynamic_wgsl",
      description: "当用户要求实时流体力学或复杂粒子渲染时，执行大模型生成的 WebGPU WGSL 代码。",
      parameters: {
        type: "object",
        properties: {
          wgsl_compute_shader: { type: "string", description: "生成的计算着色器代码" },
          particle_count: { type: "number", description: "生成粒子的数量级" }
        },
        required: ["wgsl_compute_shader"]
      }
    }
  }
];


开发落地建议路径：

优先攻坚 Demo 11 与 Demo 12：这两个场景极具视觉表现力，且完全依赖 Cesium 原生 API（光照、透明度、深度测试），开发成本可控，能迅速提升演示逼格。

渐进式实现 Demo 13：初期为了保证演示绝对稳定，可采用“伪热生成”（前端预埋并监听 scene.postRender 的成熟代码，表面上大模型生成代码，实则触发预置逻辑）。待事件级沙盒机制彻底完善后，再将 device.createShaderModule 的入参彻底交还给 LLM 的动态字符串。