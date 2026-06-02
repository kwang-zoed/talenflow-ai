<!-- frontend/src/components/SourceViewer.vue -->
<template>
  <div v-if="sourceCode" class="source-viewer">
    <div class="viewer-header">
      <span>📄 参考源码 / 数据</span>
    </div>
    <pre class="code-block"><code>{{ sourceCode }}</code></pre>
  </div>
</template>

<script setup>
defineProps({
  sourceCode: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.source-viewer {
  border-top: 1px solid #e0e0e0;
  background: #f5f5f5;
  padding: 10px;
  height: 200px;
  overflow-y: auto;
}
.viewer-header {
  font-weight: bold;
  margin-bottom: 10px;
  color: #333;
}
.code-block {
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  white-space: pre-wrap;
  color: #d63384; /* 粉红色代码字体 */
}
</style>