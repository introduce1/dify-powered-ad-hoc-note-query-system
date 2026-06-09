<template>
  <div class="chat-view">
    <!-- 工作流选择 -->
    <div class="chat-toolbar">
      <el-select v-model="selectedWorkflow" placeholder="选择工作流" class="wf-select">
        <el-option
          v-for="wf in workflows"
          :key="wf.key"
          :label="wf.label"
          :value="wf.key"
        />
      </el-select>

      <!-- 随记随查的操作类型选择 -->
      <el-radio-group v-if="selectedWorkflow === 'suijisuicha'" v-model="operationType" size="small" style="margin-left: 12px;">
        <el-radio-button value="检索">检索</el-radio-button>
        <el-radio-button value="录入">录入</el-radio-button>
      </el-radio-group>

      <el-button text @click="clearChat">
        <el-icon><Delete /></el-icon> 清屏
      </el-button>
    </div>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="messagesRef">
      <div v-if="showGuideTips" class="guide-tips inline-guide">
        <template v-if="selectedWorkflow === 'suijisuicha'">
          <div class="tip-section">
            <h4 v-if="operationType === '检索'">📌 检索模式</h4>
            <h4 v-else>📝 录入模式</h4>
            <div v-if="operationType === '检索'" class="tip-content">
              <p>• 输入关键词搜索已保存的碎片知识</p>
              <p>• 支持按内容、类型、员工等多维度查询</p>
              <p>• 快速定位相关记录</p>
              <p style="color:#909399; margin-top: 8px;">示例：输入"API文档"、"数据库设计"等</p>
            </div>
            <div v-else class="tip-content">
              <p>• 输入新的知识点或工作笔记</p>
              <p>• 系统自动分类保存</p>
              <p>• 下次可直接检索使用</p>
              <p style="color:#909399; margin-top: 8px;">示例：输入"MySQL 分区表优化方案"等</p>
            </div>
          </div>
        </template>
        <template v-else-if="selectedWorkflow === 'duolunduihua'">
          <div class="tip-section">
            <h4>💬 多轮对话</h4>
            <div class="tip-content">
              <p>• 支持连续提问和上下文关联</p>
              <p>• 可进行深度信息查询和讨论</p>
              <p>• 系统记住历史对话内容</p>
              <p style="color:#909399; margin-top: 8px;">示例：</p>
              <p style="color:#909399;">1. "一院上个月出图多少张？"</p>
              <p style="color:#909399;">2. "都有哪些项目？"（系统理解指一院的项目）</p>
            </div>
          </div>
        </template>
        <template v-else-if="selectedWorkflow === 'shengchanjilu'">
          <div class="tip-section">
            <h4>📊 生产记录查询</h4>
            <div class="tip-content">
              <p>• 查询出图记录、产值统计、工时等生产数据</p>
              <p>• 支持按部门、项目、时间段统计</p>
              <p>• 自然语言描述需求即可</p>
              <p style="color:#909399; margin-top: 8px;">示例：</p>
              <p style="color:#909399;">• "本月各部门出图统计"</p>
              <p style="color:#909399;">• "一院今年产值完成情况"</p>
              <p style="color:#909399;">• "哪些项目还在进行中"</p>
            </div>
          </div>
        </template>
      </div>

      <div v-if="chatList.length === 0" class="empty-hint">
        <el-icon :size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
        <p>选择工作流，开始对话</p>
      </div>
      <MessageItem
        v-for="(msg, idx) in chatList"
        :key="idx"
        :msg="msg"
        :show-retry="msg.role === 'ai' && idx === lastAiIndex"
        @retry="retryLast"
      />
    </div>

    <!-- 输入框 -->
    <div class="chat-input-bar">
      <el-input
        v-model="question"
        :placeholder="inputPlaceholder"
        @keyup.enter="submitQuestion"
        :disabled="isLoading"
        clearable
        size="large"
      />
      <el-button type="primary" :loading="isLoading" @click="submitQuestion" size="large">
        发送
      </el-button>
      <el-button v-if="controller" type="danger" @click="cancelRequest" size="large">
        取消
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import { marked } from 'marked'
import { ElMessage } from 'element-plus'
import { workflowApi, historyApi } from '@/api'
import { useAppStore } from '@/stores/app'
import MessageItem from '@/components/MessageItem.vue'

const appStore = useAppStore()

const workflows = [
  { key: 'suijisuicha', label: '随记随查（录入/检索）' },
  { key: 'duolunduihua', label: '自然语言查询（多轮对话）' },
  { key: 'shengchanjilu', label: '生产记录查询（自然语言）' },
]

