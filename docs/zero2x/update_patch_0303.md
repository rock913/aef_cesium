这是一次非常关键的语境对齐。为了符合“之江实验室”及 zero2x 的官方话语体系，我们将全面弃用发散词汇，强化 “One系列”模型矩阵、“海纳数据底座” 以及 “021科学基础模型”。

✍️ 词汇微调策略：
模型重命名：Genos → OneGenome (之江实验室基因大模型官方名称)。

数据底座定调：Act 4 明确标注为 “海纳数据底座 (Haina Data Hub)”，强调 Embedding 与联邦图谱。

核心引擎：统一称呼为 “021 科学基础模型”，它是连接宏观与微观的中枢。

专业化用词：将“宇宙漫游”等感性词汇微调为“跨尺度科研探索”；将“科学猜想”优化为“科学问题/科研意图”。

以下是为您优化后的完整代码实现：

🚀 修改点解析：
模型一致性修复 (OneGenome)：

将第三幕的标签和描述中的 Genos 全部更新为 OneGenome，确保与之江实验室“One系列”大模型矩阵（OneAstronomy, OneGenome, OnePorous）保持品牌统一。

强化“海纳数据底座” (Haina Data Hub)：

在第四幕增加了 [ HAINA DATA HUB / 海纳数据底座 ] 显性标注。

将 Embedding 描述微调为更严谨的“多源异构数据向量化”和“联邦数据图谱”，突出底座的调度和计算属性。

确立“021 科学基础模型”地位：

在 Act 1 的 Kicker 和 Act 5 的状态栏明确标注 PROJECT MODEL 021。

将第二幕的引擎描述定义为“由 021 科学基础模型驱动”，体现其作为跨尺度、多模态中枢的角色。

专业化文本修辞：

将 Omni-Bar 的提示语改为 "Initiate scientific inquiry" 和 "Describe your research intent"，更符合科学工作站的操作语境。

Act 5 的启动按钮改为 LAUNCH 021 WORKSPACE，直接将品牌与行动点挂钩。

