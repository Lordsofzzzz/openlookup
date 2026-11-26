<script setup>
defineProps({ section: { type: Object, required: true } })
</script>

<template>
  <div class="exposure-list">
    <div v-for="host in section.data.hosts" :key="host.ip" class="exposure-host">
      <div class="exposure-head">
        <span class="exposure-ip">{{ host.ip }}</span>
        <span v-if="host.tags.length" class="exposure-tags">{{ host.tags.join(' · ') }}</span>
      </div>
      <template v-if="host.found">
        <div class="exposure-details">
          <div v-if="host.ports.length" class="exposure-row"><span class="exposure-label">OPEN PORTS</span><span class="exposure-values ports"><span v-for="port in host.ports" :key="port">{{ port }}</span></span></div>
          <div v-if="host.cpes.length" class="exposure-row"><span class="exposure-label">SOFTWARE</span><span class="exposure-values"><span v-for="cpe in host.cpes" :key="cpe" class="exposure-line">{{ cpe.replace(/^cpe:\//, '') }}</span></span></div>
          <div v-if="host.hostnames.length" class="exposure-row"><span class="exposure-label">HOSTNAMES</span><span class="exposure-values"><span v-for="name in host.hostnames" :key="name" class="exposure-line">{{ name }}</span></span></div>
          <div v-if="host.vulns.length" class="exposure-row exposure-vulns"><span class="exposure-label">REPORTED CVEs</span><span class="exposure-values"><a v-for="cve in host.vulns.slice(0, 3)" :key="cve" :href="`https://nvd.nist.gov/vuln/detail/${cve}`" target="_blank" rel="noopener noreferrer">{{ cve }}</a><details v-if="host.vulns.length > 3" class="exposure-more">
            <summary><span class="exposure-show">Show all reported CVEs ({{ host.vulns.length }})</span><span class="exposure-hide">Show fewer CVEs</span></summary>
            <div class="exposure-extra"><a v-for="cve in host.vulns.slice(3)" :key="cve" :href="`https://nvd.nist.gov/vuln/detail/${cve}`" target="_blank" rel="noopener noreferrer">{{ cve }}</a></div>
          </details></span></div>
          <div v-if="!host.ports.length && !host.cpes.length && !host.vulns.length" class="fact-foot">No ports or software listed.</div>
        </div>
      </template>
      <div v-else class="exposure-empty">No exposure data indexed for this address.</div>
    </div>
    <div v-if="!section.data.hosts.length" class="fact-foot exposure-foot">No public IP addresses to check.</div>
    <div v-if="section.data.truncated" class="fact-foot exposure-foot">Showing the first 10 addresses.</div>
    <div v-for="error in section.data.errors || []" :key="error" class="note">{{ error }}</div>
    <div class="fact-foot exposure-foot">Previously observed data. Reported CVEs may be unconfirmed.</div>
  </div>
</template>
