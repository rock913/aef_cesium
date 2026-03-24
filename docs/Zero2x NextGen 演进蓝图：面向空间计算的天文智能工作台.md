Zero2x NextGen 演进蓝图：面向空间计算的天文智能工作台

文档定位：在 v7.5 完成“单渲染管线 + 宇宙网视觉”闭环后，指导系统向“全球顶级虚拟天文台 + 智能体科研工作台”演进的高阶架构指南。

## 落地状态（滚动更新）

### 2026-03-24（当前主线：origin/zero2x-v7.5）

- Earth→Sky “一镜到底”交接：已从“触发过苛刻”调整为更易触发（默认阈值 8000km），并新增排障日志开关
	- `VITE_EARTH_TO_SKY_HANDOVER_HEIGHT_KM`：交接高度阈值（默认 8000）
	- `VITE_EARTH_TO_SKY_HANDOVER`：总开关（默认开启；设为 `0/false` 可禁用）
	- `VITE_DEBUG_EARTH_TO_SKY_HANDOVER=1`：输出触发/重置日志
- Astro-GIS Catalog 动态加载（Phase 2→3 过渡）：已落地“停下再请求”
	- OrbitControls `end` 触发 + debounce（避免拖拽/缩放时高频请求）
	- 大视场 FOV 上限过滤（默认 15°），避免一次性拉取过多点
	- 已添加 Vitest 门禁，防止回退到“每帧尝试 fetch”

下一步（按优先级）：

1) 代理与协议：后端补齐 TAP/VizieR 代理的缓存/限流/观测（qps、命中率、失败率）
2) 体验闭环：Catalog layer UI 做“加载中/最后更新时间/错误提示”，并支持手动刷新
3) 数据结构：从 “sources list” 走向 “tile/region cache（按视场块缓存）”，支持 HiPS/HEALPix 的渐进式细化

核心议题 1：迈向全球顶级虚拟天文台的详细路线图

要对标 AAS WorldWide Telescope (WWT) 或 SpaceEngine，我们需要从“静态预置数据”走向“流式动态计算”。

Phase 1 (现状 v7.5)：微型数据截取 (Micro-data) + Shader 视觉欺骗，实现宏观静态宇宙的电影级表达。

Phase 2 (v8.0) 动态数据流 (Streaming Astro-GIS)：

HEALPix 瓦片化渲染：引入类似 Cesium 3D Tiles 的天文瓦片机制（HiPS）。随着相机 FOV 缩小，动态从服务器拉取更高分辨率的星空底图（无需再加载外部 Aladin DOM，而是自己写 WebWorker 动态生成 Three.js Texture）。

TAP/VizieR 星表流式加载：基于相机视锥体 (Frustum)，实时向 CDS 接口请求星表数据点并渲染。

Phase 3 (v9.0) 时域与物理一致性 (PINN & Time-Domain)：

加入时间轴（Timeline），支持万年尺度的恒星自行（Proper Motion）推演。

接入实时天文台警报流（VOEvent），GOTTA 的闪烁不再是预设 JSON，而是真实的实时超新星爆发预警。

核心议题 2：工作台 UI 重构与 OpenClaw 智能体架构融合

目前的界面（左侧菜单，右侧简易聊天）过于单薄，无法承载复杂的科研工作流。必须引入 “Session（会话/笔记本）” 概念。

2.1 界面交互重构 (The Workspace UI)

左侧栏 (Data & Context)：改为 Data Catalog & Asset Tree。展示当前 FOV 视场内加载的星表、底图层级。

右侧栏 (Agent Session)：升级为类似 Jupyter Notebook + 飞书智能体的 Agent Session 面板。

不再是简单的文字问答，而是呈现 Agent 的 思考链 (Chain of Thought)：[规划任务] -> [调用 SIMBAD 工具] -> [生成 WebGPU 代码] -> [执行] -> [得出结论]。

支持历史 Session 存档，科学家可以随时恢复上一次的探索状态。

2.2 后端接入 OpenClaw 架构

openclaw 是一种强大的开源 Agent 架构，非常适合这种多工具调用的科研场景。

架构设计：

Orchestrator (编排层)：接收前端用户的自然语言输入（如：“分析眼前这片星云”）。

Tools (工具簇)：向大模型注册天文工具。例如：query_simbad(ra, dec)、run_webgpu_compute(shader_code)、set_camera_target(x,y,z)。

LLM (OneAstronomy)：根据编排，大模型决定调用 query_simbad 获取数据，然后生成一段数据分析代码，最后调用 run_webgpu_compute 让前端 3D 画布渲染结果。

前后端契约：后端 WebSocket 推送结构化的 Agent 状态包，前端 Vue 解析这些状态，在右侧面板展示进度条、代码块和图表，同时控制 Three.js 的运镜。

核心议题 3：从 Earth 到 Sky 的“一镜到底”转场设计

这是空间尺度表达的终极浪漫（Powers of Ten 视角）。由于地球通常在 Cesium/Mapbox 引擎，而宇宙在 Three.js 引擎，我们需要精妙的“双轨欺骗”：

