import { ref, onMounted, onUnmounted } from 'vue'

export function usePerformance() {
  const fps = ref(0)
  const memory = ref(null)
  let frameCount = 0
  let lastTime = performance.now()
  let animationFrameId = null

  const measureFPS = () => {
    const currentTime = performance.now()
    frameCount++

    if (currentTime - lastTime >= 1000) {
      fps.value = Math.round(frameCount * 1000 / (currentTime - lastTime))
      frameCount = 0
      lastTime = currentTime
    }

    animationFrameId = requestAnimationFrame(measureFPS)
  }

  const measureMemory = () => {
    if (performance.memory) {
      memory.value = {
        used: Math.round(performance.memory.usedJSHeapSize / 1048576),
        total: Math.round(performance.memory.totalJSHeapSize / 1048576),
        limit: Math.round(performance.memory.jsHeapSizeLimit / 1048576)
      }
    }
  }

  onMounted(() => {
    animationFrameId = requestAnimationFrame(measureFPS)
    setInterval(measureMemory, 1000)
  })

  onUnmounted(() => {
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId)
    }
  })

  return {
    fps,
    memory
  }
} 