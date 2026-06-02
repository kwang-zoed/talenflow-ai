<template>
  <el-dialog
    :model-value="props.modelValue"
    @update:model-value="(val) => emit('update:modelValue', val)"
    :title="isEdit ? '编辑简历' : '简历录入与解析'"
    width="750px"
    top="5vh"
    append-to-body
    destroy-on-close
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      label-position="left"
    >
      <!-- 1. 顶部核心功能：文件上传与解析 -->
      <el-form-item label="简历解析">
        <el-upload
          class="upload-demo"
          drag
          :auto-upload="true"
          :show-file-list="true"
          :limit="1"
          accept=".pdf,.doc,.docx"
          :http-request="handleUploadParse"
          :on-remove="handleFileRemove"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此处 或 <em>点击上传简历</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持 .pdf, .doc, .docx 格式，上传后将自动解析并填充下方表单
            </div>
          </template>
        </el-upload>
      </el-form-item>

      <el-divider />

      <!-- 2. 基础信息 -->
      <el-form-item label="姓名" prop="name">
        <el-input v-model="form.name" placeholder="请输入求职者姓名" />
      </el-form-item>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="联系电话" prop="phone">
            <el-input v-model="form.phone" placeholder="请输入手机号" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="form.email" placeholder="请输入邮箱" />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 3. 职位意向 -->
      <el-form-item label="意向职位" prop="title">
        <el-input v-model="form.title" placeholder="例如：AI算法工程师" />
      </el-form-item>

      <el-form-item label="学历背景" prop="education">
        <el-input v-model="form.education" placeholder="例如：北京大学 计算机科学 本科" />
      </el-form-item>

      <!-- 4. 详细内容 -->
      <el-form-item label="个人简介" prop="summary">
        <el-input
          v-model="form.summary"
          type="textarea"
          :rows="3"
          maxlength="500"
          show-word-limit
          placeholder="请简要描述个人优势或自我评价"
        />
      </el-form-item>

      <el-form-item label="工作经历" prop="work_experience">
        <el-input
          v-model="form.work_experience"
          type="textarea"
          :rows="5"
          maxlength="2000"
          show-word-limit
          placeholder="请描述详细的工作经历（支持换行）"
        />
      </el-form-item>

      <el-form-item label="项目经验" prop="project_experience">
        <el-input
          v-model="form.project_experience"
          type="textarea"
          :rows="4"
          maxlength="1000"
          show-word-limit
          placeholder="请描述主要项目经历"
        />
      </el-form-item>

      <!-- 5. 技能标签 -->
      <el-form-item label="技能标签" prop="skills">
        <el-select
          v-model="form.skills"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="输入技能后回车添加（如：Python, Vue3）"
          style="width: 100%"
        >
        </el-select>
      </el-form-item>

      <el-form-item label="简历状态" prop="status">
        <el-radio-group v-model="form.status">
          <el-radio label="active">已激活</el-radio>
          <el-radio label="archived">已归档</el-radio>
        </el-radio-group>
      </el-form-item>

    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="emit('update:modelValue', false)">取消</el-button>
        <el-button type="primary" :loading="loading" @click="submitForm">
          {{ isEdit ? '保存修改' : '立即录入' }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watchEffect, nextTick, inject } from 'vue';
import { ElMessage } from 'element-plus';
import { UploadFilled } from '@element-plus/icons-vue';
import axios from '../../utils/request';
import {
  submitResumeParseTask,
  pollResumeParseResult,
} from '../../api/adminResume';
import { wirePollToProgress, saveTaskToStorage, clearTaskStorage } from '../../utils/taskProgressRunner';

const RESUME_PARSE_STORAGE_KEY = 'talentflow_resume_parse_task';
const RESUME_PARSE_RESULT_KEY = 'talentflow_resume_parse_result';

const taskProgress = inject('parseProgress', null);

const props = defineProps({
  modelValue: Boolean,
  editData: Object
});

const emit = defineEmits(['update:modelValue', 'success']);

const formRef = ref(null);
const loading = ref(false);

// 初始空表单
const initialForm = {
  user_id: 1, 
  name: '',
  phone: '',
  email: '',
  title: '',
  education: '',
  summary: '',
  work_experience: '',
  project_experience: '',
  skills: [],
  status: 'active',
  resume_language: 'zh-CN'
  // source: '' // 用于存储上传后的文件路径
};

const form = reactive({ ...initialForm });

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入电话', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: ['blur', 'change'] }
  ],
  title: [{ required: true, message: '请输入意向职位', trigger: 'blur' }],
};

const isEdit = computed(() => !!props.editData);

// 监听弹窗显示与数据回填
watchEffect(() => {
  if (props.modelValue) {
    if (isEdit.value && props.editData) {
      Object.keys(form).forEach(key => {
        if (props.editData[key] !== undefined) {
          form[key] = props.editData[key];
        }
      });
    } else {
      nextTick(() => {
        Object.assign(form, initialForm);
        formRef.value?.clearValidate();
      });
    }
  }
});

// --- 新增：文件上传解析逻辑 ---
const handleUploadParse = async (options) => {
  const { file, onSuccess, onError } = options;

  try {
    const submitRes = await submitResumeParseTask(file);
    const taskId = submitRes.data?.task_id || submitRes.task_id;
    const filename = submitRes.data?.filename || file.name;

    saveTaskToStorage(RESUME_PARSE_STORAGE_KEY, {
      taskId,
      filename,
      taskType: 'resume_parse',
    });

    const poll = pollResumeParseResult(taskId, 300000);
    wirePollToProgress(poll, taskProgress, {
      showMessage: `正在后台解析简历: ${filename}`,
      taskType: 'resume_parse',
      completeHint: '解析完成，表单已自动填充',
      completeButtonText: '',
    });

    const parsedData = await poll;
    clearTaskStorage(RESUME_PARSE_STORAGE_KEY, RESUME_PARSE_RESULT_KEY);

    Object.assign(form, {
      ...form,
      ...parsedData,
    });

    taskProgress?.update({
      status: 'success',
      message: '简历解析完成',
      percent: 100,
      taskType: 'resume_parse',
      completeHint: '表单已自动填充',
      completeButtonText: '',
    });

    ElMessage.success('简历解析成功，已自动填充！');
    onSuccess(parsedData);
  } catch (error) {
    clearTaskStorage(RESUME_PARSE_STORAGE_KEY, RESUME_PARSE_RESULT_KEY);
    ElMessage.error(error.message || '简历解析失败，请手动填写');
    onError(error);
  }
};

const handleFileRemove = () => {
  form.source = ''; // 移除文件时清空来源
};

const submitForm = async () => {
  if (!formRef.value) return;
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      try {
        if (isEdit.value) {
          await axios.put(`/admin/resumes/${props.editData.id}`, form);
          ElMessage.success('更新成功');
        } else {
          await axios.post('/admin/resumes', form);
          ElMessage.success('录入成功');
        }
        
        emit('success');
        emit('update:modelValue', false);
        
      } catch (error) {
        ElMessage.error(isEdit.value ? '更新失败' : '录入失败');
        console.error(error);
      } finally {
        loading.value = false;
      }
    }
  });
};

const handleClose = () => {
  formRef.value?.clearValidate();
};
</script>

<style scoped>
/* 调整上传组件的样式，使其更美观 */
.upload-demo {
  width: 100%;
}
:deep(.el-upload-dragger) {
  width: 100%;
  padding: 20px;
}
</style>