<template>
  <div class="z2x">
    <header id="act-1" class="hero" data-act-id="act-1">
      <HeroVisual class="hero-bg" />

      <div class="hero-center">
        <div class="brand">
          <div class="brand-kicker">MODEL 021</div>
          <div class="brand-title">zero2x</div>
          <div class="brand-sub">From awe to action. AI-Native 工作台</div>
        </div>

        <div class="omnibar" role="search">
          <div class="omnibar-hint">
            Press <kbd class="omnibar-kbd-hint">⌘K</kbd> to start your research
          </div>
          <div class="omnibar-shell" @click="focusOmni">
            <svg
              class="omnibar-icon"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>

            <input
              ref="inputEl"
              v-model="query"
              class="omnibar-input"
              type="text"
              :placeholder="placeholder"
              @keydown.meta.k.prevent="focusOmni"
              @keydown.ctrl.k.prevent="focusOmni"
              @keydown.enter.prevent="submit"
              aria-label="Zero2x omni bar"
            />

            <div class="omnibar-kbd" aria-hidden="true" title="Cmd/Ctrl + K">
              <span class="kbd">⌘</span>
              <span class="kbd">K</span>
            </div>

            <button class="btn omnibar-btn" type="button" @click.stop="submit">Run</button>
            <a
              class="btn secondary omnibar-btn"
              :href="takeMeToEarthHref"
              @click.stop.prevent="goAct2"
            >
              进入第二幕
            </a>
          </div>
          <div v-if="result" class="omnibar-result">
            <div class="result-title">AI Preview</div>
            <pre class="result-pre">{{ result }}</pre>
          </div>
        </div>

        <div class="hero-cta">
          <a class="cta" href="#act-2">开始宇宙漫游</a>
          <a class="cta ghost" :href="takeMeToEarthHref" @click.prevent="goAct2">进入第二幕：启动宏观孪生</a>
        </div>
      </div>
    </header>

    <nav class="scroll-nav" aria-label="Story progress">
      <a
        v-for="a in acts"
        :key="a.id"
        class="scroll-pill"
        :class="{ active: activeAct === a.id }"
        :href="`#${a.id}`"
      >
        <span class="dot" />
        <span class="label">{{ a.label }}</span>
      </a>
    </nav>

    <main class="acts">
      <section id="act-2" class="act" data-act-id="act-2">
        <div class="act-title">第二幕：宏观孪生</div>
        <div class="act-desc">Landing 只展示“我们有什么引擎（What）”：地学 + 天文两大基座模型。具体任务与实机交互（How）留在 /act2 逐步揭示。</div>

        <div class="bento-grid act2-grid">
          <div
            class="bento-card bento-lg"
            role="link"
            tabindex="0"
            @click="goAct2"
            @keydown.enter.prevent="goAct2"
          >
            <img class="bento-bg" :src="act2GeoWebpSrc" alt="GeoGPT cinematic poster" loading="lazy" />
            <div class="bento-overlay" />
            <div class="bento-grain" aria-hidden="true" />
            <div class="enter-arrow" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="7" y1="17" x2="17" y2="7"></line>
                <polyline points="7 7 17 7 17 17"></polyline>
              </svg>
            </div>
            <div class="bento-content">
              <div class="bento-tag">领域科学模型</div>
              <div class="bento-title">GeoGPT</div>
              <div class="bento-desc">为支持地球科学研究与应用而开发的专用大语言模型：从“任务意图”到“图层编排 / 证据链 / 报告草案”的闭环。</div>
              <div class="bento-actions">
                <button class="bento-btn" type="button" @click.stop="goAct2">启动数字孪生引擎 (Launch Digital Twin)</button>
                <a class="bento-link" :href="takeMeToEarthHref" @click.stop.prevent="goAct2">进入第二幕（实机演示）</a>
              </div>
              <div v-if="assetHint" class="asset-hint">{{ assetHint }}</div>
            </div>
          </div>

          <div
            class="bento-card"
            role="link"
            tabindex="0"
            @click="goAct2Base"
            @keydown.enter.prevent="goAct2Base"
          >
            <img class="bento-bg" :src="act2AstronomyWebpSrc" alt="OneAstronomy cinematic poster" loading="lazy" />
            <div class="bento-overlay" />
            <div class="bento-grain" aria-hidden="true" />
            <div class="enter-arrow" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="7" y1="17" x2="17" y2="7"></line>
                <polyline points="7 7 17 7 17 17"></polyline>
              </svg>
            </div>
            <div class="bento-content">
              <div class="bento-tag">跨模态统一</div>
              <div class="bento-title">OneAstronomy</div>
              <div class="bento-desc">面向天文领域的 AI 模型：统一天文跨模态数据处理，并与地球科学场景在同一叙事框架中衔接。</div>
              <div class="bento-mini">深空 → 轨道 → 目标锁定：一条镜头语言贯穿</div>
            </div>
          </div>
        </div>
      </section>

      <section id="act-3" class="act" data-act-id="act-3">
        <div class="act-title">第三幕：微观深潜</div>
        <div class="act-desc">从宏观场景穿透到 DNA / 微结构的“可视化证据”：同样用一张静态海报先建立冲击感，再进入工作台看硬核细节。</div>

        <div class="bento-grid act3-grid">
          <div
            class="bento-card"
            role="link"
            tabindex="0"
            @click="goWorkbench"
            @keydown.enter.prevent="goWorkbench"
          >
            <img class="bento-bg" :src="act3GenosWebpSrc" alt="Genos cinematic poster" loading="lazy" />
            <div class="bento-overlay" />
            <div class="bento-grain" aria-hidden="true" />
            <div class="enter-arrow" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="7" y1="17" x2="17" y2="7"></line>
                <polyline points="7 7 17 7 17 17"></polyline>
              </svg>
            </div>
            <div class="bento-content">
              <div class="bento-tag">10B 级基础模型</div>
              <div class="bento-title">Genos</div>
              <div class="bento-desc">百万碱基长程建模，单核苷酸级精准致病关联；把实验与文本证据链合并为可追溯的研究路径。</div>
            </div>
          </div>

          <div
            class="bento-card"
            role="link"
            tabindex="0"
            @click="goWorkbench"
            @keydown.enter.prevent="goWorkbench"
          >
            <img class="bento-bg" :src="act3OnePorousWebpSrc" alt="OnePorous cinematic poster" loading="lazy" />
            <div class="bento-overlay" />
            <div class="bento-grain" aria-hidden="true" />
            <div class="enter-arrow" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="7" y1="17" x2="17" y2="7"></line>
                <polyline points="7 7 17 7 17 17"></polyline>
              </svg>
            </div>
            <div class="bento-content">
              <div class="bento-tag">材料生成与预测</div>
              <div class="bento-title">OnePorous</div>
              <div class="bento-desc">秒级孔结构逆向生成与性能预测：从“目标指标”到“结构候选 + 可制造性评估 + 实验建议”。</div>
              <div class="bento-mini">下一步：替换为 WebM 预告片，保持同名路径</div>
            </div>
          </div>
        </div>
      </section>

      <section id="act-4" class="act" data-act-id="act-4">
        <div class="act-title">第四幕：数据星海</div>
        <div class="act-desc">Embedding 联邦数据图谱（此处先用轻量 Canvas 粒子实现 500+ 节点与“搜索聚焦簇”的交互原型）。</div>

        <DataGalaxy />

        <div class="card-grid" style="margin-top: 14px;">
          <div class="card"><div class="card-k">Semantic Galaxy</div><div class="card-v">粒子节点 + 聚类星云（可替换为 Three/Cesium 版本）</div></div>
          <div class="card"><div class="card-k">Search</div><div class="card-v">输入 “poyang/湿地/hydrology” → 聚焦簇</div></div>
          <div class="card"><div class="card-k">Mount</div><div class="card-v">下一步：框选/拖拽 → 工作台挂载</div></div>
        </div>
      </section>

      <section id="act-5" class="act" data-act-id="act-5">
        <div class="act-title">第五幕：极客工坊</div>
        <div class="act-desc">把“愿景”收敛为可操作的工作台：左侧意图与数据挂载，中间生成代码，右侧可视化输出与报告。</div>

        <div class="bento-grid act5-grid">
          <div class="bento-card bento-lg">
            <div class="bento-ambient workbench" aria-hidden="true" />
            <div class="bento-content">
              <div class="bento-tag">AI-Native Workbench</div>
              <div class="bento-title">从意图到可交付</div>
              <div class="bento-desc">把“构建鄱阳湖生态监测 Agent”变成一套可运行的 pipeline：数据挂载、任务拆解、代码生成、结果可视化、报告输出。</div>
              <pre class="wb-code">@AgentBuilder 帮我调用刚刚的鄱阳湖数据集，生成一份生态评估代码\n\n# 输出将在 /workbench 以打字机效果演示</pre>
              <div class="bento-actions">
                <a class="launch" :href="workbenchHref" @click.prevent="goWorkbench">Launch My Workspace</a>
              </div>
            </div>
          </div>

          <div class="bento-card">
            <div class="bento-ambient alt" aria-hidden="true" />
            <div class="bento-content">
              <div class="bento-tag">Demo Script</div>
              <div class="bento-title">汇报操作建议</div>
              <div class="bento-desc">1) 第一屏 Omni-Bar 回车 → 进入第二幕 2) 目标锁定后 → 一键进入工作台 3) 打字机输出 + 图层/报告结果。</div>
              <div class="bento-mini">这条“黄金路径”优先于滚动讲解</div>
            </div>
          </div>
        </div>
      </section>

      <footer class="foot">
        <div class="foot-inner">
          <div class="foot-left">Zero2x 021 Upgrade Branch</div>
          <div class="foot-right">
            <a class="foot-link" href="/demo" title="Tools / Validation system">Demo</a>
            <span class="sep">·</span>
            <span>Dev 8404/8405 · Prod 8406/8407 · Canary 8508/8509</span>
          </div>
        </div>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import DataGalaxy from './components/DataGalaxy.vue'
