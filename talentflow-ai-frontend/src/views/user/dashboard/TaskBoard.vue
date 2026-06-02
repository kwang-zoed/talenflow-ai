<template>
  <div class="taskboard-page">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <h3>实战任务大厅</h3>
      <div class="filter-group">
        <el-radio-group v-model="currentCategory" size="small" @change="fetchTasks">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="前端">前端</el-radio-button>
          <el-radio-button label="后端">后端</el-radio-button>
          <el-radio-button label="设计">设计</el-radio-button>
          <el-radio-button label="运维">运维</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 任务卡片网格 -->
    <div class="task-grid" v-loading="loading" element-loading-text="正在加载任务...">
      
      <!-- 空状态 -->
      <el-empty v-if="taskList.length === 0 && !loading" description="暂时没有相关任务" />

      <!-- 任务卡片循环 -->
      <div v-for="task in taskList" :key="task.id" class="task-card">
        
        <!-- 优化：给标题绑定点击跳转，体验更好 -->
        <div class="card-header" @click="goToDetail(task.id)" style="cursor: pointer;">
          <el-tag :type="getTagColor(task.category)" size="small" effect="dark">
            {{ task.category }}
          </el-tag>
          <span class="price">¥{{ task.price }}</span>
        </div>

        <!-- 卡片主体：标题 + 描述 -->
        <div class="card-body" @click="goToDetail(task.id)" style="cursor: pointer;">
          <h4 class="title">{{ task.title }}</h4>
          <p class="desc">{{ task.description }}</p>
        </div>

     <!-- 卡片底部：工期 + 技能 + 按钮 -->
      <div class="card-footer" style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px;">
        
        <!-- 左侧信息 -->
        <div class="meta" style="display: flex; align-items: center; gap: 10px;">
          <!-- 工期 -->
          <span class="item" style="color: #666; font-size: 13px;">
            <i class="el-icon-time"></i> {{ task.duration }}天
          </span>

          <!-- 技能要求 -->
          <div class="skills-wrapper" style="display: flex; gap: 5px; flex-wrap: wrap;">
            <el-tag 
              v-for="(skill, index) in (task.skills || [])" 
              :key="index" 
              size="mini" 
              type="info" 
              effect="light"
            >
              {{ skill }}
            </el-tag>
          </div>
        </div>

        <!-- 右侧按钮 -->
        <el-button 
          type="primary" 
          size="small"
          plain
          :disabled="!(task.status === 1 && task.taken_by === null)"
          @click.stop="handleApply(task)"
        >
          <!-- 按钮文字逻辑：三层判断 -->
          
          <!-- 1. 能接单：状态是1 且 没人接 -->
          <span v-if="task.status === 1 && task.taken_by === null">立即接单</span>
          
          <!-- 2. 被抢单：状态是1 但 有人接了 -->
          <span v-else-if="task.status === 1 && task.taken_by !== null">已接单</span>
          
          <!-- 3. 状态不对：状态不是1（如审核中、已结束等） -->
          <span v-else>不可接单</span>
          
        </el-button>
      </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTaskList, applyTask } from '../../../api/user' // 注意：详情页不需要在这里调用 getTaskDetail
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'

const router = useRouter()

// --- 数据定义 ---
const loading = ref(false)
const taskList = ref([])
const currentCategory = ref('') 

// --- 方法 ---

/**
 * 获取任务列表
 */
const fetchTasks = async () => {
  loading.value = true
  try {
    const res = await getTaskList({ category: currentCategory.value })
    taskList.value = res.items || res
  } catch (error) {
    ElMessage.error('加载任务失败')
  } finally {
    loading.value = false
  }
}

/**
 * 跳转详情
 */
const goToDetail = (id) => {
    // 注意：这里直接传 id 就行，不需要传整个 row 对象
    // 除非你在函数内部取 row.id
    router.push({ name: 'TaskDetail', params: { id: id } })
}

/**
 * 立即接单
 * 注意：这里使用了 @click.stop 防止触发父级的点击跳转事件
 */
const handleApply = async (task) => {
  try {
    await ElMessageBox.confirm(
      `确定接取任务 <b>"${task.title}"</b> 吗？接取后无法取消。`,
      '接单确认',
      {
        dangerouslyUseHTMLString: true,
        confirmButtonText: '确定接单',
        cancelButtonText: '再想想',
        type: 'warning'
      }
    )

    await applyTask(task.id)
    ElMessage.success('恭喜你，接单成功！')
    task.status = 'taken'

  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '接单失败')
    }
  }
}

const getTagColor = (cat) => {
  const map = {
    '前端': 'primary',
    '后端': 'success',
    '设计': 'warning',
    '运维': 'danger'
  }
  return map[cat] || 'info'
}

onMounted(() => {
  fetchTasks()
})
</script>

<style scoped>
.taskboard-page {
  padding: 0;
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

/* 任务网格布局 */
.task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

/* 卡片样式 */
.task-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #e4e7ed;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
}

.task-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  border-color: #409EFF;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.price {
  color: #F56C6C;
  font-size: 18px;
  font-weight: bold;
}

.card-body {
  flex: 1;
  margin-bottom: 20px;
}

.title {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #303133;
  height: 44px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.desc {
  margin: 0;
  font-size: 13px;
  color: #909399;
  line-height: 1.6;
  height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.card-footer {
  border-top: 1px solid #ebeef5;
  padding-top: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.meta {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 12px;
  color: #909399;
}

.meta i {
  margin-right: 4px;
}
</style>