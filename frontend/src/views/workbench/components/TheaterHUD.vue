<template>
  <div class="hud" aria-label="Theater HUD">
    <div class="card">
      <div class="k">THEATER MODE / 汇报视图</div>
      <div class="title">核心研判结论</div>
      <div class="meta">
        <span class="tag">@{{ contextId || '—' }}</span>
        <span class="sep">///</span>
        <span class="v">{{ targetName || '—' }}</span>
      </div>
      <div class="summary">{{ summary || 'System ready.' }}</div>

      <div class="row">
        <button class="btn" type="button" @click="$emit('open-omni')">打开 Omni 指令</button>
        <button class="btn secondary" type="button" @click="$emit('switch-lab')">切回 Lab</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  contextId: { type: String, default: '' },
  targetName: { type: String, default: '' },
  summary: { type: String, default: '' },
})

defineEmits(['open-omni', 'switch-lab'])
</script>

<style scoped>
.hud {
  position: absolute;
  left: 18px;
  top: 18px;
  z-index: 8;
  pointer-events: none;
}

.card {
  pointer-events: auto;
  width: min(520px, calc(100vw - 36px));
  border-radius: 16px;
  padding: 12px 14px;
  background: rgba(10, 15, 26, 0.40);
  border: 1px solid rgba(0, 240, 255, 0.20);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: 0 22px 70px rgba(0, 0, 0, 0.60);
}

.k {
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  opacity: 0.78;
  font-weight: 900;
}

.title {
  margin-top: 6px;
  font-weight: 900;
  font-size: 14px;
  letter-spacing: 0.02em;
}

.meta {
  margin-top: 6px;
  font-size: 11px;
  opacity: 0.82;
  display: flex;
  gap: 10px;
  align-items: center;
}

.tag {
  color: rgba(157, 78, 221, 0.95);
  border: 1px solid rgba(157, 78, 221, 0.35);
  border-radius: 999px;
  padding: 2px 8px;
}

.sep {
  opacity: 0.35;
}

.v {
  opacity: 0.95;
}

.summary {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.45;
  white-space: pre-wrap;
  max-height: 7.5em;
  overflow: hidden;
}

.row {
  margin-top: 10px;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn {
  padding: 8px 12px;
  border-radius: 12px;
  background: rgba(0, 240, 255, 0.86);
  border: 1px solid rgba(0, 240, 255, 0.20);
  color: #000;
  font-weight: 900;
  letter-spacing: 0.04em;
  cursor: pointer;
}

.btn.secondary {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.14);
  color: rgba(255, 255, 255, 0.92);
}
</style>
