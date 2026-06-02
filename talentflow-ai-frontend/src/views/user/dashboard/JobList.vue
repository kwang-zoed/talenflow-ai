<template>
  <div class="joblist-page">
    <div class="page-header">
      <h3>职位大厅</h3>
      <div class="filter-group">
        <el-input 
          v-model="searchKeyword" 
          placeholder="搜索职位名称" 
          class="search-input"
          @keyup.enter="fetchJobs"
        >
          <template #append>
            <el-button @click="fetchJobs"><el-icon><Search /></el-icon></el-button>
          </template>
        </el-input>
      </div>
    </div>

    <div class="job-grid" v-loading="loading" element-loading-text="正在加载职位...">
      <el-empty v-if="jobList.length === 0 && !loading" description="暂时没有相关职位" />

      <div v-for="job in filteredJobList" :key="job.id" class="job-card">
        <div class="card-header">
          <div class="header-tags">
            <el-tag type="success" size="small" effect="dark">{{ job.experience_requirement || '经验不限' }}</el-tag>
            <el-tag type="info" size="small">{{ job.education_requirement || '学历不限' }}</el-tag>
          </div>
          <span class="salary">{{ job.salary || '面议' }}</span>
        </div>

        <div class="card-body" @click="showJobDetail(job)" style="cursor: pointer;">
          <h4 class="title">{{ job.title }}</h4>
          <p class="company">{{ job.company }}</p>
          <p class="desc">{{ job.description }}</p>
        </div>

        <div class="card-footer">
          <div class="meta">
            <span class="item">
              <i class="el-icon-map-marker"></i> {{ job.location || '不限' }}
            </span>
            <span class="item view-detail" @click="showJobDetail(job)">
              <i class="el-icon-document"></i> 查看详情
            </span>
          </div>
          <div class="skills-wrapper">
            <el-tag 
              v-for="(skill, index) in (job.required_skills || job.skills || [])" 
              :key="index" 
              size="mini" 
              type="info" 
              effect="light"
            >
              {{ skill }}
            </el-tag>
          </div>
          <el-button 
            type="primary" 
            size="small"
            plain
            @click="handleApply(job)"
          >
            投递简历
          </el-button>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="showResumeDialog"
      title="选择简历"
      width="520px"
      class="resume-select-dialog"
      destroy-on-close
      @closed="resetResumeDialog"
    >
      <div v-if="resumeTotal > 0" class="resume-select-body">
        <p class="resume-select-tip">共 {{ resumeTotal }} 份简历，请选择用于本次投递的版本</p>
        <el-scrollbar max-height="300px">
          <el-radio-group v-model="selectedResumeId" class="resume-radio-group">
            <el-radio
              v-for="resume in paginatedResumeList"
              :key="resume.id"
              :label="resume.id"
              class="resume-radio-item"
            >
              <span class="resume-radio-label" :title="formatResumeLabel(resume)">
                {{ formatResumeLabel(resume) }}
              </span>
              <el-tag v-if="resume.is_default" size="small" type="success" class="default-tag">默认</el-tag>
            </el-radio>
          </el-radio-group>
        </el-scrollbar>
        <el-pagination
          v-if="resumeTotal > resumePageSize"
          v-model:current-page="resumePage"
          :page-size="resumePageSize"
          :total="resumeTotal"
          :page-sizes="[5, 10, 15]"
          layout="total, sizes, prev, pager, next"
          small
          background
          class="resume-pagination"
          @size-change="onResumePageSizeChange"
        />
      </div>
      <el-empty v-else description="暂无简历，请先创建" />
      <template #footer>
        <el-button @click="showResumeDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmApply" :loading="applying">确认投递</el-button>
      </template>
    </el-dialog>

    <el-dialog title="职位详情" v-model="showDetailDialog" width="600px" class="job-detail-dialog">
      <div v-if="currentJob" class="job-detail-content">
        <div class="detail-header">
          <h2>{{ currentJob.title }}</h2>
          <span class="detail-salary">{{ currentJob.salary || '面议' }}</span>
        </div>
        <div class="detail-meta">
          <el-tag type="success">{{ currentJob.experience_requirement || '经验不限' }}</el-tag>
          <el-tag type="info">{{ currentJob.education_requirement || '学历不限' }}</el-tag>
          <span><i class="el-icon-map-marker"></i> {{ currentJob.location || '不限' }}</span>
          <span><i class="el-icon-office-building"></i> {{ currentJob.company }}</span>
        </div>
        <div class="detail-section">
          <h4>技能要求</h4>
          <div class="detail-skills">
            <el-tag 
              v-for="(skill, index) in (currentJob.required_skills || currentJob.skills || [])" 
              :key="index" 
              size="small"
            >
              {{ skill }}
            </el-tag>
          </div>
        </div>
        <div class="detail-section">
          <h4>职位描述</h4>
          <p class="detail-description">{{ currentJob.description }}</p>
        </div>
      </div>
      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
        <el-button type="primary" @click="applyFromDetail">投递简历</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getJobList } from '../../../api/user'
import { getResumeListAPI } from '../../../api/resume'
import { startSmartApplyBackground } from '../../../utils/smartApplyTaskRunner'

const router = useRouter()
const taskProgress = inject('parseProgress', null)

const loading = ref(false)
const applying = ref(false)
const jobList = ref([])
const searchKeyword = ref('')

const showResumeDialog = ref(false)
const resumeList = ref([])
const selectedResumeId = ref(null)
const pendingJob = ref(null)
const resumePage = ref(1)
const resumePageSize = ref(5)

