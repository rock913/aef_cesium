<template>
  <div class="omnibox" :class="{ open: open }" aria-label="Omni Command">
    <div class="omnibox-top">
      <span class="spark" aria-hidden="true">✦</span>
      <input
        ref="inputEl"
        class="omnibox-input"
        :value="modelValue"
        type="text"
        :placeholder="placeholder"
        @input="$emit('update:modelValue', $event.target.value)"
        @keydown.enter.prevent="$emit('submit')"
        @keydown.esc.prevent="$emit('close')"
      />
      <div class="hint" aria-hidden="true">Cmd/Ctrl + K</div>
    </div>

    <div class="omnibox-context" v-if="contextLabel">
      <span class="k">已绑定上下文:</span>
      <span class="tag">@{{ contextLabel }}</span>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '输入指令，例如：生成该区域的水文变化热力图…' },
  contextLabel: { type: String, default: '' },
})

defineEmits(['update:modelValue', 'submit', 'close'])

const inputEl = ref(null)

watch(
  () => props.open,
  async (v) => {
    if (!v) return
    await nextTick()
    try {
      inputEl.value?.focus?.()
    } catch (_) {
      // ignore
    }
  }
)
</script>

<style scoped>
.omnibox {
  width: min(680px, calc(100vw - 24px));
  border-radius: 14px;
  overflow: hidden;
  background: rgba(15, 20, 35, 0.92);
  border: 1px solid rgba(0, 240, 255, 0.25);
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.70);
}

.omnibox-top {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.spark {
  color: rgba(0, 240, 255, 0.9);
  font-size: 14px;
}

.omnibox-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: rgba(255, 255, 255, 0.95);
  font-size: 14px;
}

.hint {
  font-size: 11px;
  opacity: 0.60;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.omnibox-context {
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.35);
  font-size: 12px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.k {
  opacity: 0.7;
}

.tag {
  color: rgba(157, 78, 221, 0.95);
  border: 1px solid rgba(157, 78, 221, 0.35);
  border-radius: 8px;
  padding: 2px 8px;
}
</style>
