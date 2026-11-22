import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const sectionNames = [
  'ip',
  'dns',
  'dnssec',
  'rdap',
  'subdomains',
  'email_security',
]
const domainPattern = /^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]{2,59})$/

export function useDomainLookup(inputEl) {
  const domain = ref('')
  const resultDomain = ref('')
  const notice = ref('')
  const sections = ref({})
  const retries = ref({})
  const retryErrors = ref({})
  const streamStatus = ref('idle')
  const idle = computed(() => streamStatus.value === 'idle')
  let eventSource

  function normalize(value) {
    let candidate = value.trim().toLowerCase().replace(/^[a-z]+:\/\//, '').split(/[/?#]/)[0].replace(/\.$/, '')
    if (!candidate || !/^[\p{L}\p{N}.-]+$/u.test(candidate)) return ''
    try { candidate = new URL(`http://${candidate}`).hostname.toLowerCase() } catch { return '' }
    return candidate
  }

  function closeStream() {
    eventSource?.close()
    eventSource = null
  }

  function clearRetries() {
    for (const controller of Object.values(retries.value)) controller.abort()
    retries.value = {}
    retryErrors.value = {}
  }

  function updateLookupUrl(host) {
    const url = new URL(window.location.href)
    const currentUrl = `${url.pathname}${url.search}${url.hash}`
    url.searchParams.set('domain', host)
    const nextUrl = `${url.pathname}${url.search}${url.hash}`
    if (nextUrl !== currentUrl) window.history.pushState({ domain: host }, '', nextUrl)
  }

  function resetSearch(updateUrl = true) {
    clearRetries()
    closeStream()
    domain.value = ''
    resultDomain.value = ''
    sections.value = {}
    notice.value = ''
    streamStatus.value = 'idle'
    document.body.classList.remove('has-results')
    if (updateUrl) {
      const url = new URL(window.location.href)
      url.searchParams.delete('domain')
      window.history.replaceState(null, '', `${url.pathname}${url.search}${url.hash}`)
    }
  }

  async function investigate({ updateUrl: shouldUpdateUrl = true } = {}) {
    const host = normalize(domain.value)
    if (!host) {
      notice.value = 'Enter a domain to continue.'
      inputEl.value?.focus()
      return
    }
    if (!domainPattern.test(host)) {
      notice.value = `“${domain.value.trim()}” is not a valid domain.`
      inputEl.value?.focus()
      return
    }

    if (shouldUpdateUrl) updateLookupUrl(host)
    clearRetries()
    closeStream()
    sections.value = {}
    domain.value = host
    resultDomain.value = host
    notice.value = ''
    streamStatus.value = 'loading'
    document.body.classList.add('has-results')
    inputEl.value?.focus()

    eventSource = new EventSource(`/api/v1/domain/${encodeURIComponent(host)}/stream`)
    eventSource.addEventListener('section', event => {
      try {
        const result = JSON.parse(event.data)
        if (!sectionNames.includes(result.section)) return
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

  async function retrySection(key) {
    if (retries.value[key]) return
    const controller = new AbortController()
    retries.value[key] = controller
    retryErrors.value[key] = ''
    try {
      const url = `/api/v1/domain/${encodeURIComponent(resultDomain.value)}/sections/${key}`
      const response = await fetch(url, { signal: controller.signal })
      if (!response.ok) throw new Error('Retry request failed')
      const result = await response.json()
      if (controller.signal.aborted) return
      if (result.section !== key) throw new Error('Unexpected section')
      if (sections.value[key]?.status === 'ok' && result.status !== 'ok') {
        retryErrors.value[key] = result.message || 'Retry failed.'
      } else {
        sections.value[key] = result
      }
    } catch {
      if (!controller.signal.aborted) retryErrors.value[key] = 'Retry request failed. Try again.'
    } finally {
      if (!controller.signal.aborted) delete retries.value[key]
    }
  }

  function handlePopState() {
    const sharedDomain = new URLSearchParams(window.location.search).get('domain')
    if (!sharedDomain) {
      resetSearch(false)
      return
    }
    domain.value = sharedDomain
    void investigate({ updateUrl: false })
  }

  onMounted(() => {
    window.addEventListener('popstate', handlePopState)
    const sharedDomain = new URLSearchParams(window.location.search).get('domain')
    if (sharedDomain) {
      domain.value = sharedDomain
      void investigate({ updateUrl: false })
    }
  })

  onBeforeUnmount(() => {
    clearRetries()
    closeStream()
    window.removeEventListener('popstate', handlePopState)
  })

  return {
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
  }
}
