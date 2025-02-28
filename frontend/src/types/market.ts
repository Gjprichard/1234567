export interface MarketData {
  price: number
  volume: number
  timestamp: Date
  symbol: string
  high: number
  low: number
  open: number
  close: number
}

export interface MarketMetrics {
  averagePrice: number
  totalVolume: number
  priceChange: number
  volatility: number
  volumeWeightedPrice: number
  momentum: number
  trendStrength: number
  timestamp: Date
}

export interface WebSocketMessage {
  type: string
  data: any
  timestamp: string
} 