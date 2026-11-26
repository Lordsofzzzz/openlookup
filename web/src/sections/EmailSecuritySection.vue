<script setup>
defineProps({ section: { type: Object, required: true } })
</script>

<template>
  <div>
    <div v-for="kind in ['spf', 'dmarc', 'mta_sts', 'tls_rpt']" :key="kind" class="email-policy">
      <div class="email-policy-heading"><strong>{{ kind.replace('_', '-').toUpperCase() }}</strong><span :class="section.data[kind].status">{{ section.data[kind].status }}</span></div>
      <p>{{ section.data[kind].summary }}</p>
      <div v-if="kind === 'dmarc' && section.data.dmarc.policy" class="email-policy-value"><span>Policy</span><strong>{{ section.data.dmarc.policy }}</strong></div>
      <div v-for="record in section.data[kind].records" :key="record" class="email-record">{{ record }}</div>
    </div>
    <div v-for="error in section.data.errors || []" :key="error" class="note">{{ error }}</div>
    <div class="fact-foot email-foot">Checks public DNS records only; a record’s presence doesn’t guarantee mail delivery.</div>
  </div>
</template>
