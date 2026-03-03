<template>
  <div class="tree" aria-label="Layer Tree">
    <div class="k">LAYER TREE</div>
    <label class="row" v-for="l in layers" :key="l.id">
      <input class="chk" type="checkbox" :checked="l.enabled" disabled />
      <span class="name">{{ l.name }}</span>
    </label>
  </div>
</template>

<script setup>
defineProps({
  layers: { type: Array, default: () => [] },
})
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
  gap: 8px;
  font-size: 12px;
  padding: 6px 6px;
  border-radius: 10px;
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
