Gemini said
我已经收到了您的诉求。针对您提供的最新截图（image_b8881e.jpg），您的思路非常准确：“第四幕”作为数据星海（Semantic Galaxy），其核心魅力在于 宏大的视觉奇观（Cinematic Spectacle），而不是让人去点击散落的表格和按钮。

我们将摒弃传统的交互卡片，把第四幕彻底升级为与前两幕对齐的 “全画幅电影级预告片” (Cinematic Wrapper) 样式。同时，使用 pointer-events-none 屏蔽掉底层画布的手动交互，让它看起来完全像是由“AI 正在自主巡航”。
根据我们前面推敲的“极致留白、暗场光影、视差穿透”理念，我为您彻底重构了 Zero2xApp.vue 中的 第二幕（宏观孪生） 和 第三幕（微观深潜）。

💡 升级方案与设计亮点
废弃传统的 Card-Grid，拥抱 Cinematic Card (电影级宽幅卡片)：
删除了原先干瘪的三列小卡片（Killer Feature / Data / AI）。采用 21:9 黄金电影画幅的无边框容器，承载全屏视频。

WebM 视频底层嵌入机制：
采用 <video autoplay loop muted playsinline> 的标准工业解法。playsinline 极其重要，它能确保在 iOS/Android 移动端视频也是作为背景静默自动播放，而不会被系统强制全屏拉起。

极简排版与渐变光盾 (Gradient Shield)：
视频由于是高对比度光影，直接放字必定会“花”。我在 CSS 中新增了 .cinematic-overlay。第二幕是从左下角发散的黑洞渐变，第三幕是四周压暗的晕影（Vignette）。这完美地托住了文字，实现了真正的**“字在光影中浮现”**。

