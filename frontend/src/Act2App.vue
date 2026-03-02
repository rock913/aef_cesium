<template>
  <div class="act2" data-testid="act2">
    <CesiumViewer
      ref="cesiumViewer"
      :initial-location="initialLocation"
      @viewer-ready="onViewerReady"
    />

    <div class="hud" :class="{ open: hudOpen }" aria-label="Act2 HUD">
      <button
        class="hud-toggle"
        type="button"
        @click="hudOpen = !hudOpen"
        :aria-expanded="hudOpen ? 'true' : 'false'"
        aria-controls="act2-hud-panel"
        title="Toggle HUD"
      >
        {{ hudOpen ? 'Close' : 'Menu' }}
      </button>

      <div class="hud-mini" @click="hudOpen = true" title="Open HUD">
        <div class="title">第二幕：宏观孪生</div>
        <div class="hint">
          <span class="pill">{{ activeChoreo || 'poyang' }}</span>
          <span class="sep">·</span>
          <span class="pill">{{ activeStep }}</span>
        </div>
      </div>

      <div v-show="hudOpen" id="act2-hud-panel" class="hud-panel">
        <div class="sub">Scroll-driven narrative · Deep space → Earth → Target</div>

        <div class="row">
          <a class="btn secondary" href="/">Back to Landing</a>
          <a class="btn secondary" href="/demo">Open Demo (Missions)</a>
          <button class="btn" type="button" :disabled="!viewerReady" @click="replay">Replay FlyTo</button>
        </div>

        <div class="targets" aria-label="Act2 targets">
          <button
            v-for="t in targets"
            :key="t.id"
            class="chip"
            type="button"
            :class="{ active: (activeChoreo || 'poyang') === t.id }"
            @click="setTarget(t.id)"
            :disabled="!viewerReady"
            :title="t.title"
          >
            {{ t.label }}
          </button>
        </div>
      </div>
    </div>

    <transition name="fade-up">
      <div v-if="viewerReady" class="info" :key="activeStep" aria-live="polite">
        <div class="info-k">{{ infoK }}</div>
        <div class="info-h">{{ infoH }}</div>
        <div class="info-p" v-for="(line, i) in infoLines" :key="i">{{ line }}</div>

        <div class="info-actions">
          <button class="btn" type="button" :disabled="!viewerReady" @click="replay">Replay</button>
          <a class="btn secondary" href="/demo">Open Demo</a>
          <button
            v-if="activeStep === 'summary'"
            class="btn"
            type="button"
            :disabled="!viewerReady"
            @click="goWorkbench"
            title="Generate an agent in the workbench"
          >
            在工作台中生成专属 Agent
          </button>
        </div>
      </div>
    </transition>

    <div class="scrolly" ref="scrollyEl" aria-label="Act 2 scrollytelling">
      <section class="card" data-act2-step="space" :data-active="activeStep === 'space'">
        <div class="k">Scene 1</div>
        <div class="h">Deep Space</div>
        <div class="p">
          你在深空中看到地球：宏观尺度先行。
        </div>
      </section>

      <section class="card" data-act2-step="earth" :data-active="activeStep === 'earth'">
        <div class="k">Scene 2</div>
        <div class="h">Earth Orbit</div>
        <div class="p">
          进入轨道视角，建立“地理上下文”。
        </div>
      </section>

      <section class="card" data-act2-step="target" :data-active="activeStep === 'target'">
        <div class="k">Scene 3</div>
        <div class="h">Target Lock</div>
        <div class="p">
          飞向目标区域：<span class="pill">{{ activeChoreo || 'poyang' }}</span>
        </div>
        <div class="p subtle">Tip: append <span class="pill">?choreo=poyang</span> to change target.</div>

        <div class="tour" aria-label="Recommended tours">
          <div class="tour-title">Recommended Path</div>
          <div class="tour-row">
            <button
              v-for="t in tours"
              :key="t.id"
              class="tour-btn"
              type="button"
              :disabled="!viewerReady || tourRunning"
              @click="playTour(t)"
              :title="t.title"
            >
              {{ t.label }}
            </button>
            <button
              v-if="tourRunning"
              class="tour-btn secondary"
              type="button"
              :disabled="!viewerReady"
              @click="stopTour"
              title="Stop tour"
            >
              Stop
            </button>
          </div>
          <div v-if="tourRunning" class="tour-status">
            Playing: <span class="pill">{{ tourStatus }}</span>
          </div>
        </div>
      </section>

      <section class="card" data-act2-step="summary" :data-active="activeStep === 'summary'">
        <div class="k">Scene 4</div>
        <div class="h">Recap</div>
        <div class="p">
          这是叙事页：只负责镜头与信息提示。验证与任务流请去 <a class="link" href="/demo">/demo</a>；生成 Agent 与代码工作流请去 <a class="link" href="/workbench">/workbench</a>。
        </div>

        <div class="tour" aria-label="Next step">
          <div class="tour-title">Next</div>
          <div class="tour-row">
            <button class="tour-btn" type="button" :disabled="!viewerReady" @click="goWorkbench">
              在工作台中生成专属 Agent
            </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import CesiumViewer from './components/CesiumViewer.vue'
