<template>
  <div class="z2x">
    <!-- 第一幕：入境 -->
    <header id="act-1" class="hero" data-act-id="act-1">
      <HeroVisual class="hero-bg" />

      <div class="hero-center">
        <div class="brand">
          <div class="brand-kicker">PROJECT MODEL 021</div>
          <div class="brand-title">zero2x</div>
          <div class="brand-sub">From awe to action. AI-Native 渐进式科研工作台</div>
        </div>

        <div class="omnibar" role="search">
          <div class="omnibar-hint">
            <span class="desktop-only">Press <kbd class="omnibar-kbd-hint">⌘K</kbd> to initiate scientific inquiry</span>
            <span class="mobile-only">Describe your research intent below</span>
          </div>
          <div class="omnibar-shell" @click="focusOmni">
            <svg class="omnibar-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            <input ref="inputEl" v-model="query" class="omnibar-input" type="text" :placeholder="placeholder" @keydown.meta.k.prevent="focusOmni" @keydown.ctrl.k.prevent="focusOmni" @keydown.enter.prevent="submit" aria-label="Zero2x omni bar" />
            <div class="omnibar-kbd" aria-hidden="true" title="Cmd/Ctrl + K">
              <span class="kbd">⌘</span>
              <span class="kbd">K</span>
            </div>
            <button class="btn omnibar-btn" type="button" @click.stop="submit">Run</button>
            <a class="btn secondary omnibar-btn" :href="takeMeToEarthHref" @click.stop.prevent="goAct2">进入视窗</a>
          </div>
          <div v-if="result" class="omnibar-result">
            <div class="result-title">021_BASE_MODEL_PREVIEW</div>
            <pre class="result-pre">{{ result }}</pre>
          </div>
        </div>

        <div class="hero-cta">
          <a class="cta" href="#act-2">向下滚动 · 跨尺度科研探索</a>
          <a class="cta ghost" :href="takeMeToEarthHref" @click.prevent="goAct2">进入视窗：宏观孪生</a>
        </div>
      </div>

      <!-- update_patch_0303: replace right-side pills with a subtle scroll hint -->
      <div class="scroll-hint" aria-hidden="true">
        <div class="mouse-icon" aria-hidden="true"></div>
        <div class="scroll-hint-text">Scroll</div>
      </div>
    </header>

    <main class="acts">
      <!-- ==========================================
           ACT 2: The Orbital Horizon
           ========================================== -->
      <section id="act-2" class="act-fullscreen group" data-act-id="act-2" data-act-title="第二幕：宏观孪生" aria-label="第二幕：宏观孪生" role="link" tabindex="0" @click="goAct2" @keydown.enter.prevent="goAct2">
        <img class="cinematic-image" :src="act2AstronomyPosterSrc" alt="Act2 cinematic poster" loading="lazy" @error="(e) => onPosterImgError(e, act2AstronomyRemotePosterSrc)" />
        <video v-if="act2CinematicVideoOk" class="cinematic-video" autoplay loop muted playsinline preload="metadata" @error="act2CinematicVideoOk = false">
          <source :src="act2CinematicMp4Src" type="video/mp4" />
          <source :src="act2CinematicWebmSrc" type="video/webm" />
        </video>

        <div class="cinematic-overlay act2"></div>

        <div class="cinematic-content act2">
          <div class="cine-container">
            <div class="cine-tags">
              <span class="cine-tag cyan">GeoGPT</span>
              <span class="cine-tag purple">OneAstronomy</span>
            </div>
            <h2 class="cine-title">从深空暗场，<br />到<span class="cine-gradient-text-2">轨道晨昏线</span>。</h2>
            <p class="cine-desc">宏观引擎：021 科学基础模型实现了天基算力与地学细节的无缝统一。在同一个平滑缩放的数字孪生坐标系中，审视行星级的多维演变。</p>
            <div v-if="assetHint" class="asset-hint">{{ assetHint }}</div>
          </div>
        </div>
      </section>

      <!-- ==========================================
           ACT 3: The Phase Transition
           ========================================== -->
      <section id="act-3" class="act-fullscreen group" data-act-id="act-3" role="link" tabindex="0" @click="goWorkbench" @keydown.enter.prevent="goWorkbench">
        <img class="cinematic-image" :src="act3GenosPosterSrc" alt="Act3 cinematic poster" loading="lazy" @error="(e) => onPosterImgError(e, act3GenosRemotePosterSrc)" />
        <video v-if="act3CinematicVideoOk" class="cinematic-video" autoplay loop muted playsinline preload="metadata" @error="act3CinematicVideoOk = false">
          <source :src="act3CinematicMp4Src" type="video/mp4" />
          <source :src="act3CinematicWebmSrc" type="video/webm" />
        </video>

        <div class="cinematic-overlay act3"></div>

        <div class="cinematic-content act3">
          <div class="cine-container">
            <div class="cine-tags">
              <span class="cine-tag purple">OneGenome</span>
              <span class="cine-tag orange">OnePorous</span>
            </div>
            <h2 class="cine-title">直视物质的<br /><span class="cine-gradient-text-3">相变临界点</span>。</h2>
            <p class="cine-desc">微观引擎：见证 OneGenome 基因序列与 OnePorous 材料晶格的耦合。我们在分子尺度的暗场下，重构科研范式并完成跨模态科学发现。</p>
          </div>
        </div>
      </section>

      <!-- ==========================================
           ACT 4: Semantic Galaxy (极简 HUD 重构版)
           ========================================== -->
      <section id="act-4" class="act-fullscreen act4-fullscreen" data-act-id="act-4" data-act-title="第四幕：数据星海" aria-label="第四幕：数据星海 / Semantic Galaxy">
        <video v-if="act4CinematicVideoOk" class="cinematic-video" autoplay loop muted playsinline preload="metadata" @error="act4CinematicVideoOk = false">
          <source :src="act4CinematicMp4Src" type="video/mp4" />
          <source :src="act4CinematicWebmSrc" type="video/webm" />
        </video>

        <!-- 遮罩重置：极其通透，仅保护顶部和底部文字，完全释放中间星海的光芒 -->
        <div class="cinematic-overlay act4"></div>

        <!-- 悬浮 HUD 层：硬核、极简、防重叠 -->
        <div class="cinematic-content act4">
          <div class="cine-container hud-layout">
            
            <!-- 顶部文案：克制、紧凑 -->
            <div class="hud-header">
              <div class="hud-kicker">
                <span class="hud-bracket">[</span> HAINA DATA HUB / 海纳数据底座 <span class="hud-bracket">]</span>
              </div>
              <!-- 强制不换行，杜绝“海”字掉落 -->
              <h2 class="hud-title">Embedding 联邦数据图谱</h2>
              <p class="hud-desc">
                数据范式跃迁：海量多源异构数据经由 021 模型向量化，在海纳底座中坍缩为语义星云。跨域关联在此实现自主推演与精准调度。
              </p>
            </div>

            <!-- 底部仪表盘：硬核极简，模拟推演状态 -->
            <div class="hud-footer">
              <div class="hud-status">
                <span class="hud-dot" aria-hidden="true"></span>
                <span class="hud-status-text">Federated Computing Active</span>
              </div>
              
              <div class="hud-metrics">
                <div class="metric">
                  <span>VECTORS</span>
                  102,400
                </div>
                <div class="metric">
                  <span>THROUGHPUT</span>
                  12 GB/s
                </div>
              </div>
            </div>
            
          </div>
        </div>
      </section>

      <!-- ==========================================
           ACT 5: 极客工坊 (Unified Scientific IDE)
           ========================================== -->
      <section id="act-5" class="act-fullscreen workbench-integrated workbench-hud" data-act-id="act-5" data-act-title="第五幕：极客工坊" aria-label="第五幕：极客工坊 / Unified Scientific IDE">
        <!-- 底座：完全无遮挡的背景视频 (保持 workbench-bg-viewport 门禁) -->
        <div class="workbench-bg-viewport">
          <video v-if="act5CinematicVideoOk" class="cinematic-video workbench-bg" autoplay loop muted playsinline preload="metadata" @error="act5CinematicVideoOk = false">
            <source :src="act5CinematicMp4Src" type="video/mp4" />
            <source :src="act5CinematicWebmSrc" type="video/webm" />
          </video>
          <div class="ar-grid-overlay" aria-hidden="true"></div>
          <div class="viewport-scanline" aria-hidden="true"></div>
          <div class="viewport-hud-overlay" aria-hidden="true">
            <div class="hud-coord">LAT: 29.1102 N / LON: 116.2984 E</div>
            <div class="hud-layer">ACTIVE_LAYER: POYANG_HYDROLOGY_V4</div>
          </div>
        </div>

        <!-- 散点式 HUD：保留 ide-frame 门禁，但去掉“封闭窗体”容器感 -->
        <div class="ide-frame hud-layer" aria-label="Unified workbench preview">
          <!-- 顶部：全局状态 (不占用中间视窗) -->
          <div class="hud-top-bar" aria-hidden="true">
            <div class="hud-id-box">
              <span class="label">MODEL_STATUS:</span>
              <span class="value">021_BASE_STABLE</span>
            </div>
            <div class="hud-center-aim">
              <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="rgba(0,240,255,0.42)" stroke-width="1" aria-hidden="true">
                <circle cx="20" cy="20" r="18" />
                <path d="M20 5V10 M20 30V35 M5 20H10 M30 20H35" />
              </svg>
            </div>
            <div class="hud-status-box">
              <span class="status-dot-blink" aria-hidden="true"></span>
              PIPELINE_READY
            </div>
          </div>

          <!-- 左侧：Agent 对话块 (轻量、可滚动、保留 AGENT_FLOW 门禁) -->
          <div class="hud-pane-left" aria-label="Agent flow preview">
            <div class="pane-tag">AGENT_EXECUTION_STREAM</div>
            <div class="pane-content chat-bubble">
              <div class="msg-ai">
                <span class="author">021_BRAIN:</span>
                海纳底座已就绪。正在解析多维科研意图，启动 021 基础模型进行跨尺度推理与知识合成。
              </div>
            </div>
          </div>

          <!-- 右侧：代码块 (无重底色，释放中心负空间) -->
          <div class="hud-pane-right" aria-label="Code preview">
            <div class="pane-tag">RESEARCH_CONTEXT.YAML</div>
            <div class="pane-content code-block">
              <pre>platform: zero2x_v0.21
