import { onBeforeUnmount } from 'vue'

import { createBrowserSearchCursorPlatform } from '../adapters/browserSearchCursor.js'
import { createSearchCursor } from '../modules/searchCursor.js'

export function useSearchCursor(inputEl) {
  const cursor = createSearchCursor(createBrowserSearchCursorPlatform())

  function setContainer(container) {
    inputEl.value = container?.querySelector('input') || null
    cursor.attach(container)
  }

  onBeforeUnmount(() => {
    inputEl.value = null
    cursor.detach()
  })

  return { setContainer }
}
