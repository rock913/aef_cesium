Zero2x 021: AI-Native 科研工作台系统规划与开发蓝图

核心愿景：视窗即数据，代码即算力

打破传统科研软件中“地图界面”与“编程界面”的物理割裂。在 Zero2x 系统中，底层的 3D 数字孪生引擎（Cesium/Three.js）就是无边框的“真实世界”。我们摒弃传统的三栏式平铺 UI，采用**“全屏孪生主导 + 全息悬浮 HUD”**的下一代空间交互范式。代码的每一次执行，都会直接在底层的 3D 宇宙中引发震撼的视觉与数据涌现。

1. 架构定型：确立“双模态底座”架构 (兼顾地球与天文)

面对未来可能接入的天文（OneAstronomy）和微观（OneGenome）场景，经过架构评估，我们明确采用“双模态底座”架构（方案 B），以保证专业级的渲染表现力。

地学主态 (021 Foundation 模式 - 当前最高优先级)：工作台底座挂载 CesiumJS。用于处理带有明确经纬度、高程、真实地形的三维地球场景，深度对接已有的 Alpha Earth Foundation (AEF) 资产。

天文/微观副态 (OneAstronomy 模式 - Phase 2 滞后开发)：工作台底座无缝切换为 Three.js。用于处理没有地球实体边界的深空星系团或微观分子晶格。

优先级策略：当前集中全部资源跑通基于 CesiumJS 的“地学场景演示”，确保能够向外界传达“AI 驱动数字孪生”的完整逻辑。天文与微观场景的 3D 整合延后至下一阶段（Phase 2），目前在叙事页（前四幕视频）中呈现即可。彻底移除遗留的冗余多幕 Cesium 演示页，将资源 100% 聚焦于 /workbench 生产力环境。

2. 核心交互演进：虫洞直达与极简架构

为了消除“长页面滚动”与“IDE 复杂交互”的冲突，同时赋予专业用户极速体验，我们对访问路径进行了“降噪除余”。

2.1 智能指令面板的“虫洞直达” (Omni-Bar Teleportation)

在首屏 (Act 1)，升级为 下拉指令选择器。对于明确科研意图的用户，绝不拖泥带水：

预置 V6.0 的核心实战剧本。

用户点击即选择，系统直接跨越叙事，跳转加载真实的 /workbench?context=xxx 环境，实现“秒级进入战斗态”。

2.2 第五幕：叙事终点的守望者 (Act 5: Standby Launchpad)

对于没有使用搜索框，而是向下滚动浏览网页的新用户，第五幕作为“去容器化的散点 HUD”存在。

它是叙事篇章的终点（CTA），展示系统已就绪，并提供 LAUNCH 021 WORKSPACE 的唯一高亮入口，引导用户进入工作台。

3. 终极工作台 UI 架构：全屏孪生 + 悬浮 HUD

彻底摒弃缺乏科技感的“左-中-右”三栏隔离排版，向科幻级“轨道指挥舱”视觉看齐。

3.1 无界视窗底座 (Z-index: 0)

CesiumJS 全屏接管：宽 100vw，高 100vh。数字地球是绝对的视觉中心和操作基底，不留任何边框。

3.2 悬浮交互装甲 (Z-index: 10, Glassmorphism)

所有的功能组件均采用深色毛玻璃（backdrop-filter: blur）面板，悬浮于 3D 视窗之上，留出巨大的中央视野。

左侧悬浮：Agent Flow

承载自然语言的输入与 021 模型的思维链 (CoT) 展现。流式打字机输出直接印在透明玻璃板上，不遮挡背后的山川湖海。

右侧悬浮：Code Editor

Monaco 代码编辑器的透明化嵌入。展示驱动地球异动的 Python / GLSL 脚本。

底部悬浮：Timeline & Mission Control

承载核心执行按钮 [EXECUTE ON TWIN]，以及地学时间轴的推演滑块。

