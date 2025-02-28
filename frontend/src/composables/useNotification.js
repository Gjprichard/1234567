import { ref, computed } from 'vue'
import { ElNotification } from 'element-plus'

export function useNotification(options = {}) {
  const {
    defaultEnabled = true,
    soundEnabled = false,
    notificationSound = '/notification.mp3'
  } = options

  const notificationEnabled = ref(defaultEnabled)
  const isSoundEnabled = ref(soundEnabled)
  const audio = new Audio(notificationSound)

  const canNotify = computed(() => {
    return notificationEnabled.value && 'Notification' in window
  })

  const requestPermission = async () => {
    if (!('Notification' in window)) return false
    
    if (Notification.permission === 'granted') return true
    
    const permission = await Notification.requestPermission()
    return permission === 'granted'
  }

  const notify = async ({ title, message, type = 'info' }) => {
    if (!canNotify.value) return
    
    if (!await requestPermission()) return
    
    ElNotification({
      title,
      message,
      type,
      duration: 5000
    })

    if (isSoundEnabled.value) {
      audio.play().catch(console.error)
    }
  }

  return {
    notificationEnabled,
    isSoundEnabled,
    notify,
    requestPermission
  }
} 