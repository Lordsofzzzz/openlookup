<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const domain = ref('')
const resultDomain = ref('')
const notice = ref('')
const sections = ref({})
const streamStatus = ref('idle')
const inputEl = ref(null)
const cursorEl = ref(null)
const mapEl = ref(null)
let removeInputListeners
let eventSource
let mapObserver
const idle = computed(() => streamStatus.value === 'idle')
const domainNotFound = computed(() => {
  const dns = sections.value.dns
  const rdap = sections.value.rdap
  return (dns?.status === 'ok' && dns.data?.nxdomain === true)
    || (rdap?.status === 'ok' && rdap.data?.registered === false)
})
const sectionNames = [
  { key: 'ip', title: 'Infrastructure' },
  { key: 'dns', title: 'DNS record set' },
  { key: 'rdap', title: 'Registration profile' },
  { key: 'subdomains', title: 'Subdomains' },
  { key: 'email_security', title: 'Email security' },
]
const COLS = 72
const LAND = [
  [[14, 21], [24, 31]],
  [[10, 22], [23, 33], [50, 58], [62, 68]],
  [[5, 22], [24, 33], [37, 42], [44, 71]],
  [[2, 24], [26, 33], [34, 42], [43, 71]],
  [[4, 24], [28, 30], [34, 42], [43, 71]],
  [[8, 26], [34, 36], [38, 72]],
  [[8, 26], [36, 71]],
  [[8, 25], [36, 44], [45, 60], [62, 70]],
  [[9, 25], [34, 47], [48, 70]],
  [[10, 24], [34, 48], [50, 69]],
  [[12, 23], [33, 48], [49, 68]],
  [[14, 22], [33, 50], [51, 67]],
  [[15, 21], [33, 52], [53, 56], [58, 66]],
  [[16, 23], [33, 52], [53, 56], [58, 62]],
  [[19, 28], [34, 50], [55, 56], [59, 60]],
  [[20, 30], [36, 48], [56, 64]],
  [[19, 31], [38, 47], [55, 57], [63, 66]],
  [[19, 31], [38, 48], [56, 59], [64, 67]],
  [[20, 31], [39, 48], [60, 64]],
  [[20, 30], [39, 48], [59, 66]],
  [[20, 29], [38, 47], [58, 67]],
  [[20, 29], [39, 46], [58, 67]],
  [[21, 29], [40, 46], [58, 67]],
  [[21, 28], [41, 45], [59, 66]],
  [[21, 27], [63, 65], [70, 71]],
  [[22, 27], [70, 71]],
  [[22, 26]],
  [[23, 25]],
]
const domainPattern = /^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]{2,59})$/

