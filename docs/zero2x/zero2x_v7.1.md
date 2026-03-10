Zero2x 021 v7.1+（蓝图 v7.2 草案）：Copilot 驱动的通用科研工作台与空间交互蓝图

核心愿景：视窗即现场，代码即算力
摒弃传统的单学科工具拼凑，Zero2x 正构建全新的 AI-Native 通用科研工作台。依托 021 基础模型的跨模态推理能力，我们打破了从广袤空天（$10^{20}$m）到微观分子（$10^{-9}$m）的物理壁垒。系统采用**“全尺度万能底座 (Omni-Scale Base) + 显性双态 UI + Copilot 空间智能副驾”**的下一代交互范式。

零、 状态更新与下一步计划 (As-built 跟踪)

本节保留 v7.1 工程约束与交付追踪体系。

已完成（可运行 + 有门禁，截止 2026-03-05）

UI / 交互（前端）

右侧 Copilot Chat 已完成三段式结构：Header / Chat History / Input Zone（Command Palette + 可展开多行输入，气泡左右分离，CoT 手风琴可折叠）。

确保 HUD overlay 默认 pointer-events: none，面板选择性 pointer-events: auto，保证 Twin 可拖拽交互。

AI Vector Overlay 默认关闭（避免遮挡与残留），仅在工具调用需要时临时启用；切换场景/预置时会自动清空并关闭。

Demo 全覆盖（12+3 = 15）

前端场景注册已覆盖 15 个 demo context（含新增 Demo 15 terminator_shield 纯视觉炫技场景）。

Backend v7 Copilot stub：/api/v7/prompts 提供 prompt presets（供 Command Palette 调用）；/api/v7/tools 注册“地学工具 + UI 工具”；/api/v7/copilot/execute 确定性路由。

TDD 门禁（已启用）

前端 Vitest：CopilotChatPanel UI 回归测试、场景注册回归测试。

后端 Pytest：v7 Copilot 合同测试。

工具调用 → 结构化产物（Phase 1 最小闭环已落地）

UI 工具定义与执行：add_cesium_imagery/vector, show_chart, generate_report, execute_editor_code 均已在纯函数映射层打通。并能稳定写入左侧的统一资产面板 (Unified Artifacts)。

下一步计划 (Phase 2 & 3)

Phase 2：Demo 1–3 真实打通（先 Earth scale）。对接 /api/v1/aef/compute_diff 等真实算子，拿到真实 tile url / geojson 并触发 UI 挂载。后端 Pytest 需覆盖真实 Tool Emissions。

Phase 3：补齐剩余 Demo 的“可视化最低可用实现（MVR）”。包括 terrain, custom shader, night mode, 3D tiles 等渲染能力，以及 Demo 14/15 的高维空间异象与双模态虫洞跃迁。

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

Landing 直达：若从首页以 `/workbench?context=<scene>` 深链进入指定场景，则在 Viewer Ready 后执行一次自动 FlyTo（等价于“在 Workbench 内选择场景”），避免只停留在全局地球。

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

Bottom (Input Zone)：Command Palette（Cmd/Ctrl+K）入口 + 可展开多行文本框（完美容纳复杂 Prompt），预置场景以 Palette 列表呈现（替代横向 chips）。

三、 核心 Demo 场景大盘与技术实现 (12+3 全矩阵)

注：本节融合 v7.1 定义的所有 Tool Calling API 逻辑，确保演示链路闭环。

🌍 第一阵列：经典传承 (OneEarth 6 大核心场景)

Demo 1: 沧海桑田的城建审计 (杭州余杭)

Prompt: "对比余杭近7年的城建扩张，使用欧氏距离算子，生成城建审计图层。"

Tools Call: aef_compute_diff(roi='yuhang', metric='euclidean', dim='A00')

UI Action: fly_to -> add_cesium_imagery(palette='Oranges') -> generate_report()

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

🌟 Demo 15: 轨道晨昏线异象 —— 太阳风暴与行星磁盾推演 (Sky-Sphere Showpiece)

场景定位：深空轨道视角 (Global Terminator View)，专为汇报视觉震撼与响应第二幕“从深空暗场到轨道晨昏线”主题而设。

