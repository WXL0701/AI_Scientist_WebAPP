import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

interface User {
  id: number
  username: string
  role: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const storedUser = localStorage.getItem('user_info')
  const parsedUser = storedUser ? JSON.parse(storedUser) : null
  const user = ref<User | null>(
    parsedUser ? { ...parsedUser, role: parsedUser.role || 'user' } : null
  )

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  function login(accessToken: string, userInfo: User) {
    token.value = accessToken
    user.value = userInfo
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('user_info', JSON.stringify(userInfo))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
  }

  return { token, user, isAuthenticated, isAdmin, login, logout }
})