import { getChoreoFromSearch } from './utils/choreo.js'
import { applyAct2Step, pickDominantAct2Entry } from './utils/act2Timeline.js'
import { navigateWithFade } from './utils/navFade.js'

const cesiumViewer = ref(null)
const viewerReady = ref(false)
const scrollyEl = ref(null)
let observer = null

const initialLocation = computed(() => {
  // Start from a far view (deep space feel). CesiumViewer will hide photorealistic tiles in far view.
  return { lat: 35.0, lon: 105.0, height: 45_000_000 }
})

const activeChoreo = ref('')
const activeStep = ref('space')
const lastIntent = ref('')

const targets = [
  { id: 'poyang', label: 'Poyang', title: '鄱阳湖（poyang）' },
  { id: 'yancheng', label: 'Yancheng', title: '盐城湿地（yancheng）' },
  { id: 'yangtze', label: 'Yangtze', title: '长三角（yangtze）' },
]

const tours = [
  {
    id: 'delta-trip',
    label: 'Delta Trip',
    title: 'poyang → yancheng → yangtze',
    targets: ['poyang', 'yancheng', 'yangtze'],
  },
  {
    id: 'coast-hop',
    label: 'Coast Hop',
    title: 'yancheng → yangtze',
    targets: ['yancheng', 'yangtze'],
  },
]

const tourRunning = ref(false)
const tourStatus = ref('')
let tourToken = 0

const hudOpen = ref(false)

const infoCopy = computed(() => {
  const step = activeStep.value
  const choreo = String(activeChoreo.value || 'poyang').trim().toLowerCase() || 'poyang'

  if (step === 'target' && choreo === 'poyang') {
    const q = String(lastIntent.value || '').trim()
    return {
      k: 'CASE / POYANG',
      h: '地理人工智能助力候鸟研究与鄱阳湖流域保护',
      lines: [
        q ? `你的问题：${q}` : '你的问题将被带入工作流（MVP：先展示为叙事提示）。',
        '“依山云纪”候鸟科学家助手整合了文献检索增强生成（RAG）数据库、候鸟知识图谱（7.2 万+节点）及多模态模型。',
        '它可以通过图像识别鸟类物种，并结合时序遥感/水文数据，为栖息地变化与保护策略提供证据。',
      ],
    }
  }

  if (step === 'summary') {
    return {
      k: 'CINEMATIC / 04',
      h: 'Recap',
      lines: ['第二幕负责“看到”。', '去 /demo 做验证与任务流；去 /workbench 生成 Agent 与代码。'],
    }
  }

  const base = {
    space: {
      k: 'CINEMATIC / 01',
      h: 'Deep Space',
      lines: ['宏观尺度先行：先看见系统，再进入细节。', '滚动推进分镜，镜头会随之变化。'],
    },
    earth: {
      k: 'CINEMATIC / 02',
      h: 'Earth Orbit',
      lines: ['轨道视角建立上下文：地理、尺度、方向。', '这里不做任务流，只做叙事镜头与提示。'],
    },
    target: {
      k: 'CINEMATIC / 03',
      h: 'Target Lock',
      lines: ['飞向目标区域：把“空间”收敛为“地点”。', '需要验证/分析/图层？请切到 /demo。'],
    },
  }
  return base[step] || { k: 'CINEMATIC', h: 'Scene', lines: [] }
})

const infoK = computed(() => infoCopy.value.k)
const infoH = computed(() => infoCopy.value.h)
const infoLines = computed(() => infoCopy.value.lines)

function goWorkbench() {
  navigateWithFade('/workbench', { reason: 'act2-to-workbench', delayMs: 520 })
}

function _readChoreoFromUrl() {
  try {
    return getChoreoFromSearch(window.location.search) || ''
  } catch (_) {
    return ''
  }
}

function _writeChoreoToUrl(name) {
  try {
    const url = new URL(window.location.href)
    url.searchParams.set('choreo', String(name || 'poyang'))
    window.history.replaceState({}, '', url.toString())
  } catch (_) {
    // ignore
  }
}

function setTarget(name) {
  const next = String(name || '').trim().toLowerCase() || 'poyang'
  activeChoreo.value = next
  _writeChoreoToUrl(next)
  _applyStep(activeStep.value)
}

function stopTour() {
  tourToken += 1
  tourRunning.value = false
  tourStatus.value = ''
}

