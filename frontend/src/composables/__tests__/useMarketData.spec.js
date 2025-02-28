import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { useMarketData } from '../useMarketData'
import { useWebSocket } from '../useWebSocket'
import { useSettings } from '../useSettings'
import { useErrorHandler } from '../useErrorHandler'

jest.mock('../useWebSocket')
jest.mock('../useSettings')
jest.mock('../useErrorHandler')

describe('useMarketData', () => {
  let mockHandleError

  beforeEach(() => {
    mockHandleError = jest.fn()
    useErrorHandler.mockReturnValue({
      error: ref(null),
      handleError: mockHandleError
    })

    useWebSocket.mockReturnValue({
      isConnected: ref(true),
      lastMessage: ref(null)
    })
    
    useSettings.mockReturnValue({
      settings: ref({
        wsEndpoint: 'wss://test.api/market'
      })
    })
  })

  it('should process market data correctly', async () => {
    const wrapper = mount({
      template: '<div/>',
      setup() {
        const { marketData, marketMetrics } = useMarketData()
        return { marketData, marketMetrics }
      }
    })

    // 模拟接收数据
    useWebSocket().lastMessage.value = {
      data: [
        { price: '100.5', volume: '1000', timestamp: '2024-01-01T00:00:00Z' },
        { price: '101.0', volume: '2000', timestamp: '2024-01-01T00:01:00Z' }
      ]
    }

    await nextTick()

    expect(wrapper.vm.marketData.length).toBe(2)
    expect(wrapper.vm.marketMetrics).toBeTruthy()
    expect(wrapper.vm.marketMetrics.averagePrice).toBeCloseTo(100.75)
    expect(mockHandleError).not.toHaveBeenCalled()
  })

  it('should handle invalid data format', async () => {
    const wrapper = mount({
      template: '<div/>',
      setup() {
        const { marketData, error } = useMarketData()
        return { marketData, error }
      }
    })

    // 模拟接收无效数据
    useWebSocket().lastMessage.value = {
      data: 'invalid data'
    }

    await nextTick()

    expect(wrapper.vm.marketData.length).toBe(0)
    expect(mockHandleError).toHaveBeenCalledWith(
      expect.any(Error),
      '处理市场数据失败'
    )
  })

  it('should calculate market metrics correctly', async () => {
    const wrapper = mount({
      template: '<div/>',
      setup() {
        const { marketMetrics } = useMarketData()
        return { marketMetrics }
      }
    })

    // 模拟价格上涨数据
    useWebSocket().lastMessage.value = {
      data: [
        { price: '100', volume: '1000', timestamp: '2024-01-01T00:00:00Z' },
        { price: '110', volume: '2000', timestamp: '2024-01-01T00:01:00Z' },
        { price: '120', volume: '1500', timestamp: '2024-01-01T00:02:00Z' }
      ]
    }

    await nextTick()

    expect(wrapper.vm.marketMetrics).toMatchObject({
      averagePrice: 110,
      totalVolume: 4500,
      priceChange: 20,
      trendStrength: 100, // 所有变化都是正的
      volumeWeightedPrice: expect.any(Number)
    })
  })

  it('should handle data processing errors gracefully', async () => {
    const wrapper = mount({
      template: '<div/>',
      setup() {
        const { marketData, marketMetrics, error, isProcessing } = useMarketData()
        return { marketData, marketMetrics, error, isProcessing }
      }
    })

    // 模拟包含无效数值的数据
    useWebSocket().lastMessage.value = {
      data: [
        { price: 'invalid', volume: '1000', timestamp: '2024-01-01T00:00:00Z' },
        { price: '101.0', volume: 'invalid', timestamp: '2024-01-01T00:01:00Z' }
      ]
    }

    await nextTick()

    expect(wrapper.vm.marketData.length).toBe(0)
    expect(wrapper.vm.marketMetrics).toBeNull()
    expect(wrapper.vm.isProcessing).toBe(false)
    expect(mockHandleError).toHaveBeenCalled()
  })

  it('should update lastUpdate timestamp', async () => {
    const wrapper = mount({
      template: '<div/>',
      setup() {
        const { lastUpdate } = useMarketData()
        return { lastUpdate }
      }
    })

    const before = new Date()
    
    useWebSocket().lastMessage.value = {
      data: [
        { price: '100', volume: '1000', timestamp: '2024-01-01T00:00:00Z' }
      ]
    }

    await nextTick()
    
    const after = new Date()

    expect(wrapper.vm.lastUpdate).toBeInstanceOf(Date)
    expect(wrapper.vm.lastUpdate.getTime()).toBeGreaterThanOrEqual(before.getTime())
    expect(wrapper.vm.lastUpdate.getTime()).toBeLessThanOrEqual(after.getTime())
  })
}) 