import HeroVisual from './components/HeroVisual.vue'
import { buildAct2ChoreoHref } from './utils/choreo.js'
import { navigateWithFade } from './utils/navFade.js'
import { buildStubPlan, parseOmniInput } from './utils/omnibarCommands.js'

const inputEl = ref(null)
const query = ref('')
const result = ref('')

const placeholders = [
  '请输入您的科学猜想... (例：叠加近十年水文变化与鸟类迁徙轨迹)',
  '例：构建一个鄱阳湖东方白鹳栖息地监测 Agent',
  '例：搜索“造山带地壳生长”，点亮相关数据簇',
]

const idx = ref(0)
const placeholder = computed(() => placeholders[idx.value % placeholders.length])

const takeMeToEarthHref = buildAct2ChoreoHref('poyang')
const act2Href = buildAct2ChoreoHref('')
const workbenchHref = '/workbench'

function withBase(p) {
  const rawBase = String(import.meta?.env?.BASE_URL || '/').trim() || '/'
  const base = rawBase.endsWith('/') ? rawBase : `${rawBase}/`
  const rel = String(p || '').replace(/^\//, '')
  return `${base}${rel}`
}

const act2GeoWebpSrc = computed(() => withBase('/zero2x/ui/act2_geogpt.webp'))
const act2AstronomyWebpSrc = computed(() => withBase('/zero2x/ui/act2_astronomy.webp'))
const act3GenosWebpSrc = computed(() => withBase('/zero2x/ui/act3_genos.webp'))
const act3OnePorousWebpSrc = computed(() => withBase('/zero2x/ui/act3_oneporous.webp'))

const assetHint = ref('')
async function _checkPosterAssets() {
  const urls = [
    act2GeoWebpSrc.value,
    act2AstronomyWebpSrc.value,
    act3GenosWebpSrc.value,
    act3OnePorousWebpSrc.value,
  ]
  try {
    const r = await Promise.all(urls.map((u) => fetch(u, { method: 'HEAD', cache: 'no-store' })))
    const ok = r.every((x) => x && x.ok)
    if (ok) {
      assetHint.value = ''
      return
    }
  } catch (_) {
    // ignore
  }
  assetHint.value = '提示：当前端口可能在运行旧的 dist / 反代了错误的 upstream，请重新 build+deploy（Docker: make docker-prod-up / make canary-rebuild-frontend）。'
}

const acts = [
  { id: 'act-1', label: 'Act 1' },
  { id: 'act-2', label: 'Act 2' },
  { id: 'act-3', label: 'Act 3' },
  { id: 'act-4', label: 'Act 4' },
  { id: 'act-5', label: 'Act 5' },
]

const activeAct = ref('act-1')
let _actObserver = null

let _timer = null

function focusOmni() {
  try {
    inputEl.value?.focus?.()
  } catch (_) {
    // ignore
  }
}

function submit() {
  const q = String(query.value || '').trim()
  if (!q) {
    result.value = ''
    return
  }

  const action = parseOmniInput(q)

  if (action.type === 'help') {
    result.value = action.text
    return
  }

  if (action.type === 'navigate') {
    // Keep the UI responsive: show a short preview, then fade-navigate.
    result.value = [
      `Command: ${q}`,
      '',
      `Routing to: ${action.href}`,
    ].join('\n')

    navigateWithFade(action.href, { reason: 'omnibar-command' })
    return
  }

  // Golden Path: any free-form intent should feel “actionable”.
  // Show a short preview, store intent, then fly to Act2.
  result.value = buildStubPlan(action.intent)
  try {
    window.sessionStorage?.setItem?.('z2x:lastIntent', q)
  } catch (_) {
    // ignore
  }
  navigateWithFade(takeMeToEarthHref, { reason: 'omnibar-intent', delayMs: 520 })
}

function _prefersReducedMotion() {
  try {
    return !!window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
  } catch (_) {
    return false
  }
}

function goAct2() {
  navigateWithFade(takeMeToEarthHref, { reason: 'landing-cta-act2' })
}

function goAct2Base() {
  navigateWithFade(act2Href, { reason: 'landing-cta-act2-base' })
}

function goWorkbench() {
  navigateWithFade(workbenchHref, { reason: 'landing-cta-workbench' })
}

function onGlobalKeydown(e) {
  // Global ⌘K / Ctrl+K
  if (!e) return
  const k = String(e.key || '').toLowerCase()
  if (k !== 'k') return
  if (e.metaKey || e.ctrlKey) {
    e.preventDefault()
    focusOmni()
  }
}

onMounted(() => {
  try {
    document.body.style.overflow = 'auto'
  } catch (_) {
    // ignore
  }

  window.addEventListener('keydown', onGlobalKeydown)

  // Scrollspy: keep a visible sense of progress when scrolling down.
  try {
    if (typeof IntersectionObserver !== 'undefined') {
      const nodes = Array.from(document.querySelectorAll('[data-act-id]'))
      _actObserver = new IntersectionObserver(
        (entries) => {
          // Pick the most visible intersecting section.
          let best = null
          for (const e of entries) {
            if (!e?.isIntersecting) continue
            if (!best) best = e
            else if ((e.intersectionRatio || 0) > (best.intersectionRatio || 0)) best = e
          }
          const id = best?.target?.dataset?.actId
          if (id) activeAct.value = id
        },
        { threshold: [0.2, 0.4, 0.6, 0.8] }
      )
      for (const n of nodes) _actObserver.observe(n)
    }
  } catch (_) {
    // ignore
  }

  _timer = setInterval(() => {
    idx.value = (idx.value + 1) % placeholders.length
  }, 2800)

  setTimeout(() => focusOmni(), 250)

  // Lightweight sanity check: if posters fail to load, show a deploy hint.
  setTimeout(() => _checkPosterAssets(), 600)
})

onUnmounted(() => {
  try {
    window.removeEventListener('keydown', onGlobalKeydown)
  } catch (_) {
    // ignore
  }
  if (_timer) {
    clearInterval(_timer)
    _timer = null
  }

  try {
    _actObserver?.disconnect?.()
  } catch (_) {
    // ignore
  }
  _actObserver = null

})
</script>

<style scoped>
.z2x {
  min-height: 100vh;
  background:
    radial-gradient(1200px 800px at 50% 20%, rgba(120, 160, 255, 0.12), rgba(0, 0, 0, 0.14)),
    linear-gradient(180deg, #030409, #000);
  color: #eef2ff;
}

.z2x ::selection {
  background: #00f0ff;
  color: #000;
}

.hero {
  position: relative;
  min-height: 100vh;
  padding: 64px 18px 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.poster {
  margin-top: 14px;
  border-radius: 22px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.09);
  background: rgba(255, 255, 255, 0.03);
}

.poster.slim {
  border-radius: 18px;
}

.poster-img {
  width: 100%;
  height: auto;
  display: block;
}

.poster-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.35);
}

