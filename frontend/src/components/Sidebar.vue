<template>
  <aside class="sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
    <div class="sidebar-header">
      <span v-if="!appStore.sidebarCollapsed" class="sidebar-title">碎片数据管理</span>
      <span v-else class="sidebar-title-mini">DM</span>
    </div>

    <el-menu
      :default-active="currentRoute"
      :collapse="appStore.sidebarCollapsed"
      router
      class="sidebar-menu"
      background-color="transparent"
      text-color="#d0d4dc"
      active-text-color="#409eff"
    >
      <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
        <el-icon><component :is="item.icon" /></el-icon>
        <template #title>{{ item.label }}</template>
      </el-menu-item>
    </el-menu>

    <div class="sidebar-footer">
      <el-tooltip :content="appStore.sidebarCollapsed ? '展开菜单' : '收起菜单'" placement="right">
        <el-button text class="collapse-btn" @click="appStore.toggleSidebar">
          <el-icon :size="18">
            <Fold v-if="!appStore.sidebarCollapsed" />
            <Expand v-else />
          </el-icon>
        </el-button>
      </el-tooltip>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const route = useRoute()

const currentRoute = computed(() => route.path)

const menuItems = [
  { path: '/chat', icon: 'ChatDotRound', label: '智能对话' },
  { path: '/history', icon: 'Clock', label: '历史会话' },
  { path: '/records', icon: 'DocumentCopy', label: '碎片记录' },
  { path: '/stats', icon: 'TrendCharts', label: '数据统计' },
]
</script>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 220px;
  background: #1d2129;
  display: flex;
  flex-direction: column;
  z-index: 100;
  transition: width 0.3s ease;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0 16px;
}

.sidebar-title {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.sidebar-title-mini {
  color: #409eff;
  font-size: 18px;
  font-weight: 700;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  padding-top: 8px;
}

.sidebar-menu :deep(.el-menu-item) {
  height: 48px;
  line-height: 48px;
  margin: 2px 8px;
  border-radius: 8px;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.06) !important;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: rgba(64, 158, 255, 0.15) !important;
  color: #409eff !important;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  justify-content: center;
}

.collapse-btn {
  color: #8c8f96;
}

.collapse-btn:hover {
  color: #fff;
}
</style>