core_model: 021_foundation
data_hub: haina_federated
status: ready_for_dispatch</pre>
            </div>
          </div>

          <!-- 底部中心：核心行动点 (视觉锚点) -->
          <div class="hud-bottom-cta">
            <div class="cta-inner">
              <p class="cta-tip">ASCEND TO THE AI-NATIVE WORKBENCH</p>
              <div class="cta-buttons">
                <a :href="workbenchLaunchpadHref" class="btn-main-glow" @click.prevent="goWorkbenchLaunchpad">LAUNCH 021 WORKSPACE</a>
                <a href="/demo" class="btn-sub-link" title="Tools / Validation system">EXPLORE SCENARIO VALIDATION</a>
              </div>
            </div>
          </div>
        </div>

        <!-- Aim must remain physically centered under zoom / ultrawide viewports (update_patch_0303). -->
        <div class="hud-center-aim-container" aria-hidden="true">
          <svg class="hud-center-aim" width="44" height="44" viewBox="0 0 40 40" fill="none" stroke="rgba(0,240,255,0.40)" stroke-width="1">
            <circle cx="20" cy="20" r="18" />
            <path d="M20 5V10 M20 30V35 M5 20H10 M30 20H35" />
          </svg>
        </div>

        <!-- 全局 HUD 装饰：四角线框 (不遮挡中心) -->
        <div class="hud-corners" aria-hidden="true">
          <div class="corner top-left"></div><div class="corner top-right"></div>
          <div class="corner bottom-left"></div><div class="corner bottom-right"></div>
        </div>

        <div class="compute-status-hud" aria-hidden="true">
          <span>COMPUTE_HUB:</span><span class="value">NANHU CLUSTER</span>
          <span class="divider">|</span>
          <span>SYSTEM_VERSION:</span><span class="value">0.21_ALPHA</span>
        </div>
      </section>

      <footer class="foot-minimal">
        <div class="foot-minimal-inner">
          <div class="foot-left">Zero2x | AI-Native 渐进式科研工作台</div>
          <div class="foot-right">
            <a class="foot-link" href="/demo" title="Tools / Validation system">Validation</a>
            <span class="sep">·</span>
            <span>© 2026 ZJ Lab</span>
          </div>
        </div>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import HeroVisual from './components/HeroVisual.vue'