下面是为您完整更新的 Zero2xApp.vue。我已经将新的 UI 结构和对应的 CSS 样式严丝合缝地织入了您的代码中。<template>
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
          <div class="omnibar-hint">Press ⌘K to start your research</div>
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
          </div>
          <div class="omnibar-actions">
            <button class="btn" type="button" @click="submit">Run</button>
            <a class="btn secondary" :href="takeMeToEarthHref" @click.prevent="goAct2">进入第二幕</a>
          </div>
          <div v-if="result" class="omnibar-result">
            <div class="result-title">AI Preview (MVP Stub)</div>
            <pre class="result-pre">{{ result }}</pre>
          </div>
        </div>

        <div class="hero-cta">
          <a class="cta" href="#act-2">开始宇宙漫游</a>
          <a class="cta ghost" :href="takeMeToEarthHref" @click.prevent="goAct2">进入第二幕：飞向鄱阳湖</a>
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
      <!-- ==========================================
           ACT 2: The Orbital Horizon (宏观孪生)
           ========================================== -->
      <section id="act-2" class="act" data-act-id="act-2">
        <div class="act-title">第二幕：宏观孪生</div>
        <div class="act-desc">不再是静态图表。宇宙与地球的无缝穿梭（Cesium 电影化叙事）。</div>
        
        <div class="cinematic-wrapper mt-6" @click="goAct2">
          <!-- 核心视频层：强制静音、循环、内联播放适配移动端 -->
          <video autoplay loop muted playsinline class="cinematic-video">
            <source src="/zero2x/ui/act2_earth.mp4" type="video/mp4" />
          </video>
          
          <!-- 防眩光黑洞遮罩：左下角压暗托字，右上角留出深空 -->
          <div class="cinematic-overlay act2"></div>

          <!-- 极简内容层 -->
          <div class="cinematic-content act2">
            <div class="cine-tags">
              <span class="cine-tag cyan">GeoGPT</span>
              <span class="cine-tag purple">OneAstronomy</span>
            </div>
            <h2 class="cine-title">
              从深空暗场，<br>
              到<span class="cine-gradient-text-2">轨道晨昏线</span>。
            </h2>
            <p class="cine-desc">
              021 引擎在无尽黑暗中寻找关联，将天文学的广袤与地球科学的微小悸动，统合在一个无缝缩放的数字孪生坐标系中。
            </p>
          </div>
        </div>
      </section>

      <!-- ==========================================
           ACT 3: The Phase Transition (微观深潜)
           ========================================== -->
      <section id="act-3" class="act" data-act-id="act-3">
        <div class="act-title">第三幕：微观深潜</div>
        <div class="act-desc">生命与材料尺度降维：直视核苷酸序列与拓扑结构的交互耦合。</div>
        
        <div class="cinematic-wrapper mt-6">
          <video autoplay loop muted playsinline class="cinematic-video">
            <source src="/zero2x/ui/act3_dna.mp4" type="video/mp4" />
          </video>
          
          <!-- 晕影遮罩：四周压暗，中心微透，文字靠右对齐 -->
          <div class="cinematic-overlay act3"></div>

          <div class="cinematic-content act3">
            <div class="cine-tags">
              <span class="cine-tag purple">Genos</span>
              <span class="cine-tag orange">OnePorous</span>
            </div>
            <h2 class="cine-title">
              直视物质的<br>
              <span class="cine-gradient-text-3">相变临界点</span>。
            </h2>
            <p class="cine-desc">
              当生命密码的发光流体，穿透高强度航空晶格。我们在微距的黑暗深处，见证结构生物学与材料热力学的跨模态融合。
            </p>
          </div>
        </div>
      </section>

      <!-- ==========================================
           ACT 4: Semantic Galaxy (语义星海 - 全屏电影级重构)
           ========================================== -->
      <section id="act-4" class="act" data-act-id="act-4">
        <div class="act-title">第四幕：数据星海</div>
        <div class="act-desc">Embedding 语义星海 (Cinematic Spectacle)：移除人工交互，由“观察者相机”自动巡航，在高维坍缩的星云簇间揭示跨学科关联。</div>

        <!-- 使用统一的 cinematic-wrapper 营造全景预告片感 -->
        <div class="cinematic-wrapper mt-6 cursor-default">
          <!-- 背景层：DataGalaxy 将作为底层的动态画布 -->
          <div class="cinematic-canvas">
            <DataGalaxy />
          </div>

          <!-- 左侧与底部深色渐变托底 -->
          <div class="cinematic-overlay act4"></div>

          <!-- 悬浮排版层：1:1 复刻设计稿 -->
          <div class="cinematic-content act4-content">
            <div class="act4-header">
              <div class="cine-tag-plain">ACT 4 / DATA GALAXY</div>
              <h2 class="cine-title">
                Embedding 语义星海
              </h2>
              <p class="cine-desc-bordered">
                021 模型正在高维空间中自主推演：多学科数据向量在此坍缩成星云簇，跨域关联被持续发现与重组。
              </p>
            </div>

            <div class="act4-footer">
              <div class="status-indicator">
                <span class="status-dot"></span>
                <span class="status-text">Autonomous Reasoning in Progress...</span>
              </div>
              
              <div class="act4-cards">
                <div class="act4-card">
                  <div class="act4-card-title">Dimensionality Reduction</div>
                  <div class="act4-card-desc">多学科向量在 3D 空间坍缩为星云簇（无需表格/连线）</div>
                </div>
                <div class="act4-card">
                  <div class="act4-card-title">Cinematic Choreography</div>
                  <div class="act4-card-desc">相机自动巡航：远景俯瞰 → 俯冲进入某簇 → 再拉远</div>
                </div>
                <div class="act4-card">
                  <div class="act4-card-title">Proximity Labels</div>
                  <div class="act4-card-desc">进入簇内自动浮现语义标签，飞离后自然消散</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ==========================================
           ACT 5: 极客工坊
           ========================================== -->
      <section id="act-5" class="act" data-act-id="act-5">
        <div class="act-title">第五幕：极客工坊</div>
        <div class="act-desc">叙事终点自然过渡到 AI-Native 工作台（Monaco / JupyterLite 预留）。</div>

        <div class="workbench">
          <div class="wb-pane">
            <div class="wb-title">Agent Flow</div>
            <pre class="wb-code">@AgentBuilder 帮我调用刚刚的鄱阳湖数据集，生成一份生态评估代码\n\n# TODO(MVP): typewriter streaming stub</pre>
          </div>
          <div class="wb-pane">
            <div class="wb-title">3D Preview</div>
            <div class="wb-preview">Cesium / Charts Placeholder</div>
          </div>
          <div class="wb-pane">
            <div class="wb-title">Interactive Papers</div>
            <div class="wb-preview">Docs / Community Placeholder</div>
          </div>
        </div>

        <div class="launch-row">
          <a class="launch" href="/workbench">Launch My Workspace</a>
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