const selectedWorkflow = ref('suijisuicha')
const operationType = ref('检索')  // 新增：操作类型（检索/录入）
const chatList = ref([])
const question = ref('')
const isLoading = ref(false)
const controller = ref(null)
const lastQuestion = ref('')
const messagesRef = ref(null)
const currentSessionId = ref(null)  // 当前会话 ID
const difyConversationId = ref(null) // Dify conversation_id（保持多轮状态）
let outputText = ''
let renderPending = false

// 从 localStorage 恢复对话
onMounted(() => {
  console.log('[ChatView] 组件挂载，加载对话记忆')
  loadChatFromStorage()
})

// 监听工作流切换，保存当前对话
watch(selectedWorkflow, (newVal, oldVal) => {
  console.log('[ChatView] 工作流切换:', oldVal, '->', newVal)
  if (oldVal) {
    saveChatToStorage(oldVal)
  }
  loadChatFromStorage()
})

// 保存对话到 localStorage
function saveChatToStorage(workflowKey = selectedWorkflow.value) {
  const key = `chat_${workflowKey}_${appStore.empId}`
  const data = {
    chatList: chatList.value,
    sessionId: currentSessionId.value,
    conversationId: difyConversationId.value,
    timestamp: Date.now()
  }
  console.log('[ChatView] 保存对话到 localStorage:', key, '消息数:', chatList.value.length)
  localStorage.setItem(key, JSON.stringify(data))
}

// 从 localStorage 加载对话
function loadChatFromStorage() {
  const key = `chat_${selectedWorkflow.value}_${appStore.empId}`
  const stored = localStorage.getItem(key)
  console.log('[ChatView] 尝试加载对话:', key, '是否存在:', !!stored)
  if (stored) {
    try {
      const data = JSON.parse(stored)
      // 只加载 24 小时内的对话
      if (Date.now() - data.timestamp < 24 * 60 * 60 * 1000) {
        chatList.value = data.chatList || []
        currentSessionId.value = data.sessionId
        difyConversationId.value = data.conversationId || null
        console.log('[ChatView] 成功加载对话，消息数:', chatList.value.length)
        nextTick(scrollToBottom)
      } else {
        console.log('[ChatView] 对话已过期（超过24小时）')
        chatList.value = []
        currentSessionId.value = null
        difyConversationId.value = null
      }
    } catch (e) {
      console.error('[ChatView] 加载对话失败:', e)
      chatList.value = []
      currentSessionId.value = null
      difyConversationId.value = null
    }
  } else {
    console.log('[ChatView] 没有找到保存的对话')
    chatList.value = []
    currentSessionId.value = null
    difyConversationId.value = null
  }
}

// 保存会话到数据库
async function saveSessionToDatabase(userQuery, aiResponse) {
  console.log('[ChatView] 准备保存会话到数据库')
  console.log('  用户问题:', userQuery.substring(0, 50))
  console.log('  AI回复长度:', aiResponse.length)
  const payload = {
    emp_id: appStore.empId,
    workflow_type: selectedWorkflow.value,
    query_text: userQuery,
    response_text: aiResponse,
    session_id: currentSessionId.value || undefined
  }
  try {
    const result = await historyApi.create(payload, { timeout: 90000, silent: true })
    console.log('[ChatView] 会话保存成功:', result)
    // 如果返回了新的 session_id，更新当前 session_id
    if (result.session_id) {
      currentSessionId.value = result.session_id
    }
  } catch (e) {
    const isTimeout = e?.code === 'ECONNABORTED' || /timeout/i.test(e?.message || '')
    if (isTimeout) {
      console.info('[ChatView] 历史保存超时，进行一次静默重试')
      try {
        const retryResult = await historyApi.create(payload, { timeout: 90000, silent: true })
        console.log('[ChatView] 会话重试保存成功:', retryResult)
        if (retryResult.session_id) {
          currentSessionId.value = retryResult.session_id
        }
        return
      } catch (retryError) {
        const retryMsg = retryError?.response?.data?.message || retryError?.message || '未知错误'
        console.info('[ChatView] 历史保存失败（已忽略，不影响当前对话）:', retryMsg)
        return
      }
    }
    const errMsg = e?.response?.data?.message || e?.message || '未知错误'
    console.info('[ChatView] 历史保存失败（已忽略，不影响当前对话）:', errMsg)
  }
}

