<template>
  <header class="navbar">
    <div class="navbar-left">
      <h2 class="page-title">{{ currentTitle }}</h2>
    </div>
    <div class="navbar-right">
      <el-tooltip content="切换暗色模式">
        <el-button text @click="appStore.toggleDarkMode">
          <el-icon :size="18">
            <Moon v-if="!appStore.darkMode" />
            <Sunny v-else />
          </el-icon>
        </el-button>
      </el-tooltip>
      <el-dropdown trigger="click">
        <span class="user-badge">
          <el-avatar :size="28" class="user-avatar">{{ appStore.empName[0] }}</el-avatar>
          <span class="user-name">{{ appStore.empName }}</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="showUserDialog = true">
              <el-icon><User /></el-icon>修改用户信息
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <el-dialog v-model="showUserDialog" title="修改用户信息" width="380px" :append-to-body="true">
      <el-form label-width="80px">
        <el-form-item label="员工编号">
          <el-input v-model="editEmpId" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="editEmpName" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUserDialog = false">取消</el-button>
        <el-button type="primary" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'

const appStore = useAppStore()
const route = useRoute()

const currentTitle = computed(() => route.meta?.title || '碎片数据管理系统')

const showUserDialog = ref(false)
const editEmpId = ref(appStore.empId)
const editEmpName = ref(appStore.empName)

function saveUser() {
  if (!editEmpId.value.trim() || !editEmpName.value.trim()) {
    ElMessage.warning('信息不能为空')
    return
  }
  appStore.setUser(editEmpId.value.trim(), editEmpName.value.trim())
  showUserDialog.value = false
  ElMessage.success('用户信息已更新')
}
</script>

<style scoped>
.navbar {
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}

.dark-mode .navbar {
  background: #1d1d1d;
  border-color: #333;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #1d2129;
}

.dark-mode .page-title {
  color: #e0e0e0;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
}

.user-badge:hover {
  background: #f5f5f5;
}

.user-avatar {
  background: #409eff;
  color: #fff;
  font-size: 13px;
}

.user-name {
  font-size: 14px;
  color: #606266;
}

.dark-mode .user-name {
  color: #bbb;
}
</style>
