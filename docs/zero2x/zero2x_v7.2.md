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

下一步（🟡）
- ✅ Demo 13 进阶：已固化“LLM 输出 WGSL 模板”（compute body 可自动 wrap 成完整 WGSL module），让模型生成代码更稳定可执行。
- 🟡 M3：推进 Demo 6-10 场景组装（优先 Demo 6：vector/extruded + charts 业务样式与示例数据）。

分支与落地记录
- 分支：`patch/0303-v72-phase4`
- 已落地基础闭环提交：`e41fdcb`（v7.2 subsurface + WebGPU tools，TDD）

本文件作为 v7.2 主版本开发文档（source of truth）。以下规划会以当前仓库实现为基线：
- Workbench 已具备 Copilot tool_call → 前端引擎执行链路（Cesium Twin + 部分 Three Twin）。
- EngineRouter 已具备：夜景模式 `setSceneMode('night')`、CZML 播放 `playCzmlAnimation()`、透明地球 `setGlobeTransparency()`、3DTiles / ExtrudedPolygons 等。

---

0. v7.2 项目规划（结合当前项目现状）

目标：优先落地“高表现、低风险”的 Demo 11/12，并以最小可用沙盒打通 Demo 13 的 WebGPU 叠加框架（Event-Driven Overlay），确保演示稳定与可扩展。

M0（已具备/保持稳定）
- Demo 11 基础能力：夜景模式（globe.enableLighting）+ CZML 时空轨迹（CzmlDataSource + clock.shouldAnimate）。
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
- binding(0)：`particles`，`var<storage, read_write>`，`array<vec4<f32>>`
- binding(1)：`uCamera`，`var<uniform>`，`view`/`proj` 两个 `mat4x4<f32>`
- binding(2)：`uParams`，`var<uniform>`，`vec4<f32>`：`(t, stepScale, _, _)`

实现约束（稳定优先）
- WebGPU 沙盒必须与 Cesium 渲染解耦（不侵入 Cesium 内部 WebGPU API）。
- 所有新能力必须可降级：WebGPU 不可用时不影响 Cesium 主渲染；地下模式不依赖外部模型也可演示。

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

调用 viewer.scene.globe.enableLighting = true 开启晨昏线与夜景。

加载包含船舶 AIS 数据的 .czml 文件。

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