.poster-btn {
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(0, 240, 255, 0.14);
  border: 1px solid rgba(0, 240, 255, 0.35);
  color: #e6fdff;
  cursor: pointer;
  font-weight: 800;
  letter-spacing: 0.2px;
}

.poster-btn:hover {
  background: rgba(0, 240, 255, 0.22);
}

.poster-link {
  color: rgba(238, 242, 255, 0.78);
  text-decoration: none;
  font-size: 12px;
}

.poster-link:hover {
  text-decoration: underline;
}

@media (max-width: 680px) {
  .poster-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .poster-btn {
    width: 100%;
  }

  .poster-link {
    text-align: center;
  }
}

.hero-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.hero-center {
  position: relative;
  width: min(1040px, 100%);
  z-index: 2;
}

.brand {
  text-align: center;
  margin-top: -10vh;
  margin-bottom: 24px;
  padding: 40px 20px;
  background: radial-gradient(ellipse at center, rgba(3, 4, 9, 0.85) 0%, rgba(3, 4, 9, 0.5) 40%, transparent 70%);
}

.brand-kicker {
  letter-spacing: 0.35em;
  text-transform: uppercase;
  opacity: 1;
  font-size: 10px;
  font-weight: 700;
  color: rgba(156, 163, 175, 1);
  margin-bottom: 12px;
}

