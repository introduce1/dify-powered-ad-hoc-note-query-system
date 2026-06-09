# 个人碎片数据管理系统 v2.0

本项目是一个面向知识录入与业务查询的智能应用，采用 `Vue 3 + Flask + MySQL + Dify` 技术栈。  
系统提供三类工作流（随记随查 / 多轮对话 / 生产记录查询），并打通会话历史、碎片数据管理和统计分析，形成从“提问 -> 查询/回答 -> 归档 -> 分析”的完整闭环。

---

## 1. 系统功能总览

### 1.1 智能对话
- 支持三个工作流切换：`suijisuicha`、`duolunduihua`、`shengchanjilu`
- 后端通过 `/api/workflow/run` 代理 Dify，前端以 SSE 实时展示输出
- 支持会话上下文（conversation_id）记忆与重置

### 1.2 历史会话
- 会话分页、筛选、重命名、删除
- 消息收藏与收藏列表
- 会话导出（JSON / Markdown）

### 1.3 碎片记录
- `zhihiku` 记录表的增删改查、批量删除、类型聚合
- 兼容旧 SQL 执行入口 `/api/records/execute`
- 按工作流控制允许访问的数据表，避免跨业务误查

### 1.4 统计看板
- 总览指标、近 N 天趋势、工作流占比
- 活跃热力图、高频关键词、最近记录

---

## 2. 系统核心

系统核心是三件事：

1. **统一工作流接入**：前端只管传 `workflow_type` 和输入参数，后端统一适配 Dify 接口差异（chatflow / workflow）。
2. **流式结果中枢**：后端负责解析复杂 SSE 事件并提取有效文本，前端只做展示与交互。
3. **数据闭环沉淀**：对话结果写入历史与统计表，支撑后续检索、分析和运营看板。

---

## 3. 项目文件架构

```text
现阶段工程文件/
├─ README.md
├─ backend/
│  ├─ main.py                 # Flask 入口，注册蓝图、健康检查、兼容路由
│  ├─ config.py               # 环境配置、数据库配置、Dify 工作流配置
│  ├─ db.py                   # MySQL 连接与 query/execute 封装，初始化核心表
│  ├─ routes/
│  │  ├─ __init__.py          # 蓝图注册
│  │  ├─ workflow.py          # 工作流代理与 SSE 转发
│  │  ├─ records.py           # 碎片记录 CRUD + SQL 兼容执行
│  │  ├─ history.py           # 会话与消息管理
│  │  └─ stats.py             # 统计分析接口
│  ├─ init_zhihiku.sql        # 知识表初始化
│  ├─ init_production_data.sql# 生产记录演示表与数据
│  ├─ init_demo_data.sql      # 业务演示基础表与数据
│  ├─ knowledge_base_tables.md
│  ├─ knowledge_base_tables.txt
│  └─ requirements.txt
├─ frontend/
│  ├─ package.json
│  ├─ vite.config.js
│  ├─ index.html
│  └─ src/
│     ├─ main.js
│     ├─ App.vue
│     ├─ api/index.js         # 前端 API 封装
│     ├─ router/index.js      # 路由定义
│     ├─ stores/app.js        # 全局状态（主题、用户、侧边栏）
│     ├─ views/
│     │  ├─ ChatView.vue
│     │  ├─ HistoryView.vue
│     │  ├─ RecordsView.vue
│     │  └─ StatsView.vue
│     └─ components/
│        ├─ Sidebar.vue
│        ├─ NavBar.vue
│        └─ MessageItem.vue
└─ DSL/                        # Dify 工作流 DSL 与校验脚本
```

---

## 4. 前端模块说明

### 4.1 应用入口与基础框架
- `frontend/src/main.js`：注册 Vue、Pinia、Router、Element Plus、Marked
- `frontend/src/App.vue`：页面骨架（侧边栏 + 顶栏 + 主视图）
- `frontend/src/router/index.js`：四大页面路由 `chat/history/records/stats`

### 4.2 全局状态
- `frontend/src/stores/app.js`
  - 主题模式（dark mode）
  - 侧边栏折叠状态
  - 本地用户信息（`empId` / `empName`）
  - 后端在线状态标记

