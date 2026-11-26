<script setup>
defineProps({ section: { type: Object, required: true } })
</script>

<template>
  <div class="dnssec-result">
    <span class="dnssec-state" :class="section.data.status">{{ section.data.status.replace('_', ' ') }}</span>
    <p>{{ section.data.summary }}</p>
  </div>
</template>