.brand-title {
  display: inline-block;
  font-size: clamp(52px, 9.5vw, 112px);
  line-height: 1.1;
  margin-top: 10px;
  margin-bottom: 16px;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-weight: 900;
  letter-spacing: -0.06em;
  text-transform: lowercase;

  /* Gradient core config */
  color: transparent;
  -webkit-text-fill-color: transparent;
  background: linear-gradient(
    90deg,
    #00f0ff 0%,
    #3bf6ff 22%,
    #9d4edd 72%,
    #c77dff 100%
  );
  background-size: 140% 100%;
  -webkit-background-clip: text;
  background-clip: text;

  /* Shadow for gradient text: must be drop-shadow, not text-shadow */
  filter:
    drop-shadow(0px 4px 12px rgba(0, 0, 0, 0.8))
    drop-shadow(0px 0px 60px rgba(0, 0, 0, 1));
}

.brand-sub {
  margin-top: 12px;
  opacity: 1;
  font-size: 15px;
  font-weight: 300;
  letter-spacing: 0.02em;
  color: rgba(209, 213, 219, 0.95);
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.8);
}

.omnibar {
  margin: 22px auto 0;
  padding: 16px 16px 14px;
  border-radius: 20px;
  background: rgba(10, 15, 26, 0.70);
  border: 1px solid rgba(255, 255, 255, 0.10);
  backdrop-filter: blur(24px);
  box-shadow: 0 0 40px rgba(0, 240, 255, 0.12);
  transition: box-shadow 500ms ease, border-color 500ms ease;
}