4. 演示剧本库 (Storyboard based on V6 Assets)

结合已有的业务成果，我们将内置以下三大实战场景供演示，通过“一键点选”完成叙事与作业的串联。

📌 剧本 A：国家水网脉动 (Context: poyang)

意图：构建鄱阳湖生态监测 Agent。

底层感知：提取 64 维空间特征，生成水文波动与候鸟迁徙交叉差分热力图。

目标定位：江西 · 鄱阳湖流域 (lake_poyang_coord)。

📌 剧本 B：城市基因突变 (Context: yuhang)

意图：审计杭州余杭区城建物理重构。

底层感知：执行欧氏距离算子，剥离季节伪装，计算物理空间重构面积。

目标定位：杭州 · 余杭未来科技城 (city_yuhang_coord)。

📌 剧本 C：行星级零样本聚类 (Context: amazon)

意图：亚马逊雨林自动化切分与监测。

底层感知：启动无监督聚类算法，自动划界森林砍伐与开荒带边界。

目标定位：巴西 · 亚马逊雨林 (forest_amazon_coord)。

5. 前端重构伪代码与工程映射

5.1 门户叙事页 (Landing.vue / Zero2xApp.vue)

实现“虫洞直达”交互逻辑的核心伪代码：

<script setup>
import { useRouter } from 'vue-router'; // 或直接使用 window.location.href

// 1. 定义 V6.0 核心演示场景
const scenarios = [
  { id: 'poyang', label: '国家水网脉动：鄱阳湖生态监测', action: '正在提取 64 维空间特征...' },
  { id: 'yuhang', label: '城市基因突变：杭州余杭城建审计', action: '执行欧氏距离算子...' },
  { id: 'amazon', label: '行星级零样本聚类：亚马逊雨林切分', action: '启动无监督聚类算法...' }
];

const isOmniOpen = ref(false);

// 2. 虫洞直达逻辑：一键跳转真实工作台，绝不冗余逗留
function teleportToWorkbench(scenario) {
  isOmniOpen.value = false;
  // 直接跳转至工作台并携带上下文，废弃原有滚动到 Act 5 的冗余逻辑
  window.location.href = `/workbench?context=${scenario.id}`;
}
</script>

<template>
  <!-- Act 1: Omni-Bar 呼出指令面板 -->
  <div class="omnibar" @click="isOmniOpen = true">
    <input readonly placeholder="请点击选择 V6.0 核心演示场景..." />
    <ul v-if="isOmniOpen" class="dropdown-menu absolute z-50">
       <li v-for="s in scenarios" @click="teleportToWorkbench(s)">
          {{ s.label }} <span class="text-xs text-blue-400">↵ 瞬间部署</span>
       </li>
    </ul>
  </div>
</template>


5.2 核心工作台 (/workbench) 伪代码实现

全面拥抱“全屏底座+悬浮面板”的下一代 UI 架构，目录结构如下：

src/
 ├─ views/
 │   └─ Workbench/             # 真实的全屏悬浮工作台应用
 │       ├─ index.vue          # 工作台主框架，负责解析 ?context=xxx
 │       ├─ components/
 │       │   ├─ AgentFlow.vue  # 左侧对话流 (Absolute 定位，透明磨砂背景)
 │       │   ├─ CodeEditor.vue # 右侧代码区 (Absolute 定位，透明磨砂背景)
 │       │   └─ CommandHUD.vue # 底部时间轴与执行控制器
 │       └─ engines/
 │           ├─ CesiumTwin.vue # 【核心】封装 Cesium，占满全屏 Fixed Inset-0, Z-index: 0
 │           └─ ThreeTwin.vue  # (Phase 2) 天文场景预留
 ├─ stores/
 │   └─ researchStore.js       # 状态管理
 └─ api/
     └─ gee_client.js          # 对接 V6 FastAPI 后端，驱动 Cesium 图层


① 工作台入口：Workbench/index.vue

