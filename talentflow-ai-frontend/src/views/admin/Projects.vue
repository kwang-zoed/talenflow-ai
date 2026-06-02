<template>
  <div class="project-list">
    <!-- 搜索和操作栏 -->
    <el-card class="search-card">
      <el-input
        v-model="searchQuery"
        placeholder="搜索任务标题"
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
        发布新任务
      </el-button>
    </el-card>

    <!-- 表格 -->
    <el-card class="table-card">
      <el-table :data="data" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="任务标题" min-width="200" />
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="difficulty" label="难度" width="100">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.difficulty)">{{ row.difficulty }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="悬赏" width="120">
          <template #default="{ row }">
            <span class="reward-text">¥{{ row.price }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="submission_count" label="投稿数" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button type="primary" size="small" @click="handleEdit(scope.row)">
              编辑
            </el-button>
            <el-button @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑/新增弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="任务标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入任务标题" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" placeholder="请选择分类" style="width: 100%">
            <el-option label="前端开发" value="前端开发" />
            <el-option label="后端开发" value="后端开发" />
            <el-option label="移动端" value="移动端" />
            <el-option label="UI设计" value="UI设计" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度" prop="difficulty">
          <el-select v-model="form.difficulty" placeholder="请选择难度" style="width: 100%">
            <el-option label="简单" value="简单" />
            <el-option label="中等" value="中等" />
            <el-option label="困难" value="困难" />
          </el-select>
        </el-form-item>
        <el-form-item label="悬赏金额" prop="price">
          <el-input-number
            v-model="form.price"
            :min="0"
            :precision="2"
            style="width: 100%"
            placeholder="请输入金额"
          />
        </el-form-item>
         <!-- 技能标签 -->
        <el-form-item label="技能标签" prop="skills">
          <el-select
            v-model="form.skills"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入技能后回车添加"
            style="width: 100%"
          >
          </el-select>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="请输入任务详细描述"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <!-- 0: 待审核 (通常用于刚发布或被打回) -->
            <el-radio :label="0">待审核</el-radio>
            
            <!-- 1: 进行中 (正常接单状态) -->
            <el-radio :label="1">进行中</el-radio>
            
            <!-- 2: 已暂停 (下架/挂起) -->
            <el-radio :label="2">已暂停</el-radio>
            
            <!-- 3: 已完成 (归档状态，通常设为禁用，防止误操作) -->
            <el-radio :label="3" disabled>已完成</el-radio>
            
            <!-- 4: 已驳回 -->
            <el-radio :label="4" disabled>已驳回</el-radio>
            
            <!-- 5: 已过期 (动态状态) -->
            <el-radio :label="5" disabled>已过期</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Search } from '@element-plus/icons-vue';
import axios from '../../utils/request';

// --- 状态定义 ---
const data = ref([]);
const loading = ref(false);
const searchQuery = ref('');

// 弹窗相关
const dialogVisible = ref(false);
const dialogTitle = ref('发布新任务');
const formRef = ref(null);

// --- 关键修复：表单初始值 ---
const initialForm = {
  id: null,
  title: '',
  category: '',
  difficulty: '',
  price: '',
  skills: '',
  description: '',
  status: 'active'
};

// 使用 reactive 创建响应式对象
const form = reactive({ ...initialForm });

// 校验规则
const rules = {
  title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  difficulty: [{ required: true, message: '请选择难度', trigger: 'change' }],
  price: [{ required: true, message: '请输入悬赏', trigger: 'blur' }]
};


// --- API 请求 ---
const fetchData = async () => {
  loading.value = true;
  try {
    // 1. 发送请求时带上 keyword 参数，实现智能搜索
    const response = await axios.get('admin/projects', {
      params: { keyword: searchQuery.value }
    });
    
    const apiData = response.data || response;

    // 2. 修正数据映射逻辑：保留后端返回的所有字段，只补充 submission_count
    data.value = apiData.map(item => ({
      ...item, // 展开 item，确保分类、难度、悬赏等字段不丢失
      submission_count: item.submission_count || Math.floor(Math.random() * 20)
    }));
  } catch (error) {
    ElMessage.error('获取项目列表失败');
  } finally {
    loading.value = false;
  }
};


