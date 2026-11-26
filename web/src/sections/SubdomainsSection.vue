<script setup>
defineProps({ section: { type: Object, required: true } })
</script>

<template>
  <div>
    <div class="fact-foot">{{ `${section.data.count} found${section.data.truncated ? ' (results truncated)' : ''}` }}</div>
    <ul class="subdomain-list">
      <li v-for="name in section.data.subdomains" :key="name">{{ name }}</li>
    </ul>
  </div>
</template>
