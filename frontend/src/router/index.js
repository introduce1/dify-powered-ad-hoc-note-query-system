import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { title: '智能对话', icon: 'ChatDotRound' },
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/HistoryView.vue'),
    meta: { title: '历史会话', icon: 'Clock' },
  },
  {
    path: '/records',
    name: 'Records',
    component: () => import('@/views/RecordsView.vue'),
    meta: { title: '碎片记录', icon: 'DocumentCopy' },
  },
  {
    path: '/stats',
    name: 'Stats',
    component: () => import('@/views/StatsView.vue'),
    meta: { title: '数据统计', icon: 'TrendCharts' },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/chat',
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} · 碎片数据管理` : '碎片数据管理系统'
})

export default router