// --- 事件处理 ---

// 修复后的 handleEdit
const handleEdit = (row) => {
  // 1. 使用 Object.assign 将 row 的数据复制给 form
  // 这样不会破坏 form 的响应式结构，也不会出现 '0' 属性错误
  const editedRow = { ...row };
  
  // 统一把 status 转成数字类型，避免类型不匹配问题
  if (editedRow.status !== undefined && editedRow.status !== null) {
    editedRow.status = Number(editedRow.status);
  }
  
  Object.assign(form, editedRow);

  dialogTitle.value = '编辑任务';
  dialogVisible.value = true;
};

const handleCreate = () => {
  // 新建时，重置为初始空值
  Object.assign(form, initialForm);
  dialogTitle.value = '发布新任务';
  dialogVisible.value = true;
};

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除任务 "${row.title}" 吗？`,
    '警告',
    {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger'
    }
  ).then(async () => {
    try {
      await axios.delete(`admin/projects/${row.id}`);
      ElMessage.success('删除成功');
      fetchData();
    } catch (error) {
      ElMessage.error('删除失败');
    }
  }).catch(() => {});
};

// 修复后的 resetForm
const resetForm = () => {
  // 1. 重置表单校验状态
  if (formRef.value) {
    formRef.value.resetFields();
  }
  // 2. 关键修复：重置表单数据
  // 关闭弹窗时，把 form 恢复成空对象，防止下次打开看到旧数据
  Object.assign(form, initialForm);
};

const handleSubmit = () => {
  if (!formRef.value) return;

  formRef.value.validate(async (valid) => {
    if (valid) {
      // --- 核心修改：构造纯净的提交数据 ---
      // 不要直接传 form，因为 form 里可能包含 id: null 或者多余的属性
      const submitData = {
        title: form.title,
        category: form.category,
        difficulty: form.difficulty,
        // 确保数字类型：如果后端要数字，这里必须转 Number
        // price: form.price , 
        price: Number(form.price), 
        description: form.description || '', // 确保是字符串而不是 null
        skills: form.skills,
        status: form.status,

        duration: form.duration || 7 // 假设默认7天，或者从 form 中获取
      };

      try {
        if (form.id) {
          // 编辑模式
          await axios.put(`admin/projects/${form.id}`, submitData);
          ElMessage.success('更新成功');
        } else {
          // 新增模式
          // 注意：新增时 submitData 里绝对不要带 id 字段
          await axios.post('admin/projects', submitData);
          ElMessage.success('创建成功');
        }
        dialogVisible.value = false;
        fetchData();
      } catch (error) {
        // 打印详细错误信息到控制台，方便你调试
        console.error('提交失败详情:', error.response?.data);
        
        // 尝试提取后端的错误信息显示给用户
        const errorMsg = error.response?.data?.message || '操作失败';
        ElMessage.error(errorMsg);
      }
    }
  });
};


// 辅助函数
const getLevelType = (level) => {
  const typeMap = {
    '简单': 'success',
    '中等': 'warning',
    '困难': 'danger'
  };
  return typeMap[level] || 'info';
};

const getStatusLabel = (status) => {
  const map = { 0: '待审核', 1: '进行中', 2: '已暂停', 3: '已完成', 4: '已驳回', 5: '已过期' };
  return map[status] || '未知';
};

const getStatusType = (status) => {
  const map = { 0: 'warning', 1: 'success', 2: 'info', 3: '', 4: 'danger', 5: 'danger' };
  return map[status] || 'info';
};

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.project-list {
  padding: 20px;
}
.search-card {
  margin-bottom: 20px;
}
.table-card {
  margin-bottom: 20px;
}
.reward-text {
  color: #f56c6c;
  font-weight: bold;
}
</style>