function normalize(value) {
  let candidate = value.trim().toLowerCase().replace(/^[a-z]+:\/\//, '').split(/[/?#]/)[0].replace(/\.$/, '')
  if (!candidate || !/^[\p{L}\p{N}.-]+$/u.test(candidate)) return ''
  try { candidate = new URL(`http://${candidate}`).hostname.toLowerCase() } catch { return '' }
  return candidate
}
function drawMap() {
  const canvas = mapEl.value
  if (!canvas) return
  const width = canvas.parentElement?.clientWidth || window.innerWidth
  const cell = Math.max(6, Math.floor(Math.min(width, 1200) / COLS))
  const dot = Math.max(2, cell - 3)
  canvas.width = COLS * cell
  canvas.height = LAND.length * cell
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.imageSmoothingEnabled = false
  LAND.forEach((spans, y) => {
    for (const [from, to] of spans) {
      for (let x = from; x <= Math.min(to, COLS - 1); x++) {
        ctx.fillStyle = `rgba(163,227,90,${0.55 + ((x * 7 + y * 13) % 5) * 0.1})`
        ctx.fillRect(x * cell, y * cell, dot, dot)
      }
    }
  })
}
function placeCursor() {
  const input = inputEl.value, cursor = cursorEl.value
  if (!input || !cursor || input.readOnly || document.activeElement !== input || input.selectionStart !== input.selectionEnd) { if (cursor) cursor.style.display = 'none'; return }
  const styles = getComputedStyle(input), canvas = document.createElement('canvas'), ctx = canvas.getContext('2d')
  ctx.font = `${styles.fontStyle} ${styles.fontWeight} ${styles.fontSize} ${styles.fontFamily}`
  const x = input.offsetLeft + parseFloat(styles.paddingLeft) + ctx.measureText(input.value.slice(0, input.selectionStart || 0)).width - input.scrollLeft
  const height = Math.round(parseFloat(styles.fontSize) * 1.3), width = Math.max(6, Math.round(ctx.measureText('0').width * 0.75))
  if (x < input.offsetLeft || x > input.offsetLeft + input.clientWidth - width) { cursor.style.display = 'none'; return }
  cursor.style.display = 'block'; cursor.style.left = `${Math.round(x)}px`; cursor.style.top = `${Math.round(input.offsetTop + (input.offsetHeight - height) / 2)}px`; cursor.style.width = `${width}px`; cursor.style.height = `${height}px`
}
function setInput(el) {
  removeInputListeners?.()
  inputEl.value = el
  if (!el) return
  const updateCursor = () => setTimeout(placeCursor, 0)
  const events = ['input', 'keyup', 'keydown', 'click', 'focus', 'blur', 'select', 'scroll']
  events.forEach(event => el.addEventListener(event, updateCursor))
  window.addEventListener('resize', placeCursor)
  removeInputListeners = () => {
    events.forEach(event => el.removeEventListener(event, updateCursor))
    window.removeEventListener('resize', placeCursor)
    removeInputListeners = null
  }
  setTimeout(placeCursor, 50)
}
document.addEventListener('selectionchange', placeCursor)
onMounted(() => {
  drawMap()
  if (typeof ResizeObserver !== 'undefined') {
    mapObserver = new ResizeObserver(drawMap)
    if (mapEl.value?.parentElement) mapObserver.observe(mapEl.value.parentElement)
  }
})
watch(idle, async (isIdle) => {
  if (isIdle) {
    await nextTick()
    drawMap()
  }
})
function closeStream() {
  eventSource?.close()
  eventSource = null
}
function resetSearch() {
  closeStream()
  domain.value = ''
  resultDomain.value = ''
  sections.value = {}
  notice.value = ''
  streamStatus.value = 'idle'
  document.body.classList.remove('has-results')
}
function sectionState(key) { return sections.value[key] ?? null }
function sectionStatus(key) {
  return sectionState(key)?.status ?? (streamStatus.value === 'loading' ? 'loading' : 'waiting')
}
function displayDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}
function dnsRecordValue(record) {
  return record.type === 'MX' && /^0(?:\s+\.)?$/.test(record.value.trim())
    ? 'No mail (null MX)'
    : record.value
}
async function investigate() {
  const host = normalize(domain.value)
  if (!host) { notice.value = 'Enter a domain to continue.'; inputEl.value?.focus(); return }
  if (!domainPattern.test(host)) { notice.value = `“${domain.value.trim()}” is not a valid domain.`; inputEl.value?.focus(); return }

  closeStream()
  sections.value = {}
  domain.value = host
  resultDomain.value = host
  notice.value = ''
  streamStatus.value = 'loading'
  document.body.classList.add('has-results')
  await nextTick()
  inputEl.value?.focus()

  eventSource = new EventSource(`/api/v1/domain/${encodeURIComponent(host)}/stream`)
  eventSource.addEventListener('section', event => {
    try {
      const result = JSON.parse(event.data)
      if (!sectionNames.some(section => section.key === result.section)) return
      sections.value = { ...sections.value, [result.section]: result }
    } catch {
      notice.value = 'The API sent an unreadable section response.'
    }
  })
  eventSource.addEventListener('done', () => {
    streamStatus.value = 'complete'
    closeStream()
  })
  eventSource.onerror = () => {
    if (streamStatus.value !== 'loading') return
    streamStatus.value = 'error'
    notice.value = 'Could not connect to the lookup API. Check that the backend is running.'
    closeStream()
  }
}
onBeforeUnmount(() => {
  closeStream()
  removeInputListeners?.()
  mapObserver?.disconnect()
  document.removeEventListener('selectionchange', placeCursor)
})
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <a class="brand" href="#" aria-label="OpenLookup home" @click.prevent="resetSearch"><span class="brand-mark"><svg width="18" height="18" viewBox="0 0 9 9" shape-rendering="crispEdges" aria-hidden="true"><rect x="1" y="0" width="4" height="1" fill="#11180f"/><rect x="0" y="1" width="1" height="1" fill="#11180f"/><rect x="5" y="1" width="1" height="1" fill="#11180f"/><rect x="0" y="2" width="1" height="1" fill="#11180f"/><rect x="5" y="2" width="1" height="1" fill="#11180f"/><rect x="2" y="2" width="2" height="1" fill="#4a6637"/><rect x="0" y="3" width="1" height="1" fill="#11180f"/><rect x="5" y="3" width="1" height="1" fill="#11180f"/><rect x="2" y="3" width="1" height="1" fill="#4a6637"/><rect x="0" y="4" width="1" height="1" fill="#11180f"/><rect x="5" y="4" width="1" height="1" fill="#11180f"/><rect x="1" y="5" width="4" height="1" fill="#11180f"/><rect x="6" y="5" width="1" height="1" fill="#11180f"/><rect x="6" y="6" width="2" height="1" fill="#11180f"/><rect x="7" y="7" width="2" height="1" fill="#11180f"/><rect x="8" y="8" width="1" height="1" fill="#11180f"/></svg></span><span class="brand-text">OpenLookup</span></a>
      <form v-if="!idle" class="search top-search has-cursor" @submit.prevent="investigate">
        <input :ref="setInput" v-model="domain" type="text" :readonly="streamStatus === 'loading'" placeholder="Enter a domain" aria-label="Domain name" autocomplete="off" autocapitalize="none" spellcheck="false" inputmode="url" />
        <span ref="cursorEl" class="cursor" aria-hidden="true"></span>
        <button type="submit" :disabled="streamStatus === 'loading'">{{ streamStatus === 'loading' ? 'LOOKING UP…' : 'LOOK UP' }}</button>
      </form>
      <a v-if="idle" class="gh-link" href="https://github.com/lordsofzzzz/openlookup" target="_blank" rel="noopener noreferrer" aria-label="OpenLookup on GitHub">
        <svg viewBox="0 0 12 12" width="24" height="24" shape-rendering="crispEdges" aria-hidden="true">
          <path class="gh-disc" d="M3 0h6v1h-6z M2 1h8v1h-8z M1 2h10v1h-10z M0 3h12v6h-12z M1 9h10v1h-10z M2 10h8v1h-8z M3 11h6v1h-6z" />
          <path class="gh-cat" d="M4 2h1v2h-1z M7 2h1v2h-1z M3 4h6v3h-6z M2 7h1v1h-1z M4 7h4v1h-4z M3 8h5v1h-5z M4 9h4v3h-4z" />
        </svg>
      </a>
    </header>

    <main class="workspace" :class="{ idle }">
      <canvas v-if="idle" ref="mapEl" class="px-map" aria-hidden="true"></canvas>
      <section class="command-row" aria-label="Domain lookup">
        <div>
          <div class="kicker">Passive reconnaissance workspace</div>
          <h1 class="page-title">Domain investigation</h1>
          <div class="page-subtitle">Inspect public DNS, email policy, registration, certificate, and network data.</div>
        </div>
        <form v-if="idle" class="search main-search has-cursor" @submit.prevent="investigate">
          <input :ref="setInput" v-model="domain" type="text" :readonly="streamStatus === 'loading'" placeholder="Enter a domain" aria-label="Domain name" autocomplete="off" autocapitalize="none" spellcheck="false" inputmode="url" autofocus />
          <span ref="cursorEl" class="cursor" aria-hidden="true"></span>
          <button type="submit" :disabled="streamStatus === 'loading'">{{ streamStatus === 'loading' ? 'LOOKING UP…' : 'LOOK UP' }}</button>
        </form>
        <div class="search-hint">PUBLIC SOURCES ONLY · NO ACTIVE PROBING</div>
      </section>
      <div v-if="notice" id="notice" role="status">{{ notice }}</div>
      <section v-if="!idle" id="results" aria-live="polite">
        <div class="subject-head">
          <div>
            <div class="subject-label">Subject</div>
            <h2 class="subject-name">{{ resultDomain }}</h2>
            <div class="subject-meta">{{ streamStatus === 'loading' ? 'Lookup in progress' : streamStatus === 'complete' ? 'Lookup complete' : 'Lookup interrupted' }}</div>
          </div>
        </div>
        <div v-if="domainNotFound" class="note" role="status">Domain not found.</div>

        <div class="layout">
          <div class="main-col">
            <section class="section">
              <div class="section-heading"><h2>Infrastructure</h2><span class="section-index" :class="sectionStatus('ip')">{{ sectionStatus('ip').toUpperCase() }}</span></div>
              <div v-if="sectionState('ip')?.message" class="note">{{ sectionState('ip').message }}</div>
              <Transition name="reveal">
                <div v-if="sectionState('ip')?.status === 'ok'" class="identity-block">
                  <div class="primary-fact">
                    <div class="fact-label">Public IP addresses</div>
                    <div v-if="sectionState('ip').data.addresses?.length" class="ip-address address-list">
                      <div v-for="address in sectionState('ip').data.addresses" :key="address">{{ address }}</div>
                    </div>
                    <div v-else class="fact-foot">No public IP addresses returned.</div>
                  </div>
                  <div class="secondary-facts">
                    <div v-for="network in sectionState('ip').data.networks || []" :key="`${network.asn}-${network.prefix}`" class="secondary-fact">
                      <div class="fact-label">{{ network.asn }}</div>
                      <strong>{{ network.name || 'ASN details' }}</strong>
                      <small>{{ network.prefix }} · {{ network.country }}</small>
                    </div>
                    <div v-if="!sectionState('ip').data.networks?.length" class="secondary-fact fact-foot">No ASN details returned.</div>
                  </div>
                </div>
              </Transition>
              <div v-if="sectionState('ip')" class="section-meta">{{ displayDate(sectionState('ip').fetched_at) }}</div>
            </section>

            <section class="section">
              <div class="section-heading"><h2>DNS record set</h2><span class="section-index" :class="sectionStatus('dns')">{{ sectionStatus('dns').toUpperCase() }}</span></div>
              <div v-if="sectionState('dns')?.message" class="note">{{ sectionState('dns').message }}</div>
              <Transition name="reveal">
                <div v-if="sectionState('dns')?.status === 'ok'" class="table-wrap">
                  <table>
                    <thead><tr><th>Type</th><th>Record value</th><th>TTL</th></tr></thead>
                    <tbody>
                      <tr v-for="(record, index) in sectionState('dns').data.records" :key="`${record.type}-${record.value}-${index}`">
                        <td class="record-type">{{ record.type }}</td><td class="value">{{ dnsRecordValue(record) }}</td><td class="ttl">{{ record.ttl }}</td>
                      </tr>
                      <tr v-if="!sectionState('dns').data.records?.length"><td colspan="3" class="fact-foot">No DNS records returned.</td></tr>
                    </tbody>
                  </table>
                </div>
              </Transition>
              <div v-if="sectionState('dns')" class="section-meta">{{ displayDate(sectionState('dns').fetched_at) }}</div>
            </section>
          </div>

          <aside class="side-col">
            <section class="side-section">
              <h2 class="side-heading">Registration profile <span class="section-index" :class="sectionStatus('rdap')">{{ sectionStatus('rdap').toUpperCase() }}</span></h2>
              <div v-if="sectionState('rdap')?.message" class="note">{{ sectionState('rdap').message }}</div>
              <Transition name="reveal">
                <dl v-if="sectionState('rdap')?.status === 'ok'" class="profile-list">
                  <div class="profile-row"><dt>Registrar</dt><dd>{{ sectionState('rdap').data.registrar || '—' }}</dd></div>
                  <div class="profile-row nameservers-row"><dt>Nameservers</dt><dd><span v-for="server in sectionState('rdap').data.nameservers || []" :key="server">{{ server }}</span><span v-if="!sectionState('rdap').data.nameservers?.length">—</span></dd></div>
                  <div class="profile-row"><dt>Created</dt><dd>{{ displayDate(sectionState('rdap').data.created) }}</dd></div>
                  <div class="profile-row"><dt>Updated</dt><dd>{{ displayDate(sectionState('rdap').data.updated) }}</dd></div>
                  <div class="profile-row"><dt>Expires</dt><dd>{{ displayDate(sectionState('rdap').data.expires) }}</dd></div>
                  <div v-for="status in sectionState('rdap').data.status || []" :key="status" class="profile-row"><dt>Status</dt><dd>{{ status }}</dd></div>
                </dl>
              </Transition>
              <div v-if="sectionState('rdap')" class="section-meta">{{ displayDate(sectionState('rdap').fetched_at) }}</div>
            </section>

            <section class="side-section">
              <h2 class="side-heading">Email security <span class="section-index" :class="sectionStatus('email_security')">{{ sectionStatus('email_security').toUpperCase() }}</span></h2>
              <div v-if="sectionState('email_security')?.message" class="note">{{ sectionState('email_security').message }}</div>
              <Transition name="reveal">
                <div v-if="sectionState('email_security')?.status === 'ok'">
                  <div v-for="kind in ['spf', 'dmarc']" :key="kind" class="email-policy">
                    <div class="email-policy-heading"><strong>{{ kind.toUpperCase() }}</strong><span :class="sectionState('email_security').data[kind].status">{{ sectionState('email_security').data[kind].status }}</span></div>
                    <p>{{ sectionState('email_security').data[kind].summary }}</p>
                    <div v-if="kind === 'dmarc' && sectionState('email_security').data.dmarc.policy" class="email-policy-value"><span>Policy</span><strong>{{ sectionState('email_security').data.dmarc.policy }}</strong></div>
                    <div v-for="record in sectionState('email_security').data[kind].records" :key="record" class="email-record">{{ record }}</div>
                  </div>
                  <div v-for="error in sectionState('email_security').data.errors || []" :key="error" class="note">{{ error }}</div>
                  <div class="fact-foot email-foot">Checks public DNS records only; a record’s presence doesn’t guarantee mail delivery.</div>
                </div>
              </Transition>
              <div v-if="sectionState('email_security')" class="section-meta">{{ displayDate(sectionState('email_security').fetched_at) }}</div>
            </section>

            <section class="side-section">
              <h2 class="side-heading">Subdomains <span class="section-index" :class="sectionStatus('subdomains')">{{ sectionStatus('subdomains').toUpperCase() }}</span></h2>
              <div v-if="sectionState('subdomains')?.message" class="note">{{ sectionState('subdomains').message }}</div>
              <Transition name="reveal">
                <div v-if="sectionState('subdomains')?.status === 'ok'">
                  <div class="fact-foot">{{ sectionState('subdomains').data.truncated ? '1000+ found (list truncated)' : `${sectionState('subdomains').data.count} found` }}</div>
                  <ul class="subdomain-list">
                    <li v-for="name in sectionState('subdomains').data.subdomains" :key="name">{{ name }}</li>
                  </ul>
                </div>
              </Transition>
              <div v-if="sectionState('subdomains')" class="section-meta">{{ displayDate(sectionState('subdomains').fetched_at) }}</div>
            </section>
          </aside>
        </div>
      </section>
    </main>
    <footer class="footer"><span class="footer-brand">OpenLookup</span></footer>
  </div>
