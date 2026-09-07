<template>
  <div class="evidence-board">
    <!-- 宏观大盘 -->
    <div v-if="currentDive === 'overview'" class="overview">
      <div class="big-number">30.8<span class="unit">万</span></div>
      <div class="big-label">处古建筑 · 天地一体监测</div>
      <div class="dive-hint">▼ 选择下潜靶点，一镜到底</div>
    </div>

    <!-- 靶向导航 -->
    <div class="target-navigator">
      <button :class="{ active: currentDive === 'shaoxing' }" @click="$emit('dive', 'shaoxing')">📍 绍兴 · 沉降</button>
      <button :class="{ active: currentDive === 'dongyang' }" @click="$emit('dive', 'dongyang')">📍 东阳 · 风灾</button>
      <button :class="{ active: currentDive === 'pingyao' }" @click="$emit('dive', 'pingyao')">📍 平遥 · 发现</button>
    </div>

    <!-- 微观证据区 -->
    <transition name="slide-fade" mode="out-in">
      <!-- 第一幕：绍兴（YOLO 动态扫描） -->
      <div v-if="currentDive === 'shaoxing'" key="sx" class="media-card">
        <h3 class="glitch-text">微观印证：{{ buildingName }}</h3>
        <div class="ai-scan-wrapper">
          <img :src="assetUrl('072500002AAaa.jpg')" class="base-image" alt="病害原图" />
          <svg viewBox="0 0 3456 2304" class="overlay-svg" preserveAspectRatio="xMidYMid meet">
            <polygon
              v-for="(poly, i) in defectPolygons"
              :key="i"
              :points="polyPoints(poly)"
              class="animated-box"
              :class="'delay-' + i"
            />
          </svg>
          <div class="scan-line"></div>
        </div>
        <p class="tag-red">⚠️ YOLO 检出：木构件开裂 · 危害等级 Ⅱ</p>
        <p class="one-liner">天上 InSAR 检出不均匀沉降 | 地下 AI 检出开裂 Ⅱ 级 → 因果闭环，优先核查</p>
      </div>

      <!-- 第二幕：东阳（CFD 视频 + FEA） -->
      <div v-else-if="currentDive === 'dongyang'" key="dy" class="media-card">
        <h3 class="glitch-text">风致响应：卢宅建筑群</h3>
        <video
          :src="assetUrl('微信视频2026-08-21_153842_980.mp4')"
          class="evidence-media"
          autoplay
          loop
          muted
          playsinline
        ></video>
        <img :src="assetUrl('FEA云图_薄弱点标注.png')" class="evidence-img" alt="FEA 薄弱点标注" />
        <p class="tag-orange">⚠️ FEA 预警：高危 · 屋檐角（分离涡）</p>
        <p class="one-liner">提前 48 小时预警 | 3000+ 工况库毫秒查表 | 锁定屋檐薄弱点</p>
      </div>

      <!-- 第三幕：平遥（AEF 语义） -->
      <div v-else-if="currentDive === 'pingyao'" key="py" class="media-card">
        <h3 class="glitch-text">跨省零微调发现</h3>
        <div class="aef-semantic-box">
          <div class="aef-heat"></div>
          <div class="placeholder-label">AEF 64 维语义张量激活图</div>
        </div>
        <p class="tag-blue">🌐 候选古建聚落检出</p>
        <p class="one-liner">浙江样本训练，山西零微调发现。模型泛化，全国推广</p>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentDive: { type: String, default: 'overview' },
  building: { type: Object, default: null },
})
defineEmits(['dive'])

const buildingName = computed(() => props.building?.name || '恒济台门')
const defectPolygons = computed(() => {
  const d = props.building?.layers?.L4_defect?.surveys?.[0]?.defects?.[0]
  return d?.polygons || [
    [[1890, 1756], [3448, 629], [3448, 922], [2025, 1921]],
    [[0, 79], [2353, 882], [2246, 986], [0, 251]],
  ]
})

function assetUrl(name) {
  return `/api/heritage/assets/${encodeURIComponent(name)}`
}
function polyPoints(poly) {
  if (!Array.isArray(poly)) return ''
  return poly.map((p) => `${p[0]},${p[1]}`).join(' ')
}
</script>