import { buildAct2ChoreoHref } from './utils/choreo.js'
import { navigateWithFade } from './utils/navFade.js'
import { buildStubPlan, parseOmniInput } from './utils/omnibarCommands.js'

const inputEl = ref(null)
const query = ref('')
const result = ref('')

const placeholders = [
  '请输入科研意图... (如：分析特定海域叶绿素浓度)',
  '调用 OneGenome 引擎分析特定序列',
  '使用 021 模型进行跨尺度演化模拟',
]

const idx = ref(0)
const placeholder = computed(() => placeholders[idx.value % placeholders.length])

const takeMeToEarthHref = buildAct2ChoreoHref('poyang')
const act2Href = buildAct2ChoreoHref('')
const workbenchHref = '/workbench'
// Launchpad passes a lightweight context parameter to the heavy workbench.
const workbenchLaunchpadHref = '/workbench?context=021_research'

const act2CinematicVideoOk = ref(true)
const act3CinematicVideoOk = ref(true)
const act4CinematicVideoOk = ref(true)
const act5CinematicVideoOk = ref(true)

function withBase(p) {
  const rawBase = String(import.meta?.env?.BASE_URL || '/').trim() || '/'
  const base = rawBase.endsWith('/') ? rawBase : `${rawBase}/`
  const rel = String(p || '').replace(/^\//, '')
  return `${base}${rel}`
}

const act2CinematicWebmSrc = computed(() => withBase('/zero2x/ui/act2_earth.webm'))
const act2CinematicMp4Src = computed(() => withBase('/zero2x/ui/act2_earth.mp4'))
const act3CinematicWebmSrc = computed(() => withBase('/zero2x/ui/act3_dna.webm'))
const act3CinematicMp4Src = computed(() => withBase('/zero2x/ui/act3_dna.mp4'))
const act4CinematicWebmSrc = computed(() => withBase('/zero2x/ui/act4_galaxy.webm'))
const act4CinematicMp4Src = computed(() => withBase('/zero2x/ui/act4_galaxy.mp4'))

// Act 5 background prefers a dedicated workbench loop; fallback to act2 earth if needed.
const act5CinematicWebmSrc = computed(() => withBase('/zero2x/ui/act5_workbench_bg.webm'))
const act5CinematicMp4Src = computed(() => withBase('/zero2x/ui/act5_workbench_bg.mp4'))

const act2GeoLocalWebpSrc = computed(() => withBase('/zero2x/ui/act2_geogpt.webp'))
const act2AstronomyLocalWebpSrc = computed(() => withBase('/zero2x/ui/act2_astronomy.webp'))
const act3GenosLocalWebpSrc = computed(() => withBase('/zero2x/ui/act3_genos.webp'))
const act3OnePorousLocalWebpSrc = computed(() => withBase('/zero2x/ui/act3_oneporous.webp'))

const act2GeoRemotePosterSrc = 'https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?q=80&w=2000&auto=format&fit=crop'
const act2AstronomyRemotePosterSrc = 'https://images.unsplash.com/photo-1462332420958-a05d1e002413?q=80&w=2000&auto=format&fit=crop'
const act3GenosRemotePosterSrc = 'https://images.unsplash.com/photo-1584036561565-baf8f50a4ba6?q=80&w=2070&auto=format&fit=crop'
const act3OnePorousRemotePosterSrc = 'https://images.unsplash.com/photo-1504917595217-d4dc5ebe6122?q=80&w=2070&auto=format&fit=crop'

const act2GeoPosterSrc = computed(() => act2GeoLocalWebpSrc.value)
const act2AstronomyPosterSrc = computed(() => act2AstronomyLocalWebpSrc.value)
const act3GenosPosterSrc = computed(() => act3GenosLocalWebpSrc.value)
const act3OnePorousPosterSrc = computed(() => act3OnePorousLocalWebpSrc.value)

function _resolveMaybeRef(v) {
  try {
    if (v && typeof v === 'object' && 'value' in v) return v.value
  } catch (_) { }
  return v
}

function onPosterImgError(e, fallbackSrc) {
  try {
    const img = e?.target
    if (!img) return
    const fallback = String(_resolveMaybeRef(fallbackSrc) || '').trim()
    if (!fallback) return
    const cur = String(img.src || '')
    if (cur === fallback) return
    img.src = fallback
  } catch (_) { }
}

const assetHint = ref('')
async function _checkPosterAssets() {
  const urls = [
    act2GeoLocalWebpSrc.value,
    act2AstronomyLocalWebpSrc.value,
    act3GenosLocalWebpSrc.value,
    act3OnePorousLocalWebpSrc.value,
  ]
  try {
    const r = await Promise.all(urls.map((u) => fetch(u, { method: 'HEAD', cache: 'no-store' })))
    const ok = r.every((x) => x && x.ok)
    if (ok) {
      assetHint.value = ''
      return
    }
  } catch (_) { }
  assetHint.value = '提示：当前端口可能在运行旧的 dist / 反代了错误的 upstream，请重新 build+deploy。'
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
  } catch (_) { }
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
    result.value = [`Command: ${q}`, '', `Routing to: ${action.href}`].join('\n')
    navigateWithFade(action.href, { reason: 'omnibar-command' })
    return
  }

  result.value = buildStubPlan(action.intent)
  try {
    window.sessionStorage?.setItem?.('z2x:lastIntent', q)
  } catch (_) { }
  navigateWithFade(takeMeToEarthHref, { reason: 'omnibar-intent', delayMs: 520 })
}

