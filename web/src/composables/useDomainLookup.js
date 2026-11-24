import { onBeforeUnmount, onMounted, reactive } from 'vue'

const sectionNames = [
  'ip',
  'dns',
  'dnssec',
  'rdap',
  'subdomains',
  'exposure',
  'email_security',
]
const domainPattern = /^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]{2,59})$/

function createBrowserAdapters() {
  return {
    createAbortController: () => new AbortController(),
    createEventSource: url => new EventSource(url),
    fetch: (url, options) => fetch(url, options),
    currentUrl: () => window.location.href,
    pushState: (state, url) => window.history.pushState(state, '', url),
    replaceState: (state, url) => window.history.replaceState(state, '', url),
    addPopStateListener: listener => window.addEventListener('popstate', listener),
    removePopStateListener: listener => window.removeEventListener('popstate', listener),
    setHasResults: value => document.body.classList.toggle('has-results', value),
  }
}

export function useDomainLookup({ focusSearch, browser = createBrowserAdapters() } = {}) {
  const state = reactive({
    domain: '',
    resultDomain: '',
    notice: '',
    sections: {},
    retries: {},
    retryErrors: {},
    streamStatus: 'idle',
  })
  const retryControllers = new Map()
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
    for (const controller of retryControllers.values()) controller.abort()
    retryControllers.clear()
    state.retries = {}
    state.retryErrors = {}
  }

  function updateLookupUrl(host) {
    const url = new URL(browser.currentUrl())
    const currentUrl = `${url.pathname}${url.search}${url.hash}`
    url.searchParams.set('domain', host)
    const nextUrl = `${url.pathname}${url.search}${url.hash}`
    if (nextUrl !== currentUrl) browser.pushState({ domain: host }, nextUrl)
  }

  function resetSearch(updateUrl = true) {
    clearRetries()
    closeStream()
    state.domain = ''
    state.resultDomain = ''
    state.sections = {}
    state.notice = ''
    state.streamStatus = 'idle'
    browser.setHasResults(false)
    if (updateUrl) {
      const url = new URL(browser.currentUrl())
      url.searchParams.delete('domain')
      browser.replaceState(null, `${url.pathname}${url.search}${url.hash}`)
    }
  }

  async function investigate({ updateUrl: shouldUpdateUrl = true } = {}) {
    const host = normalize(state.domain)
    if (!host) {
      state.notice = 'Enter a domain to continue.'
      focusSearch?.()
      return
    }
    if (!domainPattern.test(host)) {
      state.notice = `“${state.domain.trim()}” is not a valid domain.`
      focusSearch?.()
      return
    }

    if (shouldUpdateUrl) updateLookupUrl(host)
    clearRetries()
    closeStream()
    state.sections = {}
    state.domain = host
    state.resultDomain = host
    state.notice = ''
    state.streamStatus = 'loading'
    browser.setHasResults(true)
    focusSearch?.()

    eventSource = browser.createEventSource(`/api/v1/domain/${encodeURIComponent(host)}/stream`)
    eventSource.addEventListener('section', event => {
      try {
        const result = JSON.parse(event.data)
        if (!sectionNames.includes(result.section)) return
        state.sections = { ...state.sections, [result.section]: result }
      } catch {
        state.notice = 'The API sent an unreadable section response.'
      }
    })
    eventSource.addEventListener('done', () => {
      state.streamStatus = 'complete'
      closeStream()
    })
    eventSource.onerror = () => {
      if (state.streamStatus !== 'loading') return
      state.streamStatus = 'error'
      state.notice = 'Could not connect to the lookup API. Check that the backend is running.'
      closeStream()
    }
  }

  async function retrySection(key) {
    if (state.retries[key]) return
    const controller = browser.createAbortController()
    retryControllers.set(key, controller)
    state.retries[key] = true
    state.retryErrors[key] = ''
    try {
      const url = `/api/v1/domain/${encodeURIComponent(state.resultDomain)}/sections/${key}`
      const response = await browser.fetch(url, { signal: controller.signal })
      if (!response.ok) throw new Error('Retry request failed')
      const result = await response.json()
      if (controller.signal.aborted) return
      if (result.section !== key) throw new Error('Unexpected section')
      if (state.sections[key]?.status === 'ok' && result.status !== 'ok') {
        state.retryErrors[key] = result.message || 'Retry failed.'
      } else {
        state.sections[key] = result
      }
    } catch {
      if (!controller.signal.aborted) state.retryErrors[key] = 'Retry request failed. Try again.'
    } finally {
      if (!controller.signal.aborted) {
        delete state.retries[key]
        retryControllers.delete(key)
      }
    }
  }

  function handlePopState() {
    const sharedDomain = new URL(browser.currentUrl()).searchParams.get('domain')
    if (!sharedDomain) {
      resetSearch(false)
      return
    }
    state.domain = sharedDomain
    void investigate({ updateUrl: false })
  }

  onMounted(() => {
    browser.addPopStateListener(handlePopState)
    const sharedDomain = new URL(browser.currentUrl()).searchParams.get('domain')
    if (sharedDomain) {
      state.domain = sharedDomain
      void investigate({ updateUrl: false })
    }
  })

  onBeforeUnmount(() => {
    clearRetries()
    closeStream()
    browser.removePopStateListener(handlePopState)
  })

  return { state, resetSearch, investigate, retrySection }
}