.omnibar:hover {
  box-shadow: 0 0 60px rgba(0, 240, 255, 0.20);
  border-color: rgba(0, 240, 255, 0.30);
}

.omnibar-hint {
  font-size: 11px;
  opacity: 0.78;
  margin-bottom: 10px;
  color: rgba(156, 163, 175, 1);
  font-weight: 500;
}

.omnibar-kbd-hint {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 6px;
  margin: 0 6px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.10);
  border: 1px solid rgba(255, 255, 255, 0.20);
  color: rgba(209, 213, 219, 0.92);
  font-size: 11px;
  line-height: 1;
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.35);
}

.omnibar-shell {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 14px;
  background: rgba(5, 8, 16, 0.80);
  border: 1px solid rgba(255, 255, 255, 0.05);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.02);
  transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
}

.omnibar-shell:focus-within {
  border-color: rgba(0, 240, 255, 0.50);
  box-shadow: 0 0 0 4px rgba(0, 240, 255, 0.12);
  transform: translateY(-1px);
}

.omnibar-icon {
  flex: 0 0 auto;
  opacity: 1;
  color: rgba(107, 114, 128, 1);
}

.omnibar-input {
  width: 100%;
  font-size: 14px;
  padding: 8px 4px;
  border-radius: 12px;
  background: transparent;
  border: 1px solid transparent;
  color: #eef2ff;
  outline: none;
}