function goAct2() { navigateWithFade(takeMeToEarthHref, { reason: 'landing-cta-act2' }) }
function goAct2Base() { navigateWithFade(act2Href, { reason: 'landing-cta-act2-base' }) }
function goWorkbench() { navigateWithFade(workbenchHref, { reason: 'landing-cta-workbench' }) }
function goWorkbenchLaunchpad() { navigateWithFade(workbenchLaunchpadHref, { reason: 'landing-cta-workbench-launchpad' }) }

function onGlobalKeydown(e) {
  if (!e) return
  const k = String(e.key || '').toLowerCase()
  if (k !== 'k') return
  if (e.metaKey || e.ctrlKey) {
    e.preventDefault()
    focusOmni()
  }
}

onMounted(() => {
  try { document.body.style.overflow = 'auto' } catch (_) { }
  window.addEventListener('keydown', onGlobalKeydown)

  try {
    if (typeof IntersectionObserver !== 'undefined') {
      const nodes = Array.from(document.querySelectorAll('[data-act-id]'))
      _actObserver = new IntersectionObserver(
        (entries) => {
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
  } catch (_) { }

  _timer = setInterval(() => { idx.value = (idx.value + 1) % placeholders.length }, 2800)
  setTimeout(() => focusOmni(), 250)
  setTimeout(() => _checkPosterAssets(), 600)
})

onUnmounted(() => {
  try { window.removeEventListener('keydown', onGlobalKeydown) } catch (_) { }
  if (_timer) { clearInterval(_timer); _timer = null }
  try { _actObserver?.disconnect?.() } catch (_) { }
  _actObserver = null
})
</script>

<style scoped>
/* ==========================================
   全局滚动吸附 (Scroll Snapping)
   ========================================== */
:global(html) {
  scroll-snap-type: y proximity;
  scroll-behavior: smooth;
}

.z2x {
  min-height: 100vh;
  background: radial-gradient(1200px 800px at 50% 20%, rgba(120, 160, 255, 0.12), rgba(0, 0, 0, 0.14)), linear-gradient(180deg, #030409, #000);
  color: #eef2ff;
}

.z2x ::selection {
  background: #00f0ff;
  color: #000;
}

.acts {
  padding: 0;
}

/* ==========================================
   ACT 1 (Hero)
   ========================================== */
.hero {
  position: relative;
  height: 100vh;
  display: grid;
  place-items: center;
  overflow: hidden;
  scroll-snap-align: start;
  scroll-snap-stop: always;
}

.hero-bg { position: absolute; inset: 0; z-index: 0; }
.hero-center {
  position: relative;
  width: min(1040px, 100%);
  z-index: 2;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.brand {
  text-align: center;
  margin-top: 0;
  margin-bottom: 24px;
  padding: 40px 20px;
  background: radial-gradient(ellipse at center, rgba(3, 4, 9, 0.85) 0%, rgba(3, 4, 9, 0.5) 40%, transparent 70%);
}

.desktop-only { display: inline; }
.mobile-only { display: none; }

.brand-kicker { letter-spacing: 0.35em; text-transform: uppercase; font-size: 10px; font-weight: 700; color: rgba(156, 163, 175, 1); margin-bottom: 12px; }

.brand-title {
  display: inline-block;
  font-size: clamp(52px, 9.5vw, 112px);
  line-height: 1.1;
  margin-top: 10px;
  margin-bottom: 16px;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-weight: 900;
  letter-spacing: -0.06em;
  color: transparent;
  -webkit-text-fill-color: transparent;
  background: linear-gradient(90deg, #00f0ff 0%, #3bf6ff 22%, #9d4edd 72%, #c77dff 100%);
  background-size: 140% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  filter: drop-shadow(0px 4px 12px rgba(0, 0, 0, 0.8)) drop-shadow(0px 0px 60px rgba(0, 0, 0, 1));
}

.brand-sub { margin-top: 12px; font-size: 15px; font-weight: 300; letter-spacing: 0.02em; color: rgba(209, 213, 219, 0.95); text-shadow: 0 2px 10px rgba(0, 0, 0, 0.8); }

.omnibar {
  margin: 22px auto 0;
  padding: 16px;
  border-radius: 20px;
  background: rgba(10, 15, 26, 0.70);
  border: 1px solid rgba(255, 255, 255, 0.10);
  backdrop-filter: blur(24px);
  box-shadow: 0 0 40px rgba(0, 240, 255, 0.12);
  transition: box-shadow 500ms ease, border-color 500ms ease;
}
.omnibar:hover { box-shadow: 0 0 60px rgba(0, 240, 255, 0.20); border-color: rgba(0, 240, 255, 0.30); }
.omnibar-hint { font-size: 11px; opacity: 0.78; margin-bottom: 10px; color: rgba(156, 163, 175, 1); font-weight: 500; }
.omnibar-kbd-hint { display: inline-flex; align-items: center; justify-content: center; padding: 2px 6px; margin: 0 6px; border-radius: 8px; background: rgba(255, 255, 255, 0.10); border: 1px solid rgba(255, 255, 255, 0.20); font-size: 11px; box-shadow: 0 1px 0 rgba(0, 0, 0, 0.35); }

.omnibar-shell { display: flex; align-items: center; gap: 8px; padding: 8px 14px; border-radius: 14px; background: rgba(5, 8, 16, 0.80); border: 1px solid rgba(255, 255, 255, 0.05); box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.02); }
.omnibar-shell:focus-within { border-color: rgba(0, 240, 255, 0.50); box-shadow: 0 0 0 4px rgba(0, 240, 255, 0.12); }
.omnibar-icon { color: rgba(107, 114, 128, 1); flex: 0 0 auto; }
.omnibar-input { width: 100%; font-size: 14px; padding: 8px 4px; background: transparent; border: none; color: #eef2ff; outline: none; }
.omnibar-kbd { display: inline-flex; align-items: center; gap: 6px; padding: 6px 9px; border-radius: 10px; background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.14); font-size: 12px; }

.btn { display: inline-flex; align-items: center; padding: 10px 14px; border-radius: 12px; background: rgba(42, 45, 74, 1); border: 1px solid rgba(255, 255, 255, 0.08); color: #eef2ff; cursor: pointer; transition: all 180ms ease; }
.btn:hover { background: rgba(58, 63, 108, 1); }
.btn.secondary { background: transparent; border-color: rgba(255, 255, 255, 0.20); }
.btn.secondary:hover { background: rgba(255, 255, 255, 0.10); }

.omnibar-result { margin-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.12); padding-top: 12px; }
.result-title { font-size: 12px; opacity: 0.72; margin-bottom: 8px; }
.result-pre { font-size: 13px; line-height: 1.5; opacity: 0.92; }

.hero-cta { display: flex; justify-content: center; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
.cta { padding: 10px 24px; border-radius: 999px; background: rgba(0, 0, 0, 0.40); border: 1px solid rgba(255, 255, 255, 0.15); backdrop-filter: blur(16px); color: rgba(209, 213, 219, 0.92); text-decoration: none; transition: all 180ms ease; }
.cta:hover { color: #fff; border-color: rgba(0, 240, 255, 0.50); background: rgba(255, 255, 255, 0.05); }
.cta.ghost:hover { border-color: rgba(157, 78, 221, 0.50); }

.scroll-hint {
  position: absolute;
  left: 50%;
  bottom: 18px;
  transform: translateX(-50%);
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  pointer-events: none;
  opacity: 0.62;
}

.mouse-icon {
  width: 22px;
  height: 34px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.28);
  background: rgba(0, 0, 0, 0.10);
  backdrop-filter: blur(10px);
  position: relative;
}

.mouse-icon::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 7px;
  width: 4px;
  height: 6px;
  border-radius: 999px;
  background: rgba(0, 240, 255, 0.72);
  transform: translateX(-50%);
  animation: mouse-wheel 1.35s ease-in-out infinite;
}

@keyframes mouse-wheel {
  0% { opacity: 0; transform: translate(-50%, 0); }
  25% { opacity: 1; }
  55% { opacity: 0; transform: translate(-50%, 10px); }
  100% { opacity: 0; transform: translate(-50%, 10px); }
}

.scroll-hint-text {
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.46);
}

/* ==========================================
   ACT 2 / 3 / 4 (全屏幕电影视口)
   ========================================== */
.act-fullscreen {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #030409;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  scroll-snap-align: start;
  scroll-snap-stop: always;
}

.act-fullscreen.act4-fullscreen {
  cursor: default;
}

.cinematic-image,
.cinematic-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.75;
  transform: scale(1.05);
  transition: transform 10s ease-out, opacity 0.8s ease;
  z-index: 0;
}

.act-fullscreen:hover .cinematic-image,
.act-fullscreen:hover .cinematic-video {
  transform: scale(1);
  opacity: 1;
}

.cinematic-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
  pointer-events: none;
}

.cinematic-overlay.act2 { background: linear-gradient(to top right, rgba(3,4,9,0.98) 0%, rgba(3,4,9,0.60) 40%, rgba(3,4,9,0.1) 100%); }
.cinematic-overlay.act3 { background: radial-gradient(circle at center, rgba(0,0,0,0.05) 0%, rgba(3,4,9,0.9) 100%), linear-gradient(to bottom, rgba(3,4,9,0.4), rgba(3,4,9,0.8)); }

/* 🌟 核心修复 2：彻底放开遮罩，只保留顶底的微弱压暗，释放中间 3D 粒子的光芒 */
.cinematic-overlay.act4 {
  background: linear-gradient(to bottom, rgba(3,4,9,0.95) 0%, transparent 20%, transparent 80%, rgba(3,4,9,0.95) 100%);
}

.cinematic-content {
  position: absolute;
  z-index: 20;
  inset: 0;
  display: flex;
  pointer-events: none;
}

.cine-container {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 12vh 48px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.act2 .cine-container { justify-content: flex-end; align-items: flex-start; text-align: left; }
.act3 .cine-container { justify-content: flex-end; align-items: flex-end; text-align: right; }

.cine-tags { display: flex; gap: 12px; margin-bottom: 2vh; }
.cine-tag { font-size: 10px; text-transform: uppercase; letter-spacing: 0.15em; padding: 6px 12px; border-radius: 999px; backdrop-filter: blur(8px); font-weight: 900; }
.cine-tag.cyan { color: #00f0ff; border: 1px solid rgba(0, 240, 255, 0.30); background: rgba(0, 240, 255, 0.1); }
.cine-tag.purple { color: #9d4edd; border: 1px solid rgba(157, 78, 221, 0.30); background: rgba(157, 78, 221, 0.1); }
.cine-tag.orange { color: #ff6b00; border: 1px solid rgba(255, 107, 0, 0.30); background: rgba(255, 107, 0, 0.1); }

/* 🌟 核心修复 1：强制单行显示，防止中文孤字换行 */
.cine-title {
  font-size: clamp(36px, 5vw, 64px);
  font-weight: 1000;
  line-height: 1.15;
  letter-spacing: -0.02em;
  margin-bottom: 2vh;
  color: #fff;
  text-shadow: 0 4px 24px rgba(0,0,0,0.8);
  white-space: nowrap; 
}

.cine-desc {
  font-size: clamp(15px, 1.5vw, 18px);
  color: rgba(209, 213, 219, 0.95);
  max-width: 600px;
  line-height: 1.6;
  font-weight: 300;
  text-shadow: 0 2px 10px rgba(0,0,0,0.8);
}

.cine-gradient-text-2 { background: linear-gradient(to right, #00f0ff, #fff); -webkit-background-clip: text; background-clip: text; color: transparent; }
.cine-gradient-text-3 { background: linear-gradient(to left, #ff6b00, #9d4edd); -webkit-background-clip: text; background-clip: text; color: transparent; }

/* ==========================================
   Act 4: Semantic Galaxy 极简 HUD 样式
   ========================================== */
.cinematic-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
  /* 🌟 核心修复 2 补充：全局极其缓慢的推轨缩放，不管 Threejs 怎么渲染，整个星系一定在动！ */
  animation: galaxy-fly-through 40s linear infinite alternate;
}

@keyframes galaxy-fly-through {
  0% { transform: scale(1); }
  100% { transform: scale(1.15); }
}

.hud-layout {
  justify-content: space-between;
  padding: 10vh 6vw;
}

.hud-header {
  max-width: 600px;
}

.hud-kicker {
  font-family: 'Inter', sans-serif;
  font-size: 11px;
  letter-spacing: 0.3em;
  color: rgba(255,255,255,0.7);
  margin-bottom: 12px;
  font-weight: 900;
  display: flex;
  align-items: center;
  gap: 8px;
}

.hud-bracket {
  color: rgba(0, 240, 255, 0.6);
  font-weight: normal;
}

/* 🌟 核心修复 1：强制不换行 */
.hud-title {
  font-size: clamp(32px, 4vw, 56px);
  font-weight: 900;
  letter-spacing: -0.02em;
  color: #fff;
  text-shadow: 0 4px 24px rgba(0,0,0,0.8);
  margin-bottom: 16px;
  white-space: nowrap;
}

.hud-desc {
  font-size: clamp(14px, 1.2vw, 16px);
  color: rgba(255,255,255,0.85);
  line-height: 1.6;
  border-left: 2px solid rgba(0,240,255,0.6);
  padding-left: 16px;
  text-shadow: 0 2px 8px rgba(0,0,0,0.8);
}

.hud-footer {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  width: 100%;
}

.hud-status {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(10, 15, 26, 0.6);
  padding: 10px 20px;
  border-radius: 999px;
  border: 1px solid rgba(0,240,255,0.2);
  backdrop-filter: blur(12px);
  box-shadow: 0 0 30px rgba(0, 240, 255, 0.1);
}

.hud-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #00f0ff;
  box-shadow: 0 0 10px #00f0ff; animation: act4-pulse 2s infinite;
}

.hud-status-text {
  font-size: 11px; letter-spacing: 0.2em; font-weight: 700; color: #fff; text-transform: uppercase;
}

.hud-metrics {
  display: flex;
  gap: 40px;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-family: 'Inter', sans-serif;
  font-size: 28px;
  font-weight: 300;
  color: #fff;
  text-shadow: 0 0 20px rgba(255,255,255,0.3);
}

.metric span {
  font-size: 9px;
  letter-spacing: 0.2em;
  color: rgba(255,255,255,0.5);
  font-weight: 700;
}

@keyframes act4-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.45; transform: scale(0.8); }
}

/* ==========================================
   ACT 5: Unified Scientific IDE (融合工作台预览)
   ========================================== */

.workbench-integrated {
  position: relative;
  background: #000;
  cursor: default;
}

.workbench-hud {
  position: relative;
}

.workbench-bg-viewport {
  position: absolute;
  inset: 0;
  z-index: 1;
}

/* Keep the viewport readable while allowing the cinematic video to show through. */
.workbench-bg-viewport::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  /* Center is kept brighter to preserve the cinematic focal point. */
  background:
    radial-gradient(900px 520px at 50% 52%, rgba(0, 0, 0, 0.06), rgba(0, 0, 0, 0.46)),
    linear-gradient(180deg, rgba(0, 0, 0, 0.08), rgba(0, 0, 0, 0.30));
}

.cinematic-video.workbench-bg {
  opacity: 0.84;
  /* Higher contrast but keep mid-tones visible under HUD blocks. */
  filter: contrast(1.18) brightness(0.86) saturate(1.10);
}

.ar-grid-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  opacity: 0.34;
  background-image:
    radial-gradient(rgba(0, 240, 255, 0.11) 1px, transparent 0),
    linear-gradient(90deg, rgba(0, 240, 255, 0.06) 1px, transparent 1px),
    linear-gradient(rgba(0, 240, 255, 0.04) 1px, transparent 1px);
  background-size: 46px 46px, 220px 220px, 220px 220px;
  background-position: 0 0, 0 0, 0 0;
}

.viewport-scanline {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  opacity: 0.62;
  background:
    linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 240, 255, 0.05) 50%),
    linear-gradient(90deg, rgba(255, 0, 0, 0.02), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.02));
  background-size: 100% 4px, 3px 100%;
  mix-blend-mode: screen;
}

.viewport-hud-overlay {
  position: absolute;
  top: 40px;
  right: 40px;
  text-align: right;
  color: rgba(0, 240, 255, 0.95);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 10px;
  letter-spacing: 1px;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.8);
  z-index: 3;
}

