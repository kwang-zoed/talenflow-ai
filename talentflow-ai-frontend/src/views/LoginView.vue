<template>
  <div class="login-container">
    <div class="login-box">
      <h2 class="title">系统登录</h2>

      <!-- 表单区域 -->
      <el-form 
        :model="form" 
        :rules="rules" 
        ref="loginFormRef" 
        @submit.prevent="onSubmit" 
        class="login-form"
      >

        <!-- 用户名输入框 -->
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            size="large"
            prefix-icon="User"
          />
        </el-form-item>

        <!-- 密码输入框 -->
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            size="large"
            prefix-icon="Lock"
          />
        </el-form-item>

        <!-- 登录按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            native-type="submit"
            :loading="loading"
            class="submit-btn"
            size="large"
          >
            立即登录
          </el-button>
        </el-form-item>
        
        <!-- 注册跳转链接 -->
        <div class="register-link">
          还没有账号？ <el-button type="primary" link @click="goToRegister">立即注册</el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import { useRouter } from 'vue-router';
import { useUserStore } from '../store/user' // 确保引入了 Store

const router = useRouter();
const loading = ref(false);
const loginFormRef = ref(null);

const form = reactive({
  username: '',
  password: ''
});

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
};

const onSubmit = async () => {
  if (!loginFormRef.value) return;

  // 1. 表单校验
  await loginFormRef.value.validate((valid) => {
    if (!valid) return false;
  });

  try {
    loading.value = true;
    
    // 2. 使用 FormData 发送数据
    // 这是为了匹配 FastAPI 默认的 OAuth2 登录格式
    const formData = new FormData();
    formData.append('username', form.username);
    formData.append('password', form.password);

    // 3. 发送 POST 请求
    // 与业务接口一致：走当前站点 /api（8080 由 nginx 反代到 backend），避免 127.0.0.1 在外网/手机端失效
    const response = await axios.post('/api/v1/auth/login', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });

    const data = response.data;

    // 4. 处理登录成功逻辑
    // 假设后端返回 access_token 和 user 信息
    if (data.access_token) {
      const user = {
        id: data.user.id,
        username: data.user.username,
        nickname: data.user.nickname || data.user.username,
        role: data.user.role // 确保后端返回了 role
      };

      // 保存双令牌与用户信息
      const userStore = useUserStore();
      userStore.setTokens(data.access_token, data.refresh_token);
      userStore.setUserInfo(data.user);
      localStorage.setItem('user', JSON.stringify(user));

      ElMessage.success('登录成功！');

      // 5. 角色分流跳转
      // 0:求职者   1 是管理员  2 HR等需求方
      if (user.role === 1) {
        router.push('/admin');
      } else if(user.role === 2) {
        router.push('/hr');
      } else{
        router.push('/');
      }
    }

  } catch (error) {
    console.error('登录失败', error);
    // 错误提示
    const msg = error.response?.data?.detail || '登录失败，请检查用户名或密码';
    ElMessage.error(Array.isArray(msg) ? msg[0].msg : msg);
  } finally {
    loading.value = false;
  }
};

// 跳转到注册页面
const goToRegister = () => {
  router.push('/register');
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
}

.login-box {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.title {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
  font-size: 24px;
  font-weight: 500;
}

.submit-btn {
  width: 100%;
}

.register-link {
  text-align: center;
  margin-top: 10px;
  color: #666;
  font-size: 14px;
}
</style>