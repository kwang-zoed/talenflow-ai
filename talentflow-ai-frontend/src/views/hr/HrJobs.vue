<template>
  <div class="job-list">
    <!-- 搜索和操作栏 -->
    <el-card class="search-card">
      <el-input
        v-model="searchQuery"
        placeholder="搜索职位名称、公司或地点"
        style="width: 300px"
        clearable
        @clear="fetchData"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" @click="fetchData">
        <el-icon><Search /></el-icon>
        搜索
      </el-button>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        录入新职位
      </el-button>
      <el-button type="success" @click="handleBatchCreate">
        <el-icon><Document /></el-icon>
        批量录入新职位
      </el-button>
    </el-card>

    <!-- 表格 -->
    <el-card class="table-card">
      <el-table
        :data="data"
        v-loading="loading"
        border
        stripe
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="职位名称" min-width="180" />
        <el-table-column prop="company" label="公司" width="150" />
        
        <!-- 1. 新增：表格列显示地点 -->
        <el-table-column prop="location" label="工作地点" width="120">
          <template #default="{ row }">
            {{ row.location || '不限' }}
          </template>
        </el-table-column>
        
        <el-table-column prop="salary" label="薪资" width="120" />
        
        <!-- 技能要求展示 -->
        <el-table-column label="技能要求" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="skill in parseSkills(row.required_skills)"
              :key="skill"
              type="info"
              size="small"
              style="margin-right: 4px; margin-bottom: 4px"
            >
              {{ skill }}
            </el-tag>
          </template>
        </el-table-column>
        
        <!-- 职位文件链接 -->
        <el-table-column label="职位文件" width="120">
          <template #default="{ row }">
            <el-button
              v-if="row.file_path"
              type="primary"
              link
              size="small"
              @click="handleViewFile(row.file_path)"
            >
              查看PDF
            </el-button>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        
        <!-- 操作按钮 -->
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="scope">
            <el-button type="success" size="small" @click="goRecommend(scope.row)">
              智能推荐简历
            </el-button>
            <el-button
              type="primary"
              size="small"
              @click="handleEdit(scope.row)"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑/新增弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="700px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="职位名称" prop="title">
          <el-input v-model="form.title" placeholder="如：高级前端工程师" />
        </el-form-item>
        
        <el-form-item label="公司" prop="company">
          <el-input v-model="form.company" placeholder="如：字节跳动" />
        </el-form-item>
        
        <!-- 2. 新增：地点输入框 -->
        <el-form-item label="工作地点" prop="location">
          <LocationPicker v-model:city="form.location" :show-address="false" city-placeholder="如：广东省/深圳市" />
        </el-form-item>
        <el-form-item label="详细工作地址">
          <el-input v-model="form.work_address" placeholder="如：南山区科技园XX路XX号（选填，提高距离精度）" />
        </el-form-item>

        <el-form-item label="薪资范围" prop="salary">
          <el-input v-model="form.salary" placeholder="如：25k-40k" />
        </el-form-item>

        <!-- 3. 新增：经验与学历要求 -->
        <el-form-item label="经验要求" prop="experience_requirement">
          <el-input v-model="form.experience_requirement" placeholder="如：3-5年" />
        </el-form-item>
        
        <el-form-item label="学历要求" prop="education_requirement">
          <el-input v-model="form.education_requirement" placeholder="如：本科" />
        </el-form-item>

        <el-form-item label="技能标签">
          <div class="tag-input-container">
            <el-tag
              v-for="(skill, index) in skillTags"
              :key="skill"
              closable
              @close="removeSkill(index)"
            >
              {{ skill }}
            </el-tag>
            <el-input
              v-model="newSkill"
              placeholder="输入技能后按回车添加"
              class="skill-input"
              @keyup.enter="addSkill"
            />
          </div>
        </el-form-item>
        
        <el-form-item label="职位描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="请输入职位描述..."
          />
        </el-form-item>
        
        <!-- 文件上传组件 -->
        <el-form-item label="招聘文档">
          <el-upload
            class="upload-demo"
            :auto-upload="true"
            :show-file-list="true"
            :http-request="handleUploadParse"
            :on-remove="handleFileRemove"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽文件或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                上传的文件将被解析并存入向量数据库用于 AI 匹配
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 批量录入弹窗 -->
    <el-dialog
      v-model="batchDialogVisible"
      title="批量录入新职位"
      width="700px"
      @close="resetBatchForm"
    >
      <!-- 文件上传区 -->
      <div v-if="batchJobs.length === 0" style="text-align: center; padding: 40px">
        <el-upload
          class="upload-demo"
          :auto-upload="true"
          :show-file-list="true"
          :http-request="handleBatchUploadParse"
        >
          <el-button type="primary">
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            上传文件批量解析
          </el-button>
          <template #tip>
            <div class="el-upload__tip">
              支持上传包含多个职位的文档（PDF、DOCX、TXT）
            </div>
          </template>
        </el-upload>
      </div>

      <!-- 职位详情展示区（带翻页） -->
      <div v-else>
        <!-- 翻页控制 -->
        <div style="margin-bottom: 20px; text-align: right">
          <span style="margin-right: 12px">
            第 {{ currentBatchIndex + 1 }} / {{ batchJobs.length }} 个职位
          </span>
          <el-button
            size="small"
            :disabled="currentBatchIndex === 0"
            @click="currentBatchIndex--"
          >
            上一个
          </el-button>
          <el-button
            size="small"
            :disabled="currentBatchIndex === batchJobs.length - 1"
            @click="currentBatchIndex++"
          >
            下一个
          </el-button>
        </div>

        <!-- 可编辑表单 -->
        <el-form
          :model="batchJobs[currentBatchIndex]"
          label-width="100px"
        >
          <el-form-item label="职位名称">
            <el-input v-model="batchJobs[currentBatchIndex].title" placeholder="请输入职位名称" />
          </el-form-item>
          
          <el-form-item label="公司">
            <el-input v-model="batchJobs[currentBatchIndex].company" placeholder="请输入公司名称" />
          </el-form-item>
          
          <el-form-item label="工作地点">
            <el-input v-model="batchJobs[currentBatchIndex].location" placeholder="请输入工作地点" />
          </el-form-item>

          <el-form-item label="薪资范围">
            <el-input v-model="batchJobs[currentBatchIndex].salary" placeholder="请输入薪资范围" />
          </el-form-item>

          <el-form-item label="经验要求">
            <el-input v-model="batchJobs[currentBatchIndex].experience_requirement" placeholder="请输入经验要求" />
          </el-form-item>
          
          <el-form-item label="学历要求">
            <el-input v-model="batchJobs[currentBatchIndex].education_requirement" placeholder="请输入学历要求" />
          </el-form-item>

          <el-form-item label="技能标签">
            <div class="tag-input-container">
              <el-tag
                v-for="(skill, index) in batchJobs[currentBatchIndex].required_skills || []"
                :key="skill + index"
                closable
                @close="removeBatchSkill(currentBatchIndex, index)"
              >
                {{ skill }}
              </el-tag>
              <el-input
                v-model="batchNewSkill"
                placeholder="输入技能后按回车添加"
                class="skill-input"
                @keyup.enter="addBatchSkill(currentBatchIndex)"
              />
            </div>
          </el-form-item>
          
          <el-form-item label="职位描述">
            <el-input
              v-model="batchJobs[currentBatchIndex].description"
              type="textarea"
              :rows="4"
              placeholder="请输入职位描述..."
            />
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button
          v-if="batchJobs.length > 0"
          type="primary"
          :loading="batchSaving"
          @click="handleBatchSave"
        >
          全部保存（{{ batchJobs.length }} 个）
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, inject } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Search, UploadFilled, Document } from '@element-plus/icons-vue';
import axios from '../../utils/request';
import { hrSubmitParseTask, hrPollParseTaskResult, hrGetParseTaskStatus } from '../../api/job';
import LocationPicker from '@/components/LocationPicker.vue';

