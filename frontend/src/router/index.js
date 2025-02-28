import { createRouter, createWebHistory } from 'vue-router'
import MarketMonitor from '@/pages/MarketMonitor.vue'

const routes = [
  {
    path: '/',
    name: 'MarketMonitor',
    component: MarketMonitor
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router 