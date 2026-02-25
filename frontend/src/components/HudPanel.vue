<template>
  <div class="hud-container">
    <!-- Header -->
    <div class="hud-header">
      <h1 class="hud-title">
        ALPHA EARTH <span class="accent">FOUNDATION</span>
      </h1>
      <div class="hud-subtitle">
        {{ currentLocation?.name || '加载中...' }} /// 
        <span :class="statusClass">{{ statusText }}</span>
      </div>
    </div>

    <!-- Control Panel -->
    <div class="hud-panel">
      <div class="panel-section">
        <h3 class="section-title">🎯 监测场景</h3>
        <div class="mode-selector">
          <button
            v-for="(name, key) in modes"
            :key="key"
            :class="['mode-btn', { active: selectedMode === key }]"
            @click="$emit('mode-change', key)"
          >
            {{ getModeIcon(key) }} {{ getModeName(name) }}
          </button>
        </div>
      </div>

      <div class="panel-section">
        <h3 class="section-title">📍 核心监测区</h3>
        <select
          class="location-select"
          :value="selectedLocation"
          @change="$emit('location-change', $event.target.value)"
        >
          <option v-for="(loc, key) in locations" :key="key" :value="key">
            {{ loc.name }}
          </option>
        </select>
      </div>

      <div class="panel-section" v-if="currentModeInfo">
        <h3 class="section-title">{{ currentModeInfo.title }}</h3>
        <p class="mode-description">{{ currentModeInfo.desc }}</p>
        <div class="mode-formula">
          <span class="formula-label">CORE OPERATOR</span>
          <code>{{ currentModeInfo.formula }}</code>
        </div>
      </div>

      <div class="panel-section" v-if="mission">
        <h3 class="section-title">🎬 当前任务</h3>
        <div class="mission-title">{{ mission.title }}</div>
        <div class="mission-meta">
          <span class="tag">{{ mission.name }}</span>
          <span class="tag secondary">默认模式：{{ getModeName(modes?.[mission.api_mode] || mission.api_mode) }}</span>
        </div>
        <p class="mode-description">{{ mission.narrative }}</p>
        <div class="mode-formula">
          <span class="formula-label">MISSION OPERATOR</span>
          <code>{{ mission.formula }}</code>
        </div>
      </div>

      <div class="panel-section" v-if="!isCached && !loading">
        <button class="cache-btn" @click="$emit('cache-export')" :disabled="exporting">
          <span v-if="!exporting">📥 为下次演示缓存结果</span>
          <span v-else>⏳ 正在提交任务...</span>
        </button>
      </div>

      <div class="panel-section stats" v-if="stats">
        <div class="stat-item">
          <span class="stat-label">加载耗时</span>
          <span class="stat-value">{{ stats.loadTime }}ms</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">缓存状态</span>
          <span class="stat-value">{{ isCached ? '✅ 命中' : '⚡ 实时' }}</span>
        </div>
      </div>

      <div class="panel-section stats" v-if="zonalStats">
        <div class="stat-item">
          <span class="stat-label">分析面积</span>
          <span class="stat-value">{{ formatKm2(zonalStats.total_area_km2) }} km²</span>
        </div>
        <div class="stat-item" v-if="zonalStats.anomaly_area_km2 !== null && zonalStats.anomaly_area_km2 !== undefined">
          <span class="stat-label">异常面积</span>
          <span class="stat-value">{{ formatKm2(zonalStats.anomaly_area_km2) }} km²</span>
        </div>
        <div class="stat-item" v-if="zonalStats.anomaly_pct !== null && zonalStats.anomaly_pct !== undefined">
          <span class="stat-label">异常占比</span>
          <span class="stat-value">{{ formatPct(zonalStats.anomaly_pct) }}%</span>
        </div>
      </div>

      <div class="panel-section" v-if="report">
        <h3 class="section-title">📝 智能简报</h3>
        <pre class="report-box">{{ report }}</pre>
      </div>

      <!-- Debug Panel -->
      <div class="panel-section debug-panel">
        <h3 class="section-title">🛠 调试面板</h3>

        <label class="debug-toggle">
          <input
            type="checkbox"
            :checked="debugEnabled"
            @change="$emit('debug-toggle', $event.target.checked)"
          />
          <span>启用 Debug（定位黑屏/瓦片失败）</span>
        </label>

        <div v-if="debugEnabled" class="debug-body">
          <div class="debug-row">
            <span class="debug-k">API</span>
            <code class="debug-v">{{ debugInfo?.apiBase }}</code>
          </div>

          <div class="debug-row" v-if="debugInfo?.tileUrl">
            <span class="debug-k">tile_url</span>
            <code class="debug-v debug-url">{{ debugInfo.tileUrl }}</code>
          </div>

          <div class="debug-row" v-if="debugInfo?.tileLoadRemaining !== null && debugInfo?.tileLoadRemaining !== undefined">
            <span class="debug-k">Tile 队列</span>
            <span class="debug-v">{{ debugInfo.tileLoadRemaining }}</span>
          </div>

          <div class="debug-actions">
            <button
              class="debug-btn"
              @click="$emit('debug-test-tile')"
              :disabled="debugInfo?.tileTesting || !debugInfo?.tileUrl"
              title="根据相机中心点计算 z/x/y 并请求单张瓦片"
            >
              <span v-if="!debugInfo?.tileTesting">测试当前视角瓦片</span>
              <span v-else>测试中...</span>
            </button>

            <button class="debug-btn secondary" @click="$emit('debug-clear-errors')">
              清空
            </button>
          </div>

          <div v-if="debugInfo?.tileTest" class="debug-box">
            <div class="debug-box-title">Tile Test</div>
            <div class="debug-box-line">
              <span class="debug-k">URL</span>
              <code class="debug-v debug-url">{{ debugInfo.tileTest.url }}</code>
            </div>
            <div class="debug-box-line">
              <span class="debug-k">z/x/y</span>
              <span class="debug-v">{{ debugInfo.tileTest.z }}/{{ debugInfo.tileTest.x }}/{{ debugInfo.tileTest.y }}</span>
            </div>
            <div class="debug-box-line" v-if="debugInfo.tileTest.status !== null">
              <span class="debug-k">Status</span>
              <span class="debug-v">{{ debugInfo.tileTest.status }}</span>
            </div>
            <div class="debug-box-line" v-if="debugInfo.tileTest.contentType">
              <span class="debug-k">Type</span>
              <span class="debug-v">{{ debugInfo.tileTest.contentType }}</span>
            </div>
            <div class="debug-box-line" v-if="debugInfo.tileTest.bytes !== null">
              <span class="debug-k">Bytes</span>
              <span class="debug-v">{{ debugInfo.tileTest.bytes }}</span>
            </div>
            <div class="debug-box-line" v-if="debugInfo.tileTest.ms !== null">
              <span class="debug-k">Time</span>
              <span class="debug-v">{{ debugInfo.tileTest.ms }}ms</span>
            </div>
            <div class="debug-box-line error" v-if="debugInfo.tileTest.error">
              <span class="debug-k">Error</span>
              <span class="debug-v">{{ debugInfo.tileTest.error }}</span>
            </div>
          </div>

          <div v-if="debugInfo?.lastLayerError" class="debug-box error">
            <div class="debug-box-title">Last Layer Error</div>
            <div class="debug-box-line">
              <span class="debug-k">Message</span>
              <span class="debug-v">{{ debugInfo.lastLayerError.message }}</span>
            </div>
          </div>

          <div v-if="debugInfo?.imageryErrors?.length" class="debug-box">
            <div class="debug-box-title">Cesium Imagery Errors (latest {{ debugInfo.imageryErrors.length }})</div>
            <div
              v-for="(e, idx) in debugInfo.imageryErrors"
              :key="idx"
              class="debug-error-row"
            >
              <span class="tag">{{ e.layer }}</span>
              <span class="msg">{{ e.message }}</span>
              <span class="meta" v-if="e.level !== undefined">L{{ e.level }}</span>
              <span class="meta" v-if="e.timesRetried !== undefined">retry {{ e.timesRetried }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'HudPanel',
  props: {
    locations: Object,
    modes: Object,
    selectedLocation: String,
    selectedMode: String,
    currentLocation: Object,
    isCached: Boolean,
    loading: Boolean,
    exporting: Boolean,
    stats: Object,
    mission: Object,
    zonalStats: Object,
    report: String,
    debugEnabled: Boolean,
    debugInfo: Object
  },
  emits: ['mode-change', 'location-change', 'cache-export', 'debug-toggle', 'debug-test-tile', 'debug-clear-errors'],
  
  setup(props) {
    const modeInfo = {
      dna: {
        title: '🧬 地表 DNA 解析',
        desc: 'AI 自动识别土地功能基因',
        formula: 'PCA(Vector_64d)'
      },
      change: {
        title: '⚠️ 时空风险雷达',
        desc: '锁定地表属性本质突变',
        formula: 'Euclidean_Dist(V1, V2)'
      },
      intensity: {
        title: '🏗️ 建设强度场',
        desc: '数字化全域开发强度',
        formula: 'Dim_0_Response'
      },
      eco: {
        title: '🌿 生态韧性底线',
        desc: '监测生态屏障完整性',
        formula: 'Inverse(Dim_2)'
      }
    }
    
    const currentModeInfo = computed(() => {
      return modeInfo[props.selectedMode]
    })
    
    const statusText = computed(() => {
      if (props.loading) return '计算中...'
      return props.isCached ? '极速缓存 (Asset)' : '实时计算 (Cloud)'
    })
    
    const statusClass = computed(() => {
      return props.isCached ? 'status-cached' : 'status-live'
    })
    
    function getModeIcon(key) {
      const icons = {
        dna: '🧬',
        change: '⚠️',
        intensity: '🏗️',
        eco: '🌿'
      }
      return icons[key] || '📊'
    }
    
    function getModeName(fullName) {
      return fullName.split(' ')[0]
    }

    function formatKm2(v) {
      if (v === null || v === undefined || Number.isNaN(Number(v))) return '—'
      return Number(v).toFixed(2)
    }

    function formatPct(v) {
      if (v === null || v === undefined || Number.isNaN(Number(v))) return '—'
      return Number(v).toFixed(2)
    }
    
    return {
      currentModeInfo,
      statusText,
      statusClass,
      getModeIcon,
      getModeName,
      formatKm2,
      formatPct
    }
  }
}
</script>

