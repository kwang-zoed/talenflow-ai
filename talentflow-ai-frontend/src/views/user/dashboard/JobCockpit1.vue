<template>
  <div class="cockpit-container">
    <!-- 1. 顶部数据看板 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6" v-for="item in statsData" :key="item.label">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-wrapper" :style="{ backgroundColor: item.color }">
              <el-icon :size="24" color="#fff">
                <component :is="item.icon" />
              </el-icon>
            </div>
            <div class="text-wrapper">
              <p class="label">{{ item.label }}</p>
              <p class="value">{{ item.value }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="main-content">
      <!-- 2. 左侧核心功能区 -->
      <el-col :span="16">
        <el-card shadow="never" class="function-card">
          <template #header>
            <div class="card-header">
              <span>核心功能</span>
            </div>
          </template>
          <div class="function-grid">
            <div class="func-item" @click="goToTaskHall">
              <el-icon :size="40" color="#409EFF"><Search /></el-icon>
              <span>寻找新机会</span>
            </div>
            <div class="func-item" @click="goToMyApplications">
              <el-icon :size="40" color="#67C23A"><Document /></el-icon>
              <span>我的投递记录</span>
            </div>
            <div class="func-item" @click="goToResume">
              <el-icon :size="40" color="#E6A23C"><List /></el-icon>
              <span>管理我的简历</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 3. 右侧智能推荐区 -->
      <el-col :span="8">
        <el-card shadow="never" class="recommend-card" v-loading="pageLoading">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <span>平台推荐</span>
                <el-tooltip content="基于您的简历和RAG技术智能匹配">
                  <el-icon class="question-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </div>
              <el-tooltip content="刷新推荐列表">
                <el-icon 
                  class="refresh-icon" 
                  :class="{ 'is-rotating': pageLoading }" 
                  @click="fetchRecommendations"
                >
                  <Refresh />
                </el-icon>
              </el-tooltip>
            </div>
          </template>

          <div class="scroll-container">
            <el-pull-refresh v-model="isRefreshing" @refresh="onRefresh" :pull-distance="60">
              <!-- 空状态 -->
              <div v-if="recommendedJobs.length === 0" class="empty-jobs">
                <el-empty :image-size="100" description="暂无推荐职位">
                  <el-button type="primary" @click="fetchRecommendations">点击刷新</el-button>
                </el-empty>
              </div>

              <!-- 职位列表 -->
              <div v-else class="job-list">
                <!-- 修改点1：key 改为 item.job_id -->
                <div v-for="(item, index) in recommendedJobs" :key="item.job_id" class="job-item">
                  <div class="score-tag">匹配度 {{ item.score }}%</div>
                  
                  <!-- 修改点2：直接访问 item.job_title -->
                  <h3 class="job-title">{{ item.job_title }}</h3>
                  
                  <div class="job-meta">
                    <!-- 注意：后端日志里没看到 company 和 salary，如果后端没返这两个字段，这里会显示空或undefined -->
                    <!-- 建议先注释掉或确认后端是否返回了 company/salary -->
                    <span>{{ item.company || '未知公司' }}</span> 
                    <span class="salary">{{ item.salary || '面议' }}</span>
                  </div>
                  
                  <div class="skills">
                    <el-tag 
                      v-for="skill in item.matched_skills" 
                      :key="skill" 
                      size="small" 
                      class="skill-tag"
                    >
                      {{ skill }}
                    </el-tag>
                  </div>
                  
                  <div class="action-area">
                    <el-button 
                      type="primary" 
                      link 
                      :loading="item.loading" 
                      @click="handleSmartApply(item)"
                    >
                      {{ item.loading ? 'AI处理中...' : '一键智能投递' }}
                    </el-button>
                  </div>
                  <el-divider />
                </div>
              </div>
            </el-pull-refresh>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Search, 
  List, 
  Document, 
  QuestionFilled, 
  Refresh 
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 1. 引入 Pinia Store
// 注意：请确保路径正确，通常位于 src/store/
import { useUserStore } from '../../../store/user'
import { useResumeStore } from '../../../store/resume' // 需要创建这个文件



const router = useRouter()
const userStore = useUserStore()
const resumeStore = useResumeStore()

// --- 数据定义 ---
const pageLoading = ref(false)
const isRefreshing = ref(false)
const recommendedJobs = ref([])

// 顶部统计数据
const statsData = ref([
  { label: '累计收益', value: '¥ 0.00', icon: 'Wallet', color: '#67C23A' },
  { label: '简历浏览量', value: 128, icon: 'TrendCharts', color: '#409EFF' },
  { label: '面试邀请', value: 5, icon: 'Document', color: '#E6A23C' },
  { label: '待处理事项', value: 2, icon: 'List', color: '#F56C6C' },
])

// --- 核心逻辑：获取用户 ID (基于你提供的 Store 结构) ---
// 因为 userInfo 是对象，所以取 id 字段
const currentUserId = computed(() => userStore.userInfo?.id)

// --- 页面跳转 ---
const goToTaskHall = () => router.push('/dashboard/tasks')
const goToMyApplications = () => router.push('/dashboard/applications')
const goToResume = () => router.push('/dashboard/resume')
// 2. 引入 API (请确保路径正确)
import { submitRecommendTask, pollRecommendResult ,smartApply, getRecommendedJobs } from '../../../api/user'
import { getResumeListAPI} from '../../../api/resume'

// --- 核心逻辑：获取推荐 ---
const fetchRecommendations = async () => {
  if (!currentUserId.value) return;

  pageLoading.value = true;
  
  try {
    // 1. 提交任务
    const submitRes = await submitRecommendTask(currentUserId.value);
    const taskId = submitRes.task_id;

    // 2. 开始智能轮询 (这里会自动处理等待和重试)
    // 注意：pollRecommendResult 内部已经封装了轮询逻辑，不需要我们手动写 setInterval
    const resultData = await pollRecommendResult(taskId);

    // 3. 更新 UI
    recommendedJobs.value = resultData.map(job => ({
      ...job,
      loading: false
    }));

  } catch (error) {
    if (error.message.includes('超时')) {
      ElMessage.warning('AI响应较慢，请稍后手动刷新');
    } else {
      ElMessage.error(error.message);
    }
  } finally {
    pageLoading.value = false;
    isRefreshing.value = false;
  }
}

const onRefresh = () => {
  fetchRecommendations()
}

// --- 核心逻辑：智能投递 ---
// 状态变量
const showResumeDialog = ref(false);
const confirmLoading = ref(false);
const resumeList = ref([]);
const selectedResumeId = ref(null);
let pendingJobId = null;
let pendingJobTitle = ref('');

// 1. 点击“一键投递”按钮触发的函数
const handleSmartApply = async (job) => {
  try {
    // 第一步：获取简历列表
    const res = await getResumeListAPI();
    resumeList.value = res || [];

    // 第二步：根据简历数量决定逻辑
    if (resumeList.value.length === 0) {
      ElMessage.warning('请先去创建您的简历');
      return;
    }

    // 第三步：暂存职位信息 (注意这里取值的变化！！！)
    // 原代码可能是 job.id，现在是 job.job.id
    pendingJobId = job.job.id;
    pendingJobTitle.value = job.job.title;

    if (resumeList.value.length === 1) {
      // 只有一份简历：直接投递
      selectedResumeId.value = resumeList.value[0].id;
      // 原代码可能是 job.description，现在是 job.job.description
      executeApply(job.job.job_id, resumeList.value[0].id, job.job.description);
    } else {
      // 多份简历：弹窗选择
      showResumeDialog.value = true;
    }
  } catch (error) {
    console.error("获取简历失败:", error);
    ElMessage.error("初始化投递失败");
  }
};

// 2. 弹窗确认按钮
const confirmSelection = () => {
  if (!selectedResumeId.value) {
    ElMessage.warning("请选择一份简历");
    return;
  }
  // 注意：这里传参也要对应上
  executeApply(pendingJobId, selectedResumeId.value, pendingJobTitle.value);
};

// 3. 真正执行投递的函数
const executeApply = async (jobId, resumeId, jobDesc) => {
  confirmLoading.value = true;
  try {
    await smartApply({
      user_id: currentUserId.value,
      job_id: jobId,
      job_description: jobDesc, // 确保这里传的是字符串
      resume_id: resumeId
    });

    ElMessage.success('投递成功！AI正在为您生成求职信');
    showResumeDialog.value = false;
  } catch (error) {
    ElMessage.error('投递失败，请重试');
  } finally {
    confirmLoading.value = false;
  }
};


// --- 初始化 ---
onMounted(() => {
  fetchRecommendations()
})
</script>

<style scoped>
.cockpit-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

/* 统计卡片样式 */
.stats-row {
  margin-bottom: 20px;
}
.stat-card {
  border-radius: 8px;
}
.card-content {
  display: flex;
  align-items: center;
}
.icon-wrapper {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
}
.text-wrapper .label {
  font-size: 14px;
  color: #999;
  margin: 0;
}
.text-wrapper .value {
  font-size: 20px;
  font-weight: bold;
  color: #333;
  margin: 5px 0 0;
}

/* 主体布局 */
.main-content {
  display: flex;
}

/* 左侧功能区 */
.function-card {
  border-radius: 8px;
}
.function-grid {
  display: flex;
  justify-content: space-around;
  padding: 20px 0;
  text-align: center;
}
.func-item {
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: transform 0.2s;
}
.func-item:hover {
  transform: translateY(-5px);
  color: #409EFF;
}
.func-item span {
  margin-top: 10px;
  font-size: 16px;
  font-weight: 500;
}

/* 右侧推荐区 */
.recommend-card {
  border-radius: 8px;
  height: 800px;
  display: flex;
  flex-direction: column;
}

/* 头部样式修改 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.question-icon {
  color: #909399;
  cursor: help;
}

/* 刷新按钮样式 */
.refresh-icon {
  font-size: 18px;
  color: #909399;
  cursor: pointer;
  transition: transform 0.3s;
}
.refresh-icon:hover {
  color: #409EFF;
}
/* 旋转动画 */
.is-rotating {
  animation: rotate 1s linear infinite;
}
@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 滚动容器 */
.scroll-container {
  flex: 1;
  overflow-y: auto;
  height: 100%;
}
.job-item {
  margin-bottom: 10px;
  position: relative;
}
.score-tag {
  position: absolute;
  top: 0;
  right: 0;
  background-color: #67C23A;
  color: white;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: bold;
}
.job-title {
  font-size: 16px;
  font-weight: bold;
  color: #333;
  margin: 0 0 8px 0;
  line-height: 1.4;
  padding-right: 60px;
}
.job-meta {
  font-size: 13px;
  color: #999;
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
}
.salary {
  color: #F56C6C;
  font-weight: bold;
}
.skills {
  margin-bottom: 15px;
}
.skill-tag {
  margin-right: 5px;
  margin-bottom: 5px;
  background-color: #f0f2f5;
  color: #606266;
  border: none;
}
.action-area {
  text-align: right;
}

/* 滚动条样式 */
.scroll-container::-webkit-scrollbar {
  width: 6px;
}
.scroll-container::-webkit-scrollbar-thumb {
  background-color: #ddd;
  border-radius: 3px;
}
</style>