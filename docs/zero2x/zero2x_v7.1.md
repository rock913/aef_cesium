Zero2x 021 v7.2：Copilot 驱动的通用科研工作台与空间交互蓝图

核心愿景：视窗即现场，代码即算力
摒弃传统的单学科工具拼凑，Zero2x 正构建全新的 AI-Native 通用科研工作台。依托 021 基础模型的跨模态推理能力，我们打破了从广袤空天（$10^{20}$m）到微观分子（$10^{-9}$m）的物理壁垒。系统采用**“全尺度万能底座 (Omni-Scale Base) + 显性双态 UI + Copilot 空间智能副驾”**的下一代交互范式。

零、 状态更新与下一步计划 (As-built 跟踪)

本节保留 v7.1 工程约束与交付追踪体系。

已完成（可运行 + 有门禁，截止 2026-03-06）

UI / 交互（前端）

右侧 Copilot Chat 已完成三段式结构：Header / Chat History / Input Zone（chips 紧贴 textarea 上方，气泡左右分离，CoT 手风琴可折叠）。

已落地（v7.1+ 体验升维，前端优先级最高）：

- Global Standby：进入 /workbench 后默认深空轨道视角待机（慢速旋转），不再“进入即跳本地”。
- Intent-Driven Dive：仅在 Copilot 工具事件触发 fly_to/camera_fly_to 后才停止待机并俯冲到目标区域。
- Cmd/Ctrl+K Command Palette：输入区默认折叠胶囊；唤醒后多行自适应 + 毛玻璃指令列表；执行后自动折叠。
- 赛博 HUD 顶栏：顶部导航采用 glass + scanline HUD 视觉（不影响 Twin 拖拽），提供 Lab/Theater 门控、Scale Toggle 与命令面板入口。
- Lab Mode 状态保持：执行流程不再强制切换 Theater；Theater 仅由显式拨片/F11 触发。
- 术语升级：UI 可见文案 Macro → Sky（内部 scale key 仍为 macro，避免破坏数据/逻辑）。

交互细节（补充）：为减少视觉干扰，移除了输入区上方常驻的“演示 chips 条”，演示列表统一收敛到 Cmd/Ctrl+K 的 Command Palette 内。

确保 HUD overlay 默认 pointer-events: none，面板选择性 pointer-events: auto，保证 Twin 可拖拽交互。

Demo 全覆盖（12+2 = 14）

前端场景注册已覆盖 14 个 demo context（含新增 Demo 13 global）。

Backend v7 Copilot stub：/api/v7/prompts 提供 prompt chips；/api/v7/tools 注册“地学工具 + UI 工具”；/api/v7/copilot/execute 确定性路由。

TDD 门禁（已启用）

前端 Vitest：CopilotChatPanel UI 回归测试、场景注册回归测试。

后端 Pytest：v7 Copilot 合同测试。

工具调用 → 结构化产物（Phase 1 最小闭环已落地）

UI 工具定义与执行：add_cesium_imagery/vector, show_chart, generate_report, execute_editor_code 均已在纯函数映射层打通。并能稳定写入左侧的统一资产面板 (Unified Artifacts)。

工具命名兼容：文档中使用的 `fly_to` 与工程内的 `camera_fly_to` 语义一致；后端 tools 列表与前端 handler 均支持两者兼容（推荐蓝图名 `fly_to`；保留 `camera_fly_to` 作为历史/兼容名）。

As-built（补充，截止 2026-03-06）：

- `fly_to` 已作为 `camera_fly_to` 的别名正式进入后端 tools 列表，并在前端 Workbench 事件应用层按同等语义处理。
- 合同门禁已覆盖：后端 tools 列表包含 `fly_to`；前端 Vitest 全绿。

下一步计划 (Phase 2 & 3)

Phase 2：Earth scale 真实打通（以同源瓦片为主）。本仓库不提供 `/api/v1/aef/*`，真实链路以既有 `/api/layers -> /api/tiles/{tile_id}/{z}/{x}/{y}` 为准：

