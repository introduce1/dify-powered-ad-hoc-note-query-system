<template>
  <div class="records-view">
    <!-- 工具栏 -->
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索记录内容..."
        clearable
        prefix-icon="Search"
        class="search-input"
        @input="debouncedFetch"
      />
      <el-select v-model="filterType" placeholder="全部类型" clearable @change="fetchRecords">
        <el-option v-for="t in recTypes" :key="t.rec_type" :label="`${t.rec_type} (${t.count})`" :value="t.rec_type" />
      </el-select>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon> 新增记录
      </el-button>
      <el-button :disabled="!selectedIds.length" type="danger" plain @click="bulkDelete">
        批量删除 ({{ selectedIds.length }})
      </el-button>
    </div>

    <!-- 记录表格 -->
    <el-table
      :data="records"
      v-loading="loading"
      stripe
      @selection-change="onSelectionChange"
      style="width: 100%"
    >
      <el-table-column type="selection" width="45" />
      <el-table-column prop="content" label="记录内容" min-width="300" show-overflow-tooltip />
      <el-table-column prop="rec_type" label="类型" width="130">
        <template #default="{ row }">
          <el-tag size="small">{{ row.rec_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="emp_id" label="员工" width="80" align="center" />
      <el-table-column prop="product_code" label="产品编号" width="110" />
      <el-table-column prop="create_time" label="创建时间" width="170" />
      <el-table-column label="操作" width="140" align="center">
        <template #default="{ row }">
          <el-button text size="small" @click="editRecord(row)">编辑</el-button>
          <el-popconfirm title="确认删除？" @confirm="deleteRecord(row.id)">
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
        layout="prev, pager, next, total"
        @current-change="fetchRecords"
      />
    </div>

    <!-- 新增 / 编辑弹窗 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingRecord ? '编辑记录' : '新增记录'"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" label-width="80px">
        <el-form-item label="内容" required>
          <el-input v-model="formData.content" type="textarea" :rows="4" placeholder="请输入记录内容" />
        </el-form-item>
        <el-form-item label="类型">
          <el-input v-model="formData.rec_type" placeholder="如：备忘、生产检查记录" />
        </el-form-item>
        <el-form-item label="产品编号">
          <el-input v-model="formData.product_code" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRecord">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { recordsApi } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const records = ref([])
const recTypes = ref([])
const loading = ref(false)
const keyword = ref('')
const filterType = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const selectedIds = ref([])

const showCreateDialog = ref(false)
const editingRecord = ref(null)
const saving = ref(false)
const formData = ref({ content: '', rec_type: '备忘', product_code: '' })

let debounceTimer = null
function debouncedFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchRecords, 300)
}

async function fetchRecords() {
  loading.value = true
  try {
    const res = await recordsApi.list({
      keyword: keyword.value,
      rec_type: filterType.value,
      emp_id: appStore.empId,
      page: page.value,
      page_size: pageSize,
    })
    records.value = res.data || []
    total.value = res.total || 0
  } catch { /* handled */ } finally {
    loading.value = false
  }
}

async function fetchTypes() {
  try {
    const res = await recordsApi.types()
    recTypes.value = res.types || []
  } catch { /* handled */ }
}

function onSelectionChange(rows) {
  selectedIds.value = rows.map((r) => r.id)
}

function editRecord(row) {
  editingRecord.value = row
  formData.value = {
    content: row.content,
    rec_type: row.rec_type,
    product_code: row.product_code || '',
  }
  showCreateDialog.value = true
}

function closeDialog() {
  showCreateDialog.value = false
  editingRecord.value = null
  formData.value = { content: '', rec_type: '备忘', product_code: '' }
}

async function saveRecord() {
  if (!formData.value.content.trim()) {
    ElMessage.warning('内容不能为空')
    return
  }
  saving.value = true
  try {
    if (editingRecord.value) {
      await recordsApi.update(editingRecord.value.id, {
        ...formData.value,
        emp_id: appStore.empId,
      })
      ElMessage.success('更新成功')
    } else {
      await recordsApi.create({
        ...formData.value,
        emp_id: appStore.empId,
      })
      ElMessage.success('创建成功')
    }
    closeDialog()
    fetchRecords()
    fetchTypes()
  } catch { /* handled */ } finally {
    saving.value = false
  }
}

async function deleteRecord(id) {
  try {
    await recordsApi.remove(id)
    ElMessage.success('删除成功')
    fetchRecords()
    fetchTypes()
  } catch { /* handled */ }
}

async function bulkDelete() {
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条记录？`, '批量删除')
    await recordsApi.bulkDelete(selectedIds.value)
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    fetchRecords()
    fetchTypes()
  } catch { /* cancelled */ }
}

onMounted(() => {
  fetchRecords()
  fetchTypes()
})
</script>

<style scoped>
.records-view {
  max-width: 1200px;
  margin: 0 auto;
}

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.search-input {
  width: 260px;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}
</style>
