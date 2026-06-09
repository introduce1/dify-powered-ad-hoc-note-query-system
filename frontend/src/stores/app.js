/**
 * 全局应用状态（主题、用户信息、侧边栏）
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  // ── 主题 ───────────────────────────────────────────────────────────────
  const darkMode = ref(localStorage.getItem('darkMode') === 'true')

  function toggleDarkMode() {
    darkMode.value = !darkMode.value
    localStorage.setItem('darkMode', String(darkMode.value))
    document.documentElement.classList.toggle('dark', darkMode.value)
  }

  // 初始化时同步 HTML class
  if (darkMode.value) document.documentElement.classList.add('dark')

  // ── 侧边栏 ─────────────────────────────────────────────────────────────
  const sidebarCollapsed = ref(false)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  // ── 用户信息（简单本地管理，无登录体系） ───────────────────────────────
  const empId = ref(localStorage.getItem('empId') || '001')
  const empName = ref(localStorage.getItem('empName') || '默认用户')

  function setUser(id, name) {
    empId.value = id
    empName.value = name
    localStorage.setItem('empId', id)
    localStorage.setItem('empName', name)
  }

  // ── 通知 / 系统状态 ─────────────────────────────────────────────────────
  const serverOnline = ref(true)

  function setServerStatus(online) {
    serverOnline.value = online
  }

  return {
    darkMode,
    toggleDarkMode,
    sidebarCollapsed,
    toggleSidebar,
    empId,
    empName,
    setUser,
    serverOnline,
    setServerStatus,
  }
})