通过这些调整，zero2x 的前端语境已经从一个“泛 AI 网站”回归到了一个极具之江特色的专业科研操作系统。
<template>
  <div class="z2x">
    <!-- 第一幕：入境 (Hero / Neural Sphere) -->
    <header id="act-1" class="hero" data-act-id="act-1">
      <div class="hero-visual-wrapper">
        <HeroVisual class="hero-bg" />
      </div>

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
            
            <div class="omnibar-kbd desktop-only" aria-hidden="true">
              <span class="kbd">⌘</span><span class="kbd">K</span>
            </div>
            
            <button class="btn omnibar-btn desktop-only" type="button" @click.stop="submit">Run</button>
            <a class="btn secondary omnibar-btn desktop-only" :href="takeMeToEarthHref" @click.stop.prevent="goAct2">进入视窗</a>
          </div>
          
          <div v-if="result" class="omnibar-result">
            <div class="result-title">021_BASE_MODEL_PREVIEW</div>
            <pre class="result-pre">{{ result }}</pre>
          </div>
        </div>
        
        <div class="scroll-hint desktop-only">
          <div class="mouse-icon"></div>
          <span>Scroll to explore hierarchy</span>
        </div>
      </div>
    </header>

    <main class="acts">
      <!-- 第二幕：宏观孪生 (021 Model + OneAstronomy) -->
      <section id="act-2" class="act-fullscreen group" data-act-id="act-2" @click="goAct2">
        <video v-if="act2CinematicVideoOk" class="cinematic-video" autoplay loop muted playsinline preload="metadata" @error="act2CinematicVideoOk = false">
          <source :src="act2CinematicMp4Src" type="video/mp4" />
        </video>
        <div class="cinematic-overlay act2"></div>
        <div class="cinematic-content">
          <div class="cine-container act2-layout">
            <div class="cine-tags">
              <span class="cine-tag cyan">021 Foundation</span>
              <span class="cine-tag purple">OneAstronomy</span>
            </div>
            <h2 class="cine-title">从深空暗场，<br />到<span class="cine-gradient-text-2">轨道晨昏线</span>。</h2>
            <p class="cine-desc">宏观引擎：021 科学基础模型实现了天基算力与地学细节的无缝统一。在同一个平滑缩放的数字孪生坐标系中，审视行星级的多维演变。</p>
          </div>
        </div>
      </section>

      <!-- 第三幕：微观深潜 (OneGenome + OnePorous) -->
      <section id="act-3" class="act-fullscreen group" data-act-id="act-3" @click="goWorkbenchLaunchpad">
        <video v-if="act3CinematicVideoOk" class="cinematic-video" autoplay loop muted playsinline preload="metadata" @error="act3CinematicVideoOk = false">
          <source :src="act3CinematicMp4Src" type="video/mp4" />
        </video>
        <div class="cinematic-overlay act3"></div>
        <div class="cinematic-content">
          <div class="cine-container act3-layout">
            <div class="cine-tags">
              <span class="cine-tag purple">OneGenome</span>
              <span class="cine-tag orange">OnePorous</span>
            </div>
            <h2 class="cine-title">直视物质的<br /><span class="cine-gradient-text-3">相变临界点</span>。</h2>
            <p class="cine-desc">微观引擎：见证 OneGenome 基因序列与 OnePorous 材料晶格的耦合。我们在分子尺度的暗场下，重构科研范式并完成跨模态科学发现。</p>
          </div>
        </div>
      </section>

      <!-- 第四幕：数据星海 (海纳数据底座 - Haina Data Hub) -->
      <section id="act-4" class="act-fullscreen group" data-act-id="act-4">
        <video v-if="act4CinematicVideoOk" class="cinematic-video" autoplay loop muted playsinline preload="metadata" @error="act4CinematicVideoOk = false">
          <source :src="act4CinematicMp4Src" type="video/mp4" />
        </video>
        <div class="cinematic-overlay act4"></div>
        <div class="cinematic-content">
          <div class="cine-container hud-layout">
            <div class="hud-header">
              <div class="hud-kicker"><span class="hud-bracket">[</span> HAINA DATA HUB / 海纳数据底座 <span class="hud-bracket">]</span></div>
              <h2 class="hud-title">Embedding 联邦数据图谱</h2>
              <p class="hud-desc">数据范式跃迁：海量多源异构数据经由 021 模型向量化，在海纳底座中坍缩为语义星云。跨域关联在此实现自主推演与精准调度。</p>
            </div>
            <div class="hud-footer">
              <div class="hud-status">
                <span class="hud-dot"></span>
                <span class="hud-status-text">Federated Computing Active</span>
              </div>
              <div class="hud-metrics">
                <div class="metric"><span>VECTORS</span>102,400</div>
                <div class="metric"><span>THROUGHPUT</span>12 GB/s</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 第五幕：极客工坊 (021 Model Workflow Launchpad) -->
      <section id="act-5" class="act-fullscreen workbench-hud" data-act-id="act-5">
        <div class="workbench-bg-viewport">
          <video v-if="act5CinematicVideoOk" class="cinematic-video brightness-[0.75] contrast-[1.15]" autoplay loop muted playsinline preload="metadata" @error="act5CinematicVideoOk = false">
            <source :src="act2CinematicMp4Src" type="video/mp4" />
          </video>
          <div class="ar-grid-overlay"></div>
        </div>

        <div class="hud-layer">
          <div class="hud-top-bar">
            <div class="hud-id-box">
              <span class="label">MODEL_STATUS:</span>
              <span class="value">021_BASE_STABLE</span>
            </div>
            <div class="hud-status-box">
              <span class="status-dot-blink"></span>
              <span class="desktop-only">PIPELINE_READY</span>
            </div>
          </div>

          <div class="hud-content-area">
            <div class="hud-pane-left">
              <div class="pane-tag">AGENT_EXECUTION_STREAM</div>
              <div class="pane-content chat-bubble">
                <div class="msg-ai">
                  <span class="author">021_BRAIN:</span>
                  海纳底座已就绪。正在解析多维科研意图，启动 021 基础模型进行跨尺度推理与知识合成。
                </div>
              </div>
            </div>

            <div class="hud-pane-right desktop-only">
              <div class="pane-tag">RESEARCH_CONTEXT.YAML</div>
              <div class="pane-content code-block">
                <pre>platform: zero2x_v0.21