<style scoped>
.hud-container {
  pointer-events: none;
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
}

.hud-header {
  pointer-events: auto;
  position: absolute;
  top: 20px;
  left: 20px;
  background: rgba(16, 20, 24, 0.95);
  border-left: 5px solid #00F5FF;
  padding: 15px 25px;
  backdrop-filter: blur(10px);
  border-radius: 0 4px 4px 0;
}

.hud-title {
  color: #FFF;
  font-weight: 700;
  font-size: 24px;
  margin: 0;
}

.accent {
  color: #00F5FF;
}

.hud-subtitle {
  color: #00F5FF;
  font-size: 12px;
  margin-top: 5px;
}

.mission-title {
  font-weight: 800;
  letter-spacing: 0.5px;
  margin: 6px 0 6px;
}

.mission-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: rgba(0, 245, 255, 0.14);
  border: 1px solid rgba(0, 245, 255, 0.25);
  color: #dff;
}

.tag.secondary {
  background: rgba(255, 0, 255, 0.12);
  border-color: rgba(255, 0, 255, 0.22);
  color: #ffd7ff;
}

.report-box {
  white-space: pre-wrap;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 10px;
  max-height: 220px;
  overflow: auto;
  font-size: 12px;
  color: #eaeaea;
}

.status-cached {
  color: #00FF00;
  font-weight: bold;
}

