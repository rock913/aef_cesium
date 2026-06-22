<template>
  <div class="editor-panel" aria-label="Editor Panel">
    <div class="panel-title">NOTEBOOK / CODE</div>
    <div class="editor-shell">
      <slot />
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.editor-panel {
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

.editor-shell {
  flex: 1;
  min-height: 0;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.30);
}
</style>
