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

    <!-- 3. 简历预览弹窗 (核心新增功能) -->
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
const currentResume = ref(null); // 存储当前点击的简历对象

// --- 模拟数据获取 ---
const fetchData = () => {
  loading.value = true;
  // 模拟网络延迟
  setTimeout(() => {
    data.value = [
      {
        id: '1',
        userName: '张三',
        jobTitle: '高级前端工程师',
        phone: '138-0000-0001',
        email: 'zhangsan@example.com',
        education: '本科 (计算机科学)',
        experience: '5年',
        skills: ['Vue3', 'TypeScript', 'Vite', 'Node.js', 'React'],
        status: 'Active',
        updatedAt: '2023-10-27 10:00',
        bio: '热爱前端技术，有丰富的Vue生态开发经验，注重代码质量和性能优化。'
      },
      {
        id: '2',
        userName: '李四',
        jobTitle: 'Java 后端开发',
        phone: '139-0000-0002',
        email: 'lisi@example.com',
        education: '硕士 (软件工程)',
        experience: '3年',
        skills: ['Spring Boot', 'MySQL', 'Redis', 'Docker'],
        status: 'Pending',
        updatedAt: '2023-10-26 15:30',
        bio: '熟悉微服务架构，有高并发系统处理经验。'
      },
      {
        id: '3',
        userName: '王五',
        jobTitle: 'UI 设计师',
        phone: '137-0000-0003',
        email: 'wangwu@example.com',
        education: '本科 (视觉传达)',
        experience: '4年',
        skills: ['Figma', 'Sketch', 'Photoshop', 'Illustrator'],
        status: 'Active',
        updatedAt: '2023-10-25 09:15',
        bio: '追求极致的设计细节，擅长移动端交互设计。'
      }
    ];
    pagination.total = 3;
    loading.value = false;
  }, 600);
};

// --- 事件处理 ---

// 预览功能实现
const handlePreview = (row) => {
  currentResume.value = row; // 将当前行数据赋值给预览对象
  previewVisible.value = true; // 打开弹窗
};

const handleAdd = () => {
  ElMessage.info('这里可以对接上传组件或跳转录入页面');
};

const handleEdit = (row) => {
  ElMessage.success(`正在编辑 ${row.userName} 的信息`);
};

const handleDelete = (row) => {
  // 这里已经被 el-popconfirm 包裹，直接执行删除逻辑
  ElMessage.success(`已删除 ${row.userName} 的简历`);
  fetchData(); 
};

// 初始化
onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.resumes-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

/* 顶部卡片 */
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

/* 表格卡片 */
.table-card {
  border-radius: 8px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

/* --- 预览弹窗样式 --- */
.resume-detail-view {
  padding: 10px;
}

.resume-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.resume-header .name {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.resume-header .job-title {
  font-size: 14px;
  color: #606266;
  margin-top: 4px;
  display: block;
}

.section {
  margin-top: 15px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
  border-left: 4px solid #409EFF;
  padding-left: 8px;
}

.bio-text {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  background: #f9f9f9;
  padding: 10px;
  border-radius: 4px;
}

.mb-4 {
  margin-bottom: 16px;
}
</style>