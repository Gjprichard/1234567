import { ref, watch } from 'vue'

const SETTINGS_KEY = 'alert_settings'

export function useSettings() {
  // 从本地存储加载设置
  const loadSettings = () => {
    const saved = localStorage.getItem(SETTINGS_KEY)
    return saved ? JSON.parse(saved) : null
  }

  // 保存设置到本地存储
  const saveSettings = (settings) => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
  }

  const settings = ref(loadSettings() || {
    alertEnabled: true,
    priceThreshold: 3.0,
    volumeThreshold: 50.0,
    maxAlerts: 100,
    checkInterval: 15000,
    notificationEnabled: true,
    soundEnabled: false
  })

  // 监听设置变化并保存
  watch(settings, (newSettings) => {
    saveSettings(newSettings)
  }, { deep: true })

  return {
    settings
  }
} 