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
          <el-menu-item index="/runs">
            <el-icon><DataLine /></el-icon>
            <span>Runs</span>
          </el-menu-item>
          <el-menu-item index="/prompts">
            <el-icon><Document /></el-icon>
            <span>Prompts</span>
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
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { Platform, DataLine, Document } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => {
  // If in run detail, keep runs active
  if (route.path.startsWith('/runs')) return '/runs'
  return route.path
})

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