### 4.3 业务视图
- `ChatView.vue`：三工作流对话入口、SSE 流式展示、会话本地缓存、重试/取消
- `HistoryView.vue`：历史会话列表、消息详情、收藏与导出
- `RecordsView.vue`：碎片记录管理页（检索、筛选、编辑、删除）
- `StatsView.vue`：统计图表展示（趋势、占比、热力图、关键词）

### 4.4 API 封装
- `frontend/src/api/index.js`
  - `workflowApi`：工作流列表、流式运行
  - `recordsApi`：碎片记录与兼容 SQL 执行
  - `historyApi`：会话与消息相关操作
  - `statsApi`：统计图表数据
  - `healthApi`：健康检查

---

## 5. 后端模块说明

### 5.1 启动入口
- `backend/main.py`
  - 创建 Flask 应用，启用 CORS
  - 注册蓝图：`/api/workflow`、`/api/records`、`/api/history`、`/api/stats`
  - 提供 `/health` 与根路由 `/`
  - 提供兼容入口 `/execute -> /api/records/execute`

### 5.2 配置与数据库
- `backend/config.py`
  - 服务地址、端口、数据库连接参数
  - 三个工作流的 Dify 配置（`WORKFLOW_CONFIG`）
- `backend/db.py`
  - 封装 `query/query_one/execute/execute_lastrowid`
  - 初始化核心表：`record`、`zhihiku`、`chat_session`、`chat_message`、`query_stat`

### 5.3 业务路由
- `backend/routes/workflow.py`
  - 负责 Dify 请求代理和 SSE 事件解析
  - 统一提取有效文本并流式回传前端
  - 记录 `query_stat` 统计
- `backend/routes/records.py`
  - `zhihiku` 的 CRUD 与筛选
  - SQL 兼容执行接口 `/api/records/execute`
  - 工作流级表访问白名单控制
  - 常见 SQL 错误（如字段不存在）可读化返回
- `backend/routes/history.py`
  - 会话与消息管理、收藏、导出
  - 会话删除时级联消息逻辑
- `backend/routes/stats.py`
  - 总览、趋势、工作流分布、热力图、关键词统计

---

## 6. 核心数据流

### 6.1 智能对话链路
1. 前端 `ChatView` 收集输入与 `workflow_type`
2. `POST /api/workflow/run` 进入后端
3. 后端按工作流配置请求 Dify 并消费 SSE
4. 解析有效文本片段后实时回传前端
5. 前端渲染消息并异步写入历史

### 6.2 生产记录查询链路
1. LLM/工作流生成 SQL
2. 调用 `/api/records/execute`
3. 后端校验 SQL 类型与可访问表
4. 执行查询并返回数据；字段错误时返回可读错误信息

### 6.3 统计链路
1. 工作流调用过程写入 `query_stat`
2. 记录与会话数据进入 `zhihiku/chat_session/chat_message`
3. `stats` 路由聚合数据供前端看板展示

---

## 7. 关键实现细节（How）

这一节对应“这些功能具体怎么落地”的实现说明，按代码真实行为描述。

### 7.1 对话与流式输出是怎么实现的

#### 前端（`ChatView.vue`）
- 用户发送后进入 `startStream()`，按 `workflow_type` 组装不同 `inputs`
- 调用 `workflowApi.run()`，底层使用 `fetch` 请求 `/api/workflow/run`，并声明 `Accept: text/event-stream`
- 前端通过 `ReadableStream + getReader()` 持续读取流，并以 `\n\n` 拆分 SSE 事件
- 每个事件中提取 `data:` JSON，读取 `answer/text` 字段作为文本块
- 文本块通过 `mergeStreamText()` 合并，避免重复片段和回流覆盖
- 渲染前走 `buildDisplayText()`，会做去重和 SQL 回显清洗，尽量只展示结果文本

#### 后端（`routes/workflow.py`）
- `run_workflow()` 读取 `workflow_type/user/conversation_id/inputs`
- 根据 `Config.WORKFLOW_CONFIG` 判断当前是 `chatflow` 还是 `workflow` 应用类型
- 对不同工作流做输入适配：
  - `duolunduihua`：`query/question` 转换为 `sys.query`
  - `shengchanjilu`：优先保障 `question` 字段存在
- 调用 `generate_stream()` 代理 Dify SSE，逐事件解析并向前端透传统一格式
- 事件优先级：`obj.event` > `SSE event 行` > 字段推断（`_infer_event_type`）
- 在 `text_chunk/message/agent_message` 时提取文本，`workflow_finished` 时兜底提取最终输出