- v7 Copilot execute 优先内部调用 `/api/layers` 获取真实 `tile_url`，并通过 `add_cesium_imagery` 挂载到 Cesium。
- 若 GEE 不可用/返回非 200：必须确定性降级为同源示例 overlay（如 OSM），同时 `generate_report` 解释原因，保证演示链路不崩。
- 后端 Pytest 以“事件形态/工具发射”做合同门禁，不依赖真实 GEE。

As-built（截止 2026-03-06）：Demo 1/3/4/5/周口等已接入上述“真实优先 + 降级可解释”策略；亚马逊 Demo 同时挂载 imagery（真实优先）+ 矢量聚类仍为示例占位。

Phase 3：补齐剩余 Demo 的“可视化最低可用实现（MVR）”。包括 terrain, custom shader, night mode, 3D tiles 等渲染能力，以及 Demo 14 的宏微观双模态虫洞跃迁。

As-built（补充，截止 2026-03-06）：

- 后端 `/api/v7/tools` 已注册 Phase 3 工具：`enable_3d_terrain`, `add_cesium_3d_tiles`, `apply_custom_shader`, `generate_cesium_custom_shader`, `add_cesium_extruded_polygons`, `set_scene_mode`, `play_czml_animation`, `set_globe_transparency`, `add_subsurface_model`, `trigger_gsap_wormhole`。
- 后端 v7 确定性路由已在 Demo 7/11/14 的事件序列中显式发射上述关键工具（MVR 级别，允许 stub result）。
- 前端 Workbench 已能接收并“可见化”这些工具调用（Artifacts 层确定性写入 + Cesium 侧 best-effort 应用：terrain/tileset/night/CZML/透明度/挤出体；虫洞以 macro→micro 量子俯冲动画实现）。
- TDD 门禁已扩展：后端 Pytest 覆盖 Phase 3 tools list + Demo 7/11/14 发射序列；前端 Vitest 覆盖 Phase 3 artifacts 归约逻辑。

一、 架构演进：全尺度万能底座 (Omni-Scale Foundation)

为了全面兼容四大核心学科，工作台底层视窗不再绑定单一引擎，升级为受 021 模型自动调度的**“万能渲染容器”**。

1.1 空天视界 (Sky-Sphere)

🌍 空天态 (Sky / 021-Earth)：引擎 CesiumJS。处理全球地形、卫星遥感特征与天基算力投射。

🌌 天文态 (OneAstronomy / 021-Space)：引擎 Three.js。渲染星系、宇宙微波背景与引力波。

1.2 微观深潜 (Micro-Sphere)

🧬 基因态 (OneGenome / 021-Bio)：引擎 Three.js。分子晶格与 DNA 构象预测。

🧊 材料态 (OnePorous / 021-Material)：引擎 Three.js。航天材料应力拓扑分析。

二、 UI 架构重构：空间计算 IDE (Spatial IDE)

全面汲取 Cursor 与 VS Code 的精髓，采用严格的**“左-中-右”流式网格系统**，同时结合大屏演示诉求引入**“双态引擎”**。

2.1 界面双态引擎 (Dual-State UI) 与显性演示门控

系统顶栏设计了极具科技感的**“状态切换拨片”**，解耦了场景执行与 UI 状态，将控制权完全交还给演示者：

🛠️ 硬核作业态 (Lab Mode - 默认)：左右实体面板停靠，呈现代码、产物与 Agent 思维链，展示系统“白盒可解释性”。

🎬 沉浸演示态 (Theater Mode)：一键折叠两侧面板，3D 视窗铺满 100vw/100vh，专为领导视察与大屏投屏设计。

2.2 全局视界降临 (Global-to-Local Spatial Flow)

初始降临 (Global Standby)：进入 /workbench 后，Cesium 始终默认悬停于“宏观地球轨道视角”，不急于切入局部。

