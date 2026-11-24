import { type Ref, onBeforeUnmount } from 'vue'

export function useSearchCursor(inputEl: Ref<HTMLInputElement | null>, cursorEl: Ref<HTMLElement | null>) {
  let removeInputListeners: (() => void) | null = null

  function placeCursor() {
    const input = inputEl.value
    const cursor = cursorEl.value
    if (!input || !cursor || input.readOnly || document.activeElement !== input || input.selectionStart !== input.selectionEnd) {
      if (cursor) cursor.style.display = 'none'
      return
    }
    const styles = getComputedStyle(input)
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')
    if (!context) return
    context.font = `${styles.fontStyle} ${styles.fontWeight} ${styles.fontSize} ${styles.fontFamily}`
    const x = input.offsetLeft + parseFloat(styles.paddingLeft) + context.measureText(input.value.slice(0, input.selectionStart || 0)).width - input.scrollLeft
    const height = Math.round(parseFloat(styles.fontSize) * 1.3)
    const width = Math.max(6, Math.round(context.measureText('0').width * 0.75))
    if (x < input.offsetLeft || x > input.offsetLeft + input.clientWidth - width) {
      cursor.style.display = 'none'
      return
    }
    cursor.style.display = 'block'
    cursor.style.left = `${Math.round(x)}px`
    cursor.style.top = `${Math.round(input.offsetTop + (input.offsetHeight - height) / 2)}px`
    cursor.style.width = `${width}px`
    cursor.style.height = `${height}px`
  }

  function setInput(node: unknown) {
    const element = node instanceof HTMLInputElement ? node : null
    removeInputListeners?.()
    inputEl.value = element
    if (!element) return
    const updateCursor = () => setTimeout(placeCursor, 0)
    const events = ['input', 'keyup', 'keydown', 'click', 'focus', 'blur', 'select', 'scroll']
    events.forEach(event => element.addEventListener(event, updateCursor))
    window.addEventListener('resize', placeCursor)
    removeInputListeners = () => {
      events.forEach(event => element.removeEventListener(event, updateCursor))
      window.removeEventListener('resize', placeCursor)
      removeInputListeners = null
    }
    setTimeout(placeCursor, 50)
  }

  function setCursor(node: unknown) {
    const element = node instanceof HTMLElement ? node : null
    cursorEl.value = element
    placeCursor()
  }

  document.addEventListener('selectionchange', placeCursor)
  onBeforeUnmount(() => {
    removeInputListeners?.()
    document.removeEventListener('selectionchange', placeCursor)
  })

  return { setInput, setCursor, placeCursor }
}
