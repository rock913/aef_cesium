<template>
  <div class="agent-panel" aria-label="Agent Panel">
    <div class="panel-title">021 MODEL FLOW</div>

    <pre class="panel-pre">{{ text }}</pre>

    <div class="panel-row">
      <button class="btn" type="button" @click="$emit('execute')">EXECUTE ON TWIN</button>
      <button class="btn secondary" type="button" @click="$emit('reset')">Reset</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  text: { type: String, default: '' },
})

defineEmits(['execute', 'reset'])
</script>

<style scoped>
.agent-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.panel-title {
  font-size: 12px;
  opacity: 0.78;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-weight: 900;
}

.panel-pre {
  flex: 1;
  min-height: 0;
  white-space: pre-wrap;
  overflow: auto;
  padding: 10px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.30);
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 12px;
  line-height: 1.45;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.panel-row {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 9px 12px;
  border-radius: 12px;
  background: rgba(0, 240, 255, 0.18);
  border: 1px solid rgba(0, 240, 255, 0.35);
  color: #eaffff;
  text-decoration: none;
  cursor: pointer;
}

.btn.secondary {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.16);
  color: rgba(255, 255, 255, 0.86);
}
</style>
