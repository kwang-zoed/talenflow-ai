<template>
  <div class="applications-page">
    <div class="page-header">
      <h3>我的投递记录</h3>
    </div>

    <el-table :data="applicationList" stripe style="width: 100%" v-loading="loading" empty-text="暂无投递记录">
      <el-table-column prop="title" label="职位/任务" min-width="200">
        <template #default="scope">
          <div class="title-cell">
            <el-tag :type="scope.row.type === '职位' ? 'primary' : 'success'" size="small">
              {{ scope.row.type }}
            </el-tag>
            <span class="title">{{ scope.row.title }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="技能要求" min-width="180">
        <template #default="scope">
          <div class="skills-tags">
            <el-tag
              v-for="(skill, index) in scope.row.skills || []"
              :key="index"
              size="small"
              type="info"
              style="margin-right: 4px; margin-bottom: 4px; display: inline-block;"
            >
              {{ skill }}
            </el-tag>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="applied_at" label="投递时间" width="160">
        <template #default="scope">
          {{ formatDate(scope.row.applied_at) }}
        </template>
      </el-table-column>

      <el-table-column prop="status" label="当前状态" width="120">
        <template #default="scope">
          <el-tag :type="getStatusTag(scope.row.status)">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMyApplications } from '../../../api/user'

const applicationList = ref([])
const loading = ref(false)

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getMyApplications()
    applicationList.value = res.data || res
  } catch (error) {
    ElMessage.error('获取投递记录失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  return dateString.split('T')[0]
}

const getStatusTag = (status) => {
  if (status === '待沟通') return 'warning'
  if (status === '已录用') return 'success'
  if (status === '不合适') return 'info'
  return ''
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.applications-page {
  width: 100%;
  min-height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  background-color: #f5f7fa;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: #fff;
  padding: 15px 20px;
  border-radius: 4px;
}

.page-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-cell .title {
  color: #303133;
  font-weight: 500;
}
</style>
