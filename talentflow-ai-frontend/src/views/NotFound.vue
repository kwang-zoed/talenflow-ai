<template>
  <div class="not-found-container">
    <div class="content">
      <h1 class="error-code">404</h1>
      <h2 class="error-title">页面未找到</h2>
      <p class="error-message">抱歉，您访问的页面不存在或已被移除。</p>
      
      <div class="actions">
        <button @click="goBack" class="btn-secondary">
          返回上一页
        </button>
        <router-link to="/" class="btn-primary">
          返回首页
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goBack = () => {
  router.go(-1)
}
</script>

<style scoped>
.not-found-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
  text-align: center;
}

.content {
  padding: 2rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  max-width: 400px;
}

.error-code {
  font-size: 4rem;
  color: #ff4d4f;
  margin-bottom: 0.5rem;
}

.error-title {
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 1rem;
}

.error-message {
  color: #666;
  margin-bottom: 2rem;
  line-height: 1.6;
}

.actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

button, .btn-primary {
  padding: 0.6rem 1.2rem;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.3s;
}

.btn-primary {
  background-color: #1890ff;
  color: white;
  border: 1px solid #1890ff;
}

.btn-primary:hover {
  background-color: #40a9ff;
  border-color: #40a9ff;
}

.btn-secondary {
  background-color: transparent;
  color: #666;
  border: 1px solid #d9d9d9;
}

.btn-secondary:hover {
  background-color: #f5f5f5;
  color: #333;
}
</style>