转场剧本与技术流：

起飞 (Earth)：在 Cesium 中，相机从地面目标快速垂直拉升，拉到距离地表 20,000 公里（看到地球全貌，大气层变薄）。

淡入 (The Blend)：此时，隐藏在背后的 Three.js Canvas (Alpha透明) 里的 Native Skybox (8K 银河贴图) 的 Opacity 开始从 0 缓动到 1。

交接 (The Handover)：地球模型快速变小，化为一个蓝色的像素点（交接点）。此时销毁/隐藏 Cesium 上下文。Three.js 相机接管位置。

跃迁 (To Macro Space)：Three.js 相机视野（FOV）猛然拉长，穿过太阳系（如果做了太阳系粒子），直接向后狂飙 10 万光年。之前加载的 50,000 个红移粒子出现在视野中，完成从行星级到宇宙级的空间跨越！

核心议题 4：解决 GOTTA (Demo 3) 和 Inpaint (Demo 4) 的前端颗粒感

目前局部特写时画面粗糙，是因为在 WebGL/WebGPU 中，普通的 Sprite 或低分辨率 Canvas 贴图在近距离观看时会暴露像素。

视觉升级策略 (The Polish)：

针对 GOTTA (瞬变源超新星)：
放弃使用单张 .png 贴图。改用 Procedural Volumetric Shader（程序化体积着色器）。利用 3D Simplex Noise 生成动态翻滚的等离子体动画；叠加 3 层不同半径和颜色的 THREE.PointLight 配合高强度 Bloom 阈值，制造极度刺眼的物理眩光（Lens Flare）。

针对 Inpaint (蟹状星云雷达扫描)：

提升贴图精度：生成贴图时，分辨率至少开到 2048x2048。

抗锯齿 (Anti-Aliasing)：在 Fragment Shader 中，计算扫描线 mask 时，必须使用 smoothstep(radius+0.02, radius-0.02, d) 来产生柔和的羽化边缘，绝对不要用 if(d > radius) 这种硬截断（会产生严重锯齿）。

叠加高频噪点：在混合后的颜色上，叠加一层极细微的动态胶片噪点（Film Grain），能极大掩盖低清贴图的颗粒感，增加物理真实度。

核心议题 5：是否应该与 VSCode 等 IDE 整合？

深入反思结论：坚决不建议将系统做成 VSCode 的插件，也不建议在系统中完整嵌入 VSCode。

为什么？（空间计算的产品哲学）

VSCode 的心智模型是 “以代码文件为中心的开发者工具 (Developer IDE)”。

Zero2x 的心智模型是 “以数据和空间实体为中心的科学探索工作台 (Scientific Spatial Workspace)”。

如果我们把宇宙放进 VSCode，宇宙就成了代码的附属品（一个预览窗口）；如果我们把完整的 VSCode 塞进我们的 UI，界面会立刻变得极其沉重、拥挤，破坏“数字孪生”的沉浸感。

最佳实践方案：嵌入 Monaco Editor Widget
科学家确实需要写代码（Python/WGSL），但他们需要的是 Jupyter Notebook 的体验。

我们只需要在右侧的 Agent Session 面板 中，按需挂载 Monaco Editor（VSCode 的底层代码高亮组件） 实例。

当智能体生成代码，或者科学家需要微调算法时，展开一个轻量级的 Monaco 代码块。这种 “Block-based Computing” 既满足了硬核计算需求，又保住了 3D 空间计算工作台的独立与轻盈。

核心议题 6：面向“空间计算 (Spatial Computing)”的系统化研究思考

当 Apple Vision Pro 和 Meta Quest 推动空间计算时代到来时，传统的数据大屏将走向死亡。Zero2x 必须提前布局以下三点：

数据空间化 (Data as Environment)：数据不再是右侧面板里的 2D 图表。光变曲线（Lightcurve）应该直接在星体旁边以 3D 轨迹漂浮呈现；红移数据不再是表格，而是直接反映为纵深空间的位移。

自然多模态交互 (Multi-modal Gaze & Voice)：
在未来的 VR/XR 版本中，鼠标将被“眼动追踪 (Gaze)”取代。科学家注视 3D 宇宙网中的某个密集区，说出：“Agent，分解我正在看的这个星系团”，OpenClaw 架构会结合视场射线 (Raycast) 提取坐标，执行计算，并直接在空间中返回全息拆解图层。

算力去中心化 (Edge WebGPU Compute)：
空间计算设备需要极高的帧率。将重度天体物理模拟（如 N-body 引力推演）从云端剥离，完全下放到前端，利用 WebGPU 的 Compute Shader 在本地浏览器/头显内并发执行千万级粒子的物理信息神经网络（PINN）推理。

总结：Zero2x 的最终形态，不仅是一个网页，而是一个运行在云边端协同架构上的 “沉浸式宇宙元宇宙 (Immersive Cosmic Metaverse)”。