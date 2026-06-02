<template>
  <div class="dandelion-chat-layout">
    <!-- 左侧：部落历史/导航 -->
    <div class="sidebar">
      <div class="logo-area">
        <el-icon :size="30" color="#F7BA2A"><umbrella /></el-icon>
        <span class="logo-text">AI 蒲公英部落</span>
      </div>

      <div class="new-chat-btn">
        <el-button type="primary" icon="Plus" @click="createNewChat" style="width: 100%">
          开启新探索
        </el-button>
      </div>

      <div class="history-list">
        <div v-for="(item, index) in historyList" :key="index" class="history-item">
          <el-icon><ChatDotRound /></el-icon>
          <span class="title">{{ item.title }}</span>
        </div>
      </div>

      <div class="user-profile">
        <el-avatar :size="32" src="https://i.pravatar.cc/150?img=3" />
        <span class="username">部落成员</span>
      </div>
    </div>

    <!-- 右侧：主聊天区 -->
    <div class="main-chat">
      <!-- 消息展示区 -->
      <div class="messages-container" ref="msgContainer">
        <div v-if="messages.length === 0" class="welcome-screen">
          <el-empty description="欢迎来到 AI 蒲公英部落" :image-size="200">
            <el-button type="primary" @click="quickStart">🌱 种下第一个问题</el-button>
          </el-empty>
        </div>

        <div v-for="(msg, index) in messages" :key="index" :class="['msg-bubble', msg.role]">
          <div class="msg-content" v-html="msg.content"></div>
        </div>

        <!-- 正在生成状态 -->
        <div v-if="loading" class="msg-bubble assistant">
          <div class="msg-content">
            <el-icon class="is-loading"><Loading /></el-icon> 蒲公英正在随风飘送答案...
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <el-input
          v-model="inputText"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 4 }"
          placeholder="向部落智慧提问..."
          @keydown.enter.exact.prevent="handleSend"
        />
        <el-button
          type="primary"
          :icon="Position"
          :loading="loading"
          @click="handleSend"
          class="send-btn"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { chatStream } from '../api/chat' // 引入刚才写的API
import { Plus, ChatDotRound, Umbrella, Position, Loading } from '@element-plus/icons-vue'

// --- 数据状态 ---
const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const msgContainer = ref(null)
const historyList = ref([
  { title: '如何种植数字蒲公英？' },
  { title: 'AI 部落的起源' },
])

// --- 自动滚动逻辑 ---
const scrollToBottom = async () => {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}

// --- 发送消息 ---
const handleSend = async () => {
  if (!inputText.value.trim()) return

  const userMsg = inputText.value
  inputText.value = ''

  // 1. 添加用户消息
  messages.value.push({ role: 'user', content: userMsg })
  loading.value = true
  scrollToBottom()

  try {
    // 2. 添加一个空的 AI 消息占位
    messages.value.push({ role: 'assistant', content: '' })
    scrollToBottom()

    // 3. 调用流式接口
    await chatStream(
      { message: userMsg, thread_id: 'demo-thread-001' }, // 这里实际应从路由或store获取
      (chunk) => {
        // 累加内容
        messages.value[messages.value.length - 1].content += chunk
        scrollToBottom()
      },
      () => {
        // 完成
        loading.value = false
      }
    )
  } catch (error) {
    ElMessage.error('部落信号中断，请重试')
    loading.value = false
  }
}

// --- 其他交互 ---
const createNewChat = () => {
  messages.value = []
  ElMessage.success('开启了新的探索旅程')
}

const quickStart = () => {
  inputText.value = '请介绍一下 AI 蒲公英部落的愿景'
}

const handleClearHistory = () => {
  messages.value = []
}
</script>

<style scoped>
.dandelion-chat-layout {
  display: flex;
  height: 100vh;
  background-color: #f4f6f8;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
}

/* --- 左侧侧边栏 --- */
.sidebar {
  width: 260px;
  background-color: #2c3e50; /* 深蓝色背景 */
  color: white;
  display: flex;
  flex-direction: column;
  padding: 20px;
  box-shadow: 2px 0 5px rgba(0, 0, 0, 0.1);
}

.logo-area {
  font-size: 20px;
  font-weight: bold;
  margin-bottom: 30px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.new-chat-btn {
  margin-bottom: 20px;
}

.history-list {
  flex: 1;
  overflow-y: auto;
}

.history-item {
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: #bdc3c7;
  transition: all 0.3s;
}

.history-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: white;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

/* --- 右侧主聊天区 --- */
.main-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #fff;
  position: relative;
}

.messages-container {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
  background-image: radial-gradient(#e5e7eb 1px, transparent 1px);
  background-size: 20px 20px;
}

.welcome-screen {
  margin-top: 100px;
}

/* 消息气泡样式 */
.msg-bubble {
  max-width: 70%;
  margin-bottom: 20px;
  padding: 12px 18px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 15px;
  position: relative;
  animation: fadeIn 0.3s ease;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.msg-bubble.user {
  background-color: #409eff;
  color: white;
  margin-left: auto;
  border-bottom-right-radius: 2px;
}

.msg-bubble.assistant {
  background-color: #f0f2f5;
  color: #333;
  margin-right: auto;
  border-bottom-left-radius: 2px;
}

/* 输入区域 */
.input-area {
  padding: 20px 30px;
  background-color: #fff;
  display: flex;
  gap: 10px;
  border-top: 1px solid #ebeef5;
}

.input-area .el-textarea {
  flex: 1;
}

.send-btn {
  width: 100px;
  height: auto;
  padding: 10px 0;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>