function playTour(tour) {
  if (!viewerReady.value) return
  const list = Array.isArray(tour?.targets) ? tour.targets : []
  if (!list.length) return

  stopTour()
  tourRunning.value = true
  const token = tourToken

  // Keep the narrative coherent: always replay the full step sequence per target.
  // This is intentionally simple and deterministic; later we can make a finer-grained timeline.
  let i = 0
  const tick = () => {
    if (token !== tourToken) return
    const next = list[i]
    if (!next) {
      stopTour()
      return
    }

    tourStatus.value = next
    setTarget(next)
    replay()

    i += 1
    // replay() runs ~2s; give it a little buffer.
    setTimeout(tick, 2600)
  }

  tick()
}

function _applyStep(stepId) {
  if (!viewerReady.value) return
  try {
    applyAct2Step(cesiumViewer.value, stepId, activeChoreo.value || 'poyang')
  } catch (_) {
    // ignore
  }
}

function _setupObserver() {
  if (!scrollyEl.value) return
  if (typeof IntersectionObserver === 'undefined') return

  try {
    observer?.disconnect?.()
  } catch (_) {
    // ignore
  }

  const root = scrollyEl.value
  const sections = Array.from(root.querySelectorAll('[data-act2-step]'))
  if (!sections.length) return

  observer = new IntersectionObserver(
    (entries) => {
      const best = pickDominantAct2Entry(entries)
      const step = best?.target?.dataset?.act2Step || ''
      if (!step) return
      if (step === activeStep.value) return
      activeStep.value = step
      _applyStep(step)
    },
    {
      root,
      threshold: [0.15, 0.35, 0.55, 0.75],
    }
  )

  for (const el of sections) observer.observe(el)
}

function onViewerReady() {
  viewerReady.value = true

  // Default: keep a calm orbit rotation in deep space until choreo is triggered.
  try {
    cesiumViewer.value?.startGlobalRotation?.()
  } catch (_) {
    // ignore
  }

  // Initialize target + step.
  activeChoreo.value = _readChoreoFromUrl() || 'poyang'
  _applyStep(activeStep.value)
}

function replay() {
  // Replay as a short scroll-timeline sequence.
  const seq = ['space', 'earth', 'target', 'summary']
  let i = 0
  const run = () => {
    const step = seq[i]
    if (!step) return
    activeStep.value = step
    _applyStep(step)
    i += 1
    if (i < seq.length) setTimeout(run, 650)
  }
  run()
}

onMounted(() => {
  try {
    lastIntent.value = window.sessionStorage?.getItem?.('z2x:lastIntent') || ''
  } catch (_) {
    lastIntent.value = ''
  }

  try {
    document.body.style.overflow = 'hidden'
  } catch (_) {
    // ignore
  }

  // Set initial target early so the UI pills show correctly.
  activeChoreo.value = _readChoreoFromUrl() || 'poyang'

  // Cinematic default: keep HUD collapsed.
  hudOpen.value = false

  // Observer wires scroll to narrative steps.
  _setupObserver()
})

watch(scrollyEl, () => {
  _setupObserver()
})

onBeforeUnmount(() => {
  stopTour()
  try {
    observer?.disconnect?.()
  } catch (_) {
    // ignore
  }

  try {
    document.body.style.overflow = 'auto'
  } catch (_) {
    // ignore
  }
})
</script>

<style scoped>
.act2 {
  width: 100vw;
  height: 100vh;
  position: relative;
  overflow: hidden;
}

.hud {
  position: absolute;
  left: 14px;
  top: 14px;
  z-index: 2600;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  max-width: min(560px, calc(100vw - 28px));
  pointer-events: auto;
}

.hud-toggle {
  flex: 0 0 auto;
  padding: 10px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(10, 15, 25, 0.52);
  backdrop-filter: blur(12px);
  color: rgba(255, 255, 255, 0.92);
  font-weight: 900;
  letter-spacing: 0.2px;
  cursor: pointer;
}

.hud-mini {
  padding: 10px 12px;
  border-radius: 16px;
  background: rgba(10, 15, 25, 0.50);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(12px);
  box-shadow:
    0 18px 70px rgba(0, 0, 0, 0.35),
    inset 0 0 0 1px rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.92);
  cursor: pointer;
}

.hud-panel {
  margin-top: 0;
  padding: 12px;
  border-radius: 18px;
  background:
    radial-gradient(520px 240px at 20% 20%, rgba(0, 240, 255, 0.08), transparent 60%),
    rgba(10, 15, 25, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(14px);
  box-shadow:
    0 18px 70px rgba(0, 0, 0, 0.35),
    inset 0 0 0 1px rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.92);
}

