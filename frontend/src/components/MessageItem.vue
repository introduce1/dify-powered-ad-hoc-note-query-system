<template>
  <div :class="['message-item', msg.role === 'user' ? 'user-msg' : 'ai-msg']">
    <el-avatar
      :size="36"
      class="msg-avatar"
      :class="msg.role"
    >
      {{ msg.role === 'user' ? 'U' : 'AI' }}
    </el-avatar>

    <div class="msg-body">
      <div class="msg-header">
        <span class="msg-role" :class="msg.role">
          {{ msg.role === 'user' ? '用户' : 'AI' }}
        </span>
        <div class="msg-actions">
          <el-tooltip content="复制" placement="top">
            <el-button text size="small" @click="handleCopy">
              <el-icon :size="14"><DocumentCopy /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip v-if="msg.role === 'ai' && showRetry" content="重新生成" placement="top">
            <el-button text size="small" @click="$emit('retry')">
              <el-icon :size="14"><Refresh /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>

      <div v-if="msg.typing" class="thinking">
        <span>正在思考</span>
        <span class="dots"></span>
      </div>

      <div class="msg-content markdown-body" v-html="msg.html"></div>
    </div>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'

const props = defineProps({
  msg: { type: Object, required: true },
  showRetry: { type: Boolean, default: false },
})

defineEmits(['retry'])

function handleCopy() {
  const text = props.msg.raw || stripHtml(props.msg.html || '')
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => ElMessage.success('已复制'))
  }
}

function stripHtml(html) {
  const tmp = document.createElement('div')
  tmp.innerHTML = html
  return (tmp.textContent || '').trim()
}
</script>

<style scoped>
.message-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 16px;
  gap: 10px;
}

.user-msg {
  flex-direction: row-reverse;
}

.msg-avatar.user {
  background: #409eff;
  color: #fff;
}

.msg-avatar.ai {
  background: #67c23a;
  color: #fff;
}

.msg-body {
  max-width: 78%;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px 14px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.user-msg .msg-body {
  background: #e8f3ff;
  border-color: #d6e4ff;
}

.dark-mode .msg-body {
  background: #2a2a2a;
  border-color: #3a3a3a;
  color: #d4d4d4;
}

.dark-mode .user-msg .msg-body {
  background: #1a2a3a;
  border-color: #2a3a4a;
}

.msg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.msg-role {
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 10px;
}

.msg-role.user {
  background: #e6f4ff;
  color: #1677ff;
}

.msg-role.ai {
  background: #eefbf3;
  color: #2ca26f;
}

.msg-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.2s;
}

.message-item:hover .msg-actions {
  opacity: 1;
}

.thinking {
  color: #999;
  font-size: 13px;
  margin: 4px 0;
  display: flex;
  align-items: center;
  gap: 4px;
}

.dots::after {
  content: '...';
  animation: dots 1s steps(4, end) infinite;
}

@keyframes dots {
  0% { content: '.'; }
  33% { content: '..'; }
  66% { content: '...'; }
}

.msg-content {
  font-size: 14px;
  line-height: 1.7;
}
</style>
