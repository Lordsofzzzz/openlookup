<script setup>
defineProps({ status: String, pending: Boolean, error: String })
defineEmits(['retry'])
</script>

<template>
  <span class="retry-control">
    <button type="button" :class="status" :disabled="pending" :aria-label="pending ? 'Refreshing section' : 'Refresh section'" :title="pending ? 'Refreshing…' : 'Refresh section'" @click="$emit('retry')">
      <span aria-hidden="true" :class="{ spinning: pending }">↻</span>
    </button>
    <span v-if="error" class="retry-error" role="status">{{ error }}</span>
  </span>
</template>

<style scoped>
.retry-control { display: inline-flex; align-items: center; gap: .6rem; vertical-align: middle; }
button { display: inline-grid; place-items: center; width: 20px; height: 20px; padding: 0; border: 0; border-radius: 0; background: transparent; color: var(--dim); cursor: pointer; line-height: 1; }
button:hover:not(:disabled) { color: var(--acid); }
button.ok { color: var(--acid); }
button.error, button.timeout { color: var(--amber); }
button.loading { color: var(--muted); }
button:disabled { opacity: .65; cursor: wait; }
button span { font-size: 17px; }
.retry-error { color: var(--amber); font-size: 10px; }
.spinning { display: inline-block; animation: spin 1.1s linear infinite; transform-origin: center; will-change: transform; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
