<script setup>
defineProps({ section: { type: Object, required: true } })
</script>

<template>
  <div class="identity-block">
    <div class="primary-fact">
      <div class="fact-label">Public IP addresses</div>
      <div v-if="section.data.addresses?.length" class="ip-address address-list">
        <div v-for="address in section.data.addresses" :key="address" class="address-entry">
          <span class="address-value">{{ address }}</span>
          <span v-for="network in section.data.address_asns?.find(item => item.ip === address)?.asns || []" :key="network.asn" class="address-asn">
            <span class="asn-number">{{ network.asn }}</span>
            <span v-if="network.name" class="asn-name">{{ network.name }}</span>
          </span>
        </div>
      </div>
      <div v-else class="fact-foot">No public IP addresses returned.</div>
    </div>
    <div class="secondary-facts">
      <div class="network-ranges-heading">Network ranges</div>
      <div v-for="network in section.data.networks || []" :key="`${network.asn}-${network.prefix}`" class="secondary-fact">
        <strong>{{ network.prefix }}</strong>
        <div class="network-range-meta">
          <span>{{ network.country }}</span>
          <span v-if="network.allocated">Allocated {{ network.allocated }}</span>
        </div>
      </div>
      <div v-if="!section.data.networks?.length" class="secondary-fact fact-foot">No network ranges returned.</div>
    </div>
  </div>
</template>