负责解析 URL 上下文，并统筹底座与 UI 层的叠加。

<script setup>
import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { useResearchStore } from '@/stores/researchStore';
import CesiumTwin from './engines/CesiumTwin.vue';
import AgentFlow from './components/AgentFlow.vue';
import CodeEditor from './components/CodeEditor.vue';

const route = useRoute();
const store = useResearchStore();
const isEngineReady = ref(false);

onMounted(() => {
  // 1. 从 URL 获取上下文（如 'yuhang', 'poyang'）
  const contextId = route.query.context || 'yuhang';
  
  // 2. 初始化 Store 中的业务数据
  store.initScenario(contextId);
});

function handleEngineReady() {
  isEngineReady.value = true;
  // 3. 引擎就绪后，驱动相机飞往目标区域
  store.executeFlyTo();
}
</script>

<template>
  <div class="workbench-container relative w-screen h-screen overflow-hidden bg-black">
    <!-- 底座层 Z-index: 0 -->
    <!-- 关键点：底层必须铺满全屏，负责渲染和接收拖拽事件 -->
    <CesiumTwin class="absolute inset-0 z-0" @ready="handleEngineReady" />

    <!-- 全息 UI 层 Z-index: 10 -->
    <!-- 关键点：使用 pointer-events-none 确保鼠标能穿透空白区域操作地球 -->
    <div class="holographic-ui-layer absolute inset-0 z-10 pointer-events-none flex justify-between p-8">
      
      <!-- 左侧：AI 意图流 (恢复鼠标事件) -->
      <AgentFlow class="pointer-events-auto w-[360px] glass-panel" />

      <!-- 右侧：代码面板 (恢复鼠标事件) -->
      <CodeEditor class="pointer-events-auto w-[400px] glass-panel" />
      
    </div>
  </div>
</template>

<style scoped>
.glass-panel {
  background: rgba(10, 15, 26, 0.4);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
}
</style>


② 孪生底座：CesiumTwin.vue

深度对接 V6.0 FastAPI 后端，实现空间定位与 GEE 图层渲染。

<script setup>
import { onMounted, watch } from 'vue';
import * as Cesium from 'cesium';
import { useResearchStore } from '@/stores/researchStore';

const emit = defineEmits(['ready']);
const store = useResearchStore();
let viewer = null;

onMounted(() => {
  // 1. 初始化 Cesium 无界视窗 (隐藏默认的 Timeline, Geocoder 等原生控件)
  viewer = new Cesium.Viewer('cesiumContainer', {
    terrainProvider: Cesium.createWorldTerrain(),
    baseLayerPicker: false,
    timeline: false,
    animation: false
  });
  
  emit('ready');
});

// 2. 监听 Store 中的动作指令 (实现代码驱动视窗)
watch(() => store.currentAction, async (action) => {
  if (action.type === 'FLY_TO') {
    // 俯冲动画：复用 V6 的经纬度坐标
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(action.lon, action.lat, action.height),
      duration: 3.0
    });
  } 
  else if (action.type === 'RENDER_LAYER') {
    // 加载计算图层 (对齐 V6.0 GEE 后端 Tile URL)
    const layerUrl = `http://localhost:8505/api/tiles/${action.dataset}/{z}/{x}/{y}`;
    const imageryProvider = new Cesium.UrlTemplateImageryProvider({ url: layerUrl });
    viewer.imageryLayers.addImageryProvider(imageryProvider);
  }
});
</script>

<template>
  <div id="cesiumContainer" class="w-full h-full"></div>
</template>


③ AI 悬浮指令台：AgentFlow.vue

负责将大模型的推演过程转化为视觉可见的“打字机”流，增强科技感。

<script setup>
import { useResearchStore } from '@/stores/researchStore';
import { computed } from 'vue';

const store = useResearchStore();
const reportLogs = computed(() => store.chatLogs);

