<script setup>
import { formatLookupDate } from '../utils/formatLookupDate.js'

defineProps({ section: { type: Object, required: true } })
</script>

<template>
  <div class="dnssec-result">
    <template v-if="section.data.scored === false">
      <p>No existing WebTrustScore report.</p>
      <a href="https://webtrustscore.com/" target="_blank" rel="noreferrer">Request a scan at WebTrustScore</a>
    </template>
    <template v-else>
      <div class="email-policy-heading">
        <strong>{{ section.data.score }} / 1000</strong>
        <span v-if="section.data.band">{{ section.data.band }}</span>
      </div>
      <p>{{ section.data.scannedAt ? 'Scanned ' + formatLookupDate(section.data.scannedAt) : 'Scan date unavailable' }}</p>
      <details v-if="section.data.signals?.length">
        <summary class="section-meta">Score breakdown</summary>
        <div v-for="signal in section.data.signals" :key="signal.label" class="email-policy">
          <div class="email-policy-value"><strong>{{ signal.label }}</strong>
            <span>{{ signal.value == null ? 'Unavailable' : signal.value + '/100' }}</span></div>
          <p>Confidence {{ signal.confidence == null ? 'unavailable' : signal.confidence + '%' }}</p>
        </div>
      </details>
      <p v-else>Signal breakdown unavailable</p>
      <div class="section-meta">
        <a :href="section.data.report" target="_blank" rel="noreferrer">View scoring evidence</a>
        <span v-if="section.data.modelVersion"> · Model {{ section.data.modelVersion }}</span>
      </div>
    </template>
  </div>
</template>