const acts = [
  { id: 'act-1', label: 'Act 1' },
  { id: 'act-2', label: 'Act 2' },
  { id: 'act-3', label: 'Act 3' },
  { id: 'act-4', label: 'Act 4' },
  { id: 'act-5', label: 'Act 5' },
]

const activeAct = ref('act-1')
let _actObserver = null
let _act2AutoObserver = null
let _lastScrollY = 0
let _autoArmed = true

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

  // MVP stub: emulate “AI preview” for free-form intents.
  result.value = buildStubPlan(action.intent)
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

function _armAutoAct2OncePerSession() {
  try {
    if (typeof window === 'undefined') return
    if (_prefersReducedMotion()) return

    const key = 'z2x:auto-act2:done'
    if (window.sessionStorage?.getItem?.(key) === '1') return

    const act2 = document.getElementById('act-2')
    if (!act2) return
    if (typeof IntersectionObserver === 'undefined') return

    _lastScrollY = window.scrollY || 0
    const onScroll = () => {
      const y = window.scrollY || 0
      _autoArmed = y > _lastScrollY
      _lastScrollY = y
    }
    window.addEventListener('scroll', onScroll, { passive: true })

    _act2AutoObserver = new IntersectionObserver(
      (entries) => {
        const hit = entries?.find?.((e) => e?.isIntersecting)
        if (!hit) return
        if (!_autoArmed) return
        // Only trigger when Act2 section is mostly visible.
        if ((hit.intersectionRatio || 0) < 0.72) return

        try {
          window.sessionStorage?.setItem?.(key, '1')
        } catch (_) {
          // ignore
        }

        try {
          _act2AutoObserver?.disconnect?.()
        } catch (_) {
          // ignore
        }
        _act2AutoObserver = null

        try {
          window.removeEventListener('scroll', onScroll)
        } catch (_) {
          // ignore
        }

        navigateWithFade(takeMeToEarthHref, { reason: 'landing-scroll-act2', delayMs: 260 })
      },
      { threshold: [0.35, 0.55, 0.72, 0.9] }
    )

    _act2AutoObserver.observe(act2)
  } catch (_) {
    // ignore
  }
}

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
  try {
    document.body.style.overflow = 'auto'
  } catch (_) {
    // ignore
  }

  window.addEventListener('keydown', onGlobalKeydown)

  _armAutoAct2OncePerSession()

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
  } catch (_) {
    // ignore
  }

  _timer = setInterval(() => {
    idx.value = (idx.value + 1) % placeholders.length
  }, 2800)

  setTimeout(() => focusOmni(), 250)
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

  try {
    _act2AutoObserver?.disconnect?.()
  } catch (_) {
    // ignore
  }
  _act2AutoObserver = null
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
  margin-bottom: 20px;
}

.brand-kicker {
  letter-spacing: 0.30em;
  text-transform: uppercase;
  opacity: 0.72;
  font-size: 10px;
  font-weight: 700;
  color: rgba(156, 163, 175, 1);
}