.status-live {
  color: #FF4444;
  font-weight: bold;
}

.hud-panel {
  pointer-events: auto;
  position: absolute;
  top: 120px;
  right: 20px;
  width: 350px;
  max-height: calc(100vh - 140px);
  max-height: calc(100dvh - 140px);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  background: rgba(0, 0, 0, 0.9);
  border-top: 3px solid #FF00FF;
  padding: 20px;
  color: #EEE;
  backdrop-filter: blur(10px);
}

/* Mobile: convert to bottom drawer and keep it scrollable.
   The page-level body/html often has overflow:hidden in full-screen Cesium apps,
   so we must enable scrolling inside the HUD panel itself. */
@media screen and (max-width: 768px) {
  .hud-header {
    top: 10px;
    left: 10px;
    right: 10px;
    padding: 12px 14px;
    border-radius: 8px;
  }

  .hud-title {
    font-size: 18px;
  }

  .hud-panel {
    top: auto;
    right: 0;
    left: 0;
    bottom: 0;
    width: 100%;
    max-height: 60vh;
    border-top: none;
    border-radius: 18px 18px 0 0;
    padding: 14px;
    box-sizing: border-box;
  }

  .stats {
    flex-direction: column;
    gap: 10px;
  }
}

.panel-section {
  margin-bottom: 20px;
}

