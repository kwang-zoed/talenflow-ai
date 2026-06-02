<template>
  <div class="user-manager-container">
    <!-- 顶部搜索栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="searchForm" class="demo-form-inline">
        <el-form-item label="关键词">
          <el-input 
            v-model="searchForm.keyword" 
            placeholder="用户名/姓名" 
            clearable 
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch" icon="Search">查询</el-button>
          <el-button @click="resetSearch" icon="Refresh">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 用户列表表格 -->
    <el-card shadow="never" class="table-card">
      <el-table 
        :data="userList" 
        stripe 
        style="width: 100%" 
        v-loading="loading"
      >
        <el-table-column prop="id" label="ID" width="60" />
        
        <!-- 用户名 -->
        <el-table-column prop="full_name" label="用户名" width="150">
          <template #default="scope">
            <div class="user-account">{{ scope.row.username }}</div>
          </template>
        </el-table-column>

        <el-table-column prop="email" label="邮箱" min-width="180" />

        <!-- 角色列：根据 role 字段显示不同标签 -->
        <el-table-column prop="role" label="角色" width="100">
          <template #default="scope">
            <el-tag 
              :type="scope.row.role === 1 ? 'danger' : (scope.row.role === 2 ? 'warning' : 'success')" 
              effect="light"
            >
              {{ scope.row.role === 1 ? '管理员' : (scope.row.role === 2 ? 'HR' : '求职者') }}
            </el-tag>
          </template>
        </el-table-column>

        <!-- 状态列：Switch 开关 -->
        <el-table-column prop="is_active" label="状态" width="140">
          <template #default="scope">
            <el-switch
              v-model="scope.row.is_active"
              active-text="正常"
              inactive-text="封禁"
              :active-value="true"
              :inactive-value="false"
              :disabled="scope.row.role === 1 && scope.row.is_active"
              @change="handleStatusChange(scope.row)"
            />
            <div v-if="scope.row.role === 1 && scope.row.is_active" style="font-size: 10px; color: #909399; margin-top: 2px;">管理员不可封禁</div>
          </template>
        </el-table-column>

        <!-- 操作列 -->
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button link type="primary" size="small" @click="handleEdit(scope.row)">详情</el-button>
            <el-button link type="danger" size="small" @click="handleResetPassword(scope.row)">重置密码</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          background
          layout="prev, pager, next"
          :total="total"
          :page-size="pageSize"
          v-model:current-page="currentPage"
          @current-change="fetchData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from '../../utils/request' // 假设你封装了axios

import { useRouter } from 'vue-router' // 1. 导入 useRouter

const router = useRouter() // 2. 获取路由实例

// --- 状态定义 ---
const userList = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = 10

const searchForm = reactive({
  keyword: ''
})

// --- 数据获取 ---
const fetchData = async () => {
  loading.value = true
  try {
    const res = await axios.get('/admin/users', {
      params: {
        skip: (currentPage.value - 1) * pageSize,
        limit: pageSize,
        keyword: searchForm.keyword
      }
    })
    userList.value = res
    // 假设后端返回了总数，如果没有，可以手动计算
    // total.value = res.data.length 
  } catch (error) {
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

// --- 事件处理 ---
const handleSearch = () => {
  currentPage.value = 1
  fetchData()
}

const resetSearch = () => {
  searchForm.keyword = ''
  handleSearch()
}

// 修改状态
const handleStatusChange = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要${row.is_active ? '启用' : '封禁'}该用户吗？`, 
      '警告',
      { type: 'warning' }
    )
    await axios.put(`/admin/users/${row.id}/status?is_active=${row.is_active}`)
    ElMessage.success('状态更新成功')
  } catch (error) {
    // 如果取消或报错，回滚开关状态
    row.is_active = !row.is_active
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

// 重置密码
const handleResetPassword = (row) => {
  ElMessageBox.confirm(
    `确定要重置用户 "${row.username}" 的密码吗？重置后密码将变为默认值。`,
    '重置密码',
    { type: 'warning', confirmButtonText: '确定重置' }
  ).then(async () => {
    await axios.put(`/admin/users/${row.id}/reset-password`)
    ElMessage.success('密码已重置为 123456')
  }).catch(() => {})
}

const handleEdit = (row) => {
    // 3. 跳转到名为 'UserDetail' 的路由，并传递 id 参数
  router.push({ name: 'UserDetail', params: { id: row.id } })
}

// 初始化
onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.user-manager-container {
  padding: 20px;
}

.search-card {
  margin-bottom: 20px;
}

.user-name {
  font-weight: bold;
  color: #303133;
}

.user-account {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>