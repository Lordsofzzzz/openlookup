const domainPattern = /^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]{2,59})$/

function normalizeDomain(value) {
  let candidate = value.trim().toLowerCase().replace(/^[a-z]+:\/\//, '').split(/[/?#]/)[0].replace(/\.$/, '')
  if (!candidate || !/^[\p{L}\p{N}.-]+$/u.test(candidate)) return ''
  try { candidate = new URL(`http://${candidate}`).hostname.toLowerCase() } catch { return '' }
  return candidate
}

export function createDomainLookup({ network, navigation, isKnownSection, onNavigate }) {
  let state = {
    domain: '',
    resultDomain: '',
    notice: '',
    sections: {},
    retries: {},
    retryErrors: {},
    streamStatus: 'idle',
  }
  const listeners = new Set()
  const retryControllers = new Map()
  let streamCloser
  let removeNavigationListener
  let generation = 0
  let started = false

  function publish(patch) {
    state = { ...state, ...patch }
    for (const listener of listeners) listener(state)
  }

  function closeStream() {
    streamCloser?.()
    streamCloser = null
  }

  function clearRetries() {
    for (const controller of retryControllers.values()) controller.abort()
    retryControllers.clear()
    publish({ retries: {}, retryErrors: {} })
  }

  function resetSearch({ updateUrl = true } = {}) {
    generation++
    clearRetries()
    closeStream()
    if (updateUrl) navigation.clearDomain()
    publish({
      domain: '',
      resultDomain: '',
      sections: {},
      notice: '',
      streamStatus: 'idle',
    })
  }

  function investigate(value = state.domain, { updateUrl = true } = {}) {
    const host = normalizeDomain(value)
    if (!host) {
      publish({ notice: 'Enter a domain to continue.' })
      return { valid: false }
    }
    if (!domainPattern.test(host)) {
      publish({ notice: `“${value.trim()}” is not a valid domain.` })
      return { valid: false }
    }

    if (updateUrl) navigation.setDomain(host)
    clearRetries()
    closeStream()
    const requestGeneration = ++generation
    publish({
      domain: host,
      resultDomain: host,
      sections: {},
      notice: '',
      streamStatus: 'loading',
    })

    function handleSection(rawData) {
      if (requestGeneration !== generation) return
      try {
        const result = JSON.parse(rawData)
        if (!isKnownSection(result.section)) return
        publish({ sections: { ...state.sections, [result.section]: result } })
      } catch {
        publish({ notice: 'The API sent an unreadable section response.' })
      }
    }

    function handleDone() {
      if (requestGeneration !== generation) return
      publish({ streamStatus: 'complete' })
      closeStream()
    }

    function handleError() {
      if (requestGeneration !== generation || state.streamStatus !== 'loading') return
      publish({
        streamStatus: 'error',
        notice: 'Could not connect to the lookup API. Check that the backend is running.',
      })
      closeStream()
    }

    try {
      const closer = network.openStream(host, {
        onSection: handleSection,
        onDone: handleDone,
        onError: handleError,
      })
      if (requestGeneration !== generation || state.streamStatus !== 'loading') closer()
      else streamCloser = closer
    } catch {
      handleError()
    }

    return { valid: true, host }
  }

  async function retrySection(key) {
    if (retryControllers.has(key) || !state.resultDomain) return

    const controller = new AbortController()
    const requestGeneration = generation
    retryControllers.set(key, controller)
    publish({
      retries: { ...state.retries, [key]: true },
      retryErrors: { ...state.retryErrors, [key]: '' },
    })

    try {
      const result = await network.retrySection(state.resultDomain, key, controller.signal)
      if (controller.signal.aborted || requestGeneration !== generation) return
      if (result.section !== key) throw new Error('Unexpected section')
      if (state.sections[key]?.status === 'ok' && result.status !== 'ok') {
        publish({ retryErrors: { ...state.retryErrors, [key]: result.message || 'Retry failed.' } })
      } else {
        publish({ sections: { ...state.sections, [key]: result } })
      }
    } catch {
      if (!controller.signal.aborted && requestGeneration === generation) {
        publish({ retryErrors: { ...state.retryErrors, [key]: 'Retry request failed. Try again.' } })
      }
    } finally {
      if (retryControllers.get(key) === controller) {
        retryControllers.delete(key)
        if (requestGeneration === generation) {
          const retries = { ...state.retries }
          delete retries[key]
          publish({ retries })
        }
      }
    }
  }

  function handleNavigation() {
    const sharedDomain = navigation.getDomain()
    onNavigate?.(Boolean(sharedDomain))
    if (!sharedDomain) {
      resetSearch({ updateUrl: false })
      return
    }
    publish({ domain: sharedDomain })
    investigate(sharedDomain, { updateUrl: false })
  }

  function start() {
    if (started) return false
    started = true
    removeNavigationListener = navigation.subscribe(handleNavigation)
    const sharedDomain = navigation.getDomain()
    onNavigate?.(Boolean(sharedDomain))
    if (sharedDomain) {
      publish({ domain: sharedDomain })
      investigate(sharedDomain, { updateUrl: false })
      return true
    }
    return false
  }

  function stop() {
    started = false
    removeNavigationListener?.()
    removeNavigationListener = null
    generation++
    clearRetries()
    closeStream()
  }

  function setDomain(value) {
    if (value !== state.domain) publish({ domain: value })
  }

  return {
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    setDomain,
    resetSearch,
    investigate,
    retrySection,
    start,
    stop,
  }
}