意图驱动俯冲 (Intent-Driven FlyTo)：在 Copilot 执行指令后，才触发 flyTo 动画，从太空急速俯冲至目标区域，保留完美的空间连续性。

2.3 严谨的三栏流式布局 (Left-Center-Right)

【左侧】统一资产与产物面板 (Unified Artifacts)：宽 360px。

LAYER & DATA: 管理 GEE 图层、阈值、色标。

CODE & SCRIPT: 收纳 Monaco Editor，展示 AI 生成的底层渲染或推演代码。

CHARTS / REPORTS: 存放统计图表与自动生成的 Markdown 分析报告。

【中央】无界空间底座 (The Twin Canvas)：

Flex 自适应撑满。纯净的三维宇宙/地球，仅悬浮时间轴或极简控件。

【右侧】021 Copilot Chat (空间智能中枢)：宽 400px。

Top (Header)：折叠控制与标题。

Middle (History)：气泡式对话流 + 折叠式思维链 (CoT)。

Bottom (Input Zone)：自适应多行文本框 (完美容纳复杂 Prompt)，紧贴上方悬浮横向滚动的 Prompt Chips (预置剧本胶囊)。

三、 核心 Demo 场景大盘与技术实现 (12+2 全矩阵)

注：本节融合 v7.1 定义的所有 Tool Calling API 逻辑，确保演示链路闭环。

🌍 第一阵列：经典传承 (OneEarth 6 大核心场景)

Demo 1: 沧海桑田的城建审计 (杭州余杭)

Prompt: "对比余杭近7年的城建扩张，使用欧氏距离算子，生成城建审计图层。"

Tools Call: aef_compute_diff(roi='yuhang', metric='euclidean', dim='A00')

UI Action: fly_to/camera_fly_to -> add_cesium_imagery(palette='Oranges') -> generate_report()

Demo 2: 行星级零样本聚类 (亚马逊雨林)

Prompt: "扫描当前视窗，不使用先验标签，根据 64维特征进行零样本聚类(k=6)。"

Tools Call: aef_kmeans_cluster(bbox=current_bbox, k=6)

UI Action: add_cesium_vector(color_map='category_6')

Demo 3: 剥离季节伪装的生态穿透 (毛乌素沙地)

Prompt: "评估毛乌素近5年真实治理成效，改用余弦相似度排除秋冬植被枯黄干扰。"

Tools Call: aef_compute_diff(metric='cosine_similarity')

UI Action: add_cesium_imagery(palette='Greens')

(Demo 4 盐城红线, Demo 5 周口内涝, Demo 6 塔拉滩光伏 - 实现逻辑参照 V7.1 规范稳定集成入系统)

🚀 第二阵列：前沿开拓 (空天视界 6 大全新场景)

Demo 7: 冰原溃决预警 (珠峰) -> enable_3d_terrain + add_cesium_3d_tiles

Demo 8: 地壳形变与火山预判 (夏威夷) -> apply_custom_shader(InSAR+LST)

Demo 9: 全球碳汇三维估算 (刚果) -> add_cesium_extruded_polygons

Demo 10: 城市热岛与社会折叠 (纽约) -> show_chart + render_bivariate_map

Demo 11: 暗夜油污与船舶溯源 (马六甲) -> set_scene_mode('night') + play_czml_animation

Demo 12: 极深地下矿脉解译 (澳洲) -> set_globe_transparency(0.5) + add_subsurface_model

🔮 第三阵列：极客炫技 (系统级架构张力)

Demo 13: 气象流体力学代码热生成 (Global)

Prompt: "用 GLSL 写一段基于 GFS 数据的全球风场流体渲染代码，直接运行。"

Tools Call: LLM 生成自定义着色器代码。

UI Action: write_to_editor() (写入左侧 Code Tab) -> execute_editor_code()。

Demo 14: 宏微观双模态虫洞跃迁 (Sky to Micro)

Prompt: "地表分析完毕，挂载微观物理引擎，生成该岩石的二氧化硅分子晶体结构。"