/* Scattered HUD: keep ide-frame for TDD, but render as an unboxed HUD layer. */
.ide-frame.hud-layer {
  position: relative;
  z-index: 10;
  width: 100%;
  height: 100%;
  padding: clamp(18px, 3.2vw, 44px);
  pointer-events: none;
}

.hud-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.72);
}

.hud-id-box {
  pointer-events: none;
  color: rgba(0, 240, 255, 0.95);
  background: rgba(0, 240, 255, 0.05);
  padding: 6px 12px;
  border: 1px solid rgba(0, 240, 244, 0.22);
}

.hud-id-box .value {
  font-weight: 900;
  margin-left: 6px;
}

.hud-center-aim {
  opacity: 0.8;
}

.hud-center-aim-container {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 8;
  pointer-events: none;
  opacity: 0.9;
  filter: drop-shadow(0 0 18px rgba(0, 240, 255, 0.12));
  width: clamp(40px, 5.2vw, 56px);
  aspect-ratio: 1 / 1;
  display: grid;
  place-items: center;
}

.hud-center-aim-container .hud-center-aim {
  width: 100%;
  height: 100%;
}

.hud-status-box {
  display: flex;
  align-items: center;
  gap: 10px;
  opacity: 0.78;
}

.status-dot-blink {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(0, 240, 255, 0.95);
  box-shadow: 0 0 12px rgba(0, 240, 255, 0.65);
  animation: act4-pulse 1.2s infinite;
}