const router = useRouter();

// --- 状态定义 ---
const data = ref([]);
const loading = ref(false);
const searchQuery = ref('');

// 单条弹窗相关
const dialogVisible = ref(false);
const dialogTitle = ref('录入新职位');
const formRef = ref(null);
const selectedFile = ref(null); // 存储选中的文件对象
const fileList = ref([]); // el-upload 需要的文件列表

// 批量录入相关
const batchDialogVisible = ref(false);
const batchJobs = ref([]);
const currentBatchIndex = ref(0);
const batchSaving = ref(false);
const batchNewSkill = ref('');

const addBatchSkill = (jobIndex) => {
  const skill = batchNewSkill.value.trim();
  if (skill && batchJobs.value[jobIndex]) {
    if (!batchJobs.value[jobIndex].required_skills) {
      batchJobs.value[jobIndex].required_skills = [];
    }
    if (!batchJobs.value[jobIndex].required_skills.includes(skill)) {
      batchJobs.value[jobIndex].required_skills.push(skill);
    }
    batchNewSkill.value = '';
  }
};

const removeBatchSkill = (jobIndex, skillIndex) => {
  if (batchJobs.value[jobIndex] && batchJobs.value[jobIndex].required_skills) {
    batchJobs.value[jobIndex].required_skills.splice(skillIndex, 1);
  }
};