<style scoped>
.evidence-board {
  background: rgba(10, 15, 25, 0.92);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 14px;
  color: #d6e4f0;
  font-family: 'ui-monospace', 'SFMono-Regular', 'Menlo', monospace;
}
.overview { text-align: center; padding: 10px 0 6px; }
.big-number { font-size: 44px; font-weight: 800; color: #F0C468; line-height: 1; text-shadow: 0 0 22px rgba(240, 196, 104, 0.55); }
.big-number .unit { font-size: 18px; font-weight: 600; margin-left: 2px; }
.big-label { font-size: 13px; color: #c3d5e4; margin-top: 6px; letter-spacing: 1px; }
.dive-hint { font-size: 11px; color: #5fb3cc; margin-top: 8px; }
.target-navigator { display: flex; gap: 8px; margin: 12px 0; }
.target-navigator button {
  flex: 1; padding: 8px 4px; font-size: 12px; font-weight: 600;
  color: #8aa4b8; background: rgba(0, 245, 255, 0.05);
  border: 1px solid rgba(0, 245, 255, 0.18); border-radius: 8px; cursor: pointer;
  transition: all 0.2s;
}
.target-navigator button.active { color: #06121f; background: #00F5FF; border-color: #00F5FF; box-shadow: 0 0 14px rgba(0, 245, 255, 0.5); }
.media-card { display: flex; flex-direction: column; gap: 8px; }
.glitch-text { margin: 0; font-size: 14px; font-weight: 700; color: #e8f4ff; }
.ai-scan-wrapper { position: relative; border-radius: 6px; overflow: hidden; background: #000; }
.base-image { width: 100%; display: block; }
.overlay-svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.animated-box {
  fill: rgba(173, 255, 47, 0.12);
  stroke: #ADFF2F;
  stroke-width: 8;
  stroke-dasharray: 4200;
  stroke-dashoffset: 4200;
  animation: drawBox 1.6s ease-out forwards;
  filter: drop-shadow(0 0 5px rgba(173, 255, 47, 0.8));
}
.delay-1 { animation-delay: 0.55s; }
@keyframes drawBox { to { stroke-dashoffset: 0; } }
.scan-line {
  position: absolute; left: 0; width: 100%; height: 4px;
  background: rgba(173, 255, 47, 0.85); box-shadow: 0 0 16px #ADFF2F;
  animation: scan 2.6s infinite linear;
}
@keyframes scan {
  0% { top: 0; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { top: 100%; opacity: 0; }
}
.evidence-media { width: 100%; border-radius: 6px; border: 1px solid rgba(0, 245, 255, 0.2); }
.evidence-img { width: 100%; border-radius: 6px; border: 1px solid rgba(255, 120, 70, 0.3); }
.tag-red, .tag-orange, .tag-blue { font-size: 12px; font-weight: 700; margin: 0; }
.tag-red { color: #ff5a5a; }
.tag-orange { color: #ffb84d; }
.tag-blue { color: #5fb3cc; }
.one-liner { font-size: 11px; color: #8aa4b8; margin: 0; line-height: 1.5; }
.aef-semantic-box { position: relative; height: 150px; border-radius: 6px; overflow: hidden; border: 1px solid rgba(0, 245, 255, 0.2); }
.aef-heat {
  position: absolute; inset: 0;
  background:
    radial-gradient(circle at 30% 40%, rgba(240, 196, 104, 0.85), transparent 40%),
    radial-gradient(circle at 65% 60%, rgba(200, 154, 60, 0.7), transparent 45%),
    radial-gradient(circle at 50% 30%, rgba(58, 52, 22, 0.9), transparent 60%),
    #0b1626;
  animation: heatPulse 3s ease-in-out infinite;
}
@keyframes heatPulse { 50% { filter: brightness(1.35); } }
.placeholder-label {
  position: absolute; left: 0; right: 0; bottom: 8px; text-align: center;
  font-size: 11px; color: #F0C468; text-shadow: 0 0 8px rgba(240, 196, 104, 0.7);
}
.slide-fade-enter-active, .slide-fade-leave-active { transition: all 0.35s ease; }
.slide-fade-enter-from { opacity: 0; transform: translateX(18px); }
.slide-fade-leave-to { opacity: 0; transform: translateX(-18px); }
</style>
