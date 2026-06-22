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

以下为 Landing Page (Zero2xApp.vue) 实现“虫洞直达”交互逻辑的核心伪代码：

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


目标工作台 (/workbench) 工程拆解建议

全面拥抱“全屏底座+悬浮面板”的下一代 UI 架构：

src/
 ├─ views/
 │   ├─ Landing.vue            # 门户叙事 (前四幕+兜底第五幕)
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


开发实施关键点：

极致留白：在 Workbench/index.vue 中，必须保证屏幕正中央至少 40% 的宽度不受任何 UI 组件遮挡，让底层数字地球转动、缩放的视觉冲击力最大化。

事件穿透：除了 Agent 面板和 Code 面板，屏幕其他区域的鼠标事件（Drag, Wheel）必须能够直接穿透到背后的 Cesium canvas 上，保障地图交互的流畅性。