core_model: 021_foundation
data_hub: haina_federated
status: ready_for_dispatch</pre>
              </div>
            </div>
          </div>

          <div class="hud-bottom-cta">
            <div class="cta-inner">
              <p class="cta-tip desktop-only">ASCEND TO THE AI-NATIVE WORKBENCH</p>
              <div class="cta-buttons">
                <a :href="workbenchLaunchpadHref" class="btn-main-glow" @click.prevent="goWorkbenchLaunchpad">
                  LAUNCH 021 WORKSPACE
                </a>
              </div>
            </div>
          </div>
        </div>

        <div class="hud-center-aim-container desktop-only">
          <svg class="hud-center-aim" width="44" height="44" viewBox="0 0 40 40" fill="none" stroke="rgba(0,240,255,0.4)" stroke-width="1">
            <circle cx="20" cy="20" r="18" /><path d="M20 5V10 M20 30V35 M5 20H10 M30 20H35" />
          </svg>
        </div>

        <div class="compute-status-hud desktop-only" aria-hidden="true">
          <span>COMPUTE_HUB:</span><span class="value">NANHU CLUSTER</span>
          <span class="divider">|</span>
          <span>SYSTEM_VERSION:</span><span class="value">0.21_ALPHA</span>
        </div>
      </section>
    </main>

    <footer class="foot-minimal">
      <div class="foot-minimal-inner">
        <div class="foot-left">Zero2x | AI-Native 渐进式科研工作台</div>
        <div class="foot-right">
          <a class="foot-link" href="/demo">Validation</a>
          <span class="sep">·</span>
          <span>© 2026 ZJ Lab</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import HeroVisual from './components/HeroVisual.vue'
import { buildAct2ChoreoHref } from './utils/choreo.js'
import { navigateWithFade } from './utils/navFade.js'
import { buildStubPlan } from './utils/omnibarCommands.js'

const inputEl = ref(null)
const query = ref('')
const result = ref('')
const activeAct = ref('act-1')

const placeholders = [
  '请输入科研意图... (如：分析特定海域叶绿素浓度)',
  '调用 OneGenome 引擎分析特定序列',
  '使用 021 模型进行跨尺度演化模拟'
]
const idx = ref(0)
const placeholder = computed(() => placeholders[idx.value % placeholders.length])
const takeMeToEarthHref = buildAct2ChoreoHref('poyang')
const workbenchLaunchpadHref = '/workbench?context=021_research'

const act2CinematicVideoOk = ref(true)
const act3CinematicVideoOk = ref(true)
const act4CinematicVideoOk = ref(true)
const act5CinematicVideoOk = ref(true)

function withBase(p) {
  const base = String(import.meta?.env?.BASE_URL || '/').endsWith('/') ? import.meta?.env?.BASE_URL || '/' : `${import.meta?.env?.BASE_URL || '/'}/`
  return `${base}${String(p).replace(/^\//, '')}`
}

const act2CinematicMp4Src = computed(() => withBase('/zero2x/ui/act2_earth.mp4'))
const act3CinematicMp4Src = computed(() => withBase('/zero2x/ui/act3_dna.mp4'))
const act4CinematicMp4Src = computed(() => withBase('/zero2x/ui/act4_galaxy.mp4'))

function focusOmni() { inputEl.value?.focus() }
function submit() {
  if (!query.value.trim()) return
  result.value = buildStubPlan(query.value)
  const target = document.getElementById('act-5')
  if(target) target.scrollIntoView({ behavior: 'smooth' })
}