const lastAiIndex = computed(() => {
  for (let i = chatList.value.length - 1; i >= 0; i--) {
    if (chatList.value[i].role === 'ai') return i
  }
  return -1
})

const inputPlaceholder = computed(() => {
  const map = {
    suijisuicha: '请输入要保存或检索的内容...',
    duolunduihua: '请输入自然语言查询（如：建筑设计一院去年合同额）',
    shengchanjilu: '请输入生产记录查询（如：本月产量统计）',
  }
  return map[selectedWorkflow.value] || '请输入...'
})

const showGuideTips = computed(() =>
  ['suijisuicha', 'duolunduihua', 'shengchanjilu'].includes(selectedWorkflow.value)
)

function renderMarkdown(text) {
  return marked.parse(text || '')
}

function mergeStreamText(current, incoming) {
  if (!incoming) return current || ''
  if (!current) return incoming

  // 快照流：新块包含当前全文，直接替换为更新后的全文
  if (incoming.startsWith(current)) return incoming
  // 旧快照回流：忽略更短的旧内容
  if (current.startsWith(incoming)) return current

  // 增量流重叠：仅追加非重叠部分
  const maxOverlap = Math.min(current.length, incoming.length)
  for (let i = maxOverlap; i > 0; i--) {
    if (current.slice(-i) === incoming.slice(0, i)) {
      return current + incoming.slice(i)
    }
  }

  return current + incoming
}

function dedupeKeyValueLines(text) {
  const lines = (text || '').split('\n')
  const seen = new Set()
  const result = []

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) {
      result.push(rawLine)
      continue
    }

    // 仅对“键值行”做去重，避免误伤普通段落
    const sepIdx = Math.max(line.indexOf('：'), line.indexOf(':'))
    if (sepIdx <= 0) {
      result.push(rawLine)
      continue
    }

    const key = line.slice(0, sepIdx).replace(/\s+/g, '')
    const value = line.slice(sepIdx + 1).replace(/\s+/g, '')
    const normalizedKey = key.replace(/^员工编号$/, '编号')
    const normalized = `${normalizedKey}:${value}`

    if (seen.has(normalized)) continue
    seen.add(normalized)
    result.push(rawLine)
  }

  return result.join('\n')
}

function tryParseTrailingJson(text) {
  const source = (text || '').trim()
  if (!source) return null

  const startIndexes = []
  for (let i = 0; i < source.length; i++) {
    if (source[i] === '[' || source[i] === '{') {
      startIndexes.push(i)
    }
  }

  for (let i = startIndexes.length - 1; i >= 0; i--) {
    const start = startIndexes[i]
    const candidate = source.slice(start).trim()
    try {
      return {
        prefix: source.slice(0, start).trim(),
        payload: JSON.parse(candidate),
      }
    } catch {
      // 继续尝试更早的 JSON 起点
    }
  }

  return null
}

function formatResultPayload(payload) {
  if (Array.isArray(payload)) {
    if (!payload.length) return '未检索到数据。'

    return payload
      .map((item, index) => {
        if (item && typeof item === 'object' && !Array.isArray(item)) {
          const body = Object.entries(item)
            .map(([key, value]) => `${key}：${value ?? ''}`)
            .join('\n')
          return payload.length > 1 ? `第${index + 1}条\n${body}` : body
        }
        return String(item ?? '')
      })
      .filter(Boolean)
      .join('\n\n')
  }

  if (payload && typeof payload === 'object') {
    return Object.entries(payload)
      .map(([key, value]) => `${key}：${value ?? ''}`)
      .join('\n')
  }

  return String(payload ?? '')
}

function tryParseJsonText(text) {
  const source = (text || '').trim()
  if (!source) return null
  try {
    return JSON.parse(source)
  } catch {
    return null
  }
}

function isSqlLikeLine(line) {
  const s = (line || '').trim()
  if (!s) return false
  return /^(SELECT|WITH|INSERT|UPDATE|DELETE)\b/i.test(s) ||
    /^(FROM|INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|JOIN|WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|AND|OR)\b/i.test(s)
}

function looksLikeSqlEcho(text) {
  const source = (text || '').trim()
  if (!source) return false
  return /\bSELECT\b[\s\S]*\bFROM\b/i.test(source) ||
    /\bWITH\b[\s\S]*\bSELECT\b/i.test(source) ||
    /\bINSERT\b[\s\S]*\bINTO\b/i.test(source)
}

