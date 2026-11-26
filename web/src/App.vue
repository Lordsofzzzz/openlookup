<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import DomainSearch from './components/DomainSearch.vue'
import ResultCards from './ResultCards.vue'
import { useDomainLookup } from './composables/useDomainLookup.js'
import { useSearchCursor } from './composables/useSearchCursor.js'
import { drawPixelMap } from './utils/pixelMap.js'

const inputEl = ref(null)
const {
  domain,
  resultDomain,
  notice,
  sections,
  retries,
  retryErrors,
  streamStatus,
  idle,
  resetSearch,
  investigate,
  retrySection,
} = useDomainLookup(inputEl)
const mapEl = ref(null)
const cursorElement = ref(null)
let mapObserver
function sectionStatus(key) {
  return sections.value[key]?.status ?? (streamStatus.value === 'loading' ? 'loading' : 'waiting')
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
const { setInput, setCursor } = useSearchCursor(inputEl, cursorElement)
function drawMap() {
  drawPixelMap(mapEl.value)
}
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
onBeforeUnmount(() => {
  mapObserver?.disconnect()
})
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <a class="brand" href="#" aria-label="OpenLookup home" @click.prevent="resetSearch()"><span class="brand-mark"><svg width="18" height="18" viewBox="0 0 9 9" shape-rendering="crispEdges" aria-hidden="true"><rect x="1" y="0" width="4" height="1" fill="#11180f"/><rect x="0" y="1" width="1" height="1" fill="#11180f"/><rect x="5" y="1" width="1" height="1" fill="#11180f"/><rect x="0" y="2" width="1" height="1" fill="#11180f"/><rect x="5" y="2" width="1" height="1" fill="#11180f"/><rect x="2" y="2" width="2" height="1" fill="#4a6637"/><rect x="0" y="3" width="1" height="1" fill="#11180f"/><rect x="5" y="3" width="1" height="1" fill="#11180f"/><rect x="2" y="3" width="1" height="1" fill="#4a6637"/><rect x="0" y="4" width="1" height="1" fill="#11180f"/><rect x="5" y="4" width="1" height="1" fill="#11180f"/><rect x="1" y="5" width="4" height="1" fill="#11180f"/><rect x="6" y="5" width="1" height="1" fill="#11180f"/><rect x="6" y="6" width="2" height="1" fill="#11180f"/><rect x="7" y="7" width="2" height="1" fill="#11180f"/><rect x="8" y="8" width="1" height="1" fill="#11180f"/></svg></span><span class="brand-text">OpenLookup</span></a>
      <DomainSearch variant="top" v-model="domain" :idle="idle" :stream-status="streamStatus" :set-input="setInput" :set-cursor="setCursor" @investigate="investigate()" />
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
        <DomainSearch variant="main" v-model="domain" :idle="idle" :stream-status="streamStatus" :set-input="setInput" :set-cursor="setCursor" @investigate="investigate()" />
          <p class="note">We share the domain with lookup providers, including WebTrustScore.</p>
        <div class="search-hint">PUBLIC SOURCES ONLY · NO ACTIVE PROBING</div>
      </section>
      <div v-if="notice" id="notice" role="status">{{ notice }}</div>
      <section v-if="!idle" id="results" aria-live="polite">
        <div class="subject-head">
          <div>
            <div class="subject-label">Subject</div>
            <h2 class="subject-name">{{ resultDomain }}</h2>
          </div>
        </div>
        <ResultCards
          :sections="sections"
          :retries="retries"
          :retry-errors="retryErrors"
          :display-date="displayDate"
          :dns-record-value="dnsRecordValue"
          :status-for="sectionStatus"
          @retry="retrySection"
        />
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
.address-entry{margin:10px 0}
.address-value{display:block}
.address-asn{display:flex;align-items:baseline;gap:8px;margin:1px 0 0 2px;font:10px/1.5 var(--mono);letter-spacing:0;overflow-wrap:anywhere}
.asn-number{color:#8ecfc1;white-space:nowrap}
.asn-name{color:var(--muted);font-weight:400}
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
.secondary-facts{min-width:0}
.network-ranges-heading{padding:17px 14px 7px;color:var(--muted);font:600 12px "Pixelify Sans",sans-serif}
.secondary-fact{padding:11px 14px;border-bottom:1px solid var(--line-soft)}
.secondary-fact:last-child{border-bottom:0}
.secondary-fact strong{display:block;color:var(--text);font:600 12px/1.5 var(--mono);overflow-wrap:anywhere}
.network-range-meta{display:flex;flex-wrap:wrap;gap:3px 9px;margin-top:4px;color:var(--dim);font:10px/1.4 var(--mono)}
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
.side-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;font:600 15px "Pixelify Sans",sans-serif;padding-bottom:10px;border-bottom:1px solid var(--line);margin:0 0 2px}
.profile-list{margin:0}
.dnssec-result{padding:13px 0;border-bottom:1px solid var(--line-soft)}
.dnssec-state{display:inline-block;padding:3px 6px;border:1px solid var(--line);font:10px var(--mono);text-transform:uppercase;letter-spacing:.4px;color:var(--muted)}
.dnssec-state.secure{border-color:rgba(167,230,107,.4);color:var(--acid)}
.dnssec-state.bogus,.dnssec-state.unverified,.dnssec-state.indeterminate,.dnssec-state.not_found{border-color:rgba(216,182,107,.4);color:var(--amber)}
.dnssec-result p{margin:8px 0 0;color:var(--muted);font-size:11px;line-height:1.55}
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
.exposure-host{padding:14px 0;border-bottom:1px solid var(--line-soft)}
.exposure-head{display:grid;gap:4px}
.exposure-ip{color:var(--text);font:600 13px var(--mono);overflow-wrap:anywhere}
.exposure-tags{color:var(--acid);font:9px var(--mono);text-transform:uppercase;letter-spacing:.5px}
.exposure-details{margin:10px 0 0;padding-left:11px}
.exposure-row{display:grid;grid-template-columns:88px minmax(0,1fr);gap:8px;padding:4px 0;align-items:start}
.exposure-label{color:#a4b89e;font:9px var(--mono);letter-spacing:.35px}
.exposure-values{color:#cbd7cd;font:10px/1.6 var(--mono);overflow-wrap:anywhere}
.exposure-values.ports{display:flex;flex-wrap:wrap;gap:4px 16px;color:#8ecfc1}
.exposure-line{display:block}
.exposure-more{flex-basis:100%;margin-top:4px}
.exposure-more summary{color:var(--amber);cursor:pointer;width:fit-content}
.exposure-more summary:hover{color:var(--text)}
.exposure-hide,.exposure-more[open] .exposure-show{display:none}
.exposure-more[open] .exposure-hide{display:inline}
.exposure-extra{display:flex;flex-wrap:wrap;gap:5px 10px;margin-top:8px}
.exposure-vulns .exposure-values{display:flex;flex-wrap:wrap;gap:5px 10px}
.exposure-vulns .exposure-label{color:var(--amber)}
.exposure-vulns a{color:var(--amber);text-decoration:none;border-bottom:1px dotted currentColor}
.exposure-vulns a:hover,.exposure-vulns a:focus-visible{color:var(--text)}
.exposure-empty{margin:8px 0 0;color:var(--dim);font-size:10px}
.exposure-foot{margin-top:10px;line-height:1.5}
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
 .exposure-details{margin-left:0;padding-left:8px}
 .exposure-row{grid-template-columns:1fr;gap:2px}
 .exposure-empty{margin-left:0}
 .workspace{width:calc(100% - 30px);padding-top:23px}.topbar,.footer{padding-inline:15px}.topbar{height:60px;gap:14px}.brand{font-size:20px}.has-results .brand-text{display:none}.page-title{font-size:25px}.subject-head{padding:22px 0 18px}
 .px-map{max-width:none;transform:translate(-50%,-50%) scale(1.2)}
 .subject-meta{gap:8px 13px}
 .identity-block{grid-template-columns:1fr}.primary-fact{border-right:0;border-bottom:1px solid var(--line);padding:17px 0}
 .network-ranges-heading{padding:13px 10px 6px}.secondary-fact{padding:10px}
 .side-col{grid-template-columns:1fr}.footer{flex-direction:column;gap:7px}
}
.top-search{display:flex}
.command-row.fade{opacity:.55}
#notice{display:block}
@media(max-width:580px){.top-search{display:flex;flex:1;height:34px;min-width:0}.top-search input{padding:0 8px;font-size:10px}.top-search button{padding:0 8px;font-size:11px}.has-results .brand-text{display:none}}
</style>