function goAct2() { navigateWithFade(takeMeToEarthHref) }
function goWorkbenchLaunchpad() { navigateWithFade(workbenchLaunchpadHref) }

onMounted(() => {
  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); focusOmni() }
  })
  setInterval(() => { idx.value++ }, 3000)
  
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => { if(e.isIntersecting) activeAct.value = e.target.id })
  }, { threshold: 0.5 })
  document.querySelectorAll('[data-act-id]').forEach(el => obs.observe(el))
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700;900&family=Fira+Code:wght@400;500&display=swap');

:global(html) { scroll-snap-type: y proximity; scroll-behavior: smooth; }
.z2x { background: #030409; color: #eef2ff; font-family: 'Inter', sans-serif; overflow-x: hidden; }

.desktop-only { display: flex; }
.mobile-only { display: none; }

/* ACT 1 */
.hero { position: relative; height: 100vh; width: 100vw; display: grid; place-items: center; scroll-snap-align: start; overflow: hidden; }
.hero-visual-wrapper { position: absolute; inset: 0; display: grid; place-items: center; z-index: 0; }
.hero-bg { width: 100%; height: 100%; }
.hero-center { position: relative; z-index: 10; width: min(1040px, 90vw); display: flex; flex-direction: column; align-items: center; transform: translateY(-2vh); }

.brand { text-align: center; margin-bottom: 24px; width: 100%; }
.brand-kicker { font-size: 10px; letter-spacing: 0.4em; opacity: 0.5; font-weight: 800; margin-bottom: 8px; }
.brand-title { font-size: clamp(48px, 9vw, 112px); font-weight: 900; letter-spacing: -0.04em; background: linear-gradient(90deg, #00f0ff, #9d4edd); -webkit-background-clip: text; background-clip: text; color: transparent; text-transform: lowercase; }
.brand-sub { margin-top: 12px; font-size: clamp(13px, 1.5vw, 15px); font-weight: 300; opacity: 0.85; }

.omnibar { background: rgba(10,15,26,0.7); border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 16px; backdrop-filter: blur(24px); width: 100%; max-width: 680px; margin-top: 20px; }
.omnibar-shell { display: flex; align-items: center; gap: 12px; background: rgba(5,8,16,0.8); border: 1px solid rgba(255,255,255,0.05); border-radius: 14px; padding: 0 16px; }
.omnibar-input { flex: 1; background: transparent; border: none; color: #fff; padding: 14px 0; outline: none; font-size: 15px; }
.omnibar-kbd-hint { background: rgba(255,255,255,0.1); border-radius: 4px; padding: 2px 6px; font-size: 10px; }

.scroll-hint { margin-top: 4vh; display: flex; flex-direction: column; align-items: center; gap: 12px; opacity: 0.3; }
.mouse-icon { width: 18px; height: 28px; border: 1px solid #fff; border-radius: 10px; position: relative; }
.mouse-icon::after { content: ''; position: absolute; top: 6px; left: 50%; width: 2px; height: 5px; background: #fff; transform: translateX(-50%); animation: scroll-dot 2s infinite; }
@keyframes scroll-dot { 0%, 100% { transform: translate(-50%, 0); opacity: 1; } 50% { transform: translate(-50%, 4px); opacity: 0; } }

/* ACT COMMON */
.act-fullscreen { position: relative; width: 100vw; height: 100vh; overflow: hidden; scroll-snap-align: start; scroll-snap-stop: always; display: flex; }
.cinematic-video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; }
.cinematic-overlay { position: absolute; inset: 0; z-index: 10; pointer-events: none; }
.cinematic-overlay.act2 { background: linear-gradient(to top right, rgba(3,4,9,0.95), transparent 60%); }
.cinematic-overlay.act3 { background: radial-gradient(circle at center, transparent, rgba(3,4,9,0.85)); }
.cinematic-overlay.act4 { background: radial-gradient(circle at center, transparent 30%, rgba(3,4,9,0.9) 100%); }

.cine-container { width: 100%; max-width: 1400px; margin: 0 auto; padding: 10vh 48px; height: 100%; display: flex; flex-direction: column; }
.act2-layout { justify-content: flex-end; align-items: flex-start; text-align: left; }
.act3-layout { justify-content: flex-end; align-items: flex-end; text-align: right; }

.cine-tags { display: flex; gap: 12px; margin-bottom: 20px; }
.cine-tag { font-size: 10px; font-weight: 900; padding: 6px 14px; border-radius: 99px; text-transform: uppercase; border: 1px solid rgba(255,255,255,0.1); }
.cine-tag.cyan { color: #00f0ff; background: rgba(0,240,255,0.1); }
.cine-tag.purple { color: #9d4edd; background: rgba(157,78,221,0.1); }
.cine-tag.orange { color: #ff6b00; background: rgba(255,107,0,0.1); }

.cine-title { font-size: clamp(34px, 5vw, 68px); font-weight: 900; line-height: 1.1; margin-bottom: 20px; white-space: nowrap; text-shadow: 0 4px 20px rgba(0,0,0,0.8); }
.cine-desc { font-size: clamp(14px, 1.2vw, 17px); font-weight: 300; max-width: 50ch; color: rgba(255,255,255,0.75); line-height: 1.6; }
.cine-gradient-text-2 { background: linear-gradient(to right, #00f0ff, #fff); -webkit-background-clip: text; background-clip: text; color: transparent; }
.cine-gradient-text-3 { background: linear-gradient(to left, #ff6b00, #9d4edd); -webkit-background-clip: text; background-clip: text; color: transparent; }

/* ACT 4 */
.hud-layout { justify-content: space-between; padding: 8vh 60px; }
.hud-kicker { font-size: 11px; letter-spacing: 0.3em; color: rgba(255,255,255,0.4); margin-bottom: 12px; font-weight: 800; }
.hud-bracket { color: #00f0ff; opacity: 0.6; }
.hud-title { font-size: clamp(28px, 4vw, 56px); font-weight: 900; margin-bottom: 16px; white-space: nowrap; }
.hud-desc { font-size: 14px; max-width: 560px; line-height: 1.6; border-left: 2px solid #00f0ff; padding-left: 20px; color: rgba(255,255,255,0.8); }
.hud-footer { display: flex; justify-content: space-between; align-items: flex-end; width: 100%; }
.hud-status { display: flex; align-items: center; gap: 12px; background: rgba(0,0,0,0.5); padding: 8px 16px; border-radius: 99px; border: 1px solid rgba(255,255,255,0.1); }
.hud-dot { width: 8px; height: 8px; background: #00f0ff; border-radius: 50%; box-shadow: 0 0 10px #00f0ff; animation: pulse 2s infinite; }
.hud-status-text { font-size: 10px; font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; }
.hud-metrics { display: flex; gap: 40px; }
.metric { display: flex; flex-direction: column; gap: 4px; font-size: clamp(20px, 2.2vw, 28px); font-weight: 300; }
.metric span { font-size: 9px; font-weight: 800; color: rgba(255,255,255,0.4); letter-spacing: 0.2em; }

/* ACT 5 */
.workbench-hud { background: #000; position: relative; }
.workbench-bg-viewport { position: absolute; inset: 0; z-index: 1; }
.ar-grid-overlay { position: absolute; inset: 0; z-index: 2; background-image: radial-gradient(rgba(0, 240, 255, 0.1) 1px, transparent 0); background-size: 40px 40px; opacity: 0.3; }
.hud-layer { position: relative; z-index: 10; width: 100%; height: 100%; display: flex; flex-direction: column; padding: 40px; }
.hud-top-bar { display: flex; justify-content: space-between; align-items: flex-start; font-family: 'Fira Code', monospace; font-size: 10px; }
.hud-id-box { color: #00f0ff; background: rgba(0,240,255,0.05); padding: 6px 12px; border: 1px solid rgba(0,240,244,0.2); }
.hud-status-box { color: #fff; opacity: 0.7; display: flex; align-items: center; gap: 8px; }
.status-dot-blink { width: 6px; height: 6px; border-radius: 50%; background: #00f0ff; animation: pulse 1.5s infinite; display: inline-block; }

.hud-content-area { flex: 1; position: relative; width: 100%; }
.hud-pane-left, .hud-pane-right { position: absolute; top: 12vh; width: min(340px, 32vw); }
.hud-pane-left { left: 0; }
.hud-pane-right { right: 0; }
.pane-tag { font-family: 'Fira Code', monospace; font-size: 9px; letter-spacing: 2px; color: rgba(0,240,255,0.6); margin-bottom: 12px; border-bottom: 1px solid rgba(0,240,255,0.2); width: fit-content; }
.pane-content { background: rgba(255,255,255,0.03); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.05); padding: 18px; border-radius: 4px; }
.chat-bubble { font-size: 13px; line-height: 1.6; }
.chat-bubble .author { display: block; font-weight: 900; color: #00f0ff; margin-bottom: 6px; font-size: 9px; }
.code-block { font-family: 'Fira Code', monospace; font-size: 12px; color: #a5b4fc; line-height: 1.6; }

.hud-bottom-cta { margin-top: auto; align-self: center; text-align: center; padding-bottom: 110px; z-index: 20; }
.cta-tip { font-size: 10px; color: rgba(255,255,255,0.4); margin-bottom: 15px; letter-spacing: 2px; font-weight: 900; }
.btn-main-glow { background: #00f0ff; color: #000; padding: 18px 48px; border-radius: 4px; font-weight: 900; font-size: 15px; box-shadow: 0 0 30px rgba(0,240,255,0.4); text-decoration: none; transition: 0.3s; letter-spacing: 1px; display: inline-block; }
.btn-main-glow:hover { transform: scale(1.05); box-shadow: 0 0 50px rgba(0,240,255,0.7); }

.hud-center-aim-container { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); pointer-events: none; opacity: 0.5; }
.compute-status-hud { position: absolute; bottom: 15px; width: 100%; text-align: center; font-family: 'Fira Code', monospace; font-size: 8px; letter-spacing: 2px; color: rgba(255,255,255,0.2); pointer-events: none; }
.compute-status-hud .value { color: #00f0ff; }

/* FOOTER */
.foot-minimal { position: fixed; bottom: 30px; left: 0; width: 100%; z-index: 100; pointer-events: none; }
.foot-minimal-inner { width: min(1400px, 90vw); margin: 0 auto; display: flex; justify-content: space-between; font-size: 9px; opacity: 0.3; letter-spacing: 1px; text-transform: uppercase; font-weight: 800; }
.foot-link { pointer-events: auto; color: inherit; text-decoration: none; }
.sep { margin: 0 8px; }

/* MOBILE */
@media (max-width: 768px) {
  .mobile-only { display: block; }
  .desktop-only { display: none !important; }
  .hero-visual-wrapper { transform: scale(0.55); transform-origin: center center; }
  .brand-title { font-size: 58px; }
  .omnibar { border-radius: 16px; padding: 12px; margin-top: 10px; }
  .cine-container { padding: 12vh 24px; }
  .cine-title { white-space: normal; word-break: keep-all; font-size: 34px; line-height: 1.25; }
  .hud-layout { padding: 10vh 24px; }
  .hud-metrics { flex-direction: row; gap: 20px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 20px; width: 100%; }
  .hud-pane-left { position: relative; top: 0; left: 0; width: 100%; }
  .hud-pane-left .pane-content { background: rgba(0,0,0,0.5); border: 1px solid rgba(0,240,255,0.15); }
  .hud-bottom-cta { padding-bottom: 80px; }
  .btn-main-glow { width: 100%; text-align: center; padding: 14px 0; font-size: 13px; }
}

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>