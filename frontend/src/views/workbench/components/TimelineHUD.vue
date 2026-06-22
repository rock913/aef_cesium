<template>
  <div class="timeline" aria-label="Timeline HUD">
    <button class="icon" type="button" :aria-pressed="isPlaying" :disabled="isLoading" @click="$emit('toggle-play')">
      <span v-if="isLoading" aria-hidden="true">⌛</span>
      <span v-else-if="!isPlaying" aria-hidden="true">▶</span>
      <span v-else aria-hidden="true">⏸</span>
      <span class="sr">{{ isLoading ? 'Loading' : isPlaying ? 'Pause' : 'Play' }}</span>
    </button>

    <div class="k">SPACE‑TIME SLIDER</div>

    <div class="bar" aria-label="Timeline">
      <div class="fill" :style="{ width: `${progress}%` }" aria-hidden="true" />
      <input
        class="range"
        type="range"
        min="0"
        max="100"
        step="1"
        :value="progress"
        @input="$emit('seek', Number($event.target.value))"
        aria-label="Time Progress"
      />
      <div class="dot" :style="{ left: `${progress}%` }" aria-hidden="true" />
    </div>

    <div class="t" aria-label="Current Time">{{ currentLabel }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  minYear: { type: Number, default: 2017 },
  maxYear: { type: Number, default: 2024 },
  progress: { type: Number, default: 0 },
  isPlaying: { type: Boolean, default: false },
  isLoading: { type: Boolean, default: false },
})

defineEmits(['toggle-play', 'seek'])

const currentLabel = computed(() => {
  const a = Number(props.minYear)
  const b = Number(props.maxYear)
  const min = Number.isFinite(a) ? a : 2017
  const max = Number.isFinite(b) ? b : min + 7
  const p = Number(props.progress)
  const clamped = Number.isFinite(p) ? Math.max(0, Math.min(100, p)) : 0
  const year = Math.round(min + ((max - min) * clamped) / 100)
  return String(year)
})
</script>

<style scoped>
.timeline {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(10, 15, 26, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.10);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.55);
}

.sr {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.icon {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: rgba(0, 240, 255, 0.95);
  cursor: pointer;
  user-select: none;
}

.k {
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  opacity: 0.78;
  font-weight: 900;
  white-space: nowrap;
}

.bar {
  position: relative;
  flex: 1;
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  background: linear-gradient(90deg, rgba(0, 240, 255, 0.95), rgba(157, 78, 221, 0.90));
  opacity: 0.75;
}

.range {
  position: absolute;
  inset: 0;
  width: 100%;
  opacity: 0;
  cursor: pointer;
}

.dot {
  position: absolute;
  top: 50%;
  left: 30%;
  transform: translate(-50%, -50%);
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(0, 240, 255, 0.95);
  box-shadow: 0 0 18px rgba(0, 240, 255, 0.55);
}

.t {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  opacity: 0.88;
  min-width: 48px;
  text-align: right;
}
</style>
