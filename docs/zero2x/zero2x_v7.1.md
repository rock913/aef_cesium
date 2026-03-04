Zero2x 021 v7：Copilot 驱动的空间交互与核心场景开发蓝图

修订目标：全面转向以 "AI Copilot Chat" 为交互中枢、以 "统一资产面板" 为物料收纳的现代 IDE 布局。同时，针对所有演示场景，提供从数据源、API 接口到大模型工具调用（Tool Calling）的完整技术实现细节。

---

## 状态更新（As-built，截止 2026-03-05）

本文件仍是 v7.1 的“验收规范 + 开发蓝图”，但当前仓库已经落地了一套可运行的 **v7.1 最小闭环（MVP）**：

### 已完成（可运行 + 有门禁）

**UI / 交互（前端）**

- 右侧 Copilot Chat 已按 v7.1 伪代码完成三段式结构：Header / Chat History / Input Zone（chips 紧贴 textarea 上方，气泡左右分离，CoT 手风琴可折叠，busy 结束自动折叠并显示耗时）。
- HUD overlay 默认 `pointer-events: none`，面板选择性 `pointer-events: auto`，保证 Twin（Cesium/Three）可拖拽交互（不再被透明层吃事件）。

**Demo 全覆盖（12+2 = 14）**

- 前端场景注册已覆盖 14 个 demo context（含新增 Demo 13 `global`），避免“context 不存在 -> fallback 乱跳”类问题。
- Backend v7 Copilot stub：`/api/v7/prompts` 已提供 **>= 14** 个 prompt chips；`/api/v7/tools` 已注册一组“地学工具 + UI 工具”；`/api/v7/copilot/execute` 对 14 个 demo 做了确定性 keyword 路由并返回 tool-calling events。

**TDD 门禁（已启用）**

- 前端 Vitest：
  - CopilotChatPanel v7.1 UI 结构回归测试（header/history/input-zone + chips 顺序 + bubble/accordion）。
  - 场景注册回归测试（核心 demo + yancheng/zhoukou/global 等）。
- 后端 Pytest：
  - v7 Copilot 合同测试：prompts 数量、关键工具存在性、Demo 13 code-gen 会触发 `write_to_editor`。

**工具调用 → 结构化产物（Phase 1 最小闭环已落地）**

- 后端 v7 `/api/v7/tools` 已补齐 UI 工具定义：`add_cesium_imagery` / `add_cesium_vector` / `show_chart` / `render_bivariate_map` / `generate_report` / `write_to_editor` / `execute_editor_code`。
- 后端 v7 `/api/v7/copilot/execute`（stub 路由）对 Demo 1–3 + NYC 已发出上述 UI 工具事件，使前端可以稳定落产物。
- 前端已实现可测试的纯函数映射层，把 tool events 写入 Unified Artifacts（Layers/Charts/Reports/Code），并在 Cesium Earth scale 支持：
  - `ai-imagery`：支持直接使用 `tile_url`（UrlTemplateImageryProvider）挂载 overlay。
  - `ai-vector`：支持将 GeoJSON 作为 DataSource 挂载并在 LayerTree 开关。
- TDD：前端 Vitest 覆盖 tool→artifacts 映射；后端 Pytest 合同测试覆盖关键 demo 的 tool emissions（imagery/vector/charts）。

### 当前差距（仍是 stub / 未打通的真实链路）

- **真实计算链路仍未打通**：
  - 当前 Demo 1–3/NYC 的 UI 工具事件仍主要用于验证闭环（如示例 tile_url、示例 geojson、空 points/grid）。
  - 与既有 `/api/v1/...`（如 compute_diff/cluster/stats/report）尚未串联。
- **地学/渲染特效工具未落地**：
  - terrain、custom shader、night mode、CZML 动画、3D tiles、subsurface/voxel 等仍处于蓝图层面（工具已命名但没有 UI/引擎侧的可视化实现）。

---

## 下一步计划（按 v7.1 验收点推进，强制 TDD）

目标：把“Copilot tool-calling events”变成 **确定性的 UI 产物**（Layers/Charts/Reports/Code），并让 Demo 1–3 先闭环，再逐步铺满 14 个 demo 的渲染能力。

### Phase 1（已完成：工具 → Unified Artifacts 最小闭环）

**1) 统一事件协议（前后端）**

- 固化 v7 事件结构：`tool_call` / `tool_result` 的 `args/result` schema（先从 UI 工具开始）。
- 在后端 `GET /api/v7/tools` 中补齐 UI 工具定义（至少：`add_cesium_imagery`、`add_cesium_vector`、`show_chart`、`render_bivariate_map`、`generate_report`、`write_to_editor`）。✅

