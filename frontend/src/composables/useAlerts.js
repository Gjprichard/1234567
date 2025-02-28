import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getAlerts } from '@/api'
import { useInterval } from './useInterval'
import { useErrorHandler } from './useErrorHandler'

export function useAlerts(options = {}) {
  const {
    defaultEnabled = true,
    defaultPriceThreshold = 3.0,
    defaultVolumeThreshold = 50.0,
    maxAlerts = 100,
    checkInterval = 15000
  } = options

  const alerts = ref([])
  const alertEnabled = ref(defaultEnabled)
  const priceThreshold = ref(defaultPriceThreshold)
  const volumeThreshold = ref(defaultVolumeThreshold)
  
  const { error, loading, withErrorHandling } = useErrorHandler()

  const sortedAlerts = computed(() => {
    return [...alerts.value].sort((a, b) => {
      const scoreA = Math.abs(a.price_change) + Math.abs(a.volume_change)
      const scoreB = Math.abs(b.price_change) + Math.abs(b.volume_change)
      return scoreB - scoreA
    })
  })

  const criticalAlertsCount = computed(() => 
    alerts.value.filter(a => a.severity === 'critical').length
  )

  const warningAlertsCount = computed(() => 
    alerts.value.filter(a => a.severity === 'warning').length
  )

  const notifyNewAlerts = () => {
    if (criticalAlertsCount.value > 0) {
      ElMessage({
        type: 'error',
        message: `发现 ${criticalAlertsCount.value} 个严重波动`,
        duration: 5000
      })
    } else if (warningAlertsCount.value > 0) {
      ElMessage({
        type: 'warning',
        message: `发现 ${warningAlertsCount.value} 个异常波动`,
        duration: 3000
      })
    }
  }

  const checkForUpdates = async () => {
    if (!alertEnabled.value) return
    
    await withErrorHandling(async () => {
      const lastUpdate = alerts.value[0]?.time
      const response = await getAlerts()
      
      if (!response?.alerts?.length) return
      
      const newAlerts = response.alerts.filter(alert => 
        !lastUpdate || new Date(alert.time) > new Date(lastUpdate)
      )
      
      if (newAlerts.length > 0) {
        alerts.value = [...newAlerts, ...alerts.value].slice(0, maxAlerts)
        notifyNewAlerts()
      }
    }, '正在检查新预警...')
  }

  const delay = computed(() => alertEnabled.value ? checkInterval : null)
  useInterval(checkForUpdates, delay)

  return {
    alerts,
    sortedAlerts,
    alertEnabled,
    priceThreshold,
    volumeThreshold,
    criticalAlertsCount,
    warningAlertsCount,
    error,
    loading
  }
} 