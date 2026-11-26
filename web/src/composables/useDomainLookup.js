import { computed, onBeforeUnmount, onMounted, shallowRef, watch } from 'vue'

import { createBrowserLookupAdapters } from '../adapters/browserLookupAdapters.js'
import { createDomainLookup } from '../modules/domainLookup.js'
import { lookupSectionNames } from '../sections/registry.js'

export function useDomainLookup(inputEl) {
  const adapters = createBrowserLookupAdapters()
  const lookup = createDomainLookup({
    ...adapters,
    isKnownSection: section => lookupSectionNames.includes(section),
    onNavigate: hasDomain => {
      if (hasDomain) inputEl.value?.focus()
    },
  })
  const state = shallowRef(lookup.getState())
  const unsubscribe = lookup.subscribe(nextState => {
    state.value = nextState
  })

  const domain = computed({
    get: () => state.value.domain,
    set: lookup.setDomain,
  })
  const resultDomain = computed(() => state.value.resultDomain)
  const notice = computed(() => state.value.notice)
  const sections = computed(() => state.value.sections)
  const retries = computed(() => state.value.retries)
  const retryErrors = computed(() => state.value.retryErrors)
  const streamStatus = computed(() => state.value.streamStatus)
  const idle = computed(() => streamStatus.value === 'idle')

  function resetSearch(updateUrl = true) {
    lookup.resetSearch({ updateUrl })
  }

  async function investigate(options) {
    lookup.investigate(domain.value, options)
    inputEl.value?.focus()
  }

  watch(streamStatus, status => {
    document.body.classList.toggle('has-results', status !== 'idle')
  }, { flush: 'sync' })

  onMounted(() => {
    lookup.start()
  })

  onBeforeUnmount(() => {
    unsubscribe()
    lookup.stop()
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
    retrySection: lookup.retrySection,
  }
}