.hud-pane-left,
.hud-pane-right {
  position: absolute;
  top: clamp(86px, 14vh, 160px);
  width: min(360px, 28vw);
  pointer-events: auto;
}

.hud-pane-left {
  left: clamp(14px, 3.2vw, 44px);
}

.hud-pane-right {
  right: clamp(14px, 3.2vw, 44px);
}

.pane-tag {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 9px;
  letter-spacing: 0.22em;
  color: rgba(0, 240, 255, 0.62);
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(0, 240, 255, 0.20);
  padding-bottom: 5px;
  width: fit-content;
  text-transform: uppercase;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.70);
}

.pane-content {
  max-height: min(420px, 56vh);
  overflow: auto;
  overscroll-behavior: contain;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 18px;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.45);
}

.chat-bubble {
  font-size: clamp(12px, 1.05vw, 14px);
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.92);
}

.chat-bubble .author {
  display: block;
  font-size: 9px;
  font-weight: 900;
  color: rgba(0, 240, 255, 0.95);
  letter-spacing: 0.18em;
  margin-bottom: 8px;
  text-transform: uppercase;
}

.msg-user {
  margin-top: 14px;
  opacity: 0.58;
  font-style: italic;
  border-top: 1px dashed rgba(255, 255, 255, 0.14);
  padding-top: 10px;
}

