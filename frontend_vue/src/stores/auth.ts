import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

interface User {
  id: number
  username: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<User | null>(
    localStorage.getItem('user_info') 
      ? JSON.parse(localStorage.getItem('user_info')!) 
      : null
  )

  const isAuthenticated = computed(() => !!token.value)

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

  return { token, user, isAuthenticated, login, logout }
})