function stripSqlEcho(text) {
  const source = (text || '').trim()
  if (!source) return ''

  if (source.includes('未查询到数据')) return '未查询到数据'

  const errorMatch = source.match(/错误[:：][\s\S]*$/)
  if (errorMatch) return errorMatch[0].trim()

  const lines = source
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

  const kept = lines.filter((line) =>
    !isSqlLikeLine(line) &&
    !/^查询成功$/i.test(line) &&
    !/^查询完成[,，]?(无数据)?$/i.test(line)
  )

  if (kept.length) return kept.join('\n')
  return source
}

function extractResultOnlyText(text) {
  const source = (text || '').trim()
  if (!source) return ''

  // 纯 JSON 输出：直接格式化
  const wholeJson = tryParseJsonText(source)
  if (wholeJson !== null && typeof wholeJson === 'object') {
    return formatResultPayload(wholeJson)
  }

  const parsed = tryParseTrailingJson(source)
  if (parsed && /^(SELECT|WITH|INSERT)\b/i.test(parsed.prefix)) {
    return formatResultPayload(parsed.payload)
  }

  if (looksLikeSqlEcho(source)) {
    return stripSqlEcho(source)
  }

  return source
}

function buildDisplayText(text) {
  return dedupeKeyValueLines(extractResultOnlyText(text || ''))
}

