import { ref } from 'vue'
import { ElMessage } from 'element-plus'

export function useErrorHandler() {
  const error = ref(null)
  const loading = ref(false)

  const handleError = (err, customMessage = '') => {
    error.value = err
    ElMessage({
      type: 'error',
      message: customMessage || err.message,
      duration: 5000
    })
    console.error(err)
  }

  const clearError = () => {
    error.value = null
  }

  const withErrorHandling = async (fn, loadingMessage = '') => {
    try {
      loading.value = true
      if (loadingMessage) {
        ElMessage({
          type: 'info',
          message: loadingMessage,
          duration: 0
        })
      }
      const result = await fn()
      return result
    } catch (err) {
      handleError(err)
      return null
    } finally {
      loading.value = false
      if (loadingMessage) {
        ElMessage.closeAll()
      }
    }
  }

  return {
    error,
    loading,
    handleError,
    clearError,
    withErrorHandling
  }
} 