Zero2x v7.5 技术方案：OneAstronomy 天文架构与场景实现规范

状态：Stage 2 Complete (Stabilized) | 阶段：Phase 2.1（Deep Space Demo Stabilization）

最近更新：
- 2026-03-19：M0 已提交并推送到 zero2x-v7.5（AI_CONTEXT.md、astroStore.js、v7.5 文档口径统一）
- 2026-03-19：M1 启动（astronomy 工具函数、EngineScaleRouter 双引擎常驻叠画 + opacity 交接、earth→deep space 相机同步）
- 2026-03-19：阶段 2 完成（Demo 1 红移拉伸：InstancedMesh + aRedshift + uniform 动画；Demo 3 模态 Inpaint：shader 扫描线扩散 + 点击选点）
- 2026-03-20：阶段 2 可靠性加固（“场景霸权 2.0”+ 边缘羽化：Demo 3 触发时强制收缩 Demo 1 红移爆裂；inpaint vignette/edge feather 消除方形边界；离开 macro 自动 stop inpaint，避免 micro 下潜穿帮）
- 2026-03-23：视觉可读性加固（避免“暗点宇宙/方形卡片”）：宏观 Instanced 星海实例半径门禁提升（防 sub-pixel）；二维叠加层加入更强裁切（circle mask）与侧视解剖运镜；Docker Dev 测试 runner 强制 `--build`，避免复验时命中旧镜像导致“假绿”。

编号说明（避免 Demo 混用）：
- 本文档的验收步骤沿用 Stage 2 的历史编号与 Command Palette 文案：Redshift Burst = Demo 1，Modal Inpaint = Demo 3。
- 若以“新的四大任务=四个 Demo（Demo1–Demo4）”口径，则对应关系是：本文 Demo 1 ≈ 新口径 Demo 2；本文 Demo 3 ≈ 新口径 Demo 4。

1. 架构统合：双模态引擎底座的无缝切换

为保持与 v6.0 中规划的“双模态底座”架构连续性，我们将沿用 /workbench 路由架构，并在 EngineRouter.vue 中实现地学（Cesium）与天文（Three/WebGPU）的平滑切换。

1.1 前端目录结构映射 (Vue 3 + Vite)

在原有结构基础上，扩展 ThreeTwin 及天文专属模块：

src/
 ├─ views/Workbench/
 │   ├─ index.vue                 # 统筹容器 (解析 context, 判断模态)
 │   ├─ EngineRouter.vue          # 引擎路由 (CesiumTwin 或 ThreeTwin)
 │   ├─ engines/
 │   │   ├─ CesiumTwin.vue        # 地学主态 (v6.0已实现)
 │   │   └─ ThreeTwin.vue         # 天文副态 (v7.5核心: 挂载 WebGPURenderer)
 │   │       ├─ core/             # 天文渲染核心类
 │   │       │   ├─ AstroTileLoader.js    # 对标 Cesium 3DTiles 的 HEALPix 瓦片流加载器
 │   │       │   ├─ LogarithmicCamera.js  # 对数级空间漫游相机
 │   │       │   └─ GalacticGrid.js       # 银道/赤道发光坐标网格
 │   │       └─ shaders/          # WGSL 计算着色器目录
 │   └─ components/               # 复用 v6 悬浮玻璃态 UI (AgentFlow / CodeEditor)
 └─ stores/
     └─ astroStore.js             # 专用于 OneAstronomy 的状态流转与 AION-1 工具调用


1.2 WebGPU 环境检测与降级挂载策略

在 ThreeTwin.vue 的 onMounted 阶段进行严格的硬件能力探测：

import { WebGPURenderer } from 'three/webgpu';
import { WebGLRenderer } from 'three';

async function initRenderer() {
    let renderer;
    if (navigator.gpu) {
        try {
            const adapter = await navigator.gpu.requestAdapter();
            const limits = adapter.limits;
            // 记录最大并行计算量，存入 Store 供 N-Body 场景决定粒子数
            astroStore.setMaxCompute(limits.maxComputeInvocationsPerWorkgroup);
            renderer = new WebGPURenderer({ antialias: true, alpha: true });
        } catch(e) { /* fallback */ }
    }
    
    if (!renderer) {
        console.warn("WebGPU not supported, falling back to WebGL2 Instancing");
        renderer = new WebGLRenderer({ antialias: true, alpha: true, logarithmicDepthBuffer: true });
        astroStore.setMode('fallback'); // 降级模式，关闭复杂计算着色器
    }
    return renderer;
}


2. 核心技术攻坚：HEALPix与极限尺度的 Web 表达