.code-block {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: clamp(11px, 0.95vw, 13px);
  color: rgba(165, 180, 252, 0.94);
  line-height: 1.7;
}

.code-block pre {
  margin: 0;
  white-space: pre;
}

.hud-bottom-cta {
  position: absolute;
  left: 50%;
  bottom: clamp(18px, 4.8vh, 56px);
  transform: translateX(-50%);
  text-align: center;
  pointer-events: auto;
}

.cta-inner {
  padding: 10px 14px;
  border-radius: 14px;
  background: rgba(0, 0, 0, 0.10);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.cta-tip {
  margin: 0 0 14px;
  font-size: 10px;
  letter-spacing: 0.30em;
  color: rgba(255, 255, 255, 0.40);
  font-weight: 900;
  text-transform: uppercase;
}

.cta-buttons {
  display: flex;
  gap: 22px;
  align-items: center;
  justify-content: center;
}

.btn-main-glow {
  background: rgba(0, 240, 255, 0.96);
  color: #000;
  padding: 14px 30px;
  border-radius: 8px;
  font-weight: 900;
  font-size: 13px;
  letter-spacing: 0.14em;
  text-decoration: none;
  box-shadow: 0 0 34px rgba(0, 240, 255, 0.42);
  transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease;
  text-transform: uppercase;
}

.btn-main-glow:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 0 54px rgba(0, 240, 255, 0.70);
  filter: brightness(1.02);
}

