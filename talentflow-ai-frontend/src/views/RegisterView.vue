<template>
  <div class="register-container">
    <div class="register-box">
      <h2 class="title">用户注册</h2>

      <el-form :model="form" :rules="rules" ref="registerFormRef" label-position="top">

        <!-- 租户选择 (新增) -->
        <el-form-item label="所属公司" prop="tenant_id">
          <el-select 
            v-model="form.tenant_id" 
            placeholder="请选择您所在的公司" 
            style="width: 100%"
          >
            <el-option
              v-for="tenant in tenants"
              :key="tenant.id"
              :label="tenant.name"
              :value="tenant.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" placeholder="请再次输入密码" show-password />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="onSubmit" :loading="loading" style="width: 100%">立即注册</el-button>
        </el-form-item>

        <div class="login-link">
          已有账号？
          <router-link to="/login" class="link-type">去登录</router-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import { useRouter } from 'vue-router';

const router = useRouter();
const loading = ref(false);
const registerFormRef = ref(null);
const tenants = ref([]); // 存储租户列表

// 表单数据
const form = reactive({
  username: '',
  password: '',
  confirm_password: '',
  tenant_id: null // 新增字段，对应数据库外键
});

// 校验规则
const rules = {
  tenant_id: [{ required: true, message: '请选择所属公司', trigger: 'change' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirm_password: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== form.password) {
          callback(new Error('两次输入的密码不一致'));
        } else {
          callback();
        }
      },
      trigger: 'blur'
    }
  ]
};

// 页面加载时获取租户列表
const fetchTenants = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:8000/api/v1/auth/tenants');
    tenants.value = response.data;
  } catch (error) {
    ElMessage.error('获取公司列表失败');
  }
};

const onSubmit = async () => {
  if (!registerFormRef.value) return;
  
  await registerFormRef.value.validate(async (valid) => {
    if (!valid) return;
  });

  try {
    loading.value = true;
    // 发送注册请求，注意这里包含了 tenant_id
    await axios.post('http://127.0.0.1:8000/api/v1/auth/register', form);
    
    ElMessage.success('注册成功，请登录');
    router.push('/login');
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '注册失败');
  } finally {
    loading.value = false;
  }
};

// 初始化
onMounted(() => {
  fetchTenants();
});
</script>

<style scoped>
/* 保持和你之前一样的样式 */
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
}
.register-box {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.title { text-align: center; margin-bottom: 30px; }
.login-link { text-align: center; margin-top: 10px; }
.link-type { color: #409EFF; cursor: pointer; }
</style>