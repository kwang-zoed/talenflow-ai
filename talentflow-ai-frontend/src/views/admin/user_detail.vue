<template>
  <div class="user-detail-container">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>用户详情</span>
          <el-button @click="goBack">返回</el-button>
        </div>
      </template>
      
      <el-descriptions v-if="userData" title="基本信息" :column="2" border>
        <el-descriptions-item label="ID">{{ userData.id }}</el-descriptions-item>
        <el-descriptions-item label="用户名">{{ userData.full_name || userData.username }}</el-descriptions-item>
        <el-descriptions-item label="登录账号">{{ userData.username }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ userData.email }}</el-descriptions-item>
        <el-descriptions-item label="角色">
          <el-tag :type="userData.role === 1 ? 'danger' : 'success'">
            {{ userData.role_label }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="userData.is_active ? 'success' : 'info'">
            {{ userData.is_active ? '正常' : '封禁' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ userData.created_at }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router' // 1. 导入 useRoute 和 useRouter
import request from '../../utils/request'

const route = useRoute() // 2. 获取当前路由信息
const router = useRouter()
const userData = ref(null)
const loading = ref(true)

onMounted(async () => {
  const userId = route.params.id // 3. 从路由参数中获取 id
  try {
    // 4. 根据 ID 请求用户详情数据
    const res = await request.get(`/admin/users/${userId}`)
    userData.value = res
  } catch (error) {
    // 处理错误，例如用户不存在
  } finally {
    loading.value = false
  }
})

const goBack = () => {
  router.back() // 5. 返回上一页
}
</script>

<style scoped>
.user-detail-container { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>