Prompt: "锁定地球晨昏线视角。模拟一次深空 X 级太阳风暴冲击，渲染行星磁层（Magnetosphere）防御力场及极光折射效应。"

执行逻辑 (无数据纯算力炫技)：
前端内置一套纯数学/程序化的 shader + 场线/辉光效果（无需后端瓦片数据），由 Copilot 工具调用确定性触发挂载。

Copilot 执行流 (伪代码)：

# 1) 切换到 Sky/Macro (Three.js 引擎)
await ui.switch_scale('macro')

# 2) 启用纯视觉炫技层：终结线 + 磁层护盾
await ui.show_terminator_shield(enabled=True, intensity=1.0)

# 3) 镜头环绕以展示体积感与辉光
await ui.spin_macro_camera(duration=6.5, revolutions=0.85)


四、 核心架构重构伪代码 (Vue 3 组合式 API)

4.1 主工作台布局 (Workbench/index.vue)

集成了显性双态拨片与左中右动态面板布局。

<script setup>
import { ref } from 'vue';
import EngineRouter from './engines/EngineRouter.vue';
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


4.2 空间智能副驾面板 (CopilotChatPanel.vue)

集成了气泡历史流、可折叠 CoT，以及“Command Palette（Cmd/Ctrl+K）+ 可展开多行输入框”的组合（预置场景以 Palette 列表呈现）。

<script setup>
import { ref } from 'vue';
import { useCopilotStore } from '@/stores/copilotStore';

const store = useCopilotStore();
const promptText = ref('');
const textareaRef = ref(null);

const composerExpanded = ref(false);
const paletteOpen = ref(false);

// 动态高度计算：最大支持 120px
function autoResize() {
  const el = textareaRef.value;
  if(!el) return;
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function submitPrompt(forcedContextId = null) {
  if(!promptText.value.trim()) return;
  // 派发指令：后端执行逻辑，触发 UI Tool Events (如 flyTo, add_imagery)
  store.executeCopilotCommand(promptText.value, forcedContextId);
  promptText.value = '';
  textareaRef.value.style.height = 'auto'; // 恢复初始高度
}

function openPalette() {
  paletteOpen.value = true;
  composerExpanded.value = true;
}

function applyPreset(preset) {
  promptText.value = preset.prompt;
  autoResize();
  submitPrompt(preset.context_id || null);
  paletteOpen.value = false;
  composerExpanded.value = false;
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

    <!-- Input Zone (Command Palette + 多行自适应输入) -->
    <div class="p-4 bg-[#0a0f1a] border-t border-white/10">
      <!-- Command Palette 入口（胶囊） -->
      <button v-if="!composerExpanded" @click="openPalette()" class="px-3 py-2 w-full bg-white/5 hover:bg-white/10 rounded-lg text-left text-xs text-[#00F0FF] border border-[#00F0FF]/20 transition-colors">
        <span class="opacity-70">Cmd/Ctrl+K</span> · Command Palette / 多行输入…
      </button>

      <!-- 展开输入：自适应多行框 -->
      <div v-else class="relative mt-1">
        <textarea
          ref="textareaRef"
          v-model="promptText"
          @input="autoResize"
          rows="2"
          class="w-full bg-black/50 border border-white/20 hover:border-[#00F0FF]/50 focus:border-[#00F0FF] rounded-lg pl-3 pr-10 py-3 text-sm text-white placeholder-gray-500 resize-none outline-none transition-colors"
          placeholder="输入意图… (Enter 发送 / Shift+Enter 换行 / Cmd+K 指令面板)"
        ></textarea>

        <button @click="submitPrompt()" class="absolute right-3 bottom-3 text-[#00F0FF] hover:text-white transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>
        </button>
      </div>

      <!-- Palette 列表（预置剧本） -->
      <div v-if="paletteOpen" class="mt-2 bg-black/60 border border-white/10 rounded-lg overflow-hidden">
        <button v-for="p in store.promptPresets" :key="p.id" @click="applyPreset(p)" class="block w-full text-left px-3 py-2 hover:bg-white/5">
          <div class="text-xs text-white">{{ p.label }}</div>
          <div class="text-[10px] text-gray-400 truncate">{{ p.prompt }}</div>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hide-scrollbar::-webkit-scrollbar { display: none; }
.hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
</style>
