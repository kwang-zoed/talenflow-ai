<template>
  <div class="detail-container" v-loading="loading">
    <el-card v-if="task" class="detail-card" shadow="hover">
      
      <!-- 1. 顶部导航栏 -->
      <div class="header">
        <el-button text icon="ArrowLeft" @click="$router.back()">返回任务列表</el-button>
        <el-tag :type="getTagColor(task.category)" effect="dark" size="large">
          {{ task.category }}
        </el-tag>
      </div>

      <!-- 2. 核心信息：标题 + 赏金 -->
      <div class="main-info">
        <div class="title-section">
          <h2 class="title">{{ task.title }}</h2>
          <div class="meta-text">发布时间：{{ task.created_at }}</div>
        </div>
        <div class="price-section">
          <span class="symbol">¥</span>
          <span class="price">{{ task.price }}</span>
        </div>
      </div>

      <!-- 3. 任务描述 -->
      <div class="section">
        <h4 class="section-title">任务详情</h4>
        <div class="desc-content">
          {{ task.description }}
        </div>
      </div>

      <!-- 4. 详细参数：工期、难度、技能 -->
      <div class="section">
        <h4 class="section-title">任务要求</h4>
        <div class="meta-grid">
          <!-- 工期 -->
          <div class="meta-item">
            <div class="label"><el-icon><Clock /></el-icon> 工期要求</div>
            <div class="value">{{ task.duration || task.deadline_days }} 天</div>
          </div>
          
          <!-- 难度 -->
          <div class="meta-item">
            <div class="label"><el-icon><TrendCharts /></el-icon> 难度系数</div>
            <div class="value">{{ task.difficulty || '中等' }}</div>
          </div>

          <!-- 技能要求 (重点新增) -->
          <div class="meta-item full-width" v-if="task.skills">
            <div class="label"><el-icon><CollectionTag /></el-icon> 技能要求</div>
            <!-- 标签容器 -->
  <div class="tags-container" style="
    display: flex;
    flex-wrap: wrap; /* 关键：允许换行 */
    gap: 10px; /* 标签间距 */
  ">
    <!-- 假设 task.skills 是数组 -->
    <el-tag
      v-for="(skill, index) in task.skills"
      :key="index"
      size="small"
      style="margin: 0;"
    >
      {{ skill }}
    </el-tag>

    <!-- 可选：如果数组为空，显示提示 -->
    <span v-if="!task.skills || task.skills.length === 0" style="color: #999; font-size: 13px;">
      无特定技能要求
    </span>
  </div>
          </div>
        </div>
      </div>
       
      <!-- 5. 底部操作栏 -->
<!--
  修改重点：
  1. 移除所有 position: fixed/absolute。
  2. 使用 margin-top: 20px 与上方内容保持距离。
  3. 使用 Flex 布局让内容（状态/按钮）自动对齐。
-->
<div class="task-footer" style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #f0f0f0; display: flex; justify-content: space-between; align-items: center;">

  <!-- 左侧：显示状态标签（仅在不可接单时显示） -->
  <div v-if="Number(task.status) !== 1 || task.taken_by" class="status-container">
    <el-tag
      :type="getStatusType(task.status)"
      effect="light"
      size="large"
      style="font-size: 16px; padding: 10px 20px;"
    >
      <!-- 如果已被接单，优先显示“已被接单” -->
      {{ task.taken_by ? '已被接单' : getStatusText(task.status) }}
    </el-tag>
  </div>

  <!-- 右侧：接单按钮（仅在状态为1且未被接单时显示） -->
  <el-button
    v-if="Number(task.status) === 1 && !task.taken_by"
    type="primary"
    size="large"
    style="width: 100%;"
    @click="handleApply(task)"
  >
    立即接单
  </el-button>

</div>
    
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { 
  ArrowLeft, 
  Clock, 
  TrendCharts, 
  CollectionTag 
} 

from '@element-plus/icons-vue'
import { getTaskDetail,applyTask } from '../../../api/user' // 确保路径正确
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const loading = ref(false)
const task = ref(null)

// --- 方法 ---