天文架构面临的最大挑战是**“尺度失真（Z-fighting）”和“球面数据扭曲”**。我们通过以下三大核心技术解决。

2.1 空间索引：Astro-Tiles (基于 HEALPix 的流式数据系统)

抛弃传统经纬度图片贴图，引入天文学标准的 HEALPix (Hierarchical Equal Area isoLatitude Pixelization)。

前端实现：

开发一个 WebWorker 专门运行 healpix.js 的子集算法。

根据当前相机的 FOV 和距离中心的 Distance，计算出视野覆盖的 HEALPix $N_{side}$ 级别以及对应的 Pixel Index 集合。

发起 HTTP Range 请求，从后端的 Zarr/Parquet 数据块中拉取对应网格的数据。

后端支撑 (FastAPI)：将开源全天巡天图像（如 HiPS 格式）和星表预先切分为多层级的 HEALPix 结构，通过 CDN 提供静态二进制分发。

2.2 视觉参照：无尽坐标系 (The Galactic Grid)

因为宇宙没有“地面”，必须构建一个 Shader 级别的球形发光网格。

技术实现：创建一个巨大的 SphereGeometry（半径为相机可达最大视距），开启 backSide 渲染。

材质 (NodeMaterial/WGSL)：使用 Three.js 新一代节点材质（TSL）。通过判断 UV 坐标与网格线的距离，渲染出发光的经纬线，并实现距离相机的“深度渐隐 (Depth Fading)”，避免网格线过密导致的摩尔纹。

2.3 交互革命：对数缩放相机控制器 (Logarithmic OrbitControls)

传统的 OrbitControls 在宇宙尺度完全不可用。

技术改造：劫持 wheel 事件，滚轮步长 (Delta) 必须等于 当前相机到焦点距离的百分比（例如每次滚动前进/后退当前距离的 15%）。

UI 联动：引入 Cosmic Scale HUD。在视图右下角监听相机距离，动态显示空间尺度换算：天文单位 (AU) -> 视差秒差距 (pc) -> 千秒差距 (kpc) -> 百万秒差距 (Mpc)。

3. 四大核心场景底层架构与视觉设计

保证四个场景在底层都能复用一套 "API拉取 -> 隐空间对齐 -> WebGPU/Instancing渲染" 的标准工作流。

场景一：深空巡天与多模态红移测距 (The 3D Cosmic Web)

业务逻辑：从二维 HEALPix 切片，根据红移 $z$ 爆裂为三维网格。

数据流：后端 FastAPI 吐出 JSON { id, ra, dec, color_index }。

渲染技术 (WebGPU InstancedMesh)：

初始化包含 10 万个粒子的 InstancedMesh，材质赋予发光 Bloom 效果。

Copilot 触发后：通过 AION-1 大模型实时推理获取红移值数组 Z_array，回传前端。

GSAP 动画：使用 GSAP 驱动一个全局 Uniform 变量 u_redshift_scale 从 0 过渡到 1。在 GPU 的 Vertex Shader 中：position.z = original_z + (z_value * u_redshift_scale * max_depth)。实现数万星系瞬间在屏幕深处展开的爆炸感。

场景二：强引力透镜的“大海捞针” (Vector Search in Cosmos)

业务逻辑：基于图像特征的零样本（Zero-Shot）跨天区检索。

后端集成 (Milvus + AION-1)：

后端维护 Milvus 向量库，存储基于 AION-1 图像 Tokenizer 提取的 512 维天体特征。

接收前端传来的图像目标区，返回最相似的 Top-5 天体坐标（RA, Dec）。

视觉与运镜：

获取目标后，基于自定义的 LogarithmicCamera 执行 "样条曲线漫游 (CatmullRomCurve3)"。

运镜期间，全屏施加 Radial Blur（径向模糊后处理），模拟超光速折跃（Warp Drive）的视觉冲击。到达后弹出高科技感的 Glassmorphism 对比面板。

场景三：暗物质寻踪与图谱互生 (Modal Inpainting)

业务逻辑：可见光到 X 射线的 AI 模态生成。

数据结构：加载蟹状星云的高分辨率基底纹理 (Texture A) 和 AION-1 实时生成的 X 射线预测纹理 (Texture B)。

Shader 视觉黑魔法：

不使用生硬的透明度切换。编写一个带有**“扫描线扩散波”**的 Fragment Shader。

传入鼠标点击的世界坐标 hitPosition，随时间 t 扩大扫描半径。在半径内，采样 Texture B（并叠加极高的 HDR 亮度用于 Bloom 泛光）；半径外采样 Texture A。

边缘处添加高频噪声（Noise 函数），模拟能量解离边缘的赛博科幻感。

