<template>
  <div class="resume-manager">
    <!-- 顶部操作栏 -->
    <div class="header">
      <h2>我的简历库</h2>
      <!-- 按钮文字改为“手动新建”，以区分上传 -->
      <el-button type="primary" icon="Plus" @click="handleCreate">手动新建</el-button>
    </div>

    <!-- 简历列表 (保持不变) -->
    <el-row :gutter="20">
      <el-col :span="8" v-for="resume in resumeList" :key="resume.id">
        <el-card 
          class="resume-card" 
          :body-style="{ padding: '20px' }"
          :class="{ 'is-active': resume.id === currentResumeId }"
          shadow="hover"
        >
          <div class="card-header">
            <span class="title">{{ resume.title || '未命名简历' }}</span>
            <el-tag v-if="resume.is_default" type="success" size="small">默认</el-tag>
          </div>
          
          <div class="card-body">
            <p><i class="el-icon-user"></i> {{ resume.name || '未填写姓名' }}</p>
            <p><i class="el-icon-phone"></i> {{ resume.phone || '未填写电话' }}</p>
            <p><i class="el-icon-date"></i> 更新: {{ formatDate(resume.updated_at) }}</p>
            <p v-if="resume.residence_city || resume.use_profile_location"><i class="el-icon-location"></i> {{ resume.use_profile_location ? '默认所在地' : resume.residence_city }}</p>
          </div>

          <div class="card-footer">
            <el-button 
              v-if="resume.id !== currentResumeId"
              type="success" 
              size="small" 
              @click="selectResume(resume)"
            >
              选中
            </el-button>
            <el-tag v-else type="success" size="small">当前选中</el-tag>

            <el-button size="small" @click="handleEdit(resume)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(resume.id)">删除</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ================= 完整编辑弹窗 ================= -->
    <el-dialog 
      :title="isEdit ? '编辑简历' : '新建简历'" 
      v-model="dialogVisible"
      width="600px"
      :close-on-click-modal="false"
      @close="handleDialogClose"  
    >
      <el-form :model="form" label-position="top" size="small">
        
        <!-- 【新增】 1. 简历上传区域 -->
        <div class="upload-section">
          <el-upload
            class="upload-demo"
            drag
            action="#" 
            :auto-upload="false"
            :limit="1"
            accept=".pdf,.doc,.docx"
            :on-change="handleFileUpload"
            :on-exceed="handleExceed"
            :file-list="fileList"  
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处，或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF/Word 格式，上传后将自动解析填入下方表单
              </div>
            </template>
          </el-upload>
        </div>

        <el-divider content-position="left">基础信息</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="简历标题">
              <el-input v-model="form.title" placeholder="例如：张三的React前端简历"></el-input>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="姓名">
              <el-input v-model="form.name" placeholder="您的姓名"></el-input>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="学历">
              <el-select v-model="form.education" placeholder="最高学历" style="width: 100%">
                <el-option label="本科" value="本科"></el-option>
                <el-option label="硕士" value="硕士"></el-option>
                <el-option label="大专" value="大专"></el-option>
                <el-option label="博士" value="博士"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="电话">
              <el-input v-model="form.phone" placeholder="联系电话"></el-input>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">所在地</el-divider>
        <el-form-item label="使用账户默认所在地">
          <el-switch v-model="useProfileLocation" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <template v-if="!useProfileLocation">
          <el-form-item label="常住城市">
            <LocationPicker v-model:city="form.residence_city" v-model:address="form.residence_address" />
          </el-form-item>
        </template>
        <p v-else class="location-hint">
          将使用「我的所在地」中的默认城市。
          <router-link to="/dashboard/profile">去设置</router-link>
        </p>

        <el-divider content-position="left">职业经历</el-divider>
        
        <el-form-item label="工作经验">
          <el-input 
            type="textarea" 
            v-model="form.work_experience" 
            :rows="5" 
            placeholder="请输入您的工作经历..."
          ></el-input>
        </el-form-item>

        <el-form-item label="项目经验">
          <el-input 
            type="textarea" 
            v-model="form.project_experience" 
            :rows="5" 
            placeholder="请输入主要项目经验..."
          ></el-input>
        </el-form-item>

        <el-divider content-position="left">技能与总结</el-divider>
        
        <el-form-item label="自我评价">
          <el-input 
            type="textarea" 
            v-model="form.summary" 
            :rows="3" 
            placeholder="简短的自我介绍..."
          ></el-input>
        </el-form-item>

      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitLoading" @click="submitForm">保存简历</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue' // 引入上传图标
import { useResumeStore } from '../../../store/resume'
import { 
  getResumeListAPI, 
  createResumeAPI, 
  updateResumeAPI, 
  deleteResumeAPI,
  parseResumeFileAPI // 假设您有一个解析文件的接口
} from '../../../api/resume'
import LocationPicker from '@/components/LocationPicker.vue'

// --- Store & State ---
const resumeStore = useResumeStore()
const currentResumeId = computed(() => resumeStore.currentResumeId)

