const columns = 72
const land = [
  [[14, 21], [24, 31]], [[10, 22], [23, 33], [50, 58], [62, 68]],
  [[5, 22], [24, 33], [37, 42], [44, 71]], [[2, 24], [26, 33], [34, 42], [43, 71]],
  [[4, 24], [28, 30], [34, 42], [43, 71]], [[8, 26], [34, 36], [38, 72]],
  [[8, 26], [36, 71]], [[8, 25], [36, 44], [45, 60], [62, 70]],
  [[9, 25], [34, 47], [48, 70]], [[10, 24], [34, 48], [50, 69]],
  [[12, 23], [33, 48], [49, 68]], [[14, 22], [33, 50], [51, 67]],
  [[15, 21], [33, 52], [53, 56], [58, 66]], [[16, 23], [33, 52], [53, 56], [58, 62]],
  [[19, 28], [34, 50], [55, 56], [59, 60]], [[20, 30], [36, 48], [56, 64]],
  [[19, 31], [38, 47], [55, 57], [63, 66]], [[19, 31], [38, 48], [56, 59], [64, 67]],
  [[20, 31], [39, 48], [60, 64]], [[20, 30], [39, 48], [59, 66]],
  [[20, 29], [38, 47], [58, 67]], [[20, 29], [39, 46], [58, 67]],
  [[21, 29], [40, 46], [58, 67]], [[21, 28], [41, 45], [59, 66]],
  [[21, 27], [63, 65], [70, 71]], [[22, 27], [70, 71]], [[22, 26]], [[23, 25]],
]

export function drawPixelMap(canvas: HTMLCanvasElement | null) {
  if (!canvas) return
  const width = canvas.parentElement?.clientWidth || window.innerWidth
  const cell = Math.max(6, Math.floor(Math.min(width, 1200) / columns))
  const dot = Math.max(2, cell - 3)
  canvas.width = columns * cell
  canvas.height = land.length * cell
  const context = canvas.getContext('2d')
  if (!context) return
  context.imageSmoothingEnabled = false
  land.forEach((spans, y) => {
    for (const [from, to] of spans) {
      for (let x = from; x <= Math.min(to, columns - 1); x++) {
        context.fillStyle = `rgba(163,227,90,${0.55 + ((x * 7 + y * 13) % 5) * 0.1})`
        context.fillRect(x * cell, y * cell, dot, dot)
      }
    }
  })
}