.brand-title {
  font-size: clamp(52px, 9.5vw, 112px);
  line-height: 1.1;
  margin-top: 10px;
  font-weight: 900;
  letter-spacing: -0.04em;
  text-transform: lowercase;
  color: transparent;
  background: linear-gradient(90deg, #00f0ff, #9d4edd);
  -webkit-background-clip: text;
  background-clip: text;
  filter: drop-shadow(0 4px 24px rgba(0, 0, 0, 0.8));
}

.brand-sub {
  margin-top: 10px;
  opacity: 1;
  font-size: 14px;
  font-weight: 300;
  letter-spacing: 0.02em;
  color: rgba(209, 213, 219, 0.92);
  filter: drop-shadow(0 2px 10px rgba(0, 0, 0, 0.55));
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

.omnibar-shell {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
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
  padding: 10px 8px;
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

.omnibar-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 12px;
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
  font-weight: bold;
}

.act-desc {
  margin-top: 10px;
  opacity: 0.84;
  max-width: 820px;
}

/* ==========================================
   电影级全屏视频卡片 (Cinematic Card) CSS
   ========================================== */
.cinematic-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 21 / 9;
  border-radius: 20px;
  overflow: hidden;
  background: #030409;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.6);
  cursor: pointer;
  /* 解决移动端 safari overflow-hidden 圆角失效问题 */
  -webkit-mask-image: -webkit-radial-gradient(white, black);
}

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

.cinematic-wrapper:hover .cinematic-video {
  transform: scale(1);
  opacity: 1;
}

/* 防眩光光盾遮罩 */
.cinematic-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
  pointer-events: none;
}

/* 第二幕：左下角深沉黑洞拖住文字，右上角留白 */
.cinematic-overlay.act2 {
  background: linear-gradient(to top right, rgba(3,4,9,0.95) 0%, rgba(3,4,9,0.4) 50%, rgba(3,4,9,0.1) 100%);
}

/* 第三幕：四周强烈晕影，中间透气 */
.cinematic-overlay.act3 {
  background: radial-gradient(circle at center, transparent 0%, rgba(3,4,9,0.85) 100%),
              linear-gradient(to bottom, rgba(3,4,9,0.2), rgba(3,4,9,0.6));
}

.cinematic-content {
  position: absolute;
  z-index: 20;
  inset: 0;
  padding: 40px 48px;
  display: flex;
  flex-direction: column;
  pointer-events: none;
}

.cinematic-content.act2 {
  justify-content: flex-end;
  align-items: flex-start;
  text-align: left;
}

.cinematic-content.act3 {
  justify-content: flex-end;
  align-items: flex-end;
  text-align: right;
}

