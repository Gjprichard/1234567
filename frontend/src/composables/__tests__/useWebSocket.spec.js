import { useWebSocket } from '../useWebSocket'
import { nextTick } from 'vue'

describe('useWebSocket', () => {
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

  it('should connect on mount', () => {
    const url = 'wss://test.api'
    const { isConnected } = useWebSocket(url)

    expect(global.WebSocket).toHaveBeenCalledWith(url)
    expect(isConnected.value).toBe(false)

    mockWebSocket.onopen()
    expect(isConnected.value).toBe(true)
  })

  it('should handle reconnection', async () => {
    jest.useFakeTimers()

    const { isConnected } = useWebSocket('wss://test.api', {
      reconnectInterval: 1000,
      maxReconnectAttempts: 3
    })

    mockWebSocket.onopen()
    expect(isConnected.value).toBe(true)

    mockWebSocket.onclose()
    expect(isConnected.value).toBe(false)

    // 第一次重连
    jest.advanceTimersByTime(1000)
    expect(global.WebSocket).toHaveBeenCalledTimes(2)

    // 第二次重连
    mockWebSocket.onclose()
    jest.advanceTimersByTime(1000)
    expect(global.WebSocket).toHaveBeenCalledTimes(3)

    jest.useRealTimers()
  })

  it('should parse messages correctly', async () => {
    const { lastMessage } = useWebSocket('wss://test.api')

    const testMessage = { type: 'data', value: 123 }
    mockWebSocket.onmessage({ data: JSON.stringify(testMessage) })

    await nextTick()
    expect(lastMessage.value).toEqual(testMessage)
  })

  it('should handle message parsing errors', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation()
    const { lastMessage } = useWebSocket('wss://test.api')

    mockWebSocket.onmessage({ data: 'invalid json' })

    await nextTick()
    expect(lastMessage.value).toBeNull()
    expect(consoleSpy).toHaveBeenCalled()

    consoleSpy.mockRestore()
  })

  it('should send messages successfully', () => {
    const { send } = useWebSocket('wss://test.api')
    const message = { type: 'subscribe', channel: 'market' }

    mockWebSocket.onopen()
    const result = send(message)

    expect(result).toBe(true)
    expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify(message))
  })

  it('should not send messages when disconnected', () => {
    const { send } = useWebSocket('wss://test.api')
    const message = { type: 'subscribe', channel: 'market' }

    const result = send(message)

    expect(result).toBe(false)
    expect(mockWebSocket.send).not.toHaveBeenCalled()
  })

  it('should handle heartbeat', () => {
    jest.useFakeTimers()
    
    const { isConnected } = useWebSocket('wss://test.api', {
      heartbeatInterval: 1000
    })

    mockWebSocket.onopen()
    expect(isConnected.value).toBe(true)

    // 检查心跳消息
    jest.advanceTimersByTime(1000)
    expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify({ type: 'ping' }))

    // 模拟服务器响应
    mockWebSocket.onmessage({ data: JSON.stringify({ type: 'pong' }) })
    expect(isConnected.value).toBe(true)

    jest.useRealTimers()
  })

  it('should handle heartbeat timeout', () => {
    jest.useFakeTimers()
    
    const { isConnected } = useWebSocket('wss://test.api', {
      heartbeatInterval: 1000,
      heartbeatTimeout: 2000
    })

    mockWebSocket.onopen()
    expect(isConnected.value).toBe(true)

    // 发送心跳但没有收到响应
    jest.advanceTimersByTime(3000)
    expect(mockWebSocket.close).toHaveBeenCalled()
    expect(isConnected.value).toBe(false)

    jest.useRealTimers()
  })

  it('should cleanup on unmount', () => {
    const { unmount } = mount({
      template: '<div/>',
      setup() {
        useWebSocket('wss://test.api')
      }
    })

    unmount()
    expect(mockWebSocket.close).toHaveBeenCalled()
  })

  it('should handle connection errors', () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation()
    const error = new Error('Connection failed')
    
    global.WebSocket = jest.fn(() => {
      throw error
    })

    const { isConnected } = useWebSocket('wss://test.api')
    
    expect(isConnected.value).toBe(false)
    expect(consoleSpy).toHaveBeenCalledWith('Failed to connect:', error)

    consoleSpy.mockRestore()
  })

  it('should handle send errors', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation()
    const { send } = useWebSocket('wss://test.api')

    mockWebSocket.onopen()
    mockWebSocket.send.mockImplementation(() => {
      throw new Error('Send failed')
    })

    const result = send({ type: 'test' })

    expect(result).toBe(false)
    expect(consoleSpy).toHaveBeenCalledWith(
      'Failed to send message:',
      expect.any(Error)
    )

    consoleSpy.mockRestore()
  })

  it('should handle binary messages', async () => {
    const { lastMessage } = useWebSocket('wss://test.api')

    const buffer = new ArrayBuffer(8)
    mockWebSocket.onmessage({ data: buffer })

    await nextTick()
    expect(lastMessage.value).toBeInstanceOf(ArrayBuffer)
  })

  it('should respect max reconnection attempts', async () => {
    jest.useFakeTimers()
    
    const maxAttempts = 2
    useWebSocket('wss://test.api', {
      reconnectInterval: 1000,
      maxReconnectAttempts: maxAttempts
    })

    // 模拟多次断开连接
    for (let i = 0; i <= maxAttempts + 1; i++) {
      mockWebSocket.onclose()
      jest.advanceTimersByTime(1000)
    }

    expect(global.WebSocket).toHaveBeenCalledTimes(maxAttempts + 1)

    jest.useRealTimers()
  })
}) 