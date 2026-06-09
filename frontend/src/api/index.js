/**
 * API 请求统一封装
 * BASE_URL: 后端地址，开发时使用 vite proxy，生产时直接指向后端
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8888'
const DB_URL   = import.meta.env.VITE_DB_BASE  || 'http://localhost:51206'

// ── Axios 实例 ──────────────────────────────────────────────────────────────

const http = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const isTimeout = err?.code === 'ECONNABORTED' || /timeout/i.test(err?.message || '')
    const msg = err.response?.data?.message || err.response?.data?.error || err.message || '请求失败'
    const silent = !!err?.config?.silent
    if (isTimeout) {
      console.info('[http] 请求超时，已静默忽略提示:', err?.config?.url || '')
    } else if (!silent) {
      ElMessage.error(msg)
    }
    return Promise.reject(err)
  },
)

// ── 工作流 API ──────────────────────────────────────────────────────────────

export const workflowApi = {
  /** 获取工作流列表 */
  list: () => http.get('/api/workflow/list'),

  /**
   * 运行工作流（SSE 流式，返回 Response 对象供调用方读取）
   * @param {object} payload - { inputs, workflow_type, user, response_mode }
   * @param {AbortSignal} signal
   */
  run: (payload, signal) =>
    fetch(`${BASE_URL}/api/workflow/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify({ ...payload, response_mode: 'streaming' }),
      signal,
      cache: 'no-store',
    }),
}

// ── 碎片记录 API ─────────────────────────────────────────────────────────────

export const recordsApi = {
  list: (params = {}) => http.get('/api/records', { params }),
  create: (body) => http.post('/api/records', body),
  get: (id) => http.get(`/api/records/${id}`),
  update: (id, body) => http.put(`/api/records/${id}`, body),
  remove: (id) => http.delete(`/api/records/${id}`),
  bulkDelete: (ids) => http.post('/api/records/bulk_delete', { ids }),
  types: () => http.get('/api/records/types'),
  /** 旧接口兼容（直接执行 SQL INSERT） */
  executeSQL: (sql) => http.post('/api/records/execute', { sql }),
}

// ── 聊天历史 API ──────────────────────────────────────────────────────────────

export const historyApi = {
  listSessions: (params = {}) => http.get('/api/history/sessions', { params }),
  createSession: (body) => http.post('/api/history/sessions', body),
  getSession: (id) => http.get(`/api/history/sessions/${id}`),
  renameSession: (id, name) => http.put(`/api/history/sessions/${id}`, { session_name: name }),
  deleteSession: (id) => http.delete(`/api/history/sessions/${id}`),
  addMessage: (sessionId, body) => http.post(`/api/history/sessions/${sessionId}/messages`, body),
  toggleFavorite: (msgId) => http.put(`/api/history/messages/${msgId}/favorite`),
  listFavorites: (params = {}) => http.get('/api/history/favorites', { params }),
  exportSession: (id, format = 'json') =>
    http.post(`/api/history/sessions/${id}/export`, { format }),
  /** 创建单条历史记录（简化版） */
  create: (body, config = {}) => http.post('/api/history/messages', body, config),
}

// ── 统计 API ─────────────────────────────────────────────────────────────────

export const statsApi = {
  overview: (params = {}) => http.get('/api/stats/overview', { params }),
  daily: (params = {}) => http.get('/api/stats/daily', { params }),
  workflows: (params = {}) => http.get('/api/stats/workflows', { params }),
  heatmap: (params = {}) => http.get('/api/stats/heatmap', { params }),
  topRecords: (params = {}) => http.get('/api/stats/top_records', { params }),
  keywords: (params = {}) => http.get('/api/stats/keywords', { params }),
}

// ── 健康检查 ─────────────────────────────────────────────────────────────────

export const healthApi = {
  check: () => http.get('/health'),
}

export default http
