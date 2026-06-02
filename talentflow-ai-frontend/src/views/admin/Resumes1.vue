<template>
  <div class="resumes-container">
    <!-- 1. 顶部操作栏 -->
    <div class="header-card">
      <h2>简历数据管理</h2>
      <div class="actions">
        <el-input
          v-model="searchQuery"
          placeholder="搜索用户或技能"
          prefix-icon="Search"
          style="width: 240px; margin-right: 10px"
          @keyup.enter="fetchData"
        />
        <el-button type="primary" @click="handleAdd">
          <el-icon><Upload /></el-icon>
          手动录入
        </el-button>
      </div>
    </div>

    <!-- 2. 数据表格 -->
    <el-card shadow="never" class="table-card">
      <el-table
        :data="data"
        v-loading="loading"
        style="width: 100%"
        stripe
        border
      >
        <el-table-column prop="userName" label="用户/姓名" width="120" />
        <el-table-column prop="jobTitle" label="意向职位" width="180" />
        
        <!-- 技能标签列 -->
        <el-table-column label="技能标签" min-width="180">
          <template #default="scope">
            <el-tag
              v-for="(tag, index) in scope.row.skills"
              :key="index"
              size="small"
              type="info"
              effect="plain"
              style="margin-right: 4px; margin-bottom: 4px"
            >
              {{ tag }}
            </el-tag>
          </template>
        </el-table-column>

        <!-- 状态列 -->
        <el-table-column label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'Active' ? 'success' : 'warning'" effect="light">
              {{ scope.row.status === 'Active' ? '已激活' : '待审核' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="updatedAt" label="更新时间" width="160" />

        <!-- 操作列 -->
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button link type="primary" size="small" @click="handlePreview(scope.row)">预览</el-button>
            <el-button link type="primary" size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-popconfirm
              title="确定删除这份简历吗？"
              @confirm="handleDelete(scope.row)"
              width="160"
            >
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.current"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          layout="total, prev, pager, next, jumper"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 3. 简历预览弹窗 -->
    <el-dialog
      v-model="previewVisible"
      :title="currentResume?.userName + ' 的简历详情'"
      width="650px"
      destroy-on-close
      class="preview-dialog"
    >
      <div v-if="currentResume" class="resume-detail-view">
        <!-- 头部信息 -->
        <div class="resume-header">
          <div class="user-info">
            <h3 class="name">{{ currentResume.userName }}</h3>
            <span class="job-title">{{ currentResume.jobTitle }}</span>
          </div>
          <div class="status-badge">
            <el-tag :type="currentResume.status === 'Active' ? 'success' : 'warning'">
              {{ currentResume.status === 'Active' ? '已激活' : '待审核' }}
            </el-tag>
          </div>
        </div>

        <el-divider />

        <!-- 基础属性 -->
        <el-descriptions :column="2" size="small" border class="mb-4">
          <el-descriptions-item label="联系电话">{{ currentResume.phone }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ currentResume.email }}</el-descriptions-item>
          <el-descriptions-item label="学历">{{ currentResume.education }}</el-descriptions-item>
          <el-descriptions-item label="工作经验">{{ currentResume.experience }}</el-descriptions-item>
        </el-descriptions>

        <!-- 技能标签 -->
        <div class="section">
          <h4 class="section-title">技能栈</h4>
          <div class="tags-wrapper">
            <el-tag v-for="(skill, index) in currentResume.skills" :key="index" type="primary" effect="plain" style="margin-right: 8px; margin-bottom: 8px;">
              {{ skill }}
            </el-tag>
          </div>
        </div>

        <!-- 自我评价/简介 -->
        <div class="section" v-if="currentResume.bio">
          <h4 class="section-title">个人简介</h4>
          <p class="bio-text">{{ currentResume.bio }}</p>
        </div>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="previewVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Search, Upload } from '@element-plus/icons-vue';
import axios from '@/utils/request'; // 引入你封装好的 axios 实例

// --- 表格数据状态 ---
const data = ref([]);
const loading = ref(false);
const searchQuery = ref('');

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
});

// --- 预览弹窗状态 ---
const previewVisible = ref(false);
const currentResume = ref(null);

// --- 1. 获取列表数据 (真实接口) ---
const fetchData = async () => {
  loading.value = true;
  try {
    const response = await axios.get('/resumes/', {
      params: {
        page: pagination.current,
        limit: pagination.pageSize,
        // 如果后端支持搜索，可以加上 keyword: searchQuery.value
      }
    });

    // 假设后端返回结构是 { items: [...], total: number }
    // 如果直接返回数组，则 data.value = response.data
    data.value = response.data.items || response.data;
    pagination.total = response.data.total || data.value.length;
  } catch (error) {
    ElMessage.error('获取简历列表失败');
    console.error(error);
  } finally {
    loading.value = false;
  }
};

// --- 2. 手动录入 (跳转或弹窗) ---
const handleAdd = () => {
  // 方案A：跳转到录入页面
  // router.push('/admin/resumes/create');

  // 方案B：这里简单演示提示，实际应打开一个 Form 弹窗
  ElMessage.info('功能待实现：打开手动录入表单');
};

// --- 3. 编辑 ---
const handleEdit = (row) => {
  ElMessage.success(`正在编辑 ${row.userName} 的信息`);
  // 实际逻辑：打开包含表单的 Dialog，并将 row 数据填入
};

// --- 4. 删除 (真实接口) ---
const handleDelete = async (row) => {
  try {
    // 调用 DELETE 接口，传入 ID
    await axios.delete(`/resumes/${row.id}`);
    ElMessage.success('删除成功');
    fetchData(); // 刷新列表
  } catch (error) {
    ElMessage.error('删除失败');
  }
};

// --- 5. 预览 (本地逻辑，无需改) ---
const handlePreview = (row) => {
  currentResume.value = row;
  previewVisible.value = true;
};

// 初始化
onMounted(() => {
  fetchData();
});
</script>

<style scoped>
/* ... 保持你原有的样式不变 ... */
.resumes-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}
.header-card {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.header-card h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.table-card {
  border-radius: 8px;
}
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.resume-detail-view { padding: 10px; }
.resume-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.resume-header .name { margin: 0; font-size: 20px; color: #303133; }
.resume-header .job-title { font-size: 14px; color: #606266; margin-top: 4px; display: block; }
.section { margin-top: 15px; }
.section-title { font-size: 15px; font-weight: 600; color: #303133; margin-bottom: 10px; border-left: 4px solid #409EFF; padding-left: 8px; }
.bio-text { font-size: 13px; color: #606266; line-height: 1.6; background: #f9f9f9; padding: 10px; border-radius: 4px; }
.mb-4 { margin-bottom: 16px; }
</style>