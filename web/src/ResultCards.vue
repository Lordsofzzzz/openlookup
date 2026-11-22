<script setup>
import SectionRetry from './components/SectionRefreshButton.vue'

defineProps({
  sections: { type: Object, required: true },
  retries: { type: Object, required: true },
  retryErrors: { type: Object, required: true },
  displayDate: { type: Function, required: true },
  dnsRecordValue: { type: Function, required: true },
  statusFor: { type: Function, required: true },
})
defineEmits(['retry'])
</script>

<template>
        <div class="layout">
          <div class="main-col">
            <section class="section">
              <div class="section-heading"><h2>Infrastructure</h2><SectionRetry :status="statusFor('ip')" :pending="statusFor('ip') === 'loading' || !!retries.ip" :error="retryErrors.ip" @retry="$emit('retry', 'ip')" /></div>
              <div v-if="sections.ip?.message" class="note">{{ sections.ip.message }}</div>
              <Transition name="reveal">
                <div v-if="sections.ip?.status === 'ok'" class="identity-block">
                  <div class="primary-fact">
                    <div class="fact-label">Public IP addresses</div>
                    <div v-if="sections.ip.data.addresses?.length" class="ip-address address-list">
                      <div v-for="address in sections.ip.data.addresses" :key="address">{{ address }}</div>
                    </div>
                    <div v-else class="fact-foot">No public IP addresses returned.</div>
                  </div>
                  <div class="secondary-facts">
                    <div v-for="network in sections.ip.data.networks || []" :key="`${network.asn}-${network.prefix}`" class="secondary-fact">
                      <div class="fact-label">{{ network.asn }}</div>
                      <strong>{{ network.name || 'ASN details' }}</strong>
                      <small>{{ network.prefix }} · {{ network.country }}</small>
                    </div>
                    <div v-if="!sections.ip.data.networks?.length" class="secondary-fact fact-foot">No ASN details returned.</div>
                  </div>
                </div>
              </Transition>
              <div v-if="sections.ip" class="section-meta">{{ displayDate(sections.ip.fetched_at) }}</div>
            </section>

            <section class="section">
              <div class="section-heading"><h2>Exposure</h2><SectionRetry :status="statusFor('exposure')" :pending="statusFor('exposure') === 'loading' || !!retries.exposure" :error="retryErrors.exposure" @retry="$emit('retry', 'exposure')" /></div>
              <div v-if="sections.exposure?.message" class="note">{{ sections.exposure.message }}</div>
              <Transition name="reveal">
                <div v-if="sections.exposure?.status === 'ok'" class="exposure-list">
                  <div v-for="host in sections.exposure.data.hosts" :key="host.ip" class="exposure-host">
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
                  <div v-if="!sections.exposure.data.hosts.length" class="fact-foot exposure-foot">No public IP addresses to check.</div>
                  <div v-if="sections.exposure.data.truncated" class="fact-foot exposure-foot">Showing the first 10 addresses.</div>
                  <div v-for="error in sections.exposure.data.errors || []" :key="error" class="note">{{ error }}</div>
                  <div class="fact-foot exposure-foot">Previously observed data. Reported CVEs may be unconfirmed.</div>
                </div>
              </Transition>
              <div v-if="sections.exposure" class="section-meta">{{ displayDate(sections.exposure.fetched_at) }}</div>
            </section>

            <section class="section">
              <div class="section-heading"><h2>DNS record set</h2><SectionRetry :status="statusFor('dns')" :pending="statusFor('dns') === 'loading' || !!retries.dns" :error="retryErrors.dns" @retry="$emit('retry', 'dns')" /></div>
              <div v-if="sections.dns?.message" class="note">{{ sections.dns.message }}</div>
              <Transition name="reveal">
                <div v-if="sections.dns?.status === 'ok'" class="table-wrap">
                  <table>
                    <thead><tr><th>Type</th><th>Record value</th><th>TTL</th></tr></thead>
                    <tbody>
                      <tr v-for="(record, index) in sections.dns.data.records" :key="`${record.type}-${record.value}-${index}`">
                        <td class="record-type">{{ record.type }}</td><td class="value">{{ dnsRecordValue(record) }}</td><td class="ttl">{{ record.ttl }}</td>
                      </tr>
                      <tr v-if="!sections.dns.data.records?.length"><td colspan="3" class="fact-foot">No DNS records returned.</td></tr>
                    </tbody>
                  </table>
                </div>
              </Transition>
              <div v-if="sections.dns" class="section-meta">{{ displayDate(sections.dns.fetched_at) }}</div>
            </section>
          </div>

          <aside class="side-col">
            <section class="side-section">
              <h2 class="side-heading">DNSSEC <SectionRetry :status="statusFor('dnssec')" :pending="statusFor('dnssec') === 'loading' || !!retries.dnssec" :error="retryErrors.dnssec" @retry="$emit('retry', 'dnssec')" /></h2>
              <div v-if="sections.dnssec?.message" class="note">{{ sections.dnssec.message }}</div>
              <div v-if="sections.dnssec?.status === 'ok'" class="dnssec-result">
                <span class="dnssec-state" :class="sections.dnssec.data.status">{{ sections.dnssec.data.status.replace('_', ' ') }}</span>
                <p>{{ sections.dnssec.data.summary }}</p>
              </div>
              <div v-if="sections.dnssec" class="section-meta">{{ displayDate(sections.dnssec.fetched_at) }}</div>
            </section>

            <section class="side-section">
              <h2 class="side-heading">Registration profile <SectionRetry :status="statusFor('rdap')" :pending="statusFor('rdap') === 'loading' || !!retries.rdap" :error="retryErrors.rdap" @retry="$emit('retry', 'rdap')" /></h2>
              <div v-if="sections.rdap?.message" class="note">{{ sections.rdap.message }}</div>
              <Transition name="reveal">
                <dl v-if="sections.rdap?.status === 'ok'" class="profile-list">
                  <div class="profile-row"><dt>Registrar</dt><dd>{{ sections.rdap.data.registrar || '—' }}</dd></div>
                  <div class="profile-row nameservers-row"><dt>Nameservers</dt><dd><span v-for="server in sections.rdap.data.nameservers || []" :key="server">{{ server }}</span><span v-if="!sections.rdap.data.nameservers?.length">—</span></dd></div>
                  <div class="profile-row"><dt>Created</dt><dd>{{ displayDate(sections.rdap.data.created) }}</dd></div>
                  <div class="profile-row"><dt>Updated</dt><dd>{{ displayDate(sections.rdap.data.updated) }}</dd></div>
                  <div class="profile-row"><dt>Expires</dt><dd>{{ displayDate(sections.rdap.data.expires) }}</dd></div>
                  <div v-for="status in sections.rdap.data.status || []" :key="status" class="profile-row"><dt>Status</dt><dd>{{ status }}</dd></div>
                </dl>
              </Transition>
              <div v-if="sections.rdap" class="section-meta">{{ displayDate(sections.rdap.fetched_at) }}</div>
            </section>

            <section class="side-section">
              <h2 class="side-heading">Email security <SectionRetry :status="statusFor('email_security')" :pending="statusFor('email_security') === 'loading' || !!retries.email_security" :error="retryErrors.email_security" @retry="$emit('retry', 'email_security')" /></h2>
              <div v-if="sections.email_security?.message" class="note">{{ sections.email_security.message }}</div>
              <Transition name="reveal">
                <div v-if="sections.email_security?.status === 'ok'">
                  <div v-for="kind in ['spf', 'dmarc', 'mta_sts', 'tls_rpt']" :key="kind" class="email-policy">
                    <div class="email-policy-heading"><strong>{{ kind.replace('_', '-').toUpperCase() }}</strong><span :class="sections.email_security.data[kind].status">{{ sections.email_security.data[kind].status }}</span></div>
                    <p>{{ sections.email_security.data[kind].summary }}</p>
                    <div v-if="kind === 'dmarc' && sections.email_security.data.dmarc.policy" class="email-policy-value"><span>Policy</span><strong>{{ sections.email_security.data.dmarc.policy }}</strong></div>
                    <div v-for="record in sections.email_security.data[kind].records" :key="record" class="email-record">{{ record }}</div>
                  </div>
                  <div v-for="error in sections.email_security.data.errors || []" :key="error" class="note">{{ error }}</div>
                  <div class="fact-foot email-foot">Checks public DNS records only; a record’s presence doesn’t guarantee mail delivery.</div>
                </div>
              </Transition>
              <div v-if="sections.email_security" class="section-meta">{{ displayDate(sections.email_security.fetched_at) }}</div>
            </section>

            <section class="side-section">
              <h2 class="side-heading">Subdomains <SectionRetry :status="statusFor('subdomains')" :pending="statusFor('subdomains') === 'loading' || !!retries.subdomains" :error="retryErrors.subdomains" @retry="$emit('retry', 'subdomains')" /></h2>
              <div v-if="sections.subdomains?.message" class="note">{{ sections.subdomains.message }}</div>
              <Transition name="reveal">
                <div v-if="sections.subdomains?.status === 'ok'">
                  <div class="fact-foot">{{ `${sections.subdomains.data.count} found${sections.subdomains.data.truncated ? ' (results truncated)' : ''}` }}</div>
                  <ul class="subdomain-list">
                    <li v-for="name in sections.subdomains.data.subdomains" :key="name">{{ name }}</li>
                  </ul>
                </div>
              </Transition>
              <div v-if="sections.subdomains" class="section-meta">{{ displayDate(sections.subdomains.fetched_at) }}</div>
            </section>
          </aside>
        </div>
</template>