**2) 前端 applyCopilotEvents：把工具写入“结构化资产”**

- `add_cesium_imagery` → 写入 LayerTree（含 palette/threshold/opacity 等参数）并立即在 Cesium Twin 生效。✅
- `add_cesium_vector` → 写入一个 vector layer（GeoJSON）并可在 LayerTree 开关。✅
- `show_chart` / `render_bivariate_map` → 写入 Charts tab 的稳定数据集（当前为 JSON 预览占位）。✅
- `generate_report` → 写入 Reports tab（Markdown）。✅

**TDD（前端门禁）**

- 新增 Vitest：给定一组 tool events，断言 LayerTree/Charts/Reports/Code 的 state 发生预期变化（不跑 Cesium 引擎也能测）。✅

### Phase 2：Demo 1–3 真实打通（先 Earth scale）

- Demo 1/3：`aef_compute_diff` 走既有 `/api/v1/aef/compute_diff`（或现有后端已有等价端点），拿到 tile url 后触发 `add_cesium_imagery`。
- Demo 2：`aef_kmeans_cluster` 走 `/api/v1/aef/cluster`，拿到 geojson 后触发 `add_cesium_vector`。
- 产物同步：同时生成 `generate_report`（引用 stats/差异面积/置信度等字段），写入 Reports。

**TDD（后端门禁）**

- Pytest 合同测试升级：
  - `execute` 返回的 events 必须包含 `add_cesium_imagery/add_cesium_vector/generate_report`（对应 demo）。
  - 当外部依赖不可用（如 GEE 未初始化）时，仍需返回“可解释的降级事件”（例如 final + report 提示），保持 UI 可用与确定性。

### Phase 3：补齐剩余 Demo 的“可视化最低可用实现（MVR）”

- Demo 4–12：优先落地“可见的 UI 效果”，再逐步替换为真实算法：
  - polyline / extruded polygons / czml time animation / globe transparency / custom shader（可以先用占位实现，但 UI 与参数要固定）。
- Demo 13：code-gen 从 stub 走向“可运行脚本”：
  - 先把 `execute_editor_code` 变成“安全的 UI 执行器”（允许限定 API 的 sandbox），再接入真实 GFS 数据纹理。
- Demo 14：把 wormhole + scale 切换 + lattice 生成串成“观感闭环”（已具备基础能力，重点补 UI 工具与产物侧栏切换）。

---

## 当前验收定义（对齐 v7.1）

- UI：右侧 Chat 必须是气泡 + CoT 手风琴 + chips 紧贴输入框；中央 Twin 可交互拖拽；左侧产物面板能承接 code/report/chart/layer。
- Demo：14 个 prompt chips 点击后，**至少**触发稳定的飞行/缩放与一组可视化产物写入（哪怕产物为 stub，但结构与落点必须稳定）。
- TDD：前端 Vitest 与后端 Pytest 合同测试必须覆盖上述最低闭环，不允许回归。

一、 UI 架构重构：Copilot 驱动的“空间 IDE”布局

摒弃当前浮动且重叠的面板，采用严格的 “左-中-右”流式网格系统。

1. 右侧中枢：021 Copilot Chat (动态对话与任务规划栏)

位置：屏幕最右侧，宽度约 400px，高度 100vh，右侧边栏（可折叠 Collapse）。
设计灵感：GitHub Copilot Chat / Cursor IDE / ChatGPT。
视觉与交互重构指南：
彻底告别“静态仪表盘”感，划分为界限分明的上、中、下三个区域：

Top: 面板头部 (Header)

左侧显示标题 021 COPILOT，右侧提供明确的折叠/展开按钮 [⇥ Collapse]，允许用户随时收起侧边栏，将全屏空间还给地球视窗。

Middle: 对话流与动态卡片区 (Message History)

气泡式对话：用户的输入与 AI 的回复必须以“对话气泡（Chat Bubbles）”区分。用户在右，AI 在左。

折叠式思维链 (Collapsible CoT)：AI 的思考过程（如 [调用工具] aef_zero_shot_kmeans）封装在可折叠的 Accordion（手风琴组件）中。执行时展开，执行完毕自动折叠为 ✓ 分析完成 (耗时 3.2s)。

Bottom: 沉浸式指令输入区 (Input Zone) - 核心优化点

贴地悬浮：固定在屏幕最底部，采用悬浮磨砂质感。

Prompt Gallery (预置指令胶囊)：必须紧贴在文本输入框的正上方，采用横向滚动的单行横排设计。点击任意胶囊，自动填入输入框并发送。

