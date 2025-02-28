import { useWebSocketSubscription } from '../useWebSocketSubscription'
import { WebSocketState } from '../useWebSocket'
import { nextTick } from 'vue'

describe('useWebSocketSubscription', () => {
  let mockWebSocket

  beforeEach(() => {
    mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(),
      onopen: null,
      onclose: null,
      onerror: null,
      onmessage: null
    }

    global.WebSocket = jest.fn(() => mockWebSocket)
  })

  it('should handle subscriptions', async () => {
    const onSubscriptionSuccess = jest.fn()
    const onSubscriptionError = jest.fn()

    const { subscribe, activeSubscriptions, pendingSubscriptions } = useWebSocketSubscription(
      'wss://test.api',
      [],
      {
        onSubscriptionSuccess,
        onSubscriptionError
      }
    )

    mockWebSocket.onopen()
    await nextTick()

    // 测试订阅
    const channel = 'market.btcusdt'
    await subscribe(channel)

    expect(pendingSubscriptions.value.has(channel)).toBe(true)
    expect(activeSubscriptions.value.has(channel)).toBe(false)

    // 模拟订阅成功
    mockWebSocket.onmessage({
      data: JSON.stringify({
        type: 'subscription_success',
        channel
      })
    })

    await nextTick()

    expect(pendingSubscriptions.value.has(channel)).toBe(false)
    expect(activeSubscriptions.value.has(channel)).toBe(true)
    expect(onSubscriptionSuccess).toHaveBeenCalledWith(channel)
  })

  // ... 更多测试用例
}) 