UI Action: trigger_gsap_wormhole() -> 销毁 Cesium -> 挂载 Three.js (Micro-Sphere) -> 切换左侧资产面板模式。

四、 核心架构重构伪代码 (Vue 3 组合式 API)

4.1 主工作台布局（示意伪代码；实际实现以 frontend/src/WorkbenchApp.vue 为准）

集成了显性双态拨片与左中右动态面板布局。

<script setup>
import { ref } from 'vue';
import EngineRouter from './engines/EngineRouter.vue'; // 实际工程中由 EngineScaleRouter/EngineRouter 组合封装
import ArtifactsPanel from './components/ArtifactsPanel.vue';
import CopilotChatPanel from './components/CopilotChatPanel.vue';

// 默认硬核作业态，保留 IDE 专业感
const isTheaterMode = ref(false); 

function setMode(mode) {
  isTheaterMode.value = mode === 'theater';
}
</script>

<template>
  <div class="h-screen w-screen bg-[#030409] flex flex-col text-white overflow-hidden font-sans">
    
    <!-- 🌟 赛博顶栏：包含显性双态切换拨片 -->
    <header class="h-14 border-b border-[#00F0FF]/20 flex justify-between items-center px-6 bg-[#050810]/90 backdrop-blur-md relative z-50">
      <div class="flex items-center gap-4">
        <div class="w-2 h-2 rounded-full bg-[#00F0FF] animate-pulse shadow-[0_0_8px_#00F0FF]"></div>
        <span class="text-xl font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-[#00F0FF] to-[#9D4EDD]">
          ZERO2X <span class="text-xs font-bold text-gray-200">021 WORKBENCH</span>
        </span>
      </div>
      
      <!-- 显性演示门控 -->
      <div class="flex bg-black/60 p-1 rounded-lg border border-white/10">
        <button @click="setMode('lab')" :class="!isTheaterMode ? 'bg-[#9D4EDD] text-white font-bold' : 'text-gray-500'" class="px-5 py-1.5 rounded-md text-xs transition-all">
          🛠️ 硬核作业视图
        </button>
        <button @click="setMode('theater')" :class="isTheaterMode ? 'bg-[#00F0FF] text-black font-bold' : 'text-gray-500'" class="px-5 py-1.5 rounded-md text-xs transition-all">
          🎬 沉浸推演视图
        </button>
      </div>
    </header>

    <!-- 核心 IDE 三栏布局 -->
    <div class="flex-1 flex overflow-hidden relative">
      
      <!-- 左侧：统一资产面板 (Layers / Code / Charts / Reports) -->
      <aside :class="isTheaterMode ? '-translate-x-full opacity-0 w-0' : 'w-[360px] opacity-100'" class="border-r border-white/10 bg-[#080b12] flex-shrink-0 transition-all duration-500 z-10">
        <ArtifactsPanel />
      </aside>

      <!-- 中间：无界万能底座 (默认 Global Standby) -->
      <main class="flex-1 relative bg-black">
        <EngineRouter class="absolute inset-0" />
      </main>

      <!-- 右侧：021 Copilot Chat 中枢 -->
      <aside :class="isTheaterMode ? 'translate-x-full opacity-0 w-0' : 'w-[400px] opacity-100'" class="border-l border-white/10 bg-[#080b12] flex-shrink-0 transition-all duration-500 z-10 flex flex-col">
        <CopilotChatPanel />
      </aside>

    </div>
  </div>
</template>


4.2 空间智能副驾面板（示意伪代码；实际实现以 frontend/src/views/workbench/components/CopilotChatPanel.vue 为准）

集成了气泡历史流、可折叠 CoT，以及带有动态横向预置 Chips 和多行自适应的输入区。

<script setup>
import { ref } from 'vue';
import { useCopilotStore } from '@/stores/copilotStore';

const store = useCopilotStore();
const promptText = ref('');
const textareaRef = ref(null);

