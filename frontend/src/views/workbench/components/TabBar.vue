<template>
  <div class="tabs" aria-label="Tab System">
    <button
      v-for="t in tabs"
      :key="t.id"
      type="button"
      class="tab"
      :class="{ active: t.id === activeId }"
      @click="$emit('select', t.id)"
    >
      <span class="label">{{ t.title }}</span>
      <span v-if="t.id === activeId" class="glow" aria-hidden="true" />
    </button>
  </div>
</template>

<script setup>
defineProps({
  tabs: { type: Array, default: () => [] },
  activeId: { type: String, default: '' },
})

defineEmits(['select'])
</script>

<style scoped>
.tabs {
  height: 32px;
  display: flex;
  align-items: stretch;
  gap: 6px;
  padding: 0 8px;
  background: rgba(5, 8, 16, 0.86);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  overflow-x: auto;
}

.tab {
  position: relative;
  border: none;
  background: rgba(0, 0, 0, 0.18);
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  padding: 0 12px;
  border-radius: 10px 10px 0 0;
  cursor: pointer;
}

.tab.active {
  background: rgba(0, 0, 0, 0.65);
  color: rgba(255, 255, 255, 0.95);
}

.label {
  position: relative;
  z-index: 2;
  white-space: nowrap;
}

.glow {
  position: absolute;
  left: 10px;
  right: 10px;
  top: 0;
  height: 2px;
  background: rgba(0, 240, 255, 0.95);
  box-shadow: 0 0 18px rgba(0, 240, 255, 0.55);
}
</style>