.omnibar-input::placeholder {
  color: rgba(75, 85, 99, 1);
}

.omnibar-input:focus {
  border-color: transparent;
  box-shadow: none;
}

.omnibar-kbd {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 9px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: rgba(203, 213, 225, 0.95);
  font-size: 12px;
  letter-spacing: 0.02em;
}

.omnibar-kbd .kbd {
  display: inline-block;
  min-width: 10px;
  text-align: center;
}

.omnibar-btn {
  display: none;
  flex: 0 0 auto;
}

@media (min-width: 768px) {
  .omnibar-btn {
    display: inline-flex;
  }
}

@media (max-width: 768px) {
  .omnibar-kbd {
    display: none;
  }
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(42, 45, 74, 1);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #eef2ff;
  text-decoration: none;
  cursor: pointer;
  transition: background 180ms ease, border-color 180ms ease, transform 180ms ease;
}

.btn:hover {
  background: rgba(58, 63, 108, 1);
  transform: translateY(-1px);
}

.btn.secondary {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.20);
}

.btn.secondary:hover {
  background: rgba(255, 255, 255, 0.10);
}

.omnibar-result {
  margin-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  padding-top: 12px;
}

.result-title {
  font-size: 12px;
  opacity: 0.72;
  margin-bottom: 8px;
}

.result-pre {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.5;
  opacity: 0.92;
}

.hero-cta {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.cta {
  padding: 10px 24px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.40);
  border: 1px solid rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(16px);
  color: rgba(209, 213, 219, 0.92);
  text-decoration: none;
  transition: border-color 180ms ease, background 180ms ease, color 180ms ease;
}

.cta:hover {
  color: rgba(255, 255, 255, 0.95);
  border-color: rgba(0, 240, 255, 0.50);
  background: rgba(255, 255, 255, 0.05);
}

.cta.ghost {
  background: rgba(0, 0, 0, 0.40);
  border-color: rgba(255, 255, 255, 0.15);
}

.cta.ghost:hover {
  border-color: rgba(157, 78, 221, 0.50);
}

.acts {
  padding: 8px 18px 48px;
}

.scroll-nav {
  position: fixed;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 3000;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.scroll-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(12px);
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.4px;
}

.scroll-pill .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.35);
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.25) inset;
}

.scroll-pill.active {
  border-color: rgba(120, 160, 255, 0.45);
  background: rgba(120, 160, 255, 0.14);
  color: rgba(255, 255, 255, 0.95);
}

.scroll-pill.active .dot {
  background: rgba(120, 160, 255, 0.95);
  box-shadow: 0 0 14px rgba(120, 160, 255, 0.35);
}

.act {
  width: min(1040px, 100%);
  margin: 0 auto;
  padding: 64px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.act-title {
  font-size: 20px;
  letter-spacing: 0.04em;
}

.act-desc {
  margin-top: 10px;
  opacity: 0.84;
  max-width: 820px;
}

.bento-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.act3-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.act5-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.bento-card {
  position: relative;
  overflow: hidden;
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background:
    radial-gradient(820px 420px at 20% 10%, rgba(0, 240, 255, 0.10), transparent 55%),
    radial-gradient(820px 420px at 80% 20%, rgba(157, 78, 221, 0.10), transparent 55%),
    rgba(255, 255, 255, 0.035);
  box-shadow:
    0 22px 80px rgba(0, 0, 0, 0.42),
    inset 0 0 0 1px rgba(255, 255, 255, 0.04);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.bento-card:hover {
  transform: translateY(-6px);
  border-color: rgba(0, 240, 255, 0.4);
  box-shadow:
    0 20px 50px -15px rgba(0, 240, 255, 0.2),
    inset 0 0 20px rgba(0, 240, 255, 0.05);
}

.bento-lg {
  grid-column: span 2;
  min-height: 380px;
}

.bento-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.4;
  transform: scale(1);
  transition: opacity 0.6s ease, transform 4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.bento-card:hover .bento-bg {
  opacity: 0.7;
  transform: scale(1.08);
}

.bento-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to top,
    rgba(3, 4, 9, 0.98) 0%,
    rgba(3, 4, 9, 0.55) 50%,
    transparent 100%
  );
}

