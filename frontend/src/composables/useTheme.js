import { ref, watch } from 'vue'

export function useTheme() {
  const theme = ref(localStorage.getItem('theme') || 'dark')
  
  const setTheme = (newTheme) => {
    theme.value = newTheme
    localStorage.setItem('theme', newTheme)
    document.documentElement.setAttribute('data-theme', newTheme)
  }

  watch(theme, (newTheme) => {
    setTheme(newTheme)
  })

  // 初始化主题
  setTheme(theme.value)

  return {
    theme,
    setTheme
  }
} 