💡 附加：右侧 Chat UI 结构伪代码 (供前端直接参考)

<template>
  <div class="copilot-sidebar w-[400px] h-screen flex flex-col bg-gray-900/90 backdrop-blur-md border-l border-white/10">
    <!-- Top: Header -->
    <div class="header h-14 flex justify-between items-center px-4 border-b border-white/10">
      <span class="font-bold text-white tracking-widest">021 COPILOT</span>
      <button @click="collapse" class="text-gray-400 hover:text-white">⇥ Collapse</button>
    </div>

    <!-- Middle: Chat History (Scrollable) -->
    <div class="chat-history flex-1 overflow-y-auto p-4 space-y-4">
      <!-- User Bubble -->
      <div class="user-bubble ml-auto bg-blue-600 text-white p-3 rounded-lg max-w-[85%]">...</div>
      <!-- AI CoT Accordion -->
      <div class="ai-cot-accordion bg-black/30 border border-white/5 rounded p-2 text-sm text-gray-400">
        <details><summary>✓ 分析完成 (耗时 3.2s)</summary>...调用过程...</details>
      </div>
    </div>

    <!-- Bottom: Input Zone -->
    <div class="input-zone p-4 bg-gray-900 border-t border-white/10 flex flex-col gap-2">
      <!-- 🌟 Prompt Chips: 紧贴输入框上方 -->
      <div class="prompt-chips flex overflow-x-auto pb-1 hide-scrollbar gap-2">
        <button class="chip px-3 py-1 bg-white/5 hover:bg-white/10 rounded-full whitespace-nowrap text-xs text-cyan-400">✨ 余杭城建审计</button>
        <button class="chip px-3 py-1 bg-white/5 hover:bg-white/10 rounded-full whitespace-nowrap text-xs text-cyan-400">✨ 亚马逊聚类</button>
      </div>
      <!-- Textarea & Send -->
      <div class="relative">
        <textarea class="w-full bg-black/50 border border-white/20 rounded-lg pl-3 pr-10 py-3 text-white" rows="2" placeholder="输入自然语言指令..."></textarea>
        <button class="absolute right-2 bottom-3 text-cyan-400">↑</button>
      </div>
    </div>
  </div>
</template>


2. 左侧仓库：统一资产与产物面板 (Unified Artifacts Tab)

位置：屏幕最左侧，宽度约 360px。

Tab 1: 🗂️ LAYER & DATA：管理 GEE 瓦片图层，精细化调节 AlphaEarth 渲染管线的阈值与色标。

Tab 2: 💻 CODE & SCRIPT：收纳 Monaco Editor。展示 AI 生成的 Python 处理代码或 GLSL 渲染着色器。支持热重载。

Tab 3: 📊 CHARTS & STATS：展示基于 AlphaEarth 数据生成的 2D Echarts 统计图表。

Tab 4: 📝 REPORTS：展示最终生成的结构化 Markdown 研判报告，支持导出 PDF。

3. 中央视窗：无界空间底座 (The Twin Canvas)

位置：Flex 布局撑满剩余空间。彻底去边框化，仅保留极简的 Scale Toggle (Earth/Macro/Micro)。

二、 核心 Demo 场景大盘与技术实现细节 (12+2 全矩阵)

为了让大模型 (GeoGPT) 能够执行这些复杂的空间计算，系统后端需要向 LLM 注册一套 工具函数 (Tools/Functions)。以下的伪代码即代表 LLM 决定调用的工具序列。

🌍 第一阵列：经典传承 (OneEarth 6 大核心场景)

Demo 1: 沧海桑田的城建审计

定位点：浙江杭州 · 余杭未来科技城

预置指令 (Prompt)："对比余杭近7年的城建扩张，使用欧氏距离算子，生成城建审计图层。"

开发技术规范：

数据源：AEF Embeddings (A00 维 人造物特征), Sentinel-2 光学底图。

API 接口：POST /api/v1/aef/compute_diff

Payload: { "roi": "yuhang", "years": [2017, 2024], "metric": "euclidean", "dim": "A00" }

Copilot 执行流 (伪代码)：

await ui.fly_to(coords=[30.26, 119.92], zoom=13)
diff_layer = await tools.call('aef_compute_diff', roi='yuhang', years=[2017,2024], metric='euclidean')
await ui.add_cesium_imagery(diff_layer.tile_url, palette='Oranges', threshold=0.4)
await ui.generate_report("城建突变面积达 40.2%，高度集中在核心区。")


可视化震撼点：高亮橙色瞬间提取出隐伏在绿地下的硬化地表扩张。

Demo 2: 行星级零样本聚类 (无监督发现)