/* 标签样式 */
.cine-tags { display: flex; gap: 12px; margin-bottom: 20px; }
.cine-tag {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  padding: 4px 10px;
  border-radius: 999px;
  backdrop-filter: blur(4px);
  font-weight: 900;
}
.cine-tag.cyan { color: #00F0FF; border: 1px solid rgba(0, 240, 255, 0.3); background: rgba(0, 240, 255, 0.05); }
.cine-tag.purple { color: #9D4EDD; border: 1px solid rgba(157, 78, 221, 0.3); background: rgba(157, 78, 221, 0.05); }
.cine-tag.orange { color: #FF6B00; border: 1px solid rgba(255, 107, 0, 0.3); background: rgba(255, 107, 0, 0.05); }

/* 标题字体 */
.cine-title {
  font-size: clamp(32px, 4vw, 56px);
  font-weight: 900;
  line-height: 1.15;
  letter-spacing: -0.02em;
  margin-bottom: 16px;
  color: #fff;
  text-shadow: 0 4px 24px rgba(0,0,0,0.8);
}

.cine-desc {
  font-size: 15px;
  color: rgba(209, 213, 219, 0.9);
  max-width: 500px;
  line-height: 1.6;
  font-weight: 300;
  text-shadow: 0 2px 10px rgba(0,0,0,0.8);
}

.cine-gradient-text-2 {
  background: linear-gradient(to right, #00F0FF, #fff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.cine-gradient-text-3 {
  background: linear-gradient(to left, #FF6B00, #9D4EDD);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

/* ==========================================
   ACT 4 (Semantic Galaxy) 特定样式
   ========================================== */
.cinematic-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  /* 屏蔽 DataGalaxy 内部的鼠标交互，作为纯动态背景 */
  pointer-events: none; 
}

.cinematic-overlay.act4 {
  background: 
    linear-gradient(to right, rgba(3,4,9,0.95) 0%, rgba(3,4,9,0.4) 45%, transparent 100%),
    linear-gradient(to top, rgba(3,4,9,0.95) 0%, rgba(3,4,9,0.2) 35%, transparent 100%);
}

.act4-content {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
  pointer-events: none;
}

.act4-header {
  max-width: 520px;
}

.cine-tag-plain {
  font-size: 10px;
  letter-spacing: 0.3em;
  font-weight: 800;
  color: rgba(156, 163, 175, 1);
  margin-bottom: 12px;
  text-transform: uppercase;
}

.cine-desc-bordered {
  font-size: 14px;
  color: rgba(209, 213, 219, 0.9);
  line-height: 1.6;
  font-weight: 300;
  border-left: 2px solid rgba(255, 255, 255, 0.2);
  padding-left: 16px;
  text-shadow: 0 2px 10px rgba(0,0,0,0.8);
}

.act4-footer {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00F0FF;
  box-shadow: 0 0 10px #00F0FF;
  animation: act4-pulse 2s infinite;
}

.status-text {
  font-size: 10px;
  letter-spacing: 0.2em;
  font-weight: 800;
  color: rgba(156, 163, 175, 0.9);
  text-transform: uppercase;
}

.act4-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.act4-card {
  background: rgba(10, 15, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
  backdrop-filter: blur(12px);
}

.act4-card-title {
  font-size: 12px;
  font-weight: 700;
  color: rgba(209, 213, 219, 1);
  margin-bottom: 6px;
}

.act4-card-desc {
  font-size: 12px;
  color: rgba(156, 163, 175, 0.8);
  line-height: 1.5;
}

@keyframes act4-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

/* ------------------------------------- */

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
  .card-grid, .act4-cards {
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

@media (max-width: 768px) {
  .brand {
    margin-top: 0vh; 
    padding: 20px 10px;
  }
  .omnibar-hint,
  .omnibar-kbd,
  .omnibar-actions,
  .omnibar-shell .btn,
  .omnibar-shell a.btn {
    display: none !important;
  }
  .omnibar-shell {
    padding: 10px 14px;
  }
  .omnibar-input {
    font-size: 13px;
    width: 100%;
  }
  .hero-cta {
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 0 20px;
    margin-top: 32px;
  }
  .cta {
    width: 100%;
    max-width: 300px;
    text-align: center;
    padding: 14px 24px;
  }
  
  /* 电影级卡片移动端响应式 */
  .cinematic-wrapper {
    aspect-ratio: 16 / 12;
  }
  .cinematic-content {
    padding: 24px;
  }
}
</style>
</style>⚠️ MP4 视频上线的 3 个关键避坑指南（请务必转告前端/视频同学）：
必须剥离音轨 (Remove Audio Track)：
iOS Safari 有极严的自动播放限制。即使您在代码里写了 muted，如果 MP4 文件本身包含音轨（哪怕是完全静音的音轨），在低电量模式下仍可能被拦截导致黑屏。请务必用剪辑软件导出**“无音频”**的版本。

控制文件体积 (Size limits)：
这两个视频作为 Landing Page 的背景，单文件大小必须压缩在 3MB - 6MB 之间。可以适当降低比特率 (Bitrate)，因为我们在视频上方盖了 .cinematic-overlay (渐变暗场遮罩)，轻微的压缩画质损失是肉眼看不出来的。

首帧同名占位图 (Poster) - 可选但推荐：
如果您的服务器带宽不高，可以在 <video> 标签加上 poster 属性，例如 <video poster="/zero2x/ui/act2_earth_poster.jpg" autoplay loop muted playsinline>。这样在视频加载的这 1-2 秒内，会先显示一张极其高清的静态图，避免出现黑块。

只要替换好路径，您的页面就会立刻呈现出极具压迫感和呼吸感的“苹果级”预告片效果！