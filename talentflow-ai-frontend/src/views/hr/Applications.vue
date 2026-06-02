<template>
  <div class="resume-management">
    <div class="header-actions mb-4">
      <h3>人才投递管理</h3>
    </div>

    <el-tabs v-model="activeTab" class="application-tabs">
      <el-tab-pane label="审核任务" name="task">
        <div class="tab-content">
          <el-table :data="taskApplications" stripe style="width: 100%" v-loading="loading">
            <el-table-column prop="name" label="候选人" width="140">
              <template #default="scope">
                <div class="user-info">
                  <span class="name">{{ scope.row.candidate_name }}</span>
                  <span v-if="scope.row.experience_years" class="exp">
                    {{ scope.row.experience_years }}年经验
                  </span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="job_title" label="申请任务" width="180" />
            <el-table-column label="核心技能" min-width="180">
              <template #default="scope">
                <div class="skills-tags">
                  <el-tag
                    v-for="(skill, index) in scope.row.job_skills || []"
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
            <el-table-column label="操作" fixed="right" width="200">
              <template #default="scope">
                <el-button size="small" icon="View" @click="handleView(scope.row)">查看简历</el-button>
                <el-button
                  size="small"
                  type="primary"
                  plain
                  :disabled="['已录用', '不合适'].includes(scope.row.status)"
                  @click="handleAction(scope.row)"
                >
                  处理
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="审核简历" name="job">
        <div class="tab-content">
          <el-table :data="jobApplications" stripe style="width: 100%" v-loading="loading">
            <el-table-column prop="name" label="候选人" width="140">
              <template #default="scope">
                <div class="user-info">
                  <span class="name">{{ scope.row.candidate_name }}</span>
                  <span v-if="scope.row.experience_years" class="exp">
                    {{ scope.row.experience_years }}年经验
                  </span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="job_title" label="申请职位" width="180" />
            <el-table-column label="核心技能" min-width="180">
              <template #default="scope">
                <div class="skills-tags">
                  <el-tag
                    v-for="(skill, index) in scope.row.job_skills || []"
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
            <el-table-column label="操作" fixed="right" width="200">
              <template #default="scope">
                <el-button size="small" icon="View" @click="handleView(scope.row)">查看简历</el-button>
                <el-button
                  size="small"
                  type="primary"
                  plain
                  :disabled="['已录用', '不合适'].includes(scope.row.status)"
                  @click="handleAction(scope.row)"
                >
                  处理
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 简历详情与处理弹窗 -->
    <el-dialog v-model="dialogVisible" title="简历详情与处理" width="600px">
      <div v-if="currentResume" class="resume-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="候选人">{{ currentResume.candidate_name }}</el-descriptions-item>
          <el-descriptions-item label="申请职位">{{ currentResume.job_title }}</el-descriptions-item>
          <el-descriptions-item label="核心技能">
            <el-tag
              v-for="(skill, index) in currentResume.job_skills || []"
              :key="index"
              size="small"
              type="info"
              style="margin-right: 4px; margin-bottom: 4px;"
            >
              {{ skill }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="投递时间">{{ formatDate(currentResume.applied_at) }}</el-descriptions-item>
          <el-descriptions-item label="简历" v-if="currentResume.resume_id || currentResume.source">
            <el-link
              v-if="currentResume.source"
              :href="currentResume.source"
              target="_blank"
              type="primary"
            >
              下载附件
            </el-link>
            <el-button
              v-else-if="currentResume.resume_id"
              type="primary"
              link
              @click="openResumePreview"
            >
              查看简历
            </el-button>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 处理表单区域 -->
        <el-divider content-position="left">审核处理</el-divider>
        <el-form :model="processForm" label-width="80px">
          <el-form-item label="审核结果">
            <el-radio-group v-model="processForm.status">
              <el-radio label="待沟通">待沟通</el-radio>
              <el-radio label="已录用">已录用</el-radio>
              <el-radio label="不合适">不合适</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="处理备注">
            <el-input
              v-model="processForm.remark"
              type="textarea"
              :rows="3"
              placeholder="请输入处理意见（如：已约明天下午面试）"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitProcess">确认提交</el-button>
        </span>
      </template>
    </el-dialog>

    <el-dialog v-model="resumePreviewVisible" title="简历详情" width="720px">
      <div v-if="resumePreview" class="resume-preview-content">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="姓名">{{ resumePreview.name }}</el-descriptions-item>
          <el-descriptions-item label="电话">{{ resumePreview.phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ resumePreview.email || '-' }}</el-descriptions-item>
          <el-descriptions-item label="意向职位">{{ resumePreview.title || '-' }}</el-descriptions-item>
          <el-descriptions-item label="学历">{{ resumePreview.education || '-' }}</el-descriptions-item>
          <el-descriptions-item label="工作年限">
            {{ resumePreview.experience_years != null ? resumePreview.experience_years + '年' : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="技能">
            <el-tag
              v-for="(skill, index) in resumePreview.skills || []"
              :key="index"
              size="small"
              style="margin-right: 4px; margin-bottom: 4px;"
            >
              {{ skill }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <div v-if="resumePreview.summary" class="preview-block">
          <h4>个人简介</h4>
          <pre>{{ resumePreview.summary }}</pre>
        </div>
        <div v-if="resumePreview.work_experience" class="preview-block">
          <h4>工作经历</h4>
          <pre>{{ resumePreview.work_experience }}</pre>
        </div>
        <div v-if="resumePreview.project_experience" class="preview-block">
          <h4>项目经验</h4>
          <pre>{{ resumePreview.project_experience }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import axios from '../../utils/request'

const activeTab = ref('task')
const taskApplications = ref([])
const jobApplications = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const resumePreviewVisible = ref(false)
const currentResume = ref(null)
const resumePreview = ref(null)
const processForm = ref({ status: '待沟通', remark: '' })

const fetchData = async (type) => {
  loading.value = true
  if (type === 'task') {
    taskApplications.value = []
  } else {
    jobApplications.value = []
  }
  try {
    console.log(`[HR Applications] 正在获取 ${type} 类型数据...`)
    const response = await axios.get(`/hr/applications?type=${type}`)
    const data = response.data || response
    console.log(`[HR Applications] ${type} 返回数据:`, data)
    if (type === 'task') {
      taskApplications.value = Array.isArray(data) ? data.filter(item => item.type === 'task' || !item.type) : []
    } else {
      jobApplications.value = Array.isArray(data) ? data.filter(item => item.type === 'job' || !item.type) : []
    }
    console.log(`[HR Applications] ${type} 最终数据长度:`, type === 'task' ? taskApplications.value.length : jobApplications.value.length)
  } catch (error) {
    ElMessage.error('获取投递列表失败')
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

const handleView = async (row) => {
  try {
    const res = await axios.get(`/hr/applications/${row.id}`)
    currentResume.value = res.data || res
    processForm.value = { 
      status: currentResume.value.status || '待沟通', 
      remark: currentResume.value.remark || ''
    }
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取简历详情失败')
  }
}

const handleAction = (row) => {
  handleView(row)
}

const openResumePreview = async () => {
  if (!currentResume.value?.id) return
  try {
    const res = await axios.get(`/hr/applications/${currentResume.value.id}/resume`)
    resumePreview.value = res.data || res
    resumePreviewVisible.value = true
  } catch (error) {
    ElMessage.error('获取简历详情失败')
  }
}

const submitProcess = async () => {
  try {
    await axios.patch(`/hr/applications/${currentResume.value.id}/process`, processForm.value)
    ElMessage.success('处理成功')
    dialogVisible.value = false
    fetchData(activeTab.value)
  } catch (error) {
    ElMessage.error('处理失败')
  }
}

watch(activeTab, (newVal) => {
  fetchData(newVal)
})

onMounted(() => {
  fetchData('task')
})
</script>

<style scoped>
.resume-management {
  width: 100%;
  min-height: 100vh;
  padding: 20px;
  box-sizing: border-box;
}

.mb-4 { 
  margin-bottom: 20px; 
  display: flex;
  align-items: center;
}

.application-tabs {
  background: #fff;
  border-radius: 4px;
  padding: 0 20px;
}

.tab-content {
  padding: 10px 0;
}

.user-info { 
  display: flex; 
  flex-direction: column; 
}

.exp { 
  font-size: 12px; 
  color: #999; 
  margin-top: 4px; 
}

.resume-detail { 
  margin-bottom: 20px; 
}

.preview-block {
  margin-top: 16px;
}

.preview-block h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #303133;
}

.preview-block pre {
  margin: 0;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
}

:deep(.el-table) {
  width: 100%;
  min-width: 800px;
}

:deep(.el-table__header-wrapper),
:deep(.el-table__body-wrapper) {
  overflow-x: auto;
}

@media screen and (max-width: 768px) {
  .resume-management {
    padding: 10px;
  }
  
  :deep(.el-table) {
    min-width: 600px;
  }
}
</style>