定位点：巴西 · 亚马逊雨林

预置指令 (Prompt)："扫描当前视窗，不使用先验标签，根据 AlphaEarth 64维特征进行零样本聚类(k=6)，找出毁林区。"

开发技术规范：

数据源：AEF 64-Dim 完整隐空间向量。

API 接口：POST /api/v1/aef/cluster

Copilot 执行流 (伪代码)：

current_bbox = await ui.get_camera_bbox()
cluster_result = await tools.call('aef_kmeans_cluster', bbox=current_bbox, k=6, use_dims='all')
await ui.add_cesium_vector(cluster_result.geojson, color_map='category_6')


Demo 3: 剥离季节伪装的生态穿透

定位点：陕西 · 毛乌素沙地

预置指令 (Prompt)："评估毛乌素沙地近5年真实治理成效，摒弃欧氏距离，改用余弦相似度以排除秋冬植被枯黄干扰。"

开发技术规范：

数据源：AEF Embeddings (A01 维 三维生物量), 秋冬时相卫星图。

API 接口：POST /api/v1/aef/compute_diff

Payload: { "metric": "cosine_similarity" }

Copilot 执行流 (伪代码)：

await ui.fly_to(coords=[38.5, 109.2], zoom=10)
real_growth = await tools.call('aef_compute_diff', roi='maowusu', years=[2019,2024], metric='cosine_similarity')
await ui.add_cesium_imagery(real_growth.tile_url, palette='Greens')


Demo 4: 海岸线红线智能划界

定位点：江苏盐城 · 湿地海岸线

预置指令 (Prompt)："基于 AEF 16维特征，使用随机森林，划分自然滩涂与人工海堤的边界红线。"

开发技术规范：

数据源：AEF Top-16 Dims, 历史海岸线标定数据。

Copilot 执行流 (伪代码)：

await ui.fly_to(coords=[33.6, 120.5], zoom=11)
boundary_lines = await tools.call('aef_supervised_boundary_extraction', model='random_forest', target='coastline')
await ui.add_cesium_polyline(boundary_lines, colors={'natural': 'blue', 'artificial': 'red'})


Demo 5: 农田内涝隐形危机预警

定位点：河南 · 周口农田

预置指令 (Prompt)："近期极端降雨，利用介电常数特征，扫描光学表象下农作物根系的隐形水灾风险。"

开发技术规范：

数据源：AEF Embeddings (A02 维 介电常数/微波SAR融合)。

Copilot 执行流 (伪代码)：

water_stress = await tools.call('aef_extract_feature', roi='zhoukou', dim='A02')
await ui.add_cesium_imagery(water_stress.tile_url, palette='Purples', opacity=0.7)


Demo 6: 光伏蓝海与生态修复伴生网络

定位点：青海 · 塔拉滩光伏产业园

预置指令 (Prompt)："提取太阳能面板铺设区，并与植被恢复（生物量）特征层进行空间共现性计算。"

开发技术规范：

API 接口：POST /api/v1/aef/spatial_co_occurrence

Copilot 执行流 (伪代码)：

pv_layer = await tools.call('aef_extract_feature', dim='A00_solar')
bio_layer = await tools.call('aef_extract_feature', dim='A01_biomass')
co_matrix = await tools.call('calculate_co_occurrence', layer1=pv_layer, layer2=bio_layer)
await ui.render_bivariate_map(co_matrix)


🚀 第二阵列：前沿开拓 (Zero2x 6 大全新地学场景)

Demo 7: 冰原溃决预警与三维体积测算

定位点：喜马拉雅山脉 · 珠峰北坡冰川湖

预置指令 (Prompt)："融合高精度 DEM，测算当前冰碛湖体积，并模拟溃坝洪峰(GLOF) 3D路径。"

开发技术规范：

数据源：Copernicus DEM (30m), 冰川时序轮廓。

Copilot 执行流 (伪代码)：

await ui.enable_3d_terrain('cesium_world_terrain')
volume = await tools.call('calculate_3d_volume', roi='everest_lake', use_dem=True)
flood_path = await tools.call('simulate_glof_fluid', origin='everest_lake', volume=volume)
await ui.add_cesium_3d_tiles(flood_path)


Demo 8: 地壳形变与火山热力学预判

定位点：夏威夷 · 冒纳罗亚火山

预置指令 (Prompt)："加载 InSAR 形变相位，结合热力异常，生成火山膨胀隆起的 3D 态势图。"

开发技术规范：

数据源：Sentinel-1 InSAR, Sentinel-3 LST (地表温度)。

Copilot 执行流 (伪代码)：

