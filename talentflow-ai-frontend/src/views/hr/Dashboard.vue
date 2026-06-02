<template>
  <div class="dashboard-container" v-loading="loading">
    <!-- 1. 关键指标卡片区域 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-box bg-blue"><el-icon><Briefcase /></el-icon></div>
            <div class="text-box">
              <p class="label">发布任务总数</p>
              <p class="number">{{ stats.total_tasks }}</p>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-box bg-green"><el-icon><Clock /></el-icon></div>
            <div class="text-box">
              <p class="label">进行中</p>
              <p class="number">{{ stats.in_progress }}</p>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-box bg-orange"><el-icon><Bell /></el-icon></div>
            <div class="text-box">
              <p class="label">待审核简历</p>
              <p class="number">{{ stats.pending_review }}</p>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-box bg-purple"><el-icon><Check /></el-icon></div>
            <div class="text-box">
              <p class="label">已完成</p>
              <p class="number">{{ stats.completed }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 2. 快捷入口与近期动态 -->
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="never" header="近期任务动态">
          <!-- 如果没有数据，显示空状态 -->
          <el-empty v-if="activities.length === 0" description="暂无近期动态" />
          <el-timeline v-else>
            <el-timeline-item
              v-for="(item, index) in activities"
              :key="index"
              :timestamp="item.date"
              placement="top"
            >
              <el-card>
                <h4>{{ item.title }}</h4>
                <p>{{ item.description }}</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never" header="快捷操作">
          <div class="quick-actions">
            <el-button type="primary" icon="Plus" class="w-100 mb-2">发布新任务</el-button>
            <el-button icon="Search" class="w-100 mb-2">查看人才库</el-button>
            <el-button icon="Wallet" class="w-100">充值/结算</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Briefcase, Clock, Bell, Check, Plus, Search, Wallet } from '@element-plus/icons-vue'

import axios from '../../utils/request';

// 定义响应式数据
const loading = ref(false)
const stats = ref({
  total_tasks: 0,
  in_progress: 0,
  pending_review: 0,
  completed: 0
})
const activities = ref([])

// 获取统计数据的函数
const fetchStats = async () => {
  try {
    const res = await axios.get('/mentor/dashboard/stats')
    stats.value = res
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

// 获取近期动态的函数
const fetchActivities = async () => {
  try {
    const res = await axios.get('/mentor/dashboard/activities')
    activities.value = res.activities
  } catch (error) {
    console.error('获取近期动态失败:', error)
  }
}

// 页面挂载时调用接口
onMounted(() => {
  loading.value = true
  // 使用 Promise.all 并行请求两个接口，提高加载速度
  Promise.all([fetchStats(), fetchActivities()]).finally(() => {
    loading.value = false
  })
})
</script>

<style scoped>
.mb-4 { margin-bottom: 20px; }
.mb-2 { margin-bottom: 10px; }
.w-100 { width: 100%; }

.stat-card {
  border-radius: 8px;
}
.card-content {
  display: flex;
  align-items: center;
}
.icon-box {
  width: 50px;
  height: 50px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
  margin-right: 15px;
}
.bg-blue { background-color: #409EFF; }
.bg-green { background-color: #67C23A; }
.bg-orange { background-color: #E6A23C; }
.bg-purple { background-color: #909399; }

.number { font-size: 24px; font-weight: bold; color: #303133; margin: 0; }
.label { font-size: 14px; color: #606266; margin: 0; }
</style>