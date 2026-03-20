Zero2x 021 v7：Copilot 驱动的空间交互与核心场景开发蓝图

修订目标：全面转向以 "AI Copilot Chat" 为交互中枢、以 "统一资产面板" 为物料收纳的现代 IDE 布局。同时，针对所有演示场景，提供从数据源、API 接口到大模型工具调用（Tool Calling）的完整技术实现细节。

---

实现进度（as-built，截至 2026-03-04）

已完成（可回归）

- ✅ UI：工作台已改为严格“左-中-右”三栏 IDE 布局
	- 左侧统一资产面板：`frontend/src/views/workbench/components/UnifiedArtifactsPanel.vue`
	- 中央 Twin Canvas：`frontend/src/views/workbench/EngineScaleRouter.vue`
	- 右侧 Copilot Chat：`frontend/src/views/workbench/components/CopilotChatPanel.vue`
	- 组装入口：`frontend/src/WorkbenchApp.vue`

- ✅ Tool Calling（v7 stub 协议已打通，前后端闭环可演示）
	- 后端端点：
		- `GET /api/v7/prompts`（Prompt Gallery 数据源）
		- `GET /api/v7/tools`（工具定义列表）
		- `POST /api/v7/copilot/execute`（返回结构化 events：thought/tool_call/tool_result/final）
	- 实现：`backend/v7_copilot.py` + `backend/main.py`
	- 合同测试：`tests/test_v7_copilot_api.py`
	- 前端对接：`frontend/src/services/api.js` + `frontend/src/WorkbenchApp.vue`（渲染事件卡片 + 最小事件分发）

- ✅ 双引擎底座（安全约束不破坏 v6）
	- Earth 模式：Cesium（保持 v6 工作流）
	- Macro/Micro 模式：ThreeTwin（互斥挂载 + Dispose Gate）

- ✅ 关键问题修复（影响演示体验）
	- Twin 画布鼠标不可交互（地球拖拽不转）：修复 HUD overlay 抢事件问题（补齐 pointer-events 工具类 + 中央区域穿透）
	- “毛乌素”场景跳转回“鄱阳湖”：补齐 `maowusu` 场景注册，避免 fallback 到默认场景

已验证

- ✅ 前端测试：`frontend` Vitest 全绿（新增 `frontend/tests/scenarios021.test.js` 作为场景注册回归门禁）

当前差距（仍属蓝图阶段 / 未完全落地）

- ⏳ Demo 1-14 的“真实工具链路”尚未实现：目前为 deterministic stub + 最小 UI 分发（scale/context/layers 级别）
- ⏳ “Unified Artifacts” 的 CHARTS/REPORTS 仍主要为占位/文本预览，未形成可导出产物闭环（ECharts/Markdown/PDF）
- ⏳ 工具覆盖面不足：缺少对 `add_cesium_imagery` / `add_cesium_vector` / `generate_report` / `write_to_editor` 等关键 UI 工具的统一实现

下一步建议（按优先级，建议按 1→3 逐步验收）

1) 先把“工具 → UI 产物”补齐为通用能力（v7 基础设施）

- 新增前端工具分发器（建议集中在 `frontend/src/WorkbenchApp.vue` 或抽到 `frontend/src/services/copilotRuntime.js`）：
	- `ui.add_cesium_imagery(tile_url, palette, threshold, opacity)`：自动挂载到 Cesium 图层列表，并在 LayerTree 可调
	- `ui.add_cesium_vector(geojson, color_map)`：加载 GeoJSON 数据源并可在 LayerTree 开关
	- `ui.generate_report(markdown)`：写入 Unified Artifacts 的 REPORTS tab（后续再做 PDF 导出）
	- `ui.write_to_editor(code, language)`：写入 CODE tab（Monaco）

2) 用 TDD 实现“经典三大场景”真实闭环（先做 Demo 1-3）