deformation = await tools.call('fetch_insar_displacement', roi='mauna_loa')
thermal = await tools.call('fetch_lst_anomaly', roi='mauna_loa')
shader_code = await tools.generate_cesium_custom_shader(vertex_displacement=deformation, fragment_heat=thermal)
await ui.apply_custom_shader(shader_code)


Demo 9: 全球碳汇与三维生物量估算

定位点：刚果盆地

预置指令 (Prompt)："融合 GEDI 激光雷达树高，计算三维冠层碳储量，并以 3D 柱状体拉伸显示。"

开发技术规范：

数据源：GEDI L2A/L4B, AEF A01 维度。

Copilot 执行流 (伪代码)：

carbon_stats = await tools.call('estimate_carbon_stock', source='GEDI+AEF', roi='congo')
await ui.add_cesium_extruded_polygons(carbon_stats.geojson, height_property='carbon_tonnes', color_property='density')


Demo 10: 城市热岛与社会经济脆弱性折叠

定位点：美国 · 纽约都会区

预置指令 (Prompt)："将夏季地表温度 (LST) 与社区平均收入数据进行空间皮尔逊相关性计算。"

开发技术规范：

数据源：Landsat 8 Thermal, US Census Tracts 收入数据。

Copilot 执行流 (伪代码)：

correlation = await tools.call('spatial_pearson_correlation', var1='LST', var2='Income', roi='NYC')
await ui.show_chart('scatter_plot', data=correlation.points, x='Income', y='Temperature')
await ui.render_bivariate_map(correlation.bivariate_grid)


Demo 11: 暗夜油污追踪与船舶时空溯源

定位点：马六甲海峡

预置指令 (Prompt)："利用 SAR 图像检测原油泄漏多边形，与过去 24 小时 AIS 船舶轨迹交集碰撞。"

开发技术规范：

数据源：Sentinel-1 SAR GRD, Global AIS 船舶轨迹。

Copilot 执行流 (伪代码)：

await ui.set_scene_mode('night_mode')
oil_spill = await tools.call('detect_sar_oil_spill', roi='malacca')
suspects = await tools.call('intersect_ais_tracks', target_polygon=oil_spill, time_window='-24h')
await ui.play_time_dynamic_czml(suspects.czml_animation)


Demo 12: 极深地下矿脉高光谱解译

定位点：澳大利亚 · 皮尔巴拉矿区

预置指令 (Prompt)："使用高光谱解混算法 (Spectral Unmixing)，寻找地表下方的铁矿与锂矿隐伏脉络。"

开发技术规范：

数据源：PRISMA / EnMAP 高光谱数据立方体。

Copilot 执行流 (伪代码)：

await ui.set_globe_transparency(0.5) 
minerals = await tools.call('hyperspectral_unmixing', endmembers=['Fe', 'Li'], roi='pilbara')
await ui.add_cesium_subsurface_model(minerals.3d_voxels)


🔮 第三阵列：极客炫技 (系统级架构张力)

Demo 13: 气象流体力学代码热生成 (Copilot 本体实力)

定位点：全球视角

预置指令 (Prompt)："用 GLSL 为我写一段基于 GFS 数据的全球风场流体渲染代码，并直接在地图上运行。"

开发技术规范：

核心机理：不仅调用 API，而是利用 LLM 生成代码片段（Code Generation）。

Copilot 执行流 (伪代码)：

wind_data_url = await tools.call('get_gfs_uv_wind_data')
glsl_code = await llm.generate_code(prompt="Write a Cesium CustomShader for wind particles using texture lookup.", context=wind_data_url)
await ui.write_to_editor(glsl_code, tab='CODE & SCRIPT')
await ui.execute_editor_code()


可视化震撼点：代码在左侧急速生成，地球瞬间刮起三维粒子风暴，展现“代码即算力”的最高境界。

Demo 14: 宏微观双模态虫洞跃迁 (v7 终极特性)

定位点：跨模态跃迁

预置指令 (Prompt)："地表分析完毕，挂载微观物理引擎，生成构成该地表岩石的二氧化硅分子晶体结构。"

开发技术规范：

核心机理：触发 Vue 路由与 WebGL 上下文销毁机制（Dispose Gate）。

Copilot 执行流 (伪代码)：

await ui.trigger_gsap_wormhole_animation()
await store.dispatch('switch_scale', target='micro') # 内部触发 Cesium 卸载与 Three.js 挂载
await tools.call('generate_molecular_lattice', type='SiO2', count=8000)
await ui.switch_sidebar_context('micro_physics_panel')


可视化震撼点：无缝剥离沉重的地球引擎，瞬间掉入具有真实物理折射率的玻璃态微观宇宙。