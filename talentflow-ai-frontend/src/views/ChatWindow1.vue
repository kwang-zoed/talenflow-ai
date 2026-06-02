<!-- frontend/src/components/ChatWindow.vue -->
<template>
  <div class="chat-window">
    <!-- 1. 消息列表区域 -->
    <div class="messages-container" ref="messagesContainer">
      
      <!-- 空状态：新对话 -->
      <div v-if="sessionId === 'new' && messages.length === 0" class="empty-state">
        <h2>👋 欢迎使用 AI 助手</h2>
        <p>请在下方输入您的问题。</p>
      </div>

      <!-- 消息循环 -->
      <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
        <div class="avatar">
          {{ msg.role === 'user' ? '👤' : '🤖' }}
        </div>
        <div class="content">
          <!-- 仅显示文本内容 -->
          <div class="text">{{ msg.content }}</div>
        </div>
      </div>

      <!-- 发送中状态 -->
      <div v-if="loading" class="message ai">
        <div class="avatar">🤖</div>
        <div class="content"><em>正在思考中...</em></div>
      </div>
    </div>

    <!-- 2. 底部输入区域 (已移除上传功能) -->
    <div class="input-area">
      <div class="input-controls">
        <!-- 文本输入框 -->
        <textarea 
          v-model="inputText" 
          placeholder="请输入您的问题..." 
          @keydown.enter.prevent="handleEnter"
          :disabled="loading"
        ></textarea>

        <!-- 发送按钮 -->
        <button 
          @click="handleSend" 
          :disabled="loading || !inputText.trim()" 
          class="send-btn"
        >
          {{ loading ? '发送中...' : '发送' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
// 注意：如果 uploadFile 不再在其他地方使用，也可以从 import 中移除
import { getSessionMessages, sendMessage } from '../api/chat'
import { ElMessage } from 'element-plus'

const props = defineProps({
  sessionId: [String, Number]
})

const emit = defineEmits(['message-sent'])

// --- 状态定义 ---
const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const messagesContainer = ref(null)

// --- 核心逻辑 ---

// 1. 监听 SessionID 变化，加载历史
const loadHistory = async () => {
  if (props.sessionId === 'new') {
    messages.value = []
    return
  }

  if (props.sessionId) {
    try {
      const res = await getSessionMessages(props.sessionId)
      messages.value = res.data || []
      scrollToBottom()
    } catch (error) {
      console.error('加载历史失败', error)
    }
  }
}

// 2. 发送消息 (纯文本)
const handleSend = async () => {
  // 简单的非空校验
  if (!inputText.value.trim() || loading.value) return

  loading.value = true

  try {
    // A. 构造本地显示的消息（乐观更新）
    const userContent = inputText.value.trim()
    
    messages.value.push({
      role: 'user',
      content: userContent
    })

    // B. 调用聊天接口
    const res = await sendMessage(
      userContent, 
      props.sessionId
      // 不再传递 fileName 参数
    )

    // C. 处理响应
    messages.value.push({
      role: 'assistant',
      content: res.data.response
    })

    // D. 通知父组件更新会话 ID (如果是新会话)
    if (props.sessionId === 'new') {
      emit('message-sent', {
        id: res.data.session_id,
        title: userContent.substring(0, 10)
      })
    }

    // 清空输入
    inputText.value = ''
    scrollToBottom()

  } catch (error) {
    console.error(error)
    ElMessage.error('发送失败，请重试')
    messages.value.push({
      role: 'assistant',
      content: '❌ 系统繁忙，请稍后再试。'
    })
  } finally {
    loading.value = false
  }
}

// 3. 辅助方法
const handleEnter = (e) => {
  if (!e.shiftKey) handleSend()
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// --- 监听 ---
watch(() => props.sessionId, () => {
  loadHistory()
}, { immediate: true })

</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
}

/* 消息列表 */
.messages-container {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f4f6f8;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.empty-state {
  text-align: center;
  color: #999;
  margin-top: 100px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 80%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message.ai {
  align-self: flex-start;
}

.avatar {
  font-size: 24px;
  flex-shrink: 0;
}

.content {
  padding: 12px 16px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  line-height: 1.5;
  word-break: break-word; /* 防止长文本溢出 */
}

.message.user .content {
  background: #1890ff;
  color: #fff;
}

/* 底部输入区 */
.input-area {
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  background: #fff;
}

.input-controls {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

textarea {
  flex: 1;
  height: 44px; /* 固定高度，也可以改为 min-height 实现自动增高 */
  padding: 10px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  resize: none;
  font-family: inherit;
  font-size: 14px;
}
textarea:focus { 
  outline: 2px solid #1890ff; 
  border-color: transparent; 
}
textarea:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.send-btn {
  width: 80px;
  height: 44px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  transition: background 0.2s;
}
.send-btn:hover {
  background: #40a9ff;
}
.send-btn:disabled { 
  background: #91d5ff; 
  cursor: not-allowed; 
}
</style>