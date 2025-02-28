import { onMounted, onUnmounted, watch, ref } from 'vue'

export function useInterval(callback, delay) {
  const savedCallback = ref(callback)
  let intervalId = null

  // 当回调函数改变时更新保存的回调
  watch(() => callback, (newCallback) => {
    savedCallback.value = newCallback
  })

  // 当延迟时间改变时重启定时器
  watch(() => delay, (newDelay) => {
    if (intervalId) clearInterval(intervalId)
    if (newDelay !== null) {
      intervalId = setInterval(() => savedCallback.value(), newDelay)
    }
  }, { immediate: true })

  onMounted(() => {
    if (delay.value !== null) {
      intervalId = setInterval(() => savedCallback.value(), delay.value)
    }
  })

  onUnmounted(() => {
    if (intervalId) clearInterval(intervalId)
  })

  return intervalId
} 