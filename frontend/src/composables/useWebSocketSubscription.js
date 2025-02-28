import { ref, watch } from 'vue'
import { useWebSocket } from './useWebSocket'

export function useWebSocketSubscription(url, subscriptions = [], options = {}) {
  const {
    autoSubscribe = true,
    onSubscriptionSuccess = null,
    onSubscriptionError = null,
    ...wsOptions
  } = options

  const activeSubscriptions = ref(new Set())
  const pendingSubscriptions = ref(new Set())

  const { state, isConnected, send, ...ws } = useWebSocket(url, {
    ...wsOptions,
    onMessage: (data) => {
      if (data.type === 'subscription_success') {
        handleSubscriptionSuccess(data.channel)
      } else if (data.type === 'subscription_error') {
        handleSubscriptionError(data.channel, data.error)
      }
      options.onMessage?.(data)
    }
  })

  const handleSubscriptionSuccess = (channel) => {
    pendingSubscriptions.value.delete(channel)
    activeSubscriptions.value.add(channel)
    onSubscriptionSuccess?.(channel)
  }

  const handleSubscriptionError = (channel, error) => {
    pendingSubscriptions.value.delete(channel)
    onSubscriptionError?.(channel, error)
  }

  const subscribe = async (channel) => {
    if (!isConnected.value) return false
    if (activeSubscriptions.value.has(channel)) return true
    if (pendingSubscriptions.value.has(channel)) return false

    pendingSubscriptions.value.add(channel)
    return send({
      type: 'subscribe',
      channel
    })
  }

  const unsubscribe = async (channel) => {
    if (!isConnected.value) return false
    if (!activeSubscriptions.value.has(channel)) return true

    const success = send({
      type: 'unsubscribe',
      channel
    })

    if (success) {
      activeSubscriptions.value.delete(channel)
    }

    return success
  }

  // 自动订阅
  watch(isConnected, (connected) => {
    if (connected && autoSubscribe) {
      subscriptions.forEach(subscribe)
    }
  }, { immediate: true })

  return {
    ...ws,
    state,
    isConnected,
    activeSubscriptions,
    pendingSubscriptions,
    subscribe,
    unsubscribe
  }
} 