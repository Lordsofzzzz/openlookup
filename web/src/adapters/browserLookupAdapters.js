export function createBrowserLookupAdapters() {
  const network = {
    openStream(host, { onSection, onDone, onError }) {
      const eventSource = new EventSource(`/api/v1/domain/${encodeURIComponent(host)}/stream`)
      eventSource.addEventListener('section', event => onSection(event.data))
      eventSource.addEventListener('done', onDone)
      eventSource.onerror = onError
      return () => eventSource.close()
    },

    async retrySection(host, key, signal) {
      const url = `/api/v1/domain/${encodeURIComponent(host)}/sections/${key}`
      const response = await fetch(url, { signal })
      if (!response.ok) throw new Error('Retry request failed')
      return response.json()
    },
  }

  const navigation = {
    getDomain() {
      return new URLSearchParams(window.location.search).get('domain')
    },

    setDomain(host) {
      const url = new URL(window.location.href)
      const currentUrl = `${url.pathname}${url.search}${url.hash}`
      url.searchParams.set('domain', host)
      const nextUrl = `${url.pathname}${url.search}${url.hash}`
      if (nextUrl !== currentUrl) window.history.pushState({ domain: host }, '', nextUrl)
    },

    clearDomain() {
      const url = new URL(window.location.href)
      url.searchParams.delete('domain')
      window.history.replaceState(null, '', `${url.pathname}${url.search}${url.hash}`)
    },

    subscribe(listener) {
      window.addEventListener('popstate', listener)
      return () => window.removeEventListener('popstate', listener)
    },
  }

  return { network, navigation }
}