// 触发“执行计算”按钮 (等同于点击 Run)
function triggerExecution() {
  store.dispatchComputeJob();
}
</script>

<template>
  <div class="agent-sidebar flex flex-col h-full">
    <div class="header text-[#00f0ff] text-xs font-bold tracking-widest mb-4">
      021 MODEL FLOW
    </div>
    
    <!-- 对话日志流 -->
    <div class="logs flex-1 overflow-y-auto space-y-4">
      <div v-for="log in reportLogs" :key="log.id" class="msg text-sm text-gray-200">
        <span class="text-[#00f0ff] font-bold">021_BRAIN:</span> 
        <!-- V6 指挥官面板报告，如：异动感知、归因分析，通过打字机特效呈现 -->
        <span class="typewriter-effect">{{ log.content }}</span>
      </div>
    </div>

    <!-- 核心执行枢纽 -->
    <div class="mt-4 pt-4 border-t border-white/10">
      <button 
        @click="triggerExecution" 
        class="w-full py-3 bg-[#00f0ff] text-black font-bold rounded hover:bg-white transition-colors">
        EXECUTE ON TWIN (执行演算)
      </button>
    </div>
  </div>
</template>


开发实施关键点：

极致留白：在 Workbench/index.vue 中，必须保证屏幕正中央至少 40% 的宽度不受任何 UI 组件遮挡，让底层数字地球转动、缩放的视觉冲击力最大化。

事件穿透：除了 Agent 面板和 Code 面板，屏幕其他区域的鼠标事件（Drag, Wheel）必须能够直接穿透到背后的 Cesium canvas 上，保障地图交互的流畅性。


6. 工程落地现状与下一步计划（截至 2026-03-04）

本节用于把“蓝图伪代码”与当前仓库真实实现对齐，便于后续继续按 TDD 门禁推进。

6.1 当前已落地（已通过回归）

- 虫洞直达：Landing 的选择项可直接跳转 `/workbench?context=...`，保证 Landing 轻量、工作台重资产（Cesium/Monaco）仅在 Workbench 懒加载。
- Spatial IDE 主框架：`/workbench` 已实现「全屏引擎底座 + 左右 HUD + 中央 Canvas」结构，并支持 F11 进入沉浸态（Theater）/退出（Lab）。
- 领导可见的“态切换拨片”：顶部中央显性 Mode Toggle（Theater/Lab），并保留 `Cmd/Ctrl+K` 全局 OmniCommand 呼出。
- 带态预置剧本：OmniCommand Presets 支持“一键绑定”场景 + 模式 + Tab（用于演示剧本快速复现）。
- Tab System（真实行为）：Twin/Table/Charts 支持新建/关闭，并通过 `sessionStorage` 持久化与恢复：
  - `z2x:lastTab`（上次激活 Tab）
  - `z2x:openTabs`（打开的 Tab 列表）
- LayerTree（真实行为 + 引擎联动 + 可调参数）：LayerTree 支持 toggle + reorder + opacity/threshold/palette 参数控制，并通过 `sessionStorage` 持久化与恢复 `z2x:layers`；同时已打通到 Cesium：
  - `gee-heatmap` / `anomaly-mask` 使用真实 `UrlTemplateImageryProvider`（同源 `/api/tiles/...`）渲染，并支持 opacity 叠加。
  - `boundaries` 使用同源 GeoJSON（`/api/geojson/boundaries`）以 `GeoJsonDataSource` 渲染，并带 outline/label（默认关闭，可在 LayerTree 手动开启）。
  - LayerTree reorder 会映射到 Cesium imageryLayers 的图层叠放顺序（可真实“调层”）。

近期稳定性补丁（2026-03-04，已回归）：

