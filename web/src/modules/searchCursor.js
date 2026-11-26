export function createSearchCursor(platform) {
  let detachCurrent

  function attach(container) {
    detachCurrent?.()
    detachCurrent = null
    if (!container) return

    const { input, cursor } = platform.findElements(container)
    if (!input || !cursor) return

    function placeCursor() {
      const measurement = platform.measure(input)
      if (!measurement) {
        platform.hide(cursor)
        return
      }

      const x = measurement.inputLeft + measurement.paddingLeft + measurement.textWidth - measurement.scrollLeft
      const height = Math.round(measurement.fontSize * 1.3)
      const width = Math.max(6, Math.round(measurement.zeroWidth * 0.75))
      if (x < measurement.inputLeft || x > measurement.inputLeft + measurement.clientWidth - width) {
        platform.hide(cursor)
        return
      }

      platform.show(cursor, {
        left: Math.round(x),
        top: Math.round(measurement.inputTop + (measurement.inputHeight - height) / 2),
        width,
        height,
      })
    }

    detachCurrent = platform.subscribe(input, placeCursor)
  }

  function detach() {
    detachCurrent?.()
    detachCurrent = null
  }

  return { attach, detach }
}