.bento-grain {
  position: absolute;
  inset: 0;
  /* Procedural-ish grain via layered gradients (no external assets). */
  background:
    repeating-linear-gradient(0deg, rgba(255,255,255,0.020) 0px, rgba(255,255,255,0.020) 1px, rgba(0,0,0,0) 2px, rgba(0,0,0,0) 4px),
    repeating-linear-gradient(90deg, rgba(255,255,255,0.012) 0px, rgba(255,255,255,0.012) 1px, rgba(0,0,0,0) 2px, rgba(0,0,0,0) 6px);
  mix-blend-mode: overlay;
  opacity: 0.38;
  pointer-events: none;
}

.enter-arrow {
  position: absolute;
  top: 1.5rem;
  right: 1.5rem;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.10);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transform: translate(-10px, 10px);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 20;
  color: rgba(255, 255, 255, 0.92);
}

.bento-card:hover .enter-arrow {
  opacity: 1;
  transform: translate(0, 0);
  background: rgba(0, 240, 255, 0.15);
  border-color: rgba(0, 240, 255, 0.4);
  color: #00f0ff;
  box-shadow: 0 0 20px rgba(0, 240, 255, 0.3);
}

.bento-ambient {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(820px 420px at 30% 25%, rgba(120, 160, 255, 0.18), transparent 58%),
    radial-gradient(820px 420px at 70% 20%, rgba(0, 240, 255, 0.10), transparent 60%),
    linear-gradient(180deg, rgba(3, 4, 9, 0.2), rgba(0, 0, 0, 0.85));
}

.bento-ambient.alt {
  background:
    radial-gradient(820px 420px at 70% 18%, rgba(157, 78, 221, 0.20), transparent 60%),
    radial-gradient(820px 420px at 30% 40%, rgba(0, 240, 255, 0.10), transparent 60%),
    linear-gradient(180deg, rgba(3, 4, 9, 0.20), rgba(0, 0, 0, 0.86));
}

.bento-ambient.purple {
  background:
    radial-gradient(820px 420px at 35% 22%, rgba(199, 125, 255, 0.22), transparent 60%),
    radial-gradient(820px 420px at 70% 34%, rgba(0, 240, 255, 0.08), transparent 66%),
    linear-gradient(180deg, rgba(3, 4, 9, 0.24), rgba(0, 0, 0, 0.88));
}

.bento-ambient.workbench {
  background:
    radial-gradient(820px 420px at 25% 25%, rgba(0, 240, 255, 0.10), transparent 60%),
    radial-gradient(820px 420px at 80% 20%, rgba(120, 160, 255, 0.18), transparent 62%),
    linear-gradient(180deg, rgba(8, 10, 20, 0.22), rgba(0, 0, 0, 0.90));
}

.bento-content {
  position: relative;
  z-index: 2;
  padding: 22px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 240px;
  backdrop-filter: blur(18px);
}

.bento-tag {
  width: fit-content;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(209, 213, 219, 0.9);
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.14);
}

.bento-title {
  font-size: 26px;
  font-weight: 1000;
  letter-spacing: -0.02em;
}

.bento-desc {
  color: rgba(226, 232, 240, 0.92);
  line-height: 1.55;
  max-width: 52ch;
}

.bento-mini {
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.78;
}