- 修复“近景看不到底图切片 / AI 图层”的遮挡问题：Workbench 外挂的 imagery overlay 会被识别为业务叠加层，Photorealistic 3D Tiles 会按配置自动 hide/dim，避免遮住底图与 AI 图层。
- 修复“双击/点选边界弹出说明面板与 LayerTree 重叠”：禁用 Cesium 默认 InfoBox/SelectionIndicator（Workbench 使用自有 HUD）。
- 修复 `Entity geometry outlines are unsupported on terrain` warning：GeoJSON load 阶段禁用 stroke，避免 terrain clamp 的 polygon outline 触发一次性警告。
- 强化 `/api/layers?variant=anomaly-mask`：阈值 mask 逻辑与 palette 解析更健壮，避免多 band 影像导致 500。
- Vector Boundaries 默认关闭：首次进入/重置/预置剧本不再自动打开边界层，减少视觉干扰与 UI 重叠概率。

实现位置（与蓝图伪代码的工程映射）：

- Workbench 主容器：`frontend/src/WorkbenchApp.vue`
- 引擎路由/容器（Cesium MVP，Three.js Phase 2）：`frontend/src/views/workbench/EngineRouter.vue`
- Cesium Viewer 封装与 viewer-ready：`frontend/src/components/CesiumViewer.vue`
- 组件：`frontend/src/views/workbench/components/TabBar.vue`、`LayerTree.vue`、`OmniCommand.vue`、`TheaterHUD.vue`
- 后端（tiles + 边界 GeoJSON）：`backend/main.py`（`/api/layers`、`/api/tiles/{tile_id}/{z}/{x}/{y}`、`/api/geojson/boundaries`）

回归状态：

- 前端：`npm test` 全绿（vitest 门禁覆盖 Mode Toggle / Presets / Tabs / LayerTree / sessionStorage keys 等）。
- 后端：`pytest` 全绿（集成类用例按默认策略 skip）。
- 最新交付：已通过 Docker Prod 更新并通过 `make docker-prod-check`（同源 nginx 静态资源 + /api 反代 + /health）。

6.2 当前仍是“演示级”的部分（下一步要升级为“真实业务级”）

- Agent Flow 的“全自动任务编排”仍偏演示：当前 `EXECUTE ON TWIN` 已打通后端 stats/analyze/report 并回填 TheaterHUD，但尚未做到更复杂的多步编排（例如：多图层组合、跨期对比、任务队列/中断/重试、产物下载等）。
- 图层参数目前为 MVP（opacity/threshold/palette），尚未扩展到更完整的业务控制（palette picker、阈值自动建议、图例/色标、时间窗/时相选择、CH4 聚类类别过滤等）。
- 图层类型仍以 imagery + GeoJSON 为主，尚未引入更高级的 primitives/3D Tiles/矢量切片等（留作后续扩展）。

6.3 下一步计划（按优先级）

P0–P2（已完成落地，作为“可复现演示闭环”的基线）：

- P0：`gee-heatmap / boundaries / anomaly-mask` 已接入真实 Cesium 图层（imagery + GeoJSON），不再依赖 entities stub。
- P1：LayerTree reorder 已映射到 Cesium imageryLayers 栈顺序；opacity/threshold/palette 已可控并持久化到 `sessionStorage`。
- P2：Presets 已可绑定 layers；`EXECUTE ON TWIN` 已触发后端 stats/analyze/report 并回填 TheaterHUD（会保证 Twin Tab 与 `gee-heatmap` enabled；`boundaries` 默认不再强制开启）。

下一阶段建议（从“演示闭环”升级到“真实科研作业闭环”）：

- P3：把 Layer 参数升级为“可解释 UI”（图例/色标、分位数阈值建议、时间窗与多时相对比），并将参数从 `sessionStorage` 迁移到更可扩展的 store。
- P4：引入任务队列/中断/重试/缓存策略，让 EXECUTE 支持真正的多步编排（tiles 预热、报告导出、证据链落盘）。

Phase 2（双模态底座）：

- 在 EngineRouter 中保留 Three.js 路径（OneAstronomy/OneGenome），但严格不影响 Cesium 主线的稳定性与首屏加载。