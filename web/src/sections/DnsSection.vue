<script setup>
defineProps({ section: { type: Object, required: true } })

function dnsRecordValue(record) {
  return record.type === 'MX' && /^0(?:\s+\.)?$/.test(record.value.trim())
    ? 'No mail (null MX)'
    : record.value
}
</script>

<template>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Type</th><th>Record value</th><th>TTL</th></tr></thead>
      <tbody>
        <tr v-for="(record, index) in section.data.records" :key="`${record.type}-${record.value}-${index}`">
          <td class="record-type">{{ record.type }}</td><td class="value">{{ dnsRecordValue(record) }}</td><td class="ttl">{{ record.ttl }}</td>
        </tr>
        <tr v-if="!section.data.records?.length"><td colspan="3" class="fact-foot">No DNS records returned.</td></tr>
      </tbody>
    </table>
  </div>
</template>
