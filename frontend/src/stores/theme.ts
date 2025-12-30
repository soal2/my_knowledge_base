/**
 * Theme Store
 * Manages dark/light mode
 */

import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  // Check system preference and localStorage
  const getInitialTheme = (): 'dark' | 'light' => {
    const saved = localStorage.getItem('theme')
    if (saved === 'dark' || saved === 'light') {
      return saved
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }

  // State
  const theme = ref<'dark' | 'light'>(getInitialTheme())

  // Apply theme to document
  const applyTheme = (newTheme: 'dark' | 'light') => {
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('theme', newTheme)
  }

  // Watch for changes
  watch(theme, (newTheme) => {
    applyTheme(newTheme)
  }, { immediate: true })

  // Actions
  function toggleTheme(): void {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  function setTheme(newTheme: 'dark' | 'light'): void {
    theme.value = newTheme
  }

  return {
    theme,
    toggleTheme,
    setTheme
  }
})
