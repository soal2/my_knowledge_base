/**
 * Vue Router Configuration
 * 
 * Routes:
 * - / -> Chat (default, requires auth)
 * - /files -> Knowledge Base (requires auth)
 * - /profile -> Profile Settings (requires auth)
 * - /login -> Login (public)
 * - /register -> Register (public)
 */

import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { getAccessToken } from '@/api'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Chat',
    component: () => import('@/views/Chat.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/files',
    name: 'Files',
    component: () => import('@/views/Files.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { guest: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guards
router.beforeEach((to, _from, next) => {
  const token = getAccessToken()
  
  // Route requires authentication
  if (to.meta.requiresAuth && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }
  
  // Route is for guests only (login/register)
  if (to.meta.guest && token) {
    next({ name: 'Chat' })
    return
  }
  
  next()
})

export default router