// 动态高度计算：最大支持 120px
function autoResize() {
  const el = textareaRef.value;
  if(!el) return;
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function handleChipClick(scenario) {
  promptText.value = scenario.prompt;
  autoResize();
  submitPrompt(scenario.id);
}

function submitPrompt(forcedContextId = null) {
  if(!promptText.value.trim()) return;
  // 派发指令：后端执行逻辑，触发 UI Tool Events (如 flyTo, add_imagery)
  store.executeCopilotCommand(promptText.value, forcedContextId);
  promptText.value = '';
  textareaRef.value.style.height = 'auto'; // 恢复初始高度
}
</script>

<template>
  <div class="flex flex-col h-full w-full">
    <!-- Header -->
    <div class="h-12 border-b border-white/10 flex justify-between items-center px-4">
      <span class="text-xs font-bold tracking-widest text-[#00F0FF]">021 COPILOT</span>
      <span class="text-[10px] text-gray-500">Connected to Nanhu Hub</span>
    </div>

    <!-- Message History (气泡流 + CoT) -->
    <div class="flex-1 overflow-y-auto p-4 space-y-4">
      <div v-for="msg in store.chatHistory" :key="msg.id">
        <!-- 用户气泡 (右侧) -->
        <div v-if="msg.role === 'user'" class="ml-auto bg-[#00F0FF]/20 text-[#00F0FF] p-3 rounded-l-xl rounded-tr-xl max-w-[85%] text-sm">
          {{ msg.content }}
        </div>
        
        <!-- AI 气泡 (左侧) -->
        <div v-else class="mr-auto bg-white/5 text-gray-200 p-3 rounded-r-xl rounded-tl-xl max-w-[90%] text-sm border border-white/10">
          
          <!-- 手风琴：折叠的 Tool Calling 过程 (CoT) -->
          <details v-if="msg.tools" class="mb-2 bg-black/40 border border-white/5 rounded p-2 text-xs">
            <summary class="cursor-pointer text-gray-400 font-bold outline-none">
              ✓ 分析已完成 (耗时 {{ msg.latency }}s)
            </summary>
            <div class="mt-2 text-gray-500 pl-4 border-l-2 border-gray-700">
              > Action: fly_to(yuhang)<br>
              > Call: aef_compute_diff(dim='A00')<br>
              > Action: add_cesium_imagery(Oranges)<br>
            </div>
          </details>

          <!-- 最终模型推演回复 -->
          <div class="leading-relaxed">{{ msg.content }}</div>
        </div>
      </div>
    </div>

    <!-- Input Zone (横向 Chips + 多行自适应输入) -->
    <div class="p-4 bg-[#0a0f1a] border-t border-white/10">
      <!-- 预置指令胶囊 -->
      <div class="flex overflow-x-auto hide-scrollbar gap-2 pb-2">
        <button v-for="chip in store.promptChips" :key="chip.id" 
                @click="handleChipClick(chip)"
                class="px-3 py-1.5 bg-white/5 hover:bg-[#00F0FF]/20 rounded-full whitespace-nowrap text-xs text-[#00F0FF] border border-[#00F0FF]/20 transition-colors">
          ✨ {{ chip.shortLabel }}
        </button>
      </div>

      <!-- 自适应多行框 -->
      <div class="relative mt-1">
        <textarea 
          ref="textareaRef"
          v-model="promptText"
          @input="autoResize"
          @keydown.enter.prevent="submitPrompt()"
          rows="1"
          class="w-full bg-black/50 border border-white/20 hover:border-[#00F0FF]/50 focus:border-[#00F0FF] rounded-lg pl-3 pr-10 py-3 text-sm text-white placeholder-gray-500 resize-none outline-none transition-colors"
          placeholder="输入意图，例如：审计余杭区城建物理重构..."></textarea>
        
        <button @click="submitPrompt()" class="absolute right-3 bottom-3 text-[#00F0FF] hover:text-white transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hide-scrollbar::-webkit-scrollbar { display: none; }
.hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
</style>
