<template>
  <div class="tabs" aria-label="Tab System">
    <button v-for="t in tabs" :key="t.id" type="button" class="tab" :class="{ active: t.id === activeId }" @click="$emit('select', t.id)">
      <span class="label">{{ t.title }}</span>
      <span v-if="t.id === activeId" class="glow" aria-hidden="true" />
      <button
        v-if="t.closable"
        class="close"
        type="button"
        aria-label="Close Tab"
        title="Close"
        @click.stop="$emit('close', t.id)"
      >
        ×
      </button>
    </button>

    <div class="spacer" />

    <div class="new" aria-label="New Tab">
      <button class="plus" type="button" aria-label="New Tab" title="New Tab" @click="toggleMenu">＋</button>
      <div v-if="menuOpen" class="menu" role="menu">
        <button class="item" type="button" role="menuitem" @click="create('table')">Data Table</button>
        <button class="item" type="button" role="menuitem" @click="create('charts')">2D Charts</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  tabs: { type: Array, default: () => [] },
  activeId: { type: String, default: '' },
})

const emit = defineEmits(['select', 'close', 'new-tab'])

const menuOpen = ref(false)

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

function create(kind) {
  emit('new-tab', kind)
  menuOpen.value = false
}
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
  padding: 0 30px 0 12px;
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

.close {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.75);
  width: 18px;
  height: 18px;
  border-radius: 6px;
  cursor: pointer;
}

.close:hover {
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.95);
}

.spacer {
  flex: 1;
}

.new {
  position: relative;
  display: flex;
  align-items: center;
}

.plus {
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(0, 0, 0, 0.22);
  color: rgba(255, 255, 255, 0.82);
  height: 24px;
  width: 26px;
  border-radius: 10px;
  cursor: pointer;
}

.plus:hover {
  border-color: rgba(0, 240, 255, 0.30);
}

.menu {
  position: absolute;
  right: 0;
  top: 30px;
  min-width: 150px;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(15, 20, 35, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 20px 70px rgba(0, 0, 0, 0.60);
  z-index: 30;
}

.item {
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.88);
  cursor: pointer;
}

.item:hover {
  background: rgba(0, 240, 255, 0.12);
}
</style>