场景四：银河系碰撞推演 (End-Node WebGPU Compute)

业务逻辑：不再依赖后端集群，在轻薄本上纯前端跑 10-20 万粒子的 N-Body 模拟。

底层技术 (Compute Shaders)：

采用 WebGPU 的 ComputeNode 架构。

初始化：将 20 万颗恒星的初始位置 $(x,y,z)$ 和 质量/速度 存入两个 StorageBuffer。

WGSL 编写：编写 N-Body 引力迭代内核。利用 Shared Memory（共享显存）优化粒子间的距离计算，大幅降低复杂度。

渲染循环：每帧先调度 Compute Shader 更新 StorageBuffer，然后直接交由 Vertex Shader 读取新位置进行渲染。数据完全不回传 CPU，确保帧率稳如磐石。

4. UI/UX：统一资产与悬浮指挥舱融合

在 Workbench/index.vue 中，当 EngineRouter 判定当前处于 OneAstronomy 态时，侧边栏（HUD）动态更新为天文科研语境。

4.1 玻璃拟态与中央负空间 (De-containment)

严格遵守 v4 规划的**“去容器化”**原则。

侧边栏（Agent Flow / 代码面板）不再是实心背景，采用 backdrop-filter: blur(24px)，边框赋予 1px solid rgba(0, 240, 255, 0.2)，确保底部的星空始终在边缘可见。

物理居中准星：在屏幕正中央绝对定位一个 SVG 准星锚点 (transform: translate(-50%, -50%))。这是极暗宇宙环境下的核心视觉锚，任何缩放（Resize）都不会使它偏移。

4.2 Code Editor 的 WGSL 热重载能力

右侧 Monaco Editor 的价值在天文场景中将得到指数级放大：

配置 Monaco 支持 wgsl 语法高亮。

在 Demo 4（星系碰撞）中，将 Compute Shader 的源码直接暴露在编辑器中。

拦截 Ctrl+Enter。当用户在编辑器中修改了引力常数 $G$ 或碰撞摩擦系数，触发前端重新编译 WebGPU Pipeline。粒子流的形态在 3D 画布中瞬间发生变异，完美诠释 “代码即算力，视窗即数据” 的顶级理念。

5. 工程实施路线与 TDD 测试门禁

为了保证在整合时不破坏原有 Cesium 底座和打包逻辑，遵循以下里程碑推进：

阶段 1 (MVP: 预研与跑通壳结构 - 3天)

在 ThreeTwin.vue 中成功挂载 WebGPURenderer（带降级检测）。

实现基于 Shader 的发光银道坐标系网格（Galactic Grid）和动态 Logarithmic Camera。

TDD 门禁：vitest 检查 ThreeTwin 挂载时不抛出 Context Error；检查缩放时 UI 组件不遮挡中央 40% 视区。

阶段 2 (视觉核心与 Demo 1&3 实现 - 1周)

利用 Three.js PostProcessing 实现高品质 Bloom（泛光）。

跑通红移 Z 轴拉伸动画（Demo 1）和 Shader 扫描线纹理替换（Demo 3），后端接口暂时 Mock。

注意：阶段 2 的“模态 Inpaint / 扫描扩散”就是 Demo 3；Demo 2 属于阶段 3 的检索/运镜联调规划，请不要和 Demo 3 混用编号。

阶段 3 (硬核计算层与 Demo 2&4 实现 - 1周)

攻克 WGSL N-Body Compute Shader，完成 20 万粒子碰撞测试，确保主流显卡达到 60FPS（Demo 4）。

跑通 GSAP 动态样条运镜与 Milvus 检索联调（Demo 2）。

阶段 4 (AION-1 Copilot 串联 - 3天)

将所有 Demo 动作绑定至 astroStore.js。

通过左侧 Agent Flow 对话框输入自然语言指令，触发对应的场景运镜与计算。

---

## 阶段 2（Demo 1&3）端到端验收：以 Docker Dev 为准

本仓库推荐的“可复现验收路径”是 Docker Dev（前端 8404 / 后端 8405）。下面步骤以此为标准，确保团队在不同机器上得到一致结果。

### 0) 启动（Docker Dev）

在项目根目录：

```bash
cd cesium_app_v6
cp .env.example .env

make docker-dev-up
```

可选：若你需要从其他机器访问（公网/局域网），加：

```bash
ONEEARTH_BIND_IP=0.0.0.0 make docker-dev-up
```

### 1) 基础健康检查（建议必做）

```bash
make docker-dev-check
```

