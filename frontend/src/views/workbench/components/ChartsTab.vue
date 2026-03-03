<template>
  <div class="wrap" aria-label="2D Charts">
    <div class="title">2D Charts (统计图表)</div>

    <svg class="chart" viewBox="0 0 420 160" role="img" aria-label="chart">
      <polyline :points="polyline" fill="none" stroke="rgba(0, 240, 255, 0.95)" stroke-width="3" />
      <line x1="0" y1="150" x2="420" y2="150" stroke="rgba(255,255,255,0.12)" stroke-width="1" />
      <line x1="10" y1="0" x2="10" y2="160" stroke="rgba(255,255,255,0.08)" stroke-width="1" />
    </svg>

    <div class="hint">MVP chart stub — replace with real stats output.</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  series: { type: Array, default: () => [10, 14, 9, 22, 18, 27, 24] },
})

const polyline = computed(() => {
  const xs = 420
  const ys = 140
  const vals = props.series.map((n) => Number(n))
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const span = max - min || 1

  return vals
    .map((v, i) => {
      const x = (i / Math.max(1, vals.length - 1)) * (xs - 20) + 10
      const y = 150 - ((v - min) / span) * ys
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})
</script>

<style scoped>
.wrap {
  position: absolute;
  inset: 0;
  padding: 14px;
  overflow: auto;
  background: rgba(0, 0, 0, 0.65);
}

.title {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.80;
  font-weight: 900;
  margin-bottom: 10px;
}

.chart {
  width: min(860px, 100%);
  height: auto;
  border-radius: 14px;
  background: rgba(10, 15, 26, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.10);
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.55);
}

.hint {
  margin-top: 10px;
  font-size: 12px;
  opacity: 0.70;
}
</style>
