<template>
  <div class="stats-view">
    <!-- 总览卡片 -->
    <el-row :gutter="16" class="overview-row">
      <el-col :span="6" v-for="card in overviewCards" :key="card.label">
        <div class="stat-card">
          <div class="stat-icon" :style="{ background: card.bg }">
            <el-icon :size="24" :color="card.color"><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ card.value }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="16">
      <el-col :span="16">
        <div class="chart-card">
          <h3>每日趋势（近30天）</h3>
          <div ref="dailyChartRef" class="chart-box"></div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="chart-card">
          <h3>工作流使用占比</h3>
          <div ref="pieChartRef" class="chart-box"></div>
        </div>
      </el-col>
    </el-row>

    <!-- 最近记录 & 高频关键词 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="14">
        <div class="chart-card">
          <h3>最近新增记录</h3>
          <el-table :data="topRecords" stripe size="small" max-height="320">
            <el-table-column prop="content_short" label="内容" min-width="240" show-overflow-tooltip />
            <el-table-column prop="rec_type" label="类型" width="110">
              <template #default="{ row }"><el-tag size="small">{{ row.rec_type }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="create_time" label="时间" width="160" />
          </el-table>
        </div>
      </el-col>
      <el-col :span="10">
        <div class="chart-card">
          <h3>高频关键词</h3>
          <div class="keyword-cloud" v-if="keywords.length">
            <span
              v-for="kw in keywords"
              :key="kw.word"
              class="keyword-tag"
              :style="{ fontSize: keywordSize(kw.count) + 'px', opacity: 0.6 + kw.count / maxKeywordCount * 0.4 }"
            >
              {{ kw.word }}
            </span>
          </div>
          <el-empty v-else description="暂无数据" :image-size="60" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { statsApi } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const overview = ref({})
const topRecords = ref([])
const keywords = ref([])
const dailyData = ref([])
const workflowData = ref([])

const dailyChartRef = ref(null)
const pieChartRef = ref(null)
let dailyChart = null
let pieChart = null

const maxKeywordCount = computed(() => {
  return Math.max(...keywords.value.map((k) => k.count), 1)
})

function keywordSize(count) {
  return 14 + (count / maxKeywordCount.value) * 16
}

const overviewCards = computed(() => [
  { label: '碎片记录', value: overview.value.total_records ?? '-', icon: 'DocumentCopy', bg: '#e6f4ff', color: '#409eff' },
  { label: '聊天会话', value: overview.value.total_sessions ?? '-', icon: 'ChatDotRound', bg: '#eefbf3', color: '#67c23a' },
  { label: '今日查询', value: overview.value.today_queries ?? '-', icon: 'Search', bg: '#fef0e6', color: '#e6a23c' },
  { label: '今日新增', value: overview.value.today_records ?? '-', icon: 'CirclePlus', bg: '#fde2e2', color: '#f56c6c' },
])

async function fetchAll() {
  const empId = appStore.empId
  const [ov, daily, wf, top, kw] = await Promise.allSettled([
    statsApi.overview({ emp_id: empId }),
    statsApi.daily({ emp_id: empId }),
    statsApi.workflows({ emp_id: empId }),
    statsApi.topRecords({ emp_id: empId, limit: 10 }),
    statsApi.keywords({ emp_id: empId }),
  ])

  if (ov.status === 'fulfilled') overview.value = ov.value
  if (daily.status === 'fulfilled') dailyData.value = daily.value.data || []
  if (wf.status === 'fulfilled') workflowData.value = wf.value.data || []
  if (top.status === 'fulfilled') topRecords.value = top.value.data || []
  if (kw.status === 'fulfilled') keywords.value = kw.value.data || []

  await nextTick()
  renderDailyChart()
  renderPieChart()
}

function renderDailyChart() {
  if (!dailyChartRef.value) return
  if (!dailyChart) dailyChart = echarts.init(dailyChartRef.value)

  dailyChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['查询量', '新增记录'] },
    grid: { left: 40, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dailyData.value.map((d) => d.day.slice(5)), boundaryGap: false },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '查询量', type: 'line', smooth: true, data: dailyData.value.map((d) => d.count), areaStyle: { opacity: 0.15 }, color: '#409eff' },
      { name: '新增记录', type: 'line', smooth: true, data: dailyData.value.map((d) => d.records), areaStyle: { opacity: 0.15 }, color: '#67c23a' },
    ],
  })
}

function renderPieChart() {
  if (!pieChartRef.value) return
  if (!pieChart) pieChart = echarts.init(pieChartRef.value)

  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      label: { formatter: '{b}\n{d}%' },
      data: workflowData.value.map((d) => ({ name: d.label, value: d.count })),
    }],
  })
}

function handleResize() {
  dailyChart?.resize()
  pieChart?.resize()
}

onMounted(() => {
  fetchAll()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  dailyChart?.dispose()
  pieChart?.dispose()
})
</script>

<style scoped>
.stats-view {
  max-width: 1200px;
  margin: 0 auto;
}

.overview-row {
  margin-bottom: 16px;
}

.stat-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.dark-mode .stat-card {
  background: #1d1d1d;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1d2129;
}

.dark-mode .stat-value {
  color: #e0e0e0;
}

.stat-label {
  font-size: 13px;
  color: #999;
  margin-top: 2px;
}

.chart-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.dark-mode .chart-card {
  background: #1d1d1d;
}

.chart-card h3 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #1d2129;
}

.dark-mode .chart-card h3 {
  color: #e0e0e0;
}

.chart-box {
  height: 300px;
}

.keyword-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 16px 0;
  align-items: center;
}

.keyword-tag {
  color: #409eff;
  cursor: default;
  transition: transform 0.2s;
}

.keyword-tag:hover {
  transform: scale(1.1);
}
</style>
