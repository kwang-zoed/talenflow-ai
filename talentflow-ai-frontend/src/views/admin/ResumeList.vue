<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <h2>简历数据管理</h2>
      <a-button type="primary" @click="handleAdd">
        <template #icon><UploadOutlined /></template>
        手动录入简历
      </a-button>
    </div>

    <!-- 搜索与筛选区域 -->
    <a-card class="search-card" :bordered="false">
      <a-form layout="inline" @submit.prevent="handleSearch">
        <a-form-item label="用户/姓名">
          <a-input v-model:value="query.username" placeholder="输入用户昵称或真实姓名" allow-clear />
        </a-form-item>
        
        <a-form-item label="意向岗位">
          <a-input v-model:value="query.targetJob" placeholder="如：前端工程师" allow-clear />
        </a-form-item>

        <a-form-item label="状态">
          <a-select v-model:value="query.status" style="width: 120px" allow-clear>
            <a-select-option value="public">公开</a-select-option>
            <a-select-option value="private">私密</a-select-option>
            <a-select-option value="banned">违规</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item>
          <a-button type="primary" html-type="submit">搜索</a-button>
          <a-button style="margin-left: 8px" @click="resetSearch">重置</a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <!-- 数据表格 -->
    <a-card :bordered="false" class="table-card">
      <a-table 
        :columns="columns" 
        :data-source="data" 
        :loading="loading" 
        row-key="id"
        :pagination="pagination"
        @change="handleTableChange"
      >
        <!-- 用户信息列 -->
        <template #bodyCell="{ column, record }">
          
          <!-- 用户/技能列 -->
          <template v-if="column.key === 'user_info'">
            <div class="user-info-cell">
              <div class="name">{{ record.user_name }}</div>
              <div class="tags">
                <a-tag v-for="tag in record.skills.slice(0, 3)" :key="tag" color="blue">{{ tag }}</a-tag>
                <a-tag v-if="record.skills.length > 3" color="grey">+{{ record.skills.length - 3 }}</a-tag>
              </div>
            </div>
          </template>

          <!-- 意向岗位列 -->
          <template v-else-if="column.key === 'job_target'">
            <div>{{ record.target_job_title }}</div>
            <div class="sub-text">期望薪资: {{ record.expected_salary }}</div>
          </template>

          <!-- 解析状态列 -->
          <template v-else-if="column.key === 'parse_status'">
            <a-tag :color="record.parsed ? 'green' : 'red'">
              {{ record.parsed ? '解析成功' : '解析失败' }}
            </a-tag>
          </template>

          <!-- 隐私状态列 -->
          <template v-else-if="column.key === 'privacy'">
            <a-switch 
              checked-children="公开" 
              un-checked-children="私密" 
              :checked="record.is_public"
              @change="(val) => handlePrivacyChange(record, val)"
            />
          </template>

          <!-- 操作列 -->
          <template v-else-if="column.key === 'action'">
            <a-button type="link" size="small" @click="handleView(record)">预览</a-button>
            <a-button type="link" size="small" @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm
              title="确定要删除这份简历吗？此操作不可恢复"
              @confirm="handleDelete(record.id)"
              ok-text="是" cancel-text="否"
            >
              <a-button type="link" size="small" danger>删除</a-button>
            </a-popconfirm>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 预览/编辑弹窗 (简化版) -->
    <a-modal 
      v-model:open="modalVisible" 
      :title="modalTitle" 
      :footer="null" 
      width="800px"
      @cancel="modalVisible = false"
    >
      <div class="resume-preview-content">
        <!-- 这里放置简历预览的具体内容 -->
        <a-descriptions title="基本信息" bordered>
          <a-descriptions-item label="姓名">{{ currentRecord.user_name }}</a-descriptions-item>
          <a-descriptions-item label="电话">{{ currentRecord.phone }}</a-descriptions-item>
          <a-descriptions-item label="邮箱">{{ currentRecord.email }}</a-descriptions-item>
          <a-descriptions-item label="意向岗位" :span="2">{{ currentRecord.target_job_title }}</a-descriptions-item>
          <a-descriptions-item label="教育经历" :span="3">{{ currentRecord.education }}</a-descriptions-item>
        </a-descriptions>
        
        <div style="margin-top: 24px">
          <h3>AI 解析技能树</h3>
          <a-tag v-for="tag in currentRecord.skills" :key="tag" color="cyan">{{ tag }}</a-tag>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { UploadOutlined } from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';

