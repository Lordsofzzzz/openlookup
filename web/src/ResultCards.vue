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
              <div class="section-heading"><h2>Infrastructure</h2><SectionRetry :status="statusFor('ip')" :pending="!!retries.ip" :error="retryErrors.ip" @retry="$emit('retry', 'ip')" /></div>
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
              <div class="section-heading"><h2>DNS record set</h2><SectionRetry :status="statusFor('dns')" :pending="!!retries.dns" :error="retryErrors.dns" @retry="$emit('retry', 'dns')" /></div>
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
              <h2 class="side-heading">DNSSEC <SectionRetry :status="statusFor('dnssec')" :pending="!!retries.dnssec" :error="retryErrors.dnssec" @retry="$emit('retry', 'dnssec')" /></h2>
              <div v-if="sections.dnssec?.message" class="note">{{ sections.dnssec.message }}</div>
              <div v-if="sections.dnssec?.status === 'ok'" class="dnssec-result">
                <span class="dnssec-state" :class="sections.dnssec.data.status">{{ sections.dnssec.data.status.replace('_', ' ') }}</span>
                <p>{{ sections.dnssec.data.summary }}</p>
              </div>
              <div v-if="sections.dnssec" class="section-meta">{{ displayDate(sections.dnssec.fetched_at) }}</div>
            </section>

            <section class="side-section">
              <h2 class="side-heading">Registration profile <SectionRetry :status="statusFor('rdap')" :pending="!!retries.rdap" :error="retryErrors.rdap" @retry="$emit('retry', 'rdap')" /></h2>
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
              <h2 class="side-heading">Email security <SectionRetry :status="statusFor('email_security')" :pending="!!retries.email_security" :error="retryErrors.email_security" @retry="$emit('retry', 'email_security')" /></h2>
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
              <h2 class="side-heading">Subdomains <SectionRetry :status="statusFor('subdomains')" :pending="!!retries.subdomains" :error="retryErrors.subdomains" @retry="$emit('retry', 'subdomains')" /></h2>
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