.bento-actions {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.bento-btn {
  padding: 10px 16px;
  border-radius: 999px;
  background: rgba(0, 240, 255, 0.16);
  border: 1px solid rgba(0, 240, 255, 0.36);
  color: #e6fdff;
  cursor: pointer;
  font-weight: 900;
}

.bento-btn:hover {
  background: rgba(0, 240, 255, 0.24);
}

.bento-link {
  color: rgba(238, 242, 255, 0.82);
  text-decoration: none;
  font-size: 12px;
}

.bento-link:hover {
  text-decoration: underline;
}

.asset-hint {
  margin-top: 8px;
  font-size: 12px;
  opacity: 0.82;
  color: rgba(251, 191, 36, 0.95);
}

.card-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.card {
  padding: 14px;
  border-radius: 16px;
  background:
    radial-gradient(520px 240px at 30% 20%, rgba(120, 160, 255, 0.10), transparent 58%),
    radial-gradient(520px 240px at 80% 20%, rgba(157, 78, 221, 0.10), transparent 58%),
    rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(14px);
  box-shadow:
    0 18px 70px rgba(0, 0, 0, 0.38),
    inset 0 0 0 1px rgba(255, 255, 255, 0.04);
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

.card:hover {
  transform: translateY(-2px);
  border-color: rgba(120, 160, 255, 0.32);
  box-shadow:
    0 22px 86px rgba(0, 0, 0, 0.46),
    0 0 40px rgba(0, 240, 255, 0.06),
    inset 0 0 0 1px rgba(255, 255, 255, 0.06);
}

.card-k {
  font-size: 12px;
  opacity: 0.7;
}

.card-v {
  margin-top: 6px;
  font-size: 14px;
}

.workbench {
  margin-top: 18px;
  display: grid;
  grid-template-columns: 1.3fr 1fr 1fr;
  gap: 12px;
}

.wb-pane {
  min-height: 160px;
  padding: 14px;
  border-radius: 16px;
  background:
    radial-gradient(520px 240px at 20% 10%, rgba(0, 240, 255, 0.09), transparent 60%),
    rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(14px);
  box-shadow:
    0 18px 70px rgba(0, 0, 0, 0.38),
    inset 0 0 0 1px rgba(255, 255, 255, 0.04);
}

.wb-title {
  font-size: 12px;
  opacity: 0.72;
  margin-bottom: 10px;
}

.wb-code {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.45;
}

.wb-preview {
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px dashed rgba(255, 255, 255, 0.16);
  opacity: 0.85;
}

.launch-row {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.launch {
  padding: 12px 18px;
  border-radius: 14px;
  background: rgba(120, 160, 255, 0.26);
  border: 1px solid rgba(120, 160, 255, 0.45);
  color: #eef2ff;
  text-decoration: none;
}

.foot {
  padding: 26px 0 32px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.foot-inner {
  width: min(1040px, 100%);
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  opacity: 0.72;
  font-size: 12px;
  gap: 10px;
  flex-wrap: wrap;
}

.foot-link {
  color: rgba(255, 255, 255, 0.9);
  text-decoration: none;
  font-weight: 900;
}

.foot-link:hover {
  text-decoration: underline;
}

.sep {
  opacity: 0.6;
  margin: 0 8px;
}

@media (max-width: 920px) {
  .bento-grid {
    grid-template-columns: 1fr;
  }

  .act3-grid,
  .act5-grid {
    grid-template-columns: 1fr;
  }

  .bento-lg {
    grid-column: auto;
    min-height: 340px;
  }

  .bento-actions {
    justify-content: flex-start;
  }

  .card-grid {
    grid-template-columns: 1fr;
  }
  .workbench {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .scroll-nav {
    display: none;
  }
}

/* =========================================
   移动端 (Mobile) 响应式适配补丁
   ========================================= */
@media (max-width: 768px) {
  /* 1. 恢复视觉重心：手机屏幕高度有限，取消过度的上提拉 */
  .brand {
    margin-top: 0vh;
    padding: 20px 10px;
  }

  /* 2. 隐藏手机端无用的快捷键提示 */
  .omnibar-hint,
  .omnibar-kbd,
  .omnibar-kbd-hint {
    display: none !important;
  }

  /* 3. 释放输入框：隐藏 Omni-Bar 内部的按钮 */
  /* 手机端用户敲击软键盘上的“前往/确认”键即可触发 Enter (Run)，无需占用屏幕宽度的按钮 */
  .omnibar-actions,
  .omnibar-shell .btn,
  .omnibar-shell a.btn {
    display: none !important;
  }

  /* 4. 给输入框最大空间，并缩小一点字号 */
  .omnibar-shell {
    padding: 10px 14px; /* 增加一点内边距让触摸更舒服 */
  }

  .omnibar-input {
    font-size: 13px; /* 让长 placeholder 能多显示几个字 */
    width: 100%;
  }

  /* 5. 底部大按钮 (CTA) 友好堆叠 */
  .hero-cta {
    flex-direction: column; /* 改为垂直排列 */
    align-items: center;
    gap: 12px;
    padding: 0 20px;
    margin-top: 32px;
  }

  .cta {
    width: 100%; /* 按钮占满全宽，更符合手机端触摸习惯 */
    max-width: 300px;
    text-align: center;
    padding: 14px 24px;
  }
}
</style>
