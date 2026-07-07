<template>
  <div class="detail-fields">
    <div v-for="row in rows" :key="row.label" class="detail-row" :class="{ block: row.block }">
      <span class="detail-label">{{ row.label }}</span>
      <div class="detail-value" :class="{ pre: row.pre }">{{ row.value || '-' }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  rows: { type: Array, default: () => [] },
})
</script>

<style scoped>
.detail-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 12px;
  align-items: start;
}

.detail-row.block {
  grid-template-columns: 1fr;
  gap: 6px;
}

.detail-label {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  padding-top: 2px;
}

.detail-row.block .detail-label {
  padding-top: 0;
}

.detail-value {
  font-size: 13px;
  color: #334155;
  line-height: 1.65;
  word-break: break-word;
}

.detail-value.pre {
  white-space: pre-wrap;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  max-height: 200px;
  overflow-y: auto;
}
</style>
