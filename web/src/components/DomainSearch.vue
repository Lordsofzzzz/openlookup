<script setup>
import { ref } from 'vue'

import { useSearchCursor } from '../composables/useSearchCursor.js'

defineProps({
  variant: { type: String, required: true },
  streamStatus: String,
})
const domain = defineModel({ type: String, required: true })
defineEmits(['investigate'])

const inputEl = ref(null)
const cursorEl = ref(null)
const { setInput, setCursor } = useSearchCursor(inputEl, cursorEl)

function focus() {
  inputEl.value?.focus()
}

defineExpose({ focus })
</script>

<template>
  <form class="search has-cursor" :class="variant === 'top' ? 'top-search' : 'main-search'" @submit.prevent="$emit('investigate')">
    <input :ref="setInput" v-model="domain" type="text" :readonly="streamStatus === 'loading'" placeholder="Enter a domain" aria-label="Domain name" autocomplete="off" autocapitalize="none" spellcheck="false" inputmode="url" :autofocus="variant === 'main'" />
    <span :ref="setCursor" class="cursor" aria-hidden="true"></span>
    <button type="submit" :disabled="streamStatus === 'loading'">{{ streamStatus === 'loading' ? 'LOOKING UP…' : 'LOOK UP' }}</button>
  </form>
</template>
