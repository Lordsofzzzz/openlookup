<script setup>
import { formatLookupDate } from '../utils/formatLookupDate.js'

defineProps({ section: { type: Object, required: true } })
</script>

<template>
  <dl class="profile-list">
    <div class="profile-row"><dt>Registrar</dt><dd>{{ section.data.registrar || '—' }}</dd></div>
    <div class="profile-row nameservers-row"><dt>Nameservers</dt><dd><span v-for="server in section.data.nameservers || []" :key="server">{{ server }}</span><span v-if="!section.data.nameservers?.length">—</span></dd></div>
    <div class="profile-row"><dt>Created</dt><dd>{{ formatLookupDate(section.data.created) }}</dd></div>
    <div class="profile-row"><dt>Updated</dt><dd>{{ formatLookupDate(section.data.updated) }}</dd></div>
    <div class="profile-row"><dt>Expires</dt><dd>{{ formatLookupDate(section.data.expires) }}</dd></div>
    <div v-for="status in section.data.status || []" :key="status" class="profile-row"><dt>Status</dt><dd>{{ status }}</dd></div>
  </dl>
</template>
