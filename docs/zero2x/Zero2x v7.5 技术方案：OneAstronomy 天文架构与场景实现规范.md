Zero2x v7.5 技术方案：OneAstronomy 天文架构与场景实现规范

状态：Architecture Review | 阶段：Phase 2.0 (Deep Space & WebGPU)

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

阶段 3 (硬核计算层与 Demo 2&4 实现 - 1周)

攻克 WGSL N-Body Compute Shader，完成 20 万粒子碰撞测试，确保主流显卡达到 60FPS（Demo 4）。

跑通 GSAP 动态样条运镜与 Milvus 检索联调（Demo 2）。

阶段 4 (AION-1 Copilot 串联 - 3天)

将所有 Demo 动作绑定至 astroStore.js。

通过左侧 Agent Flow 对话框输入自然语言指令，触发对应的场景运镜与计算。

结语

这套方案确保了 Zero2x v7.5 在不破坏现有体系的前提下，平滑拓展出足以匹敌 SpaceEngine 的视觉震撼力，同时在技术硬核度上（端侧 WebGPU 计算、AION-1 结合）超越现有的所有 Web 端天文可视化项目，完美兑现“科研工作台”的终极愿景。