const resumeTotal = computed(() => resumeList.value.length)

const paginatedResumeList = computed(() => {
  const start = (resumePage.value - 1) * resumePageSize.value
  return resumeList.value.slice(start, start + resumePageSize.value)
})

const formatResumeLabel = (resume) => {
  const title = (resume.title || `简历 #${resume.id}`).trim()
  const name = (resume.name || '').trim()
  return name ? `${title}（${name}）` : title
}

const resetResumeDialog = () => {
  resumePage.value = 1
}

const onResumePageSizeChange = (size) => {
  resumePageSize.value = size
  resumePage.value = 1
}

const openResumeDialog = () => {
  resumePage.value = 1
  const defaultResume = resumeList.value.find((r) => r.is_default)
  selectedResumeId.value = defaultResume?.id ?? resumeList.value[0]?.id ?? null
  showResumeDialog.value = true
}

const showDetailDialog = ref(false)
const currentJob = ref(null)

const filteredJobList = computed(() => {
  let list = jobList.value || []
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    list = list.filter(job => 
      (job.title && job.title.toLowerCase().includes(keyword)) ||
      (job.company && job.company.toLowerCase().includes(keyword)) ||
      (job.description && job.description.toLowerCase().includes(keyword))
    )
  }
  return list
})

const fetchJobs = async () => {
  loading.value = true
  try {
    const res = await getJobList({})
    jobList.value = res.data || res || []
  } catch (error) {
    console.error('获取职位列表失败:', error)
    ElMessage.error('加载职位失败')
  } finally {
    loading.value = false
  }
}

const handleApply = async (job) => {
  try {
    const res = await getResumeListAPI()
    resumeList.value = res || []

    if (resumeList.value.length === 0) {
      ElMessage.warning('请先创建简历')
      router.push('/dashboard/resume')
      return
    }

    pendingJob.value = job

    if (resumeList.value.length === 1) {
      selectedResumeId.value = resumeList.value[0].id
      await confirmApply()
    } else {
      openResumeDialog()
    }
  } catch (error) {
    console.error('获取简历失败:', error)
    ElMessage.error('投递失败')
  }
}

const confirmApply = async () => {
  if (!selectedResumeId.value || !pendingJob.value) return

  applying.value = true
  const jobTitle = pendingJob.value.title || '职位'
  const jobSnapshot = pendingJob.value
  try {
    await startSmartApplyBackground({
      payload: {
        job_id: jobSnapshot.job_id || jobSnapshot.id,
        job_description: jobSnapshot.description,
        resume_id: selectedResumeId.value,
        mode: 'auto'
      },
      jobTitle,
      taskProgress
    })

    showResumeDialog.value = false
    showDetailDialog.value = false
    pendingJob.value = null
  } catch (error) {
    console.error('投递提交失败:', error)
    ElMessage.error(error.message || '投递提交失败，请重试')
  } finally {
    applying.value = false
  }
}

const showJobDetail = (job) => {
  currentJob.value = job
  showDetailDialog.value = true
}

const applyFromDetail = () => {
  showDetailDialog.value = false
  pendingJob.value = currentJob.value
  handleApply(currentJob.value)
}

onMounted(() => {
  fetchJobs()
})
</script>

<style scoped>
.joblist-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h3 {
  margin: 0;
  font-size: 18px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 15px;
}

.search-input {
  width: 250px;
}

.job-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.job-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.header-tags {
  display: flex;
  gap: 8px;
}

.salary {
  color: #F56C6C;
  font-weight: bold;
  font-size: 16px;
}

.card-body .title {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: bold;
  color: #333;
}

.card-body .company {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #666;
}

.card-body .desc {
  margin: 0;
  font-size: 13px;
  color: #999;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #f0f0f0;
}

.meta {
  display: flex;
  gap: 15px;
  margin-bottom: 10px;
}

.meta .item {
  font-size: 13px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 4px;
}

.meta .view-detail {
  color: #409EFF;
  cursor: pointer;
}

.meta .view-detail:hover {
  text-decoration: underline;
}

.skills-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 12px;
}

.card-footer .el-button {
  float: right;
}

.resume-select-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.resume-select-tip {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

.resume-radio-group {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 100%;
}

.resume-radio-item {
  display: flex;
  align-items: center;
  margin: 0;
  padding: 10px 12px;
  border-radius: 6px;
  height: auto;
  white-space: normal;
}

.resume-radio-item:hover {
  background: #f5f7fa;
}

.resume-radio-item :deep(.el-radio__label) {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  padding-left: 8px;
  line-height: 1.5;
}

.resume-radio-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.default-tag {
  flex-shrink: 0;
}

.resume-pagination {
  justify-content: center;
  margin-top: 4px;
}

.job-detail-dialog :deep(.el-dialog__body) {
  padding: 0 20px 20px;
}

.job-detail-content {
  line-height: 1.6;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 15px;
  border-bottom: 1px solid #f0f0f0;
}

.detail-header h2 {
  margin: 0;
  font-size: 20px;
  color: #333;
}

.detail-salary {
  font-size: 20px;
  font-weight: bold;
  color: #F56C6C;
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 15px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 14px;
  color: #666;
}

.detail-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.detail-section {
  padding: 15px 0;
}

.detail-section h4 {
  margin: 0 0 10px 0;
  font-size: 15px;
  color: #333;
}

.detail-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-description {
  margin: 0;
  color: #666;
  white-space: pre-wrap;
}
</style>