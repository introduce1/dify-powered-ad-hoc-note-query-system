<template>
  <div class="history-view">
    <!-- 搜索栏 -->
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索会话名称..."
        clearable
        prefix-icon="Search"
        class="search-input"
        @input="debouncedFetch"
      />
      <el-select v-model="filterWorkflow" placeholder="全部工作流" clearable @change="fetchSessions">
        <el-option label="随记随查" value="suijisuicha" />
        <el-option label="多轮对话" value="duolunduihua" />
        <el-option label="生产记录" value="shengchanjilu" />
      </el-select>
      <el-button type="primary" @click="createSession">
        <el-icon><Plus /></el-icon> 新建会话
      </el-button>
    </div>

    <!-- 会话列表 -->
    <el-table :data="sessions" v-loading="loading" stripe style="width: 100%">
      <el-table-column prop="session_name" label="会话名称" min-width="200">
        <template #default="{ row }">
          <el-link type="primary" @click="viewSession(row.id)">{{ row.session_name }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="workflow_type" label="工作流" width="130">
        <template #default="{ row }">
          <el-tag size="small" :type="workflowTagType(row.workflow_type)">
            {{ workflowLabel(row.workflow_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="msg_count" label="消息数" width="80" align="center" />
      <el-table-column prop="update_time" label="最近活动" width="170" />
      <el-table-column label="操作" width="160" align="center">
        <template #default="{ row }">
          <el-button text size="small" @click="renameSession(row)">重命名</el-button>
          <el-popconfirm title="确认删除该会话？" @confirm="deleteSession(row.id)">
            <template #reference>
              <el-button text size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-bar" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchSessions"
      />
    </div>

    <!-- 会话详情抽屉 -->
    <el-drawer v-model="drawerVisible" :title="currentSession?.session_name || '会话详情'" size="50%">
      <div class="session-messages">
        <div v-for="m in currentMessages" :key="m.id" :class="['s-msg', m.role]">
          <div class="s-msg-role">{{ m.role === 'user' ? '用户' : 'AI' }}</div>
          <div class="s-msg-content markdown-body" v-html="renderMd(m.content)"></div>
          <div class="s-msg-time">{{ m.create_time }}</div>
        </div>
        <el-empty v-if="currentMessages.length === 0" description="暂无消息" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { marked } from 'marked'
import { ElMessage, ElMessageBox } from 'element-plus'
import { historyApi } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const sessions = ref([])
const loading = ref(false)
const keyword = ref('')
const filterWorkflow = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)

const drawerVisible = ref(false)
const currentSession = ref(null)
const currentMessages = ref([])

let debounceTimer = null
function debouncedFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchSessions, 300)
}

async function fetchSessions() {
  loading.value = true
  try {
    const res = await historyApi.listSessions({
      emp_id: appStore.empId,
      keyword: keyword.value,
      workflow_type: filterWorkflow.value,
      page: page.value,
      page_size: pageSize,
    })
    sessions.value = res.data || []
    total.value = res.total || 0
  } catch { /* handled by interceptor */ } finally {
    loading.value = false
  }
}

async function createSession() {
  try {
    await historyApi.createSession({ emp_id: appStore.empId })
    ElMessage.success('已创建新会话')
    fetchSessions()
  } catch { /* handled */ }
}

async function viewSession(id) {
  try {
    const res = await historyApi.getSession(id)
    currentSession.value = res.session
    currentMessages.value = res.messages || []
    drawerVisible.value = true
  } catch { /* handled */ }
}

async function renameSession(row) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新名称', '重命名会话', {
      inputValue: row.session_name,
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await historyApi.renameSession(row.id, value)
    ElMessage.success('重命名成功')
    fetchSessions()
  } catch { /* cancelled */ }
}

async function deleteSession(id) {
  try {
    await historyApi.deleteSession(id)
    ElMessage.success('删除成功')
    fetchSessions()
  } catch { /* handled */ }
}

function workflowLabel(type) {
  const map = { suijisuicha: '随记随查', duolunduihua: '多轮对话', shengchanjilu: '生产记录' }
  return map[type] || type
}

function workflowTagType(type) {
  const map = { suijisuicha: '', duolunduihua: 'success', shengchanjilu: 'warning' }
  return map[type] || 'info'
}

function renderMd(text) {
  return marked.parse(text || '')
}

onMounted(fetchSessions)
</script>

<style scoped>
.history-view {
  max-width: 1100px;
  margin: 0 auto;
}

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-input {
  width: 260px;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.session-messages {
  padding: 0 8px;
}

.s-msg {
  margin-bottom: 16px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #f9fafb;
}

.s-msg.ai {
  background: #f0f9eb;
}

.s-msg-role {
  font-size: 12px;
  font-weight: 600;
  color: #999;
  margin-bottom: 4px;
}

.s-msg-time {
  font-size: 12px;
  color: #bbb;
  margin-top: 4px;
  text-align: right;
}
</style>
