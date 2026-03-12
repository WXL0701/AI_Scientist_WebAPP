import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import MainLayout from '../components/MainLayout.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue')
      },
      {
        path: 'runs',
        name: 'Runs',
        component: () => import('../views/Runs.vue')
      },
      {
        path: 'runs/:id',
        name: 'RunDetail',
        component: () => import('../views/RunDetail.vue')
      },
      {
        path: 'runs/:id/preview',
        name: 'MarkdownPreview',
        component: () => import('../views/MarkdownPreview.vue')
      },
      {
        path: 'prompts',
        name: 'Prompts',
        component: () => import('../views/Prompts.vue')
      },
      {
        path: 'prompts/:id',
        name: 'PromptSetDetail',
        component: () => import('../views/PromptSetDetail.vue')
      },
      {
        path: 'templates',
        name: 'Templates',
        component: () => import('../views/Templates.vue')
      },
      {
        path: 'users',
        name: 'Users',
        meta: { requiresAdmin: true },
        component: () => import('../views/Users.vue')
      }
    ]
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue')
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFound.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.requiresAdmin && !authStore.isAdmin) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
