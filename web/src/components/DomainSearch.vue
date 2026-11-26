<script setup>
defineProps({
  variant: { type: String, required: true },
  idle: Boolean,
  streamStatus: String,
  setContainer: { type: Function, required: true },
})
const domain = defineModel({ type: String, required: true })
defineEmits(['investigate'])
</script>

<template>
  <form v-if="variant === 'top' && !idle" :ref="setContainer" class="search top-search has-cursor" @submit.prevent="$emit('investigate')">
    <input v-model="domain" type="text" :readonly="streamStatus === 'loading'" placeholder="Enter a domain" aria-label="Domain name" autocomplete="off" autocapitalize="none" spellcheck="false" inputmode="url" />
    <span class="cursor" aria-hidden="true"></span>
    <button type="submit" :disabled="streamStatus === 'loading'">{{ streamStatus === 'loading' ? 'LOOKING UP…' : 'LOOK UP' }}</button>
  </form>
  <form v-if="variant === 'main' && idle" :ref="setContainer" class="search main-search has-cursor" @submit.prevent="$emit('investigate')">
    <input v-model="domain" type="text" :readonly="streamStatus === 'loading'" placeholder="Enter a domain" aria-label="Domain name" autocomplete="off" autocapitalize="none" spellcheck="false" inputmode="url" autofocus />
    <span class="cursor" aria-hidden="true"></span>
    <button type="submit" :disabled="streamStatus === 'loading'">{{ streamStatus === 'loading' ? 'LOOKING UP…' : 'LOOK UP' }}</button>
  </form>
</template>
