import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import MainLayout from '../components/MainLayout.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/runs',
    meta: { requiresAuth: true },
    children: [
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
        path: 'prompts',
        name: 'Prompts',
        component: () => import('../views/Prompts.vue')
      },
      {
        path: 'prompts/:id',
        name: 'PromptSetDetail',
        component: () => import('../views/PromptSetDetail.vue')
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
  } else {
    next()
  }
})

export default router
