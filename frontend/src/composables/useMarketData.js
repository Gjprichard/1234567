import { ref, computed, watch } from 'vue'
import { useWebSocket } from './useWebSocket'
import { useSettings } from './useSettings'
import { useErrorHandler } from './useErrorHandler'

// 数学工具函数
const mean = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length
const variance = (arr) => {
  const m = mean(arr)
  return mean(arr.map(x => Math.pow(x - m, 2)))
}

export function useMarketData() {
  const { settings } = useSettings()
  const { error, handleError } = useErrorHandler()
  
  const marketData = ref([])
  const lastUpdate = ref(null)
  const isProcessing = ref(false)

  // 连接 WebSocket
  const { isConnected, lastMessage } = useWebSocket(settings.value.wsEndpoint, {
    reconnectInterval: 3000,
    maxReconnectAttempts: 5,
    onError: handleError
  })

  // 处理新数据
  watch(lastMessage, async (message) => {
    if (!message) return
    
    try {
      isProcessing.value = true
      
      // 数据验证
      if (!Array.isArray(message.data)) {
        throw new Error('Invalid market data format')
      }

      // 数据处理
      const processedData = message.data.map(item => ({
        ...item,
        price: Number(item.price),
        volume: Number(item.volume),
        timestamp: new Date(item.timestamp)
      })).filter(item => 
        !isNaN(item.price) && 
        !isNaN(item.volume) && 
        item.timestamp instanceof Date
      )

      marketData.value = processedData
      lastUpdate.value = new Date()
      
    } catch (err) {
      handleError(err, '处理市场数据失败')
    } finally {
      isProcessing.value = false
    }
  })

  // 计算市场指标
  const marketMetrics = computed(() => {
    if (!marketData.value.length) return null

    try {
      const prices = marketData.value.map(item => item.price)
      const volumes = marketData.value.map(item => item.volume)

      // 计算基本指标
      const baseMetrics = {
        averagePrice: mean(prices),
        totalVolume: volumes.reduce((a, b) => a + b, 0),
        priceChange: calculatePriceChange(prices),
        volatility: calculateVolatility(prices)
      }

      // 计算高级指标
      const advancedMetrics = {
        volumeWeightedPrice: calculateVWAP(marketData.value),
        momentum: calculateMomentum(prices),
        trendStrength: calculateTrendStrength(prices)
      }

      return {
        ...baseMetrics,
        ...advancedMetrics,
        timestamp: lastUpdate.value
      }
    } catch (err) {
      handleError(err, '计算市场指标失败')
      return null
    }
  })

  // 计算成交量加权平均价格 (VWAP)
  const calculateVWAP = (data) => {
    const totalVolume = data.reduce((sum, item) => sum + item.volume, 0)
    const vwap = data.reduce((sum, item) => 
      sum + (item.price * item.volume), 0) / totalVolume
    return vwap
  }

  // 计算动量
  const calculateMomentum = (prices, period = 14) => {
    if (prices.length < period) return 0
    return ((prices[prices.length - 1] - prices[prices.length - period]) / 
            prices[prices.length - period]) * 100
  }

  // 计算趋势强度
  const calculateTrendStrength = (prices) => {
    const changes = prices.slice(1).map((price, i) => price - prices[i])
    const positiveChanges = changes.filter(change => change > 0).length
    return (positiveChanges / changes.length) * 100
  }

  return {
    marketData,
    marketMetrics,
    lastUpdate,
    isConnected,
    isProcessing,
    error
  }
} 