</template>

<style>

:root{
  --bg:#0a0e0b;--surface:#101612;--surface-2:#151d17;--surface-3:#1a241c;
  --line:#29362c;--line-soft:#202b22;--text:#e7eee8;--muted:#a3b2a7;
  --dim:#8a9a8d;--acid:#a7e66b;--acid-dim:#6e9c4c;--amber:#d8b66b;
  --mono:"SFMono-Regular",Consolas,"Liberation Mono",monospace;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.brand-mark,.brand:hover .brand-mark{animation:none}.cursor{animation:none}}
body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,Arial,sans-serif;font-size:14px;line-height:1.5;min-height:100vh;overflow-x:clip}
a{color:inherit;text-decoration:none}
button,input{font:inherit}
button{cursor:pointer}
a:focus-visible,button:focus-visible{outline:2px solid var(--acid);outline-offset:2px}
.shell{width:100%;margin:0}
.topbar{height:68px;padding:0 32px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:28px}
.brand{display:flex;align-items:center;gap:11px;white-space:nowrap;font:700 23px "Pixelify Sans",sans-serif;letter-spacing:.2px}
.brand-mark{width:29px;height:29px;display:grid;place-items:center;background:var(--acid);color:#11180f;font:700 20px "Pixelify Sans";box-shadow:3px 3px 0 #4a6637;transition:transform .12s steps(2),box-shadow .12s steps(2);animation:markBlink 6s steps(1) infinite}
.brand:hover .brand-mark{transform:translate(-2px,-2px);box-shadow:5px 5px 0 #4a6637}
.brand:active .brand-mark{transform:translate(2px,2px);box-shadow:1px 1px 0 #4a6637}
@keyframes markBlink{0%,94%,98%,100%{background:var(--acid)}96%{background:#4a6637}}
.brand:hover .brand-mark{animation:markBounce .35s steps(3) 1}
@keyframes markBounce{0%{transform:translate(0,0)}40%{transform:translate(-2px,-6px)}100%{transform:translate(-2px,-2px)}}
.gh-link{display:inline-flex;align-items:center;justify-content:center;min-width:32px;min-height:32px;margin-left:auto;padding:2px;--gh-disc:#a3e35a;--gh-cat:#0a0e0b;transition:transform .12s ease,filter .12s ease}
.gh-link svg{display:block;image-rendering:pixelated}
.gh-disc{fill:var(--gh-disc)}
.gh-cat{fill:var(--gh-cat)}
.gh-link:hover,.gh-link:focus-visible{--gh-disc:#b6ee74;transform:translate(-1px,-1px);filter:drop-shadow(1px 1px 0 #4f7a2a)}
.gh-link:active{--gh-disc:#8fcf47;transform:translate(1px,1px);filter:none}
.gh-link:focus-visible{outline:2px solid #e8f1ea;outline-offset:3px}
.shell{display:flex;flex-direction:column;min-height:100vh}
.workspace{flex:1;width:min(1380px,100% - 64px);margin:0 auto;padding:31px 0 60px}
.workspace:not(.idle) .command-row{display:none}
#results{transition:opacity .2s ease}
#results.out{opacity:0}
.reveal-enter-active{transition:opacity .32s ease,transform .32s ease}
.reveal-enter-from{opacity:0;transform:translateY(7px)}
@media(prefers-reduced-motion:reduce){.reveal-enter-active{transition:none}.reveal-enter-from{transform:none}}
.command-row{transition:opacity .25s ease}
.command-row.fade{opacity:0}
.topbar{position:sticky;top:0;z-index:10;background:transparent}
.topbar::before{content:"";position:absolute;z-index:-1;inset:0;background:rgba(10,14,11,.72);border-bottom:1px solid var(--line);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px)}
.topbar{border-bottom:0}
.topbar .search{flex:0 1 440px;width:auto;height:38px;margin:0 0 0 auto}
.topbar .search button{padding:0 14px}
.workspace.idle{display:flex;flex-direction:column;justify-content:center;padding:0 0 9vh}
.idle .command-row{border-bottom:0;padding:0;gap:22px}
.idle .command-row>div:first-child{text-align:center}
.idle .page-title{font-size:clamp(30px,5vw,46px);margin:12px 0 9px}
.idle .page-subtitle{font-size:14px}
.idle .search{width:min(640px,100%);height:54px}
.idle .search input{font-size:14px}
.idle .search button{padding:0 24px;font-size:14px}
.idle .search-hint{margin-top:-4px}
.idle #results{display:none}
.workspace.idle{position:relative;overflow:hidden}
.workspace.idle>*:not(.px-map){position:relative;z-index:1}
.px-map{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);max-width:100%;opacity:.14;image-rendering:pixelated;pointer-events:none;z-index:0;-webkit-mask-image:radial-gradient(ellipse 60% 70% at 50% 50%,#000 40%,transparent 100%);mask-image:radial-gradient(ellipse 60% 70% at 50% 50%,#000 40%,transparent 100%)}
body{position:relative}
.shell{position:relative;z-index:1}
.idle #notice{text-align:center}
.command-row{display:grid;grid-template-columns:1fr;justify-items:center;gap:17px;padding:5px 0 27px;border-bottom:1px solid var(--line)}
.command-row>div:first-child{width:100%;text-align:left}
.kicker,.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:1.7px;color:var(--acid);font-weight:700}
.page-title{font:600 29px/1.15 "Pixelify Sans",sans-serif;margin:8px 0 5px}
.page-subtitle{color:var(--muted);font-size:12px;line-height:1.6}
.search{position:relative;display:flex;min-width:0;width:min(560px,100%);justify-self:center;border:1px solid #435441;border-radius:4px;overflow:hidden;background:#0d130f;height:42px}
.search:focus-within{border-color:var(--acid)}
.search input{min-width:0;flex:1;background:transparent;border:0;outline:0;color:var(--text);padding:0 13px;font-size:12px}
.search input::placeholder{color:var(--dim)}
.has-cursor input{caret-color:transparent}
.cursor{display:none;position:absolute;pointer-events:none;background:var(--acid);opacity:.85;animation:curBlink 1s steps(1) infinite}
@keyframes curBlink{0%,55%{opacity:.85}56%,100%{opacity:0}}
.search button{border:0;background:var(--acid);color:#172011;padding:0 17px;font:700 13px "Pixelify Sans",sans-serif;letter-spacing:.3px}
.search button:hover{background:#c0f28d}
.search-hint{text-align:center;color:var(--dim);font-size:11px;margin-top:-8px}
.subject-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;padding:26px 0 22px}
.subject-head>div:first-child{min-width:0}
.subject-label{font-size:11px;letter-spacing:1.4px;color:var(--muted);text-transform:uppercase;margin-bottom:8px}
.subject-name{font:600 clamp(27px,4vw,39px)/1 "Pixelify Sans",sans-serif;letter-spacing:.1px;overflow-wrap:anywhere}
.subject-name span{color:var(--acid)}
.subject-meta{display:flex;gap:18px;flex-wrap:wrap;margin-top:13px;color:var(--muted);font-size:11px}
.subject-meta b{font-weight:600;color:var(--text);margin-left:5px}
.address-list{font-size:clamp(18px,2vw,26px);line-height:1.5;overflow-wrap:anywhere}
.section-meta{margin-top:9px;color:var(--dim);font-size:10px;line-height:1.5}
.section-index{font-size:10px;text-transform:uppercase}
.section-index.ok{color:var(--acid)}
.section-index.error,.section-index.timeout{color:var(--amber)}
.section-index.loading{color:var(--muted)}
.subdomain-list{list-style:none;padding:0;margin:9px 0 0;max-height:360px;overflow:auto}
.subdomain-list li{padding:8px 0;border-bottom:1px solid var(--line-soft);font:11px var(--mono);overflow-wrap:anywhere}
.layout{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(280px,.85fr);gap:28px}
.main-col,.side-col{min-width:0}
.section{margin-bottom:27px}
.section-heading{display:flex;align-items:center;justify-content:space-between;gap:15px;border-bottom:1px solid var(--line);padding-bottom:10px;margin-bottom:0}
.section-heading h2{margin:0;font:600 16px "Pixelify Sans",sans-serif;letter-spacing:.15px}
.section-index{color:var(--dim);font:11px var(--mono)}
.identity-block{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(180px,.7fr);border-bottom:1px solid var(--line)}
.primary-fact{padding:19px 22px 20px 0;border-right:1px solid var(--line)}
.fact-label{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:1.1px}
.ip-address{font:600 clamp(15px,2vw,22px) var(--mono);letter-spacing:-1.2px;margin:13px 0 7px;color:var(--text)}
.fact-foot{color:var(--muted);font-size:11px}
.fact-foot .marker{color:var(--acid);margin-right:6px}
.secondary-facts{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
.secondary-fact{padding:18px 14px;border-bottom:1px solid var(--line-soft)}
.secondary-fact:nth-child(odd){border-right:1px solid var(--line-soft)}
.secondary-fact:nth-last-child(-n+2){border-bottom:0}
.secondary-fact strong,.secondary-fact small{overflow-wrap:anywhere}
.secondary-fact strong{display:block;font:600 17px var(--mono);margin-top:9px}
.secondary-fact small{display:block;color:var(--muted);font-size:11px;margin-top:4px}
.table-wrap{max-height:520px;overflow:auto}
table{border-collapse:collapse;width:100%;min-width:480px}
th{text-align:left;padding:12px 10px;color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:600;border-bottom:1px solid var(--line)}
thead th{position:sticky;top:0;background:var(--bg)}
td{padding:13px 10px;border-bottom:1px solid var(--line-soft);font-size:11px;vertical-align:top}
tr:last-child td{border-bottom:0}
td.value{font:11px var(--mono);color:#cbd7cd;overflow-wrap:anywhere;max-width:330px}
.record-type{font:600 11px var(--mono);color:var(--acid)}
.ttl,.source{font:11px var(--mono);color:var(--muted);white-space:nowrap}
.side-section{margin-bottom:25px}
.side-heading{font:600 15px "Pixelify Sans",sans-serif;padding-bottom:10px;border-bottom:1px solid var(--line);margin:0 0 2px}
.profile-list{margin:0}
.profile-row{display:grid;grid-template-columns:105px minmax(0,1fr);gap:10px;padding:12px 0;border-bottom:1px solid var(--line-soft);font-size:11px}
.profile-row dt{color:var(--muted)}
.profile-row dd{margin:0;text-align:right;overflow-wrap:anywhere;color:var(--text)}
.nameservers-row dd{display:grid;gap:4px;font:10px var(--mono)}
.email-policy{padding:13px 0;border-bottom:1px solid var(--line-soft)}
.email-policy-heading{display:flex;justify-content:space-between;gap:12px;font:11px var(--mono);text-transform:uppercase}
.email-policy-heading strong{color:var(--acid)}
.email-policy-heading span{color:var(--muted)}
.email-policy-heading span.found{color:var(--acid)}
.email-policy-heading span.missing,.email-policy-heading span.multiple,.email-policy-heading span.unavailable{color:var(--amber)}
.email-policy p{margin:7px 0;color:var(--muted);font-size:11px;line-height:1.55}
.email-policy-value{display:flex;justify-content:space-between;margin-top:8px;font:10px var(--mono);text-transform:uppercase;color:var(--muted)}
.email-policy-value strong{color:var(--text)}
.email-record{margin-top:6px;padding:8px;background:var(--surface);font:10px/1.5 var(--mono);overflow-wrap:anywhere;color:#cbd7cd}
.email-foot{margin-top:10px;line-height:1.5}
.note{border-left:2px solid var(--acid-dim);padding:10px 12px;background:#111812;color:var(--muted);font-size:11px;line-height:1.6;margin-top:14px}
.note b{color:var(--text);font-weight:600}
.footer{border-top:1px solid var(--line);padding:17px 32px 23px;display:flex;justify-content:space-between;gap:20px;color:var(--dim);font-size:11px}
.footer-brand{font-family:"Pixelify Sans",sans-serif;color:var(--muted)}
#notice{display:none;margin-top:12px;color:var(--amber);font-size:11px;line-height:1.5}
@media(max-width:850px){
 .workspace{width:min(100% - 40px,720px)}.topbar,.footer{padding-inline:20px}
 .layout{grid-template-columns:1fr;gap:8px}.side-col{display:grid;grid-template-columns:1fr 1fr;gap:25px}
}
@media(max-width:580px){
 .workspace{width:calc(100% - 30px);padding-top:23px}.topbar,.footer{padding-inline:15px}.topbar{height:60px;gap:14px}.brand{font-size:20px}.has-results .brand-text{display:none}.page-title{font-size:25px}.subject-head{padding:22px 0 18px}
 .px-map{max-width:none;transform:translate(-50%,-50%) scale(1.2)}
 .subject-meta{gap:8px 13px}
 .identity-block{grid-template-columns:1fr}.primary-fact{border-right:0;border-bottom:1px solid var(--line);padding:17px 0}
 .secondary-facts{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.secondary-fact{padding:14px 10px}
 .side-col{grid-template-columns:1fr}.footer{flex-direction:column;gap:7px}
}
.top-search{display:flex}
.command-row.fade{opacity:.55}
#notice{display:block}
@media(max-width:580px){.top-search{display:flex;flex:1;height:34px;min-width:0}.top-search input{padding:0 8px;font-size:10px}.top-search button{padding:0 8px;font-size:11px}.has-results .brand-text{display:none}}
</style>
