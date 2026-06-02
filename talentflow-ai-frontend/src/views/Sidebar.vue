<!-- frontend/src/components/Sidebar.vue -->
<template>
  <div class="sidebar">
    <div class="new-chat" @click="$emit('new-chat')">
      + 新建对话
    </div>
    <div class="history-list">
      <div 
        v-for="item in history" 
        :key="item.id" 
        class="history-item"
        :class="{ active: item.id === activeId }"
        @click="$emit('select-chat', item)"
      >
        {{ item.title }}
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  history: {
    type: Array,
    default: () => []
  },
  activeId: [String, Number]
})

// 定义触发的事件
const emit = defineEmits(['new-chat', 'select-chat'])
</script>

<style scoped>
.sidebar {
  width: 260px;
  background: #f7f9fb;
  border-right: 1px solid #e0e0e0;
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.new-chat {
  padding: 20px;
  cursor: pointer;
  font-weight: bold;
  border-bottom: 1px solid #e0e0e0;
}
.history-list {
  flex: 1;
  overflow-y: auto;
}
.history-item {
  padding: 15px 20px;
  cursor: pointer;
  border-bottom: 1px solid #eee;
}
.history-item.active {
  background: #e6f4ff;
  border-right: 3px solid #1890ff;
}
</style>