说明（复现一致性）：
- 从 2026-03-23 起，`make docker-dev-check` 内部的 `backend_test/frontend_test` 以 `--build` 方式运行，确保容器内 pytest/vitest 真实运行最新代码与门禁，避免旧镜像缓存造成“容器内假绿”。
- 如需单独跑：`make docker-dev-pytest` / `make docker-dev-vitest`。

如果你只想快速确认服务是否起来：

```bash
curl -fsS http://127.0.0.1:8405/health
```

### 2) 进入 Workbench（验证入口）

打开：

- `http://127.0.0.1:8404/workbench`

在右上角 Scale Toggle 点击 `Sky`（macro）。

### 3) Demo 1：Redshift Burst（红移拉伸）验收

触发方式（推荐，符合“无按钮化”原则）：

1. 右侧 021 Copilot 面板点击 `Command (Cmd/Ctrl+K)`
2. 选择预置：`[v7.5] OneAstronomy · Redshift Burst (Demo 1)`

预期现象：

- Sky（macro）中 Instanced 星系点云沿 +Z 方向出现“红移拉伸爆裂展开”
- Bloom 有轻微增强（更显著的爆裂观感）

视觉可读性检查（避免“暗点宇宙”）：
- 默认相机距离下，宏观星海不应只剩“几颗暗点”。若出现 sub-pixel 现象，优先检查 Instanced 球体半径与亮度/泛光强度。
- 当前基线做法：宏观 Instanced SphereGeometry 半径已提升到可读级别（以代码门禁约束）。

### 4) Demo 3：Modal Inpaint（模态互生）验收

触发方式（推荐）：

1. 在 Command Palette 选择：`[v7.5] OneAstronomy · Modal Inpaint (Demo 3)`
2. 在 3D 画布任意位置点击：设置扫描中心并触发扫描线扩散

预期现象：

- 出现带边缘噪声/扫描线的“模态替换”视窗
- 点击后扫描中心移动，替换区域从点击点向外扩散
- 视觉不应出现“长方形截图边界”（inpaint 边缘应羽化融入深空）
- 若先触发 Demo 1 再触发 Demo 3：底层爆裂应自动收缩回 0（避免粒子刺穿/穿插）

视觉无界融合门禁（Anti-screenshot）：
- inpaint 必须维持 Additive + 无 depthTest/depthWrite + shader 羽化（vignette/edge feather）。任何回归为“方形面片边界”都视为阻断缺陷。

退出方式（两种任选其一）：

- 在代码面板 Run 中输入并执行：`inpaint stop`
- 或刷新页面重新进入（最粗暴兜底）

### 5) 常见问题排障（Docker Dev）

- 页面打不开/空白：先执行 `make docker-dev-ps` 与 `make docker-dev-logs` 查看容器是否正常启动
- 前端能开但 /api 502：确认后端健康 `curl -fsS http://127.0.0.1:8405/health`
- 公网访问 HMR 失效：按仓库口径可先禁用 HMR：`VITE_DISABLE_HMR=1 ONEEARTH_BIND_IP=0.0.0.0 make docker-dev-up`

---

## 下一步计划（Phase 2.2 → Stage 3）

目标：在保持 Stage 2 Demo 1&3 稳定可验收的前提下，推进 Stage 3（Demo 2 & Demo 4）并补齐“工程化可回归”的验收机制。

1) Stage 2 稳定性收尾（短迭代）
- 增加“视觉回归检查清单”：Demo 1 → Demo 3 → micro 下潜 → 回 macro 的顺序切换，确认无残留、无遮挡、无穿帮
- 将关键场景状态（inpaint enabled、macro opacity、redshift scale）写入一个只读 debug 面板或日志点（仅 DEV），便于 Docker Dev 排障

2) Stage 3 / Demo 2（检索 + 运镜）
- 定义 Demo 2 的 action contract（输入/输出字段、失败兜底、延迟策略），并在前端用 mock/placeholder 保持可演示
- 落地样条运镜骨架（CatmullRomCurve3 + timeline），并在 Vitest 中新增最小 wiring 测试（不追求像素级）

3) Stage 3 / Demo 4（WebGPU Compute 预研）
- 建立 Compute 运行能力探测与“降级路径”（无 WebGPU 时自动回退为 Instancing 静态演示）
- 先跑通 2–5 万粒子验证 pipeline 与性能基线，再扩展到目标规模

---

结语

这套方案确保了 Zero2x v7.5 在不破坏现有体系的前提下，平滑拓展出足以匹敌 SpaceEngine 的视觉震撼力，同时在技术硬核度上（端侧 WebGPU 计算、AION-1 结合）超越现有的所有 Web 端天文可视化项目，完美兑现“科研工作台”的终极愿景。
