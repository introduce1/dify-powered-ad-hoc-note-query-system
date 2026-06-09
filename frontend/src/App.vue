<template>
  <div class="app-layout" :class="{ 'dark-mode': appStore.darkMode }">
    <Sidebar />
    <div class="app-main" :class="{ collapsed: appStore.sidebarCollapsed }">
      <NavBar />
      <div class="app-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import Sidebar from '@/components/Sidebar.vue'
import NavBar from '@/components/NavBar.vue'

const appStore = useAppStore()
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin-left: 220px;
  transition: margin-left 0.3s ease;
}

.app-main.collapsed {
  margin-left: 64px;
}

.app-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f5f7fa;
}

.dark-mode .app-content {
  background: #141414;
}
</style>
