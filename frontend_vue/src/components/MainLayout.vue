<template>
  <div class="common-layout">
    <el-container class="h-100">
      <el-aside width="240px" class="aside-menu">
        <div class="logo">
          <el-icon class="logo-icon"><Platform /></el-icon>
          <span>AI Scientist</span>
        </div>
        <el-menu
          :default-active="activeMenu"
          router
          class="el-menu-vertical"
          background-color="#001529"
          text-color="#fff"
          active-text-color="#409EFF"
        >
          <el-menu-item index="/dashboard">
            <el-icon><Odometer /></el-icon>
            <span>Dashboard</span>
          </el-menu-item>
          <el-menu-item index="/runs">
            <el-icon><DataLine /></el-icon>
            <span>Runs</span>
          </el-menu-item>
          <el-menu-item index="/prompts">
            <el-icon><Document /></el-icon>
            <span>Prompts</span>
          </el-menu-item>
          <el-menu-item index="/templates">
            <el-icon><Collection /></el-icon>
            <span>Templates</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.isAdmin" index="/users">
            <el-icon><User /></el-icon>
            <span>Users</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container>
        <el-header class="header">
          <div class="header-content">
            <div class="breadcrumb">
              <!-- Optional Breadcrumb -->
            </div>
            <div class="user-info">
              <el-tag size="small" type="info" effect="plain">{{ buildIdShort }}</el-tag>
              <el-button link type="primary" @click="openEnvDialog">Env</el-button>
              <span class="username">{{ authStore.user?.username }}</span>
              <el-button link type="danger" @click="handleLogout">Logout</el-button>
            </div>
          </div>
        </el-header>
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
    <el-dialog v-model="envDialogVisible" title="Environment Check" width="520px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="Build">{{ buildId }}</el-descriptions-item>
        <el-descriptions-item label="Origin">{{ currentOrigin }}</el-descriptions-item>
        <el-descriptions-item label="API Base">{{ apiBase }}</el-descriptions-item>
        <el-descriptions-item label="Backend Health">{{ healthStatus }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="envDialogVisible = false">Close</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { Platform, DataLine, Document, Odometer, User, Collection } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const envDialogVisible = ref(false)
const healthStatus = ref('checking')
const buildId = import.meta.env.VITE_APP_BUILD_ID || 'dev'
const buildIdShort = computed(() => `build:${String(buildId).slice(0, 12)}`)
const currentOrigin = computed(() => window.location.origin)
const apiBase = computed(() => `${window.location.origin}/api`)

const activeMenu = computed(() => {
  if (route.path.startsWith('/runs')) return '/runs'
  if (route.path.startsWith('/templates')) return '/templates'
  return route.path
})

const openEnvDialog = async () => {
  envDialogVisible.value = true
  healthStatus.value = 'checking'
  try {
    const res = await fetch('/api/health', { method: 'GET' })
    healthStatus.value = res.ok ? 'ok' : `http_${res.status}`
  } catch (_error) {
    healthStatus.value = 'unreachable'
  }
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.h-100 {
  height: 100vh;
}
.aside-menu {
  background-color: #001529;
  color: #fff;
  display: flex;
  flex-direction: column;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: bold;
  background-color: #002140;
}
.logo-icon {
  margin-right: 10px;
}
.el-menu-vertical {
  border-right: none;
}
.header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 60px;
}
.header-content {
  display: flex;
  justify-content: space-between;
  width: 100%;
  align-items: center;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}
.username {
  font-weight: 500;
  color: #606266;
}
.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}
</style>
