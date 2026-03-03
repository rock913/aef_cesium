<template>
  <div class="timeline" aria-label="Timeline HUD">
    <div class="k">SPACE‑TIME SLIDER</div>
    <div class="bar" aria-hidden="true">
      <div class="dot" />
    </div>
    <button class="btn" type="button" @click="$emit('execute')">EXECUTE ON TWIN</button>
  </div>
</template>

<script setup>
defineEmits(['execute'])
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

.btn {
  padding: 9px 12px;
  border-radius: 12px;
  background: rgba(0, 240, 255, 0.86);
  border: 1px solid rgba(0, 240, 255, 0.20);
  color: #000;
  font-weight: 900;
  letter-spacing: 0.08em;
  cursor: pointer;
  white-space: nowrap;
}
</style>
