<template>
  <div class="task-management" v-loading="loading">
    <!-- 顶部操作栏 -->
    <div class="header-actions mb-4">
      <el-button type="primary" icon="Plus" @click="openCreateDialog">发布新任务</el-button>
      <el-input
        v-model="searchQuery"
        placeholder="搜索任务标题..."
        style="width: 240px; margin-left: 10px;"
        clearable
        @keyup.enter="fetchTasks"
      />
    </div>

    <!-- 任务列表表格 -->
    <el-table :data="taskList" stripe style="width: 100%" border>
      <el-table-column prop="id" label="ID" width="60" align="center" />
      <el-table-column prop="title" label="任务标题" min-width="180" />
      <el-table-column prop="category" label="分类" width="100" align="center" />
      <el-table-column prop="price" label="预算" width="100" align="center">
        <template #default="scope">¥{{ (scope.row.price / 100).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="difficulty" label="难度" width="80" align="center" />
      <el-table-column prop="status" label="状态" width="100" align="center">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)">
            {{ getStatusLabel(scope.row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="投递数" width="80" align="center">
        <template #default="scope">
          {{ scope.row.applications ? scope.row.applications.length : 0 }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="发布时间" width="170" align="center">
        <template #default="scope">
          {{ new Date(scope.row.created_at).toLocaleString() }}
        </template>
      </el-table-column>

      <el-table-column label="操作" fixed="right" width="200" align="center">
        <template #default="scope">
          <el-button size="small" type="primary" link @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" link @click="handleDelete(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination mt-4" style="display: flex; justify-content: flex-end;">
      <el-pagination
        background
        layout="prev, pager, next, total"
        :total="total"
        :page-size="10"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 发布/编辑 任务的弹窗 (复用同一个弹窗) -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑任务' : '发布新任务'"
      width="600px"
      @close="resetForm"
    >
      <el-form :model="taskForm" label-width="100px">
        <el-form-item label="任务标题" required>
          <el-input v-model="taskForm.title" placeholder="请输入任务标题" />
        </el-form-item>
        <el-form-item label="任务描述" required>
          <el-input v-model="taskForm.description" type="textarea" :rows="3" placeholder="请输入详细描述" />
        </el-form-item>
        <el-form-item label="分类" required>
          <el-input v-model="taskForm.category" placeholder="如：前端、设计、后端" />
        </el-form-item>
        <el-form-item label="预算(分)" required>
          <el-input-number v-model="taskForm.price" :min="0" :step="100" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="难度等级">
          <el-select v-model="taskForm.difficulty" placeholder="请选择难度" style="width: 100%;">
            <el-option label="初级" value="初级" />
            <el-option label="中级" value="中级" />
            <el-option label="高级" value="高级" />
          </el-select>
        </el-form-item>
        <el-form-item label="截止天数" required>
          <el-input-number v-model="taskForm.duration" :min="1" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="状态" v-if="isEdit">
          <el-select v-model="taskForm.status" placeholder="请选择状态" style="width: 100%;">
            <el-option label="待审核" :value="0" />
            <el-option label="进行中" :value="1" />
            <el-option label="已暂停" :value="2" />
            <el-option label="已完成" :value="3" disabled />
            <el-option label="已驳回" :value="4" disabled />
            <el-option label="已过期" :value="5" disabled />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitTask">确认提交</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import request from '../../utils/request' // 确保你的 axios 封装路径正确

// --- 基础状态 ---
const loading = ref(false)
const searchQuery = ref('')
const taskList = ref([])
const total = ref(0)
const currentPage = ref(1)

// --- 弹窗与表单状态 ---
const dialogVisible = ref(false)
const isEdit = ref(false) // 区分是发布还是编辑
const taskForm = ref({
  id: null,
  title: '',
  description: '',
  category: '',
  price: 0,
  difficulty: '中级',
  duration: 7,
  status: 1  // 统一用数字类型
  // skills: [], // 显式加上这个字段，防止后端校验报错
})

// --- 获取任务列表 ---
const fetchTasks = async () => {
  loading.value = true
  try {
    const res = await request.get('/mentor/tasks', {
      params: {
        skip: (currentPage.value - 1) * 10,
        limit: 10,
        title: searchQuery.value
      }
    })
    // 兼容后端返回数组或 { data: [...], total: xx } 的情况
    taskList.value = Array.isArray(res) ? res : (res.items || res)
    total.value = res.total || taskList.value.length
  } catch (error) {
    console.error('获取任务列表失败:', error)
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

// --- 状态码转换 ---
const getStatusLabel = (status) => {
  const map = { 0: '待审核', 1: '进行中', 2: '已暂停', 3: '已完成', 4: '已驳回', 5: '已过期' }
  return map[status] || '未知'
}
const getStatusType = (status) => {
  const map = { 0: 'warning', 1: 'success', 2: 'info', 3: '', 4: 'danger', 5: 'danger' }
  return map[status] || 'info'
}

// --- 打开弹窗（发布） ---
const openCreateDialog = () => {
  isEdit.value = false
  dialogVisible.value = true
}

// --- 打开弹窗（编辑） ---
const handleEdit = (row) => {
  isEdit.value = true
  // 浅拷贝数据到表单，防止修改时直接影响表格显示
  const editedRow = { ...row }
  
  // 统一把 status 转成数字类型，避免类型不匹配问题
  if (editedRow.status !== undefined && editedRow.status !== null) {
    editedRow.status = Number(editedRow.status)
  }
  
  taskForm.value = editedRow
  dialogVisible.value = true
}

// --- 提交任务（发布或编辑） ---
const submitTask = async () => {
  try {
    if (isEdit.value) {
      // 编辑请求 (PUT)
      await request.put(`/mentor/tasks/${taskForm.value.id}`, taskForm.value)
      ElMessage.success('任务修改成功！')
    } else {
      const payload = { ...taskForm.value }
      if (!payload.skills) payload.skills = []
      // 发布请求 (POST)
      await request.post('/mentor/tasks', taskForm.value)
      ElMessage.success('任务发布成功！')
    }
    dialogVisible.value = false
    fetchTasks() // 刷新列表
  } catch (error) {
    console.error(error)
    ElMessage.error(isEdit.value ? '修改失败' : '发布失败')
  }
}

// --- 删除任务 ---
const handleDelete = (id) => {
  ElMessageBox.confirm('确定要删除该任务吗？删除后不可恢复！', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    loading.value = true
    try {
      await request.delete(`/mentor/tasks/${id}`)
      ElMessage.success('删除成功')
      fetchTasks()
    } catch (error) {
      ElMessage.error('删除失败')
    } finally {
      loading.value = false
    }
  })
}

// --- 分页切换 ---
const handlePageChange = (page) => {
  currentPage.value = page
  fetchTasks()
}

// --- 重置表单 ---
const resetForm = () => {
  taskForm.value = { id: null, title: '', description: '', category: '', price: 0, difficulty: '中级', duration: 7, status: 1 }
}

// --- 页面挂载时拉取数据 ---
onMounted(() => {
  fetchTasks()
})
</script>

<style scoped>
.task-management {
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
}
.mb-4 { margin-bottom: 20px; }
.mt-4 { margin-top: 20px; }
</style>