const resumeList = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)

// 1. 定义上传文件列表的状态 (默认为空数组)
const fileList = ref([]) 

const defaultForm = {
  id: null,
  title: '',
  name: '',
  phone: '',
  email: '',
  education: '',
  experience: '',
  work_experience: '',
  project_experience: '',
  skills: '',
  summary: '',
  is_default: 0,
  residence_city: '',
  residence_address: '',
  use_profile_location: 1,
}
const form = ref({ ...defaultForm })
const useProfileLocation = computed({
  get: () => form.value.use_profile_location ?? 1,
  set: (v) => { form.value.use_profile_location = v },
})

// --- 方法 ---
const handleFileUpload = async (file) => {
  const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
  if (!file.raw || !allowedTypes.includes(file.raw.type)) {
    ElMessage.error('请上传有效的 PDF 或 Word 文件');
    return;
  }
  
  const formData = new FormData()
  formData.append('file', file.raw)
  
  submitLoading.value = true // 开启加载状态
  
  try {
    // 1. 调用解析接口
    const res = await parseResumeFileAPI(formData)
    const data = res.parsed_data
    
    // 2. 回填表单
    form.value = {
      ...form.value,
      name: data.name,
      phone: data.phone,
      email: data.email,
      title: data.title,
      summary: data.summary,
      work_experience: data.work_experience,
      project_experience: data.project_experience,
    }
    
    ElMessage.success('解析成功，请核对信息')
    
  } catch (error) {
    ElMessage.error('简历解析失败：' + (error.response?.data?.message || '服务器内部错误，请尝试手动填写'));
  } finally {
    submitLoading.value = false
  }
}

// 【新增】处理超出限制
const handleExceed = () => {
  ElMessage.warning('一次只能上传一个文件')
}

const fetchResumes = async () => {
  try {
    const res = await getResumeListAPI()
    resumeList.value = res || []
  } catch (error) {
    ElMessage.error('加载简历列表失败')
  }
}

// 监听 dialogVisible 的变化，或者直接在取消/保存成功的方法里重置
const handleCreate = () => {
  isEdit.value = false
  form.value = { ...defaultForm }
  fileList.value = [] // 新建时，确保清空旧文件
  dialogVisible.value = true
}

const handleEdit = (resume) => {
  isEdit.value = true
  form.value = {
    ...defaultForm,
    ...JSON.parse(JSON.stringify(resume)),
    use_profile_location: resume.use_profile_location ?? 1,
  }
  dialogVisible.value = true
}

const submitForm = () => {
  if (!form.value.work_experience && !form.value.project_experience && !form.value.summary) {
    ElMessage.warning('请至少填写工作经历、项目经验或自我评价中的一项')
    return
  }

  submitLoading.value = true
  
  const apiCall = isEdit.value 
    ? updateResumeAPI(form.value.id, form.value)
    : createResumeAPI(form.value)

  apiCall
    .then(() => {
      ElMessage.success('保存成功，数据已同步至向量库')
      dialogVisible.value = false
      fetchResumes()
    })
    .catch((err) => {
      ElMessage.error('保存失败: ' + (err.message || '请检查网络'))
    })
    .finally(() => {
      submitLoading.value = false
    })
}

const selectResume = (resume) => {
  resumeStore.setCurrentResume(resume.id)
  ElMessage.success(`已选中 "${resume.title}" 用于后续投递`)
}

const handleDelete = (id) => {
  ElMessageBox.confirm('确定要删除这份简历吗？此操作将从数据库和向量库中同时移除。', '警告', {
    type: 'warning'
  }).then(async () => {
    try {
      await deleteResumeAPI(id)
      ElMessage.success('删除成功')
      fetchResumes()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString()
}

// 3. 监听弹窗关闭事件 (可选，但更保险)
// 当用户点击右上角的 X 或点击遮罩层关闭时触发
const handleDialogClose = () => {
  fileList.value = [] // 清空文件列表
  form.value = { ...defaultForm } // 可选：同时重置表单内容
}

onMounted(() => {
  fetchResumes()
})
</script>

<style scoped>
.resume-manager {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100%;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
}

/* 上传区域样式 */
.upload-section {
  margin-bottom: 20px;
  padding: 10px;
  background-color: #fafafa;
  border: 1px dashed #d9d9d9;
  border-radius: 4px;
}

/* 卡片样式 */
.resume-card {
  border: 1px solid #ebeef5;
  transition: all 0.3s;
}

.resume-card.is-active {
  border-color: #67c23a;
  background-color: #f0f9eb;
  box-shadow: 0 0 15px rgba(103, 194, 58, 0.2);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.title {
  font-weight: bold;
  font-size: 16px;
  color: #303133;
}

.card-body p {
  margin: 8px 0;
  color: #606266;
  font-size: 13px;
  display: flex;
  align-items: center;
}

.card-body i {
  margin-right: 8px;
  color: #909399;
  width: 16px;
}

.card-footer {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>