### 7.2 conversation_id 上下文记忆怎么做

- 后端维护 `_conversation_store: {(emp_id, workflow_type): conversation_id}`
- 前端不传 `conversation_id` 时，后端按 `(用户, 工作流)` 自动恢复历史上下文
- 收到 Dify 返回的新 `conversation_id` 后实时更新内存映射
- 前端“清屏”时会调用 `/api/workflow/reset`，清除当前用户或当前工作流的上下文记忆

这套机制的目标是：前端偶尔漏传 `conversation_id` 也不会丢上下文。

### 7.3 生产记录 SQL 查询是怎么安全控制的

核心入口是 `POST /api/records/execute`（`routes/records.py`）。

- 仅允许 `INSERT` 和 `SELECT`，其他语句直接拒绝（403）
- `_extract_sql_tables()` 从 SQL 中提取 `INSERT INTO / FROM / JOIN` 涉及表名
- 根据 `workflow_type` 命中 `WORKFLOW_ALLOWED_TABLES` 做白名单校验
- 若包含未授权表，返回 403 并给出 `blocked_tables`
- `SELECT` 执行异常时，`_format_select_exception()` 会识别常见错误：
  - 如 `Unknown column ...`，返回 400 并可附带该表 `SHOW COLUMNS` 字段提示

这部分保证了“多工作流多数据表”并存时，既可查又不会串库乱查。

### 7.4 历史会话是怎么持久化的

前端在对话完成后调用 `historyApi.create()`，对应后端 `POST /api/history/messages`。

- 请求体：`emp_id/workflow_type/query_text/response_text/session_id?`
- 后端优先复用有效 `session_id`，否则自动新建会话
- 同时写入两条消息（用户 + AI）
- 自动更新 `chat_session.msg_count` 与 `update_time`
- 前端带有超时静默重试，不阻塞当前对话体验

前端还会把当前工作流对话缓存到 localStorage（按 `workflow + emp_id` 隔离，24 小时有效），用于页面刷新后的快速恢复。

### 7.5 统计模块是怎么聚合的

统计接口集中在 `routes/stats.py`：

- `overview`：聚合 `zhihiku/chat_session/chat_message/query_stat` 的总体指标
- `daily`：查询 `query_stat` 与 `zhihiku` 的日粒度数据，并补齐缺失日期
- `workflows`：按 `workflow_type` 分组计数，结合配置映射工作流中文标签
- `heatmap`：近 84 天将“查询量 + 新增记录量”按日期叠加
- `keywords`：对近 30 天 `query_text` 做简易中文分词（2 字以上）+ 停用词过滤，输出 Top 20

### 7.6 前端为什么能“看起来很顺滑”

- SSE 分片在浏览器端做增量渲染，不需要等待完整响应
- 使用 `requestAnimationFrame` 节流 DOM 更新，避免每个 chunk 都触发重排
- 接口层统一在 `api/index.js` 处理错误提示与静默失败场景，减少页面逻辑噪声
- 聊天结果做展示清洗（去重、去 SQL 回显），降低工作流中间文本对用户的干扰

---

## 8. 关键数据表

### 8.1 系统核心表
- `zhihiku`：碎片记录主表
- `chat_session`：会话表
- `chat_message`：消息表
- `query_stat`：查询统计流水

### 8.2 生产记录相关表（来自 `init_production_data.sql`）
- `drawing_record`：出图记录
- `production_value`：月度产值
- `production_plan`：年度/季度计划
- `work_hours`：工时记录
- `project_progress`：项目进度

---

## 9. 运行方式

### 9.1 后端
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### 9.2 前端
```bash
cd frontend
npm install
npm run dev
```

默认前端开发端口为 `3000`，后端默认端口为 `8888`。  
可通过 `backend/config.py` 对应环境变量覆盖配置。

---

## 10. 二次开发建议

- 新增工作流时，优先在 `config.py` 注册，再补充 `workflow.py` 参数适配逻辑
- 新增查询场景时，维护好 `records.py` 的表白名单与字段提示
- 生产记录场景建议同步维护 `knowledge_base_tables.md`，降低 SQL 生成错误率
- 若需要更严格结果控制，可在前端 `ChatView.vue` 仅展示业务节点 `result` 字段