function scrollToBottom() {
  nextTick(() => {
    const el = messagesRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function clearChat() {
  if (controller.value) {
    controller.value.abort()
    controller.value = null
    isLoading.value = false
  }
  chatList.value = []
  currentSessionId.value = null
  difyConversationId.value = null
  outputText = ''
  lastQuestion.value = ''
  // 清除 localStorage
  const key = `chat_${selectedWorkflow.value}_${appStore.empId}`
  localStorage.removeItem(key)
  // 通知后端清除 conversation_id 记忆
  const BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8888'
  fetch(`${BASE_URL}/api/workflow/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user: appStore.empId, workflow_type: selectedWorkflow.value }),
  }).catch(() => {})
}

function retryLast() {
  if (lastQuestion.value) startStream(lastQuestion.value)
}

function cancelRequest() {
  if (controller.value) {
    controller.value.abort()
    controller.value = null
    isLoading.value = false
    ElMessage.info('已取消')
  }
}

function submitQuestion() {
  const q = (question.value || '').trim()
  if (!q) {
    ElMessage.warning('请输入内容')
    return
  }

  chatList.value.push({
    role: 'user', typing: false, raw: q, html: renderMarkdown(q),
  })
  lastQuestion.value = q
  question.value = ''
  startStream(q)
}

async function startStream(q) {
  outputText = ''
  isLoading.value = true

  const aiMsg = { role: 'ai', html: '', typing: true, raw: '' }
  chatList.value.push(aiMsg)
  const msgIndex = chatList.value.length - 1
  scrollToBottom()

  let inputs = {}
  if (selectedWorkflow.value === 'suijisuicha') {
    inputs = {
      operation: operationType.value,  // 使用用户选择的操作类型
      emp_id: appStore.empId,
      content: q,
      rec_type: '备忘',  // 默认类型
      product_code: ''
    }
  } else if (selectedWorkflow.value === 'duolunduihua') {
    inputs = { query: q }
  } else {
    inputs = { question: q, data_scope: '' }
  }

  controller.value = new AbortController()

  try {
    const res = await workflowApi.run(
      {
        inputs,
        workflow_type: selectedWorkflow.value,
        user: appStore.empId,
        conversation_id: difyConversationId.value || undefined,
      },
      controller.value.signal,
    )
    if (!res.ok) throw new Error('HTTP ' + res.status)
    if (!res.body) throw new Error('ReadableStream not supported')

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let sseBuffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const rawChunk = decoder.decode(value, { stream: true })
      console.log('[ChatView] 收到流数据块:', rawChunk.substring(0, 300))
      sseBuffer += rawChunk
      const events = sseBuffer.split(/\r?\n\r?\n/)
      sseBuffer = events.pop() || ''

      for (const evt of events) {
        let dataLine = ''
        for (const line of evt.split(/\r?\n/)) {
          const l = line.trim()
          if (l.startsWith('data:')) dataLine += l.slice(5).trim()
        }
        if (!dataLine) continue

        let parsed
        try { parsed = JSON.parse(dataLine) } catch { parsed = { text: dataLine } }
        console.log('[ChatView] 解析SSE事件:', parsed)

        if (parsed.conversation_id && typeof parsed.conversation_id === 'string') {
          difyConversationId.value = parsed.conversation_id
        }

        if (parsed.error && chatList.value[msgIndex]) {
          chatList.value[msgIndex].typing = false
          chatList.value[msgIndex].html = `<p style="color:#d4380d;">${String(parsed.error)}</p>`
          throw new Error(String(parsed.error))
        }

        const chunkText = (typeof parsed.answer === 'string' ? parsed.answer : '') ||
          (typeof parsed.text === 'string' ? parsed.text : '')

        if (chunkText && chatList.value[msgIndex]) {
          outputText = mergeStreamText(outputText, chunkText)
          const displayText = buildDisplayText(outputText)
          aiMsg.raw = outputText
          if (!renderPending) {
            renderPending = true
            requestAnimationFrame(() => {
              if (chatList.value[msgIndex]) {
                chatList.value[msgIndex].html = renderMarkdown(displayText)
              }
              renderPending = false
              scrollToBottom()
            })
          }
        }

        if (parsed.done === true && chatList.value[msgIndex]) {
          chatList.value[msgIndex].typing = false
          if (!outputText.trim()) {
            chatList.value[msgIndex].html = renderMarkdown('未收到返回内容，请重试。')
          }
        }
      }
    }

    // 处理流结束时未被 \n\n 切开的最后一个 SSE 事件
    if (sseBuffer.trim()) {
      let dataLine = ''
      for (const line of sseBuffer.split(/\r?\n/)) {
        const l = line.trim()
        if (l.startsWith('data:')) dataLine += l.slice(5).trim()
      }
      if (dataLine) {
        let parsed
        try { parsed = JSON.parse(dataLine) } catch { parsed = { text: dataLine } }
        console.log('[ChatView] 解析残留SSE事件:', parsed)

        if (parsed.conversation_id && typeof parsed.conversation_id === 'string') {
          difyConversationId.value = parsed.conversation_id
        }

        const chunkText = (typeof parsed.answer === 'string' ? parsed.answer : '') ||
          (typeof parsed.text === 'string' ? parsed.text : '')
        if (chunkText && chatList.value[msgIndex]) {
          outputText = mergeStreamText(outputText, chunkText)
          chatList.value[msgIndex].html = renderMarkdown(buildDisplayText(outputText))
        }
        if (parsed.done === true && chatList.value[msgIndex]) {
          chatList.value[msgIndex].typing = false
        }
      }
    }

    if (chatList.value[msgIndex]?.typing) {
      chatList.value[msgIndex].typing = false
      chatList.value[msgIndex].html = renderMarkdown(buildDisplayText(outputText) || '未收到返回内容，请重试。')
    } else if (chatList.value[msgIndex] && !chatList.value[msgIndex].html?.trim()) {
      chatList.value[msgIndex].html = renderMarkdown('未收到返回内容，请重试。')
    }

    console.log('[ChatView] 流式传输完成，outputText 长度:', outputText.length)

    // 对话完成后保存（不阻塞UI）
    if (outputText) {
      const displayText = buildDisplayText(outputText) || outputText
      saveChatToStorage()
      saveSessionToDatabase(q, displayText).catch(e =>
        console.error('[ChatView] 后台保存失败:', e)
      )
    }
  } catch (err) {
    console.error('[ChatView] 流式传输错误:', err)
    if (chatList.value[msgIndex]) {
      const errMsg = err?.name === 'AbortError'
        ? '请求已取消'
        : (err?.message || String(err) || '请求失败')
      chatList.value[msgIndex].typing = false
      chatList.value[msgIndex].html = `<p style="color:#d4380d;">${errMsg}</p>`
    }
  } finally {
    console.log('[ChatView] 清理资源')
    isLoading.value = false
    controller.value = null
  }
}
</script>

<style scoped>
.chat-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  max-width: 960px;
  margin: 0 auto;
}

.chat-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.wf-select {
  width: 280px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.empty-hint {
  text-align: center;
  padding: 80px 0;
  color: #c0c4cc;
}

.empty-hint p {
  margin-top: 12px;
  font-size: 14px;
}

.guide-tips {
  margin-top: 40px;
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

.inline-guide {
  margin-top: 8px;
  margin-bottom: 14px;
}

.tip-section {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 8px;
  padding: 20px;
  text-align: left;
}

.tip-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

.tip-content {
  font-size: 13px;
  line-height: 1.8;
  color: #555;
}

.tip-content p {
  margin: 6px 0;
}

.chat-input-bar {
  display: flex;
  gap: 10px;
  padding: 12px 0 4px;
  flex-shrink: 0;
  border-top: 1px solid #eee;
}

.chat-input-bar .el-input {
  flex: 1;
}
</style>