.btn-sub-link {
  font-size: 10px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.46);
  letter-spacing: 0.22em;
  text-decoration: none;
  text-transform: uppercase;
}

.btn-sub-link:hover {
  color: rgba(255, 255, 255, 0.86);
  text-decoration: underline;
}

.hud-corners {
  position: absolute;
  inset: 0;
  z-index: 11;
  pointer-events: none;
}

.corner {
  position: absolute;
  width: 22px;
  height: 22px;
  border: 1px solid rgba(0, 240, 255, 0.30);
}

.corner.top-left { top: 18px; left: 18px; border-right: none; border-bottom: none; }
.corner.top-right { top: 18px; right: 18px; border-left: none; border-bottom: none; }
.corner.bottom-left { bottom: 18px; left: 18px; border-right: none; border-top: none; }
.corner.bottom-right { bottom: 18px; right: 18px; border-left: none; border-top: none; }

.compute-status-hud {
  position: absolute;
  bottom: 10px;
  left: 0;
  width: 100%;
  text-align: center;
  z-index: 9;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 9px;
  letter-spacing: 0.18em;
  color: rgba(255, 255, 255, 0.34);
  text-transform: uppercase;
  pointer-events: none;
}

.compute-status-hud .value {
  color: rgba(0, 240, 255, 0.90);
  margin: 0 8px 0 6px;
}

.compute-status-hud .divider {
  margin: 0 12px;
  opacity: 0.22;
}

.foot-minimal {
  position: fixed;
  bottom: 24px;
  left: 0;
  width: 100%;
  z-index: 3200;
  pointer-events: none;
}

.foot-minimal-inner {
  width: min(1400px, calc(100% - 48px));
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  opacity: 0.48;
}

.foot-minimal .foot-link {
  pointer-events: auto;
  color: rgba(255, 255, 255, 0.9);
  text-decoration: none;
  font-weight: 900;
}

.foot-minimal .foot-link:hover {
  text-decoration: underline;
}

.sep { opacity: 0.6; margin: 0 8px; }

/* =========================================
   响应式适配 (Mobile & Tablet)
   ========================================= */
@media (max-width: 920px) {
  .hud-pane-left,
  .hud-pane-right {
    width: min(320px, 34vw);
    top: clamp(76px, 12vh, 140px);
  }
}

@media (max-width: 860px) {
  .scroll-hint { bottom: 14px; }
}

@media (max-width: 768px) {
  .brand { margin-top: 0vh; padding: 20px 10px; }
  .omnibar-kbd, .omnibar-kbd-hint, .omnibar-actions, .omnibar-shell .btn, .omnibar-shell a.btn { display: none !important; }
  .desktop-only { display: none !important; }
  .mobile-only { display: inline !important; }
  .omnibar-shell { padding: 10px 14px; }
  .omnibar-input { font-size: 13px; width: 100%; }
  .hero-cta { flex-direction: column; align-items: center; gap: 12px; padding: 0 20px; margin-top: 32px; }
  .cta { width: 100%; max-width: 300px; text-align: center; padding: 14px 24px; }
  
  .cine-container { padding: 10vh 24px; }
  
  /* 移动端屏幕窄，允许换行 */
  .cine-title, .hud-title {
    white-space: normal; 
    word-break: keep-all; 
  }
  
  .hud-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }
  .hud-metrics { gap: 20px; }
  .metric { font-size: 18px; }
  
  .viewport-hud-overlay { top: 20px; right: 20px; }

  .hud-pane-right { display: none; }
  .hud-pane-left {
    width: calc(100% - (clamp(18px, 3.2vw, 44px) * 2));
    left: clamp(18px, 3.2vw, 44px);
    right: auto;
    top: clamp(96px, 15vh, 160px);
  }

  .hud-bottom-cta { width: calc(100% - 36px); }
  .cta-buttons { flex-direction: column; gap: 12px; }
  .btn-main-glow { width: 100%; text-align: center; }
}

@media (max-height: 720px) {
  .hud-pane-left,
  .hud-pane-right { top: clamp(70px, 10vh, 120px); }
  .pane-content { max-height: min(320px, 44vh); padding: 14px; }
  .hud-bottom-cta { bottom: 14px; }
}

@media (prefers-reduced-motion: reduce) {
  .viewport-scanline { display: none; }
  .status-dot-blink { animation: none; }
  .mouse-icon::after { animation: none; }
}
</style>