- Demo 1（余杭 diff）/ Demo 3（毛乌素 cosine diff）：优先落地 `POST /api/v1/aef/compute_diff` 的最小可用实现（可先返回 mock tile_url，但必须走统一工具链路渲染）
- Demo 2（亚马逊 kmeans）：落地 `POST /api/v1/aef/cluster` 的最小实现（可先 stub GeoJSON，但必须走 vector 工具链路渲染）
- 每个 Demo 的验收标准固定为：
	- Copilot Events 卡片正确
	- Twin 发生可见变化（飞行 + 图层挂载）
	- REPORTS 产生一段结构化 Markdown 结论

3) 再拓展到“前沿开拓 + 极客炫技”

- Demo 7/9/11 等：优先把“数据源接入方式 + Cesium 可视化载体（3D Tiles/CZML/Extrusion）”规范化成工具
- Demo 13：将代码生成限定为可控 sandbox（仅允许 CustomShader/GLSL 模板插槽），并为执行添加开关与审计日志

---

一、 UI 架构重构：Copilot 驱动的“空间 IDE”布局

摒弃当前浮动且重叠的面板，采用严格的 “左-中-右”流式网格系统。

1. 右侧中枢：021 Copilot Chat (动态对话与任务规划栏)

位置： 屏幕最右侧，宽度约 400px，高度 100vh，侧边栏（可折叠）。
设计灵感： GitHub Copilot Chat / Cursor IDE。

Prompt Gallery (预置指令库)：在输入框上方提供横向滚动的“场景胶囊 (Chips)”。用户点击如 [演示: 亚马逊雨林聚类]，输入框会自动填入完整的 Prompt 并执行。解决用户“不知道问什么、不想打字”的痛点。

思维链 (CoT) 与工具调用流：当用户输入后，界面以动态卡片展示 AI 思考过程：

[思考] 提取目标坐标...

[调用工具] camera_fly_to(lat=-10.04, lon=-55.42)

[调用工具] aef_zero_shot_kmeans(k=6)

2. 左侧仓库：统一资产与产物面板 (Unified Artifacts Tab)

位置： 屏幕最左侧，宽度约 360px。

Tab 1: 🗂️ LAYER & DATA：管理 GEE 瓦片图层，精细化调节 AlphaEarth 渲染管线的阈值与色标。

Tab 2: 💻 CODE & SCRIPT：收纳 Monaco Editor。展示 AI 生成的 Python 处理代码或 GLSL 渲染着色器。支持热重载。

Tab 3: 📊 CHARTS & STATS：展示基于 AlphaEarth 数据生成的 2D Echarts 统计图表。

Tab 4: 📝 REPORTS：展示最终生成的结构化 Markdown 研判报告，支持导出 PDF。

3. 中央视窗：无界空间底座 (The Twin Canvas)

位置： Flex 布局撑满剩余空间。彻底去边框化，仅保留极简的 Scale Toggle (Earth/Macro/Micro)。

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
# LLM 智能选择 cosine_similarity 排除光照/季节的绝对值干扰
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

# LLM 准确理解“隐形水灾”需要调用 A02 维度
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
# 生成着色器注入左侧代码编辑器并热执行
shader_code = await tools.generate_cesium_custom_shader(vertex_displacement=deformation, fragment_heat=thermal)
await ui.apply_custom_shader(shader_code)


Demo 9: 全球碳汇与三维生物量估算

定位点：刚果盆地

预置指令 (Prompt)："融合 GEDI 激光雷达树高，计算三维冠层碳储量，并以 3D 柱状体拉伸显示。"

开发技术规范：

数据源：GEDI L2A/L4B, AEF A01 维度。

Copilot 执行流 (伪代码)：

carbon_stats = await tools.call('estimate_carbon_stock', source='GEDI+AEF', roi='congo')
# 在 Cesium 中利用 Extruded Polygon 实现 3D 拔地而起的效果
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

# 设置地表半透明
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