<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps({ status: String, pending: Boolean, error: String })
defineEmits(['retry'])

// `spinning` outlives `pending` until the current turn finishes,
// so the icon never snaps back mid-rotation.
const spinning = ref(props.pending)
const icon = ref(null)

watch(() => props.pending, (pending) => {
  if (pending) spinning.value = true
})

function onIteration() {
  if (!props.pending) spinning.value = false
}
</script>

<template>
  <span class="retry-control">
    <button
      type="button"
      :class="[status, { busy: spinning }]"
      :disabled="pending"
      :aria-busy="pending"
      :aria-label="pending ? 'Refreshing section' : 'Refresh section'"
      :title="pending ? 'Refreshing…' : 'Refresh section'"
      @click="$emit('retry')"
    >
      <svg
        ref="icon"
        class="icon"
        :class="{ spinning }"
        viewBox="0 0 24 24"
        width="16"
        height="16"
        fill="none"
        stroke="currentColor"
        stroke-width="2.25"
        stroke-linecap="square"
        stroke-linejoin="miter"
        aria-hidden="true"
        @animationiteration="onIteration"
      >
        <path d="M20 12a8 8 0 1 1-8-8" />
        <path d="M11 1.5 14.5 4 11 6.5" />
      </svg>
    </button>
    <span v-if="error" class="retry-error" role="status">{{ error }}</span>
  </span>
</template>

<style scoped>
.retry-control { display: inline-flex; align-items: center; gap: .6rem; vertical-align: middle; }
button {
  display: inline-grid; place-items: center; width: 24px; height: 24px; padding: 0;
  border: 0; border-radius: 0; background: transparent;
  color: var(--dim); cursor: pointer; line-height: 1;
}
button:hover:not(:disabled) { color: var(--acid); }
button:active:not(:disabled) { transform: translateY(1px); }
button.ok { color: var(--acid-dim); }
button.error, button.timeout { color: var(--amber); }
button.loading { color: var(--muted); }
button:disabled { cursor: wait; }
button.busy { color: var(--acid); }
.icon { display: block; transform-origin: 50% 50%; }
.spinning { animation: spin .9s cubic-bezier(.45, 0, .25, 1) infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.retry-error { color: var(--amber); font-size: 10px; }
@media (prefers-reduced-motion: reduce) {
  .spinning { animation: pulse 1.2s ease-in-out infinite; }
  @keyframes pulse { 50% { opacity: .35; } }
}
</style>