.section-title {
  color: #00F5FF;
  font-size: 14px;
  margin-bottom: 10px;
  font-weight: 600;
}

.mode-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mode-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(0, 245, 255, 0.3);
  color: #FFF;
  padding: 10px 15px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 13px;
  text-align: left;
}

.mode-btn:hover {
  background: rgba(0, 245, 255, 0.2);
  border-color: #00F5FF;
}

.mode-btn.active {
  background: rgba(0, 245, 255, 0.3);
  border-color: #00F5FF;
  border-width: 2px;
}

.location-select {
  width: 100%;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(0, 245, 255, 0.3);
  color: #FFF;
  padding: 10px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.location-select:focus {
  outline: none;
  border-color: #00F5FF;
}

.mode-description {
  color: #CCC;
  font-size: 13px;
  margin-bottom: 10px;
  line-height: 1.5;
}

.mode-formula {
  background: rgba(255, 255, 255, 0.05);
  padding: 10px;
  border-radius: 4px;
  border-left: 3px solid #FF00FF;
}

.formula-label {
  display: block;
  color: #888;
  font-size: 11px;
  margin-bottom: 5px;
}

.mode-formula code {
  color: #00FF00;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.cache-btn {
  width: 100%;
  background: linear-gradient(135deg, #00F5FF 0%, #FF00FF 100%);
  border: none;
  color: #000;
  padding: 12px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  transition: all 0.3s;
}

.cache-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 245, 255, 0.5);
}

.cache-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.stats {
  display: flex;
  gap: 15px;
  padding-top: 15px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.stat-item {
  flex: 1;
}

.stat-label {
  display: block;
  color: #888;
  font-size: 11px;
  margin-bottom: 3px;
}

.stat-value {
  display: block;
  color: #00F5FF;
  font-size: 16px;
  font-weight: 600;
}

.debug-panel {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 15px;
}

.debug-toggle {
  display: flex;
  gap: 10px;
  align-items: center;
  color: #CCC;
  font-size: 12px;
  user-select: none;
}

.debug-toggle input {
  transform: translateY(1px);
}

.debug-body {
  margin-top: 10px;
}

.debug-row {
  display: flex;
  gap: 10px;
  margin: 6px 0;
}

.debug-k {
  width: 70px;
  color: #888;
  font-size: 11px;
  flex: 0 0 auto;
}

.debug-v {
  color: #EEE;
  font-size: 11px;
  line-height: 1.4;
  word-break: break-all;
}

.debug-url {
  display: inline-block;
  max-height: 60px;
  overflow: auto;
}

.debug-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.debug-btn {
  flex: 1;
  background: rgba(0, 245, 255, 0.18);
  border: 1px solid rgba(0, 245, 255, 0.35);
  color: #00F5FF;
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.debug-btn:hover:not(:disabled) {
  background: rgba(0, 245, 255, 0.28);
}

.debug-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.debug-btn.secondary {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.18);
  color: #DDD;
}

.debug-box {
  margin-top: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  padding: 10px;
}

.debug-box.error {
  border-color: rgba(255, 68, 68, 0.35);
}

.debug-box-title {
  color: #00F5FF;
  font-size: 11px;
  margin-bottom: 6px;
  font-weight: 600;
}

.debug-box-line {
  display: flex;
  gap: 10px;
  margin: 4px 0;
}

.debug-box-line.error .debug-v {
  color: #FF8888;
}

.debug-error-row {
  display: flex;
  gap: 8px;
  align-items: baseline;
  padding: 4px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.debug-error-row:first-of-type {
  border-top: none;
}

.debug-error-row .tag {
  color: #FF00FF;
  font-size: 10px;
  flex: 0 0 auto;
}

.debug-error-row .msg {
  color: #EEE;
  font-size: 11px;
  word-break: break-word;
  flex: 1 1 auto;
}

.debug-error-row .meta {
  color: #888;
  font-size: 10px;
  flex: 0 0 auto;
}

/* 滚动条样式 */
.hud-panel::-webkit-scrollbar {
  width: 6px;
}

.hud-panel::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
}

.hud-panel::-webkit-scrollbar-thumb {
  background: rgba(0, 245, 255, 0.5);
  border-radius: 3px;
}
</style>