// 获取状态文字
const getStatusText = (status) => {
  const map = {
    0: '待审核',
    1: '进行中',
    2: '已暂停',
    3: '已完成'
  };
  return map[status] || '未知';
};

// 获取标签颜色类型
const getStatusType = (status) => {
  const map = {
    0: 'warning', // 待审核 - 橙色
    1: 'success', // 进行中 - 绿色 (虽然这里不显示)
    2: 'info',    // 已暂停 - 灰色
    3: 'danger'   // 已完成 - 红色
  };
  return map[status] || 'info';
};

/**
 * 解析技能字符串
 * 支持 "Vue, React" 或 ["Vue", "React"] 格式
 */
const parseSkills = (skills) => {
  if (!skills) return []
  if (Array.isArray(skills)) return skills
  // 如果是字符串，按逗号或顿号分割
  return skills.split(/[,、\s]+/).filter(s => s)
}

/**
 * 获取分类颜色
 */
const getTagColor = (cat) => {
  const map = { 
    '前端': 'primary', 
    '后端': 'success', 
    '设计': 'warning', 
    '运维': 'danger',
    '测试': 'info' 
  }
  return map[cat] || 'info'
}

/**
 * 获取详情数据
 */
const fetchDetail = async () => {
  loading.value = true
  try {
    // 调用后端接口
    const res = await getTaskDetail(route.params.id)
    task.value = res
  } catch (error) {
    ElMessage.error('加载任务详情失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

/**
 * 立即接单
 */
const handleApply = async (currentTask) => {
  try {
    await ElMessageBox.confirm(
      `确定接取任务 <b>"${currentTask.title}"</b> 吗？<br/>接单后将锁定任务状态。`,
      '接单确认',
      {
        dangerouslyUseHTMLString: true,
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 调用接单接口
    await applyTask(currentTask.id)
    
    ElMessage.success('接单成功！')
    
    // 乐观更新状态，按钮变灰
    currentTask.status = 'taken'
    
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  }
}

// --- 生命周期 ---
onMounted(() => {
  fetchDetail()
})
</script>

<style scoped>
/* 容器 */
.detail-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 84px); /* 减去顶部高度 */
}

/* 卡片主体 */
.detail-card {
  max-width: 900px;
  margin: 0 auto;
  border-radius: 8px;
}

/* 1. 头部 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

/* 2. 核心信息 */
.main-info {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 30px;
}

.title {
  margin: 0 0 10px 0;
  font-size: 24px;
  color: #303133;
  font-weight: 600;
}

.meta-text {
  font-size: 12px;
  color: #909399;
}

.price-section {
  text-align: right;
}

.symbol {
  font-size: 18px;
  color: #F56C6C;
  font-weight: bold;
  vertical-align: top;
}

.price {
  font-size: 32px;
  color: #F56C6C;
  font-weight: bold;
}

/* 3. 描述区域 */
.section {
  margin-bottom: 30px;
}

.section-title {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #303133;
  border-left: 4px solid #409EFF;
  padding-left: 10px;
}

.desc-content {
  line-height: 1.8;
  color: #606266;
  background: #f5f7fa;
  padding: 20px;
  border-radius: 4px;
  white-space: pre-wrap; /* 保留换行符 */
}

/* 4. 参数网格 */
.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr); /* 默认两列 */
  gap: 20px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

/* 技能要求占满一行 */
.full-width {
  grid-column: span 2; 
}

.label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}

.label .el-icon {
  margin-right: 5px;
}

.value {
  font-size: 16px;
  color: #303133;
  font-weight: 500;
}

/* 技能标签样式 */
.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.skill-tag-item {
  margin: 0;
}

/* 5. 底部操作栏 */
.footer-action {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.apply-btn {
  width: 200px;
  font-size: 16px;
  font-weight: bold;
}

.status-text {
  color: #909399;
  font-size: 14px;
}

/* 移动端适配 */
@media (max-width: 600px) {
  .main-info {
    flex-direction: column;
    gap: 15px;
  }
  .price-section {
    text-align: left;
  }
  .meta-grid {
    grid-template-columns: 1fr; /* 手机端单列 */
  }
  .full-width {
    grid-column: span 1;
  }
}
</style>