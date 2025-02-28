import { ref, onMounted, onUnmounted, watch } from 'vue'

export const WebSocketState = {
  CONNECTING: 0,
  CONNECTED: 1,
  CLOSING: 2,
  CLOSED: 3
}

export function useWebSocket(url, options = {}) {
  const {
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    heartbeatInterval = 30000,
    heartbeatTimeout = 5000,
    onError = console.error,
    onMessage = null,
    onStateChange = null,
    protocols = []
  } = options

  const socket = ref(null)
  const state = ref(WebSocketState.CLOSED)
  const isConnected = ref(false)
  const reconnectAttempts = ref(0)
  const lastMessage = ref(null)
  const error = ref(null)
  
  let heartbeatTimer = null
  let heartbeatTimeoutTimer = null

  // 监听状态变化
  watch(state, (newState) => {
    onStateChange?.(newState)
  })

  const handleStateChange = (newState) => {
    state.value = newState
    isConnected.value = newState === WebSocketState.CONNECTED
  }

  const startHeartbeat = () => {
    if (heartbeatTimer) clearInterval(heartbeatTimer)
    if (heartbeatTimeoutTimer) clearTimeout(heartbeatTimeoutTimer)

    heartbeatTimer = setInterval(() => {
      if (!isConnected.value) return

      send({ type: 'ping' })
      
      heartbeatTimeoutTimer = setTimeout(() => {
        if (socket.value) {
          socket.value.close()
        }
      }, heartbeatTimeout)
    }, heartbeatInterval)
  }

  const stopHeartbeat = () => {
    if (heartbeatTimer) clearInterval(heartbeatTimer)
    if (heartbeatTimeoutTimer) clearTimeout(heartbeatTimeoutTimer)
  }

  const connect = () => {
    try {
      handleStateChange(WebSocketState.CONNECTING)
      socket.value = new WebSocket(url, protocols)
      
      socket.value.onopen = () => {
        handleStateChange(WebSocketState.CONNECTED)
        reconnectAttempts.value = 0
        error.value = null
        startHeartbeat()
      }

      socket.value.onclose = () => {
        handleStateChange(WebSocketState.CLOSED)
        stopHeartbeat()
        handleReconnect()
      }

      socket.value.onerror = (err) => {
        error.value = err
        onError(err)
      }

      socket.value.onmessage = (event) => {
        try {
          if (event.data instanceof ArrayBuffer) {
            lastMessage.value = event.data
            onMessage?.(event.data)
            return
          }

          const data = JSON.parse(event.data)
          
          if (data.type === 'pong') {
            if (heartbeatTimeoutTimer) {
              clearTimeout(heartbeatTimeoutTimer)
            }
            return
          }

          lastMessage.value = data
          onMessage?.(data)
        } catch (e) {
          error.value = e
          onError('Failed to parse message:', e)
        }
      }
    } catch (e) {
      error.value = e
      onError('Failed to connect:', e)
    }
  }

  const handleReconnect = () => {
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    setTimeout(() => {
      reconnectAttempts.value++
      connect()
    }, reconnectInterval)
  }

  const send = (data) => {
    if (!isConnected.value) return false
    
    try {
      socket.value.send(JSON.stringify(data))
      return true
    } catch (e) {
      console.error('Failed to send message:', e)
      return false
    }
  }

  const disconnect = () => {
    if (!socket.value) return

    try {
      handleStateChange(WebSocketState.CLOSING)
      stopHeartbeat()
      socket.value.close()
    } catch (e) {
      error.value = e
      onError('Failed to disconnect:', e)
    }
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    stopHeartbeat()
    if (socket.value) {
      socket.value.close()
    }
  })

  return {
    state,
    isConnected,
    lastMessage,
    error,
    reconnectAttempts,
    send,
    connect,
    disconnect
  }
} 