.info {
  position: absolute;
  left: 14px;
  bottom: 14px;
  z-index: 2550;
  padding: 14px;
  border-radius: 18px;
  background: rgba(10, 15, 25, 0.68);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(12px);
  color: rgba(255, 255, 255, 0.92);
  max-width: min(520px, calc(100vw - 28px));
  pointer-events: auto;
}

.info-k {
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 1.2px;
  opacity: 0.72;
}

.info-h {
  margin-top: 6px;
  font-size: 18px;
  font-weight: 900;
  letter-spacing: 0.2px;
}

.info-p {
  margin-top: 8px;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.55;
  opacity: 0.9;
}

.info-actions {
  margin-top: 12px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.fade-up-enter-active,
.fade-up-leave-active {
  transition: all 0.55s cubic-bezier(0.16, 1, 0.3, 1);
}

.fade-up-enter-from {
  opacity: 0;
  transform: translateY(16px);
  filter: blur(4px);
}

.fade-up-leave-to {
  opacity: 0;
  transform: translateY(8px);
  filter: blur(4px);
}

.title {
  font-weight: 900;
  letter-spacing: 0.4px;
}

.sub {
  margin-top: 6px;
  font-size: 12px;
  opacity: 0.76;
}

.row {
  margin-top: 10px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 9px 12px;
  border-radius: 12px;
  background: rgba(120, 160, 255, 0.18);
  border: 1px solid rgba(120, 160, 255, 0.35);
  color: #eef2ff;
  text-decoration: none;
  cursor: pointer;
}

.btn.secondary {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.16);
}

.hint {
  margin-top: 8px;
  font-size: 12px;
  opacity: 0.78;
  display: flex;
  align-items: center;
  gap: 8px;
}

.hint .sep {
  opacity: 0.5;
}

.targets {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chip {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.9);
  font-weight: 900;
  font-size: 11px;
  letter-spacing: 0.2px;
  cursor: pointer;
}

.chip.active {
  border-color: rgba(120, 160, 255, 0.55);
  background: rgba(120, 160, 255, 0.18);
}

.chip:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.tour {
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.10);
}

.tour-title {
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.8px;
  opacity: 0.75;
}

.tour-row {
  margin-top: 8px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.tour-btn {
  padding: 8px 10px;
  border-radius: 12px;
  border: 1px solid rgba(120, 160, 255, 0.35);
  background: rgba(120, 160, 255, 0.14);
  color: #eef2ff;
  font-weight: 900;
  font-size: 11px;
  letter-spacing: 0.2px;
  cursor: pointer;
}

.tour-btn.secondary {
  border-color: rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.06);
}

.tour-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.tour-status {
  margin-top: 10px;
  font-size: 12px;
  opacity: 0.82;
}

.pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.scrolly {
  position: absolute;
  right: 14px;
  top: 14px;
  bottom: 14px;
  width: min(360px, calc(100vw - 28px));
  z-index: 2500;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  pointer-events: auto;
}

.card {
  padding: 12px 12px 12px;
  border-radius: 18px;
  background: rgba(10, 15, 25, 0.56);
  border: 1px solid rgba(255, 255, 255, 0.10);
  backdrop-filter: blur(12px);
  color: rgba(255, 255, 255, 0.92);
  min-height: 120px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 10px;
  transition: opacity 220ms ease, transform 220ms ease, border-color 220ms ease, background 220ms ease;
}

.card[data-active='true'] {
  border-color: rgba(0, 240, 255, 0.22);
  background:
    radial-gradient(520px 240px at 20% 20%, rgba(0, 240, 255, 0.10), transparent 62%),
    rgba(10, 15, 25, 0.62);
  transform: translateY(-1px);
  opacity: 1;
  box-shadow:
    0 18px 60px rgba(0, 0, 0, 0.35),
    0 0 36px rgba(0, 240, 255, 0.06);
}

.card[data-active='false'] {
  opacity: 0.42;
  transform: scale(0.98);
}

.k {
  font-size: 11px;
  letter-spacing: 0.8px;
  font-weight: 900;
  opacity: 0.7;
}

.h {
  font-size: 18px;
  font-weight: 900;
  letter-spacing: 0.2px;
}

.p {
  font-size: 13px;
  font-weight: 700;
  line-height: 1.55;
  opacity: 0.9;
}

.p.subtle {
  opacity: 0.72;
}

.link {
  color: rgba(170, 205, 255, 0.95);
  text-decoration: none;
  font-weight: 900;
}

.link:hover {
  text-decoration: underline;
}

@media (max-width: 900px) {
  .scrolly {
    left: 14px;
    right: 14px;
    width: auto;
    top: 90px;
  }

  .card {
    min-height: 46vh;
  }

  .info {
    left: 14px;
    right: 14px;
    max-width: none;
  }
}
</style>
