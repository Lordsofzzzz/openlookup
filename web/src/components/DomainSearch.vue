<script setup>
defineProps({
  variant: { type: String, required: true },
  idle: Boolean,
  streamStatus: String,
  setInput: { type: Function, required: true },
  setCursor: { type: Function, required: true },
})
const domain = defineModel({ type: String, required: true })
defineEmits(['investigate'])
</script>

<template>
  <form v-if="variant === 'top' && !idle" class="search top-search has-cursor" @submit.prevent="$emit('investigate')">
    <input :ref="setInput" v-model="domain" type="text" :readonly="streamStatus === 'loading'" placeholder="Enter a domain" aria-label="Domain name" autocomplete="off" autocapitalize="none" spellcheck="false" inputmode="url" />
    <span :ref="setCursor" class="cursor" aria-hidden="true"></span>
    <button type="submit" :disabled="streamStatus === 'loading'">{{ streamStatus === 'loading' ? 'LOOKING UP…' : 'LOOK UP' }}</button>
  </form>
  <form v-if="variant === 'main' && idle" class="search main-search has-cursor" @submit.prevent="$emit('investigate')">
    <input :ref="setInput" v-model="domain" type="text" :readonly="streamStatus === 'loading'" placeholder="Enter a domain" aria-label="Domain name" autocomplete="off" autocapitalize="none" spellcheck="false" inputmode="url" autofocus />
    <span :ref="setCursor" class="cursor" aria-hidden="true"></span>
    <button type="submit" :disabled="streamStatus === 'loading'">{{ streamStatus === 'loading' ? 'LOOKING UP…' : 'LOOK UP' }}</button>
  </form>
</template>
