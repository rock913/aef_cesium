<template>
  <div class="tree" aria-label="Layer Tree">
    <div class="k">LAYER TREE</div>
    <div class="row" v-for="(l, i) in layers" :key="l.id">
      <label class="left">
        <input class="chk" type="checkbox" :checked="!!l.enabled" @change="toggle(l.id)" />
        <span class="name">{{ l.name }}</span>
      </label>
      <div class="ops" aria-label="Reorder">
        <button class="op" type="button" :disabled="i === 0" title="Move Up" @click="move(l.id, -1)">↑</button>
        <button class="op" type="button" :disabled="i === layers.length - 1" title="Move Down" @click="move(l.id, 1)">↓</button>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  layers: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:layers'])

function toggle(id) {
  const next = (props.layers || []).map((l) => (l.id === id ? { ...l, enabled: !l.enabled } : l))
  emit('update:layers', next)
}

function move(id, dir) {
  const arr = [...(props.layers || [])]
  const idx = arr.findIndex((l) => l.id === id)
  if (idx < 0) return
  const j = idx + (dir < 0 ? -1 : 1)
  if (j < 0 || j >= arr.length) return
  const tmp = arr[idx]
  arr[idx] = arr[j]
  arr[j] = tmp
  emit('update:layers', arr)
}
</script>

<style scoped>
.tree {
  position: absolute;
  right: 18px;
  top: 18px;
  z-index: 8;
  width: 220px;
  border-radius: 14px;
  padding: 10px 10px;
  background: rgba(10, 15, 26, 0.40);
  border: 1px solid rgba(255, 255, 255, 0.10);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 18px 55px rgba(0, 0, 0, 0.55);
}

.k {
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  opacity: 0.78;
  font-weight: 900;
  margin-bottom: 8px;
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  padding: 6px 6px;
  border-radius: 10px;
}

.left {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.ops {
  display: flex;
  gap: 6px;
}

.op {
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(0, 0, 0, 0.22);
  color: rgba(255, 255, 255, 0.82);
  width: 22px;
  height: 20px;
  border-radius: 8px;
  cursor: pointer;
}

.op:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.op:hover:enabled {
  border-color: rgba(0, 240, 255, 0.30);
}

.row:hover {
  background: rgba(255, 255, 255, 0.06);
}

.chk {
  accent-color: rgba(0, 240, 255, 0.95);
}

.name {
  opacity: 0.92;
}
</style>
