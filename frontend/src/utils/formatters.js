export const formatters = {
  price: new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 8
  }),

  change: (value) => {
    const sign = value > 0 ? '+' : ''
    return `${sign}${value.toFixed(2)}`
  },

  time: (value) => {
    const date = new Date(value)
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  },

  volume: (value) => {
    if (value >= 1_000_000_000) {
      return `$${(value / 1_000_000_000).toFixed(2)}B`
    }
    if (value >= 1_000_000) {
      return `$${(value / 1_000_000).toFixed(2)}M`
    }
    return `$${value.toFixed(2)}`
  }
}

export const getChangeClass = (change, threshold, type = 'price') => {
  const absChange = Math.abs(change)
  
  if (absChange >= threshold * 2) return 'change-critical'
  if (absChange >= threshold) return 'change-warning'
  return change > 0 ? 'change-up' : 'change-down'
}

export const getSeverityText = (severity) => {
  const texts = {
    critical: '严重波动',
    warning: '异常波动',
    normal: '轻微波动'
  }
  return texts[severity] || texts.normal
} 