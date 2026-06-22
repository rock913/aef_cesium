<template>
  <div v-if="active" class="swipe-root" aria-label="Swipe HUD">
    <div class="line" :style="{ left: `${positionPct}%` }">
      <div
        class="handle"
        role="slider"
        tabindex="0"
        aria-label="Swipe Split"
        :aria-valuemin="0"
        :aria-valuemax="100"
        :aria-valuenow="Math.round(positionPct)"
        @pointerdown="onDown"
        @keydown="onKey"
      >
        <span class="chev" aria-hidden="true">⇆</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  active: { type: Boolean, default: false },
  position: { type: Number, default: 0.5 },
})

const emit = defineEmits(['update:position'])

const dragging = ref(false)
const lastKnownX = ref(0)

const positionPct = computed(() => {
  const p = Number(props.position)
  const n = Number.isFinite(p) ? p : 0.5
  return Math.max(0, Math.min(1, n)) * 100
})

function _emitFromClientX(clientX) {
  const w = window.innerWidth || 1
  const x = Math.max(0, Math.min(w, clientX))
  emit('update:position', x / w)
}

function onDown(e) {
  if (!e) return
  dragging.value = true
  try {
    e.currentTarget?.setPointerCapture?.(e.pointerId)
  } catch (_) {
    // ignore
  }
  lastKnownX.value = Number(e.clientX) || 0
  _emitFromClientX(lastKnownX.value)
}

function onMove(e) {
  if (!dragging.value) return
  lastKnownX.value = Number(e.clientX) || lastKnownX.value
  _emitFromClientX(lastKnownX.value)
}

function onUp() {
  dragging.value = false
}

function onKey(e) {
  const k = String(e?.key || '').toLowerCase()
  if (!k) return
  const cur = Math.max(0, Math.min(1, Number(props.position) || 0.5))
  if (k === 'arrowleft') {
    e.preventDefault?.()
    emit('update:position', Math.max(0, cur - 0.02))
  } else if (k === 'arrowright') {
    e.preventDefault?.()
    emit('update:position', Math.min(1, cur + 0.02))
  }
}

watch(
  () => props.active,
  (v) => {
    if (!v) dragging.value = false
  }
)

onMounted(() => {
  if (typeof window === 'undefined') return
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
})

onBeforeUnmount(() => {
  if (typeof window === 'undefined') return
  window.removeEventListener('pointermove', onMove)
  window.removeEventListener('pointerup', onUp)
})
</script>

<style scoped>
.swipe-root {
  position: absolute;
  inset: 0;
  /* Under the HUD layer (which sits at z-index: 10 in WorkbenchApp). */
  z-index: 5;
  pointer-events: none;
}

.line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  transform: translateX(-1px);
  background: rgba(0, 240, 255, 0.92);
  box-shadow: 0 0 18px rgba(0, 240, 255, 0.55), 0 0 28px rgba(157, 78, 221, 0.25);
}

.handle {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 38px;
  height: 54px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.55);
  border: 1px solid rgba(0, 240, 255, 0.35);
  display: grid;
  place-items: center;
  cursor: ew-resize;
  pointer-events: auto;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.chev {
  color: rgba(0, 240, 255, 0.95);
  font-size: 14px;
  font-weight: 900;
  letter-spacing: 0.12em;
}
</style>