// --- 表单初始值 (更新：添加新字段) ---
const initialForm = {
  id: null,
  job_id: '', // 默认为空，用户不填就不传
  title: '',
  company: '',
  salary: '',
  // 4. 新增：初始化新字段
  location: '',
  work_address: '',
  experience_requirement: '',
  education_requirement: '',
  required_skills: '', // 字符串格式，提交时转数组
  description: '',
  file_path: ''
};

const form = reactive({ ...initialForm });

// --- 技能标签管理 ---
const skillTags = ref([]);
const newSkill = ref('');

const addSkill = () => {
  const skill = newSkill.value.trim();
  if (skill && !skillTags.value.includes(skill)) {
    skillTags.value.push(skill);
    newSkill.value = '';
  }
};

const removeSkill = (index) => {
  skillTags.value.splice(index, 1);
};

// --- 校验规则 (更新：添加新字段规则) ---
const rules = {
  title: [{ required: true, message: '请输入职位名称', trigger: 'blur' }],
  company: [{ required: true, message: '请输入公司名称', trigger: 'blur' }],
  salary: [{ required: true, message: '请输入薪资范围', trigger: 'blur' }],
  // 5. 新增：为新字段添加必填规则
  location: [{ required: true, message: '请输入工作地点', trigger: 'blur' }],
  experience_requirement: [{ required: true, message: '请输入经验要求', trigger: 'blur' }],
  education_requirement: [{ required: true, message: '请输入学历要求', trigger: 'blur' }]
};

// --- 辅助函数 ---
// 将后端返回的 JSON 字符串或数组转为数组，方便 el-tag 循环
const parseSkills = (skills) => {
  if (!skills) return [];
  if (Array.isArray(skills)) return skills;
  try {
    return JSON.parse(skills);
  } catch (e) {
    return [skills];
  }
};

// --- API 请求 ---
const fetchData = async () => {
  loading.value = true;
  try {
    const response = await axios.get('hr/jobs', { params: { keyword: searchQuery.value } });
    data.value = response.data || response;
  } catch (error) {
    ElMessage.error('获取职位列表失败');
    console.error(error);
  } finally {
    loading.value = false;
  }
};

// --- 文件处理 ---
const handleFileRemove = () => {
  selectedFile.value = null;
  fileList.value = [];
};

const handleViewFile = (filePath) => {
  if (!filePath) return;
  window.open(filePath, '_blank');
};

// --- 事件处理 ---
const goRecommend = (row) => {
  router.push(`/hr/jobs/${row.id}/recommend`);
};

