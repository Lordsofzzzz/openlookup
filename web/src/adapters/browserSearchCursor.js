export function createBrowserSearchCursorPlatform() {
  return {
    findElements(container) {
      return {
        input: container.querySelector('input'),
        cursor: container.querySelector('.cursor'),
      }
    },

    measure(input) {
      if (input.readOnly || document.activeElement !== input || input.selectionStart !== input.selectionEnd) return null

      const styles = getComputedStyle(input)
      const canvas = document.createElement('canvas')
      const context = canvas.getContext('2d')
      if (!context) return null
      context.font = `${styles.fontStyle} ${styles.fontWeight} ${styles.fontSize} ${styles.fontFamily}`

      return {
        inputLeft: input.offsetLeft,
        inputTop: input.offsetTop,
        inputHeight: input.offsetHeight,
        clientWidth: input.clientWidth,
        paddingLeft: parseFloat(styles.paddingLeft),
        scrollLeft: input.scrollLeft,
        fontSize: parseFloat(styles.fontSize),
        textWidth: context.measureText(input.value.slice(0, input.selectionStart || 0)).width,
        zeroWidth: context.measureText('0').width,
      }
    },

    show(cursor, position) {
      cursor.style.display = 'block'
      cursor.style.left = `${position.left}px`
      cursor.style.top = `${position.top}px`
      cursor.style.width = `${position.width}px`
      cursor.style.height = `${position.height}px`
    },

    hide(cursor) {
      cursor.style.display = 'none'
    },

    subscribe(input, update) {
      const timers = new Set()
      const schedule = (callback, delay) => {
        const timer = setTimeout(() => {
          timers.delete(timer)
          callback()
        }, delay)
        timers.add(timer)
      }
      const delayedUpdate = () => schedule(update, 0)
      const events = ['input', 'keyup', 'keydown', 'click', 'focus', 'blur', 'select', 'scroll']
      events.forEach(event => input.addEventListener(event, delayedUpdate))
      window.addEventListener('resize', update)
      document.addEventListener('selectionchange', update)
      schedule(update, 0)
      schedule(update, 50)

      return () => {
        events.forEach(event => input.removeEventListener(event, delayedUpdate))
        window.removeEventListener('resize', update)
        document.removeEventListener('selectionchange', update)
        for (const timer of timers) clearTimeout(timer)
        timers.clear()
      }
    },
  }
}