// 表格列定义
const columns = [
  { title: '用户 / 核心技能', key: 'user_info', width: 250 },
  { title: '意向岗位', key: 'job_target', width: 180 },
  { title: '解析状态', key: 'parse_status', width: 100 },
  { title: '隐私设置', key: 'privacy', width: 120 },
  { title: '更新时间', dataIndex: 'updated_at', width: 160 },
  { title: '操作', key: 'action', fixed: 'right', width: 200 },
];

// 模拟数据源 (实际请替换为 API 调用)
const data = ref([
  {
    id: 1,
    user_name: '张三',
    phone: '138****1234',
    email: 'zhangsan@example.com',
    skills: ['Vue3', 'TypeScript', 'Node.js', 'Webpack'],
    target_job_title: '高级前端工程师',
    expected_salary: '25k-40k',
    parsed: true,
    is_public: true,
    education: '本科 - 计算机科学 - 某某大学',
    updated_at: '2026-05-01 10:30',
  },
  {
    id: 2,
    user_name: '李四',
    phone: '139****5678',
    email: 'lisi@example.com',
    skills: ['Java', 'Spring Boot', 'MySQL', 'Redis', 'Docker'],
    target_job_title: '后端开发工程师',
    expected_salary: '20k-30k',
    parsed: true,
    is_public: false,
    education: '硕士 - 软件工程',
    updated_at: '2026-04-28 15:20',
  },
  {
    id: 3,
    user_name: '王五',
    phone: '137****9999',
    email: 'wangwu@example.com',
    skills: [],
    target_job_title: '产品经理',
    expected_salary: '面议',
    parsed: false, // 模拟解析失败
    is_public: true,
    education: '本科',
    updated_at: '2026-04-25 09:10',
  }
]);

// 搜索与分页状态
const query = reactive({ username: '', targetJob: '', status: '' });
const loading = ref(false);
const pagination = reactive({ current: 1, pageSize: 10, total: 30, showSizeChanger: true, showTotal: total => `共 ${total} 条` });
const modalVisible = ref(false);
const modalTitle = ref('简历详情');
const currentRecord = ref({});

// 方法
const handleSearch = () => {
  pagination.current = 1;
  fetchData();
};

const resetSearch = () => {
  query.username = '';
  query.targetJob = '';
  query.status = '';
  handleSearch();
};

const handleTableChange = (pag) => {
  pagination.current = pag.current;
  pagination.pageSize = pag.pageSize;
  fetchData();
};

const fetchData = () => {
  loading.value = true;
  // TODO: 调用 API 获取数据
  setTimeout(() => {
    loading.value = false;
  }, 500);
};

const handleView = (record) => {
  currentRecord.value = record;
  modalTitle.value = '简历预览';
  modalVisible.value = true;
};

const handleEdit = (record) => {
  currentRecord.value = { ...record }; // 复制对象避免直接修改
  modalTitle.value = '编辑简历信息';
  modalVisible.value = true;
};

const handleDelete = (id) => {
  // TODO: 调用删除 API
  message.success('删除成功');
  fetchData();
};

const handlePrivacyChange = (record, checked) => {
  // TODO: 调用更新隐私状态 API
  message.success(`已设置为 ${checked ? '公开' : '私密'}`);
  record.is_public = checked;
};

const handleAdd = () => {
  message.info('此处可打开上传组件或跳转页面');
};

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.page-container {
  padding: 24px;
  background: #f0f2f5;
  min-height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.search-card {
  margin-bottom: 16px;
}

.user-info-cell {
  display: flex;
  flex-direction: column;
}

.user-info-cell .name {
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
}

.sub-text {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.resume-preview-content {
  padding: 10px;
}
</style>