const handleEdit = (row) => {
  // 重置表单状态
  Object.assign(form, initialForm);
  fileList.value = [];
  selectedFile.value = null;
  skillTags.value = [];
  
  // 填充数据
  Object.assign(form, row);
  
  // 处理技能标签显示
  if (Array.isArray(row.required_skills)) {
    skillTags.value = [...row.required_skills];
  } else if (row.required_skills) {
    skillTags.value = row.required_skills.split(',').map(s => s.trim()).filter(s => s);
  }
  
  // 处理文件列表回显 (显示真实文件名)
  if (row.file_path) {
    const fileName = row.file_path.split('/').pop() || '已上传文件';
    fileList.value = [{ name: fileName, url: row.file_path }];
  }
  dialogTitle.value = '编辑职位';
  dialogVisible.value = true;
};

const handleCreate = () => {
  Object.assign(form, initialForm);
  fileList.value = [];
  selectedFile.value = null;
  skillTags.value = [];
  newSkill.value = '';
  dialogTitle.value = '录入新职位';
  dialogVisible.value = true;
};

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除职位 "${row.title}" 吗？`,
    '警告',
    {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger'
    }
  ).then(async () => {
    try {
      await axios.delete(`hr/jobs/${row.id}`);
      ElMessage.success('删除成功');
      fetchData();
    } catch (error) {
      ElMessage.error('删除失败');
      console.error(error);
    }
  }).catch(() => {});
};

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields();
  }
  Object.assign(form, initialForm);
  fileList.value = [];
  selectedFile.value = null;
};

// --- 新版：Celery 异步解析（提交+轮询+全局进度条+持久化恢复）---
const progressRef = inject('parseProgress', null)
let currentPollPromise = ref(null)

const STORAGE_KEY_PARSE_TASK = 'talentflow_hr_parse_task'
const STORAGE_KEY_PARSE_RESULT = 'talentflow_hr_parse_result'

function saveParseTask(taskId, filename, isBatch) {
  try {
    localStorage.setItem(STORAGE_KEY_PARSE_TASK, JSON.stringify({
      taskId, filename, isBatch, timestamp: Date.now()
    }))
  } catch (e) {}
}

function getSavedParseTask() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY_PARSE_TASK)
    if (saved) {
      const data = JSON.parse(saved)
      if (Date.now() - data.timestamp < 600000) return data
    }
  } catch (e) {}
  return null
}

function clearSavedParseTask() {
  try { localStorage.removeItem(STORAGE_KEY_PARSE_TASK) } catch (e) {}
}

function getCompletedParseResult() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY_PARSE_RESULT)
    if (saved) {
      const wrapper = JSON.parse(saved)
      if (Date.now() - wrapper.timestamp < 600000) return wrapper.data
    }
  } catch (e) {}
  return null
}

function clearCompletedParseResult() {
  try { localStorage.removeItem(STORAGE_KEY_PARSE_RESULT) } catch (e) {}
}

function fillFormFromParsedResult(result) {
  if (!result) return
  if (result.is_batch) return
  
  form.title = result.title || form.title
  form.company = result.company || form.company
  form.salary = result.salary || form.salary
  form.location = result.location || form.location
  form.experience_requirement = result.experience_requirement || form.experience_requirement
  form.education_requirement = result.education_requirement || form.education_requirement
  form.description = result.description || form.description
  
  if (result.required_skills && Array.isArray(result.required_skills)) {
    skillTags.value = [...result.required_skills]
  }
}

const handleUploadParse = async ({ file, onSuccess, onError }) => {
  try {
    dialogVisible.value = true
    
    const submitRes = await hrSubmitParseTask(file, false)
    const taskId = submitRes.data?.task_id || submitRes.task_id
    const filename = submitRes.data?.filename || file.name
    
    saveParseTask(taskId, filename, false)
    
    if (progressRef) {
      progressRef.show(`正在后台解析: ${filename}`)
    }
    
    const poll = hrPollParseTaskResult(taskId, 300000)
    currentPollPromise.value = poll
    
    poll.onProgress = (statusData) => {
      if (progressRef) progressRef.update(statusData)
    }
    
    const finalResult = await poll
    
    clearSavedParseTask()
    
    // 在页面上等待完成：直接回填，进度条只显示完成状态
    if (!finalResult.is_batch) {
      fillFormFromParsedResult(finalResult)
      ElMessage.success('解析完成，表单已自动填充')
    }
    
    // 进度条显示完成，但不显示"前往填充"按钮（因为已经自动回填了）
    if (progressRef) {
      progressRef.update({
        status: 'success',
        message: '解析完成',
        percent: 100,
        data: finalResult
      })
    }
    
    fileList.value = [{ name: filename, url: '#' }]
    onSuccess({})
    
  } catch (err) {
    clearSavedParseTask()
    ElMessage.error(err.message || '解析失败')
    if (progressRef) progressRef.hide()
    onError && onError(err)
  }
};

// --- 提交处理 ---
const handleSubmit = () => {
  if (!formRef.value) return;
  formRef.value.validate(async (valid) => {
    if (valid) {
      const formData = new FormData();
      
      // 8. 新增：添加新字段到提交数据中
      formData.append('title', form.title);
      formData.append('company', form.company);
      formData.append('salary', form.salary); // 注意：后端字段名为 salary_range
      formData.append('location', form.location);
      formData.append('work_address', form.work_address || '');
      formData.append('experience_requirement', form.experience_requirement);
      formData.append('education_requirement', form.education_requirement);
      formData.append('description', form.description);

      // 9. 处理技能标签数组
      formData.append('required_skills', JSON.stringify(skillTags.value));

      // 10. 添加文件 (如果选择了新文件)
      if (selectedFile.value) {
        formData.append('file', selectedFile.value);
      }

      try {
        if (form.id) {
          // 编辑模式 (PUT)
          // 注意：这里假设你的 PUT 接口路径是 `/hr/jobs/${form.id}`
          await axios.put(`hr/jobs/${form.id}`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          ElMessage.success('更新成功');
        } else {
          // 新增模式 (POST)
          await axios.post('hr/jobs', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          ElMessage.success('创建成功');
        }
        dialogVisible.value = false;
        fetchData();
      } catch (error) {
        console.error(error);
        ElMessage.error('操作失败，请检查后端日志');
      }
    }
  });
};

// --- 批量录入相关 ---
const handleBatchCreate = () => {
  batchJobs.value = [];
  currentBatchIndex.value = 0;
  batchDialogVisible.value = true;
};

const resetBatchForm = () => {
  batchJobs.value = [];
  currentBatchIndex.value = 0;
};

const handleBatchUploadParse = async ({ file, onSuccess, onError }) => {
  try {
    batchDialogVisible.value = true
    
    const submitRes = await hrSubmitParseTask(file, true)
    const taskId = submitRes.data?.task_id || submitRes.task_id
    const filename = submitRes.data?.filename || file.name
    
    saveParseTask(taskId, filename, true)
    
    if (progressRef) {
      progressRef.show(`正在后台批量解析: ${filename}`)
    }
    
    const poll = hrPollParseTaskResult(taskId, 300000)
    currentPollPromise.value = poll
    
    poll.onProgress = (statusData) => {
      if (progressRef) progressRef.update(statusData)
    }
    
    const finalResult = await poll
    
    clearSavedParseTask()
    
    if (progressRef) {
      progressRef.update({
        status: 'success',
        message: '批量解析完成',
        percent: 100,
        data: finalResult
      })
    }
    
    if (finalResult.is_batch && finalResult.jobs) {
      batchJobs.value = finalResult.jobs
      currentBatchIndex.value = 0
      ElMessage.success(`批量解析完成，共 ${batchJobs.value.length} 个职位`)
    } else {
      batchJobs.value = []
    }
    
    onSuccess({})
    
  } catch (err) {
    clearSavedParseTask()
    ElMessage.error(err.message || '批量解析失败')
    if (progressRef) progressRef.hide()
    onError && onError(err)
  }
};

const handleBatchSave = async () => {
  if (batchJobs.value.length === 0) return;
  batchSaving.value = true;
  let successCount = 0;
  let failCount = 0;
  
  for (let i = 0; i < batchJobs.value.length; i++) {
    try {
      const job = batchJobs.value[i];
      const formData = new FormData();
      formData.append('title', job.title || '未命名职位');
      formData.append('company', job.company || '未知公司');
      formData.append('salary', job.salary || '面议');
      formData.append('location', job.location || '不限');
      formData.append('experience_requirement', job.experience_requirement || '不限');
      formData.append('education_requirement', job.education_requirement || '不限');
      formData.append('description', job.description || '');
      formData.append('required_skills', JSON.stringify(
        Array.isArray(job.required_skills) ? job.required_skills : []
      ));
      
      await axios.post('hr/jobs', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      successCount++;
    } catch (error) {
      console.error(`第 ${i + 1} 个职位保存失败:`, error);
      failCount++;
    }
  }
  
  batchSaving.value = false;
  
  if (failCount === 0) {
    ElMessage.success(`全部保存成功，共 ${successCount} 个职位`);
  } else {
    ElMessage.warning(`保存完成：成功 ${successCount} 个，失败 ${failCount} 个`);
  }
  
  batchDialogVisible.value = false;
  fetchData();
};

function handleGlobalParseComplete(event) {
  const result = event.detail
  if (!result) return
  
  if (result.is_batch) {
    batchDialogVisible.value = true
    if (result.jobs) {
      batchJobs.value = result.jobs
      currentBatchIndex.value = 0
    }
  } else {
    dialogVisible.value = true
    handleCreate()
    fillFormFromParsedResult(result)
  }
  ElMessage.success('已完成解析，前往填充')
}

async function resumePolling() {
  const completedResult = getCompletedParseResult()
  if (completedResult) {
    try {
      await ElMessageBox({
        title: '发现解析结果',
        message: completedResult.is_batch 
          ? `检测到批量解析结果（${completedResult.jobs?.length || 0}个职位），是否立即打开批量录入？`
          : '检测到职位解析结果，是否自动填入新建职位表单？',
        showCancelButton: true,
        confirmButtonText: '立即回填',
        cancelButtonText: '暂不需要',
        type: 'info'
      })
      
      clearCompletedParseResult()
      
      if (completedResult.is_batch) {
        if (completedResult.jobs && completedResult.jobs.length > 0) {
          batchJobs.value = completedResult.jobs
          currentBatchIndex.value = 0
          batchDialogVisible.value = true
          ElMessage.success(`共 ${completedResult.jobs.length} 个职位`)
        }
      } else {
        dialogVisible.value = true
        handleCreate()
        fillFormFromParsedResult(completedResult)
        ElMessage.success('解析结果已填入表单')
      }
      
    } catch (e) {}
    return
  }
  
  const savedTask = getSavedParseTask()
  if (!savedTask) return
  
  console.log('[HrJobs.vue] 发现未完成任务，先查状态:', savedTask.taskId)
  
  try {
    const statusResp = await hrGetParseTaskStatus(savedTask.taskId)
    const statusData = statusResp.data?.status ? statusResp.data : statusResp
    
    console.log('[HrJobs.vue] 任务当前状态:', statusData)
    
    if (statusData.status === 'success') {
      // 已经完成了，保存到 completed 下次检测到就弹确认框
      try {
        localStorage.setItem(STORAGE_KEY_PARSE_RESULT, JSON.stringify({
          data: statusData.data,
          timestamp: Date.now()
        }))
      } catch (e) {}
      // 刚完成也立即检测一次
      resumePolling()
      return
    }
    
    if (statusData.status === 'processing') {
      // 还在进行，直接更新现有进度（不重新 show 避免"看起来重置"）
      if (progressRef) {
        progressRef.update(statusData)
      }
    }
    
  } catch (e) {
    console.warn('[HrJobs.vue] 查询状态失败:', e)
  }
}

onMounted(() => {
  fetchData()
  window.addEventListener('globalParseComplete', handleGlobalParseComplete)
  resumePolling()
})

onUnmounted(() => {
  window.removeEventListener('globalParseComplete', handleGlobalParseComplete)
  currentPollPromise.value = null
})
</script>

<style scoped>
.job-list {
  padding: 20px;
}
.search-card {
  margin-bottom: 20px;
}
.text-muted {
  color: #999;
  font-size: 13px;
}
.tag-input-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  min-height: 36px;
}
.skill-input {
  border: none;
  outline: none;
  flex: 1;
  min-width: 100px;
}
</style>