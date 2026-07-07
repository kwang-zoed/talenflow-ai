<template>
  <article class="match-card">
    <div class="score-ring" :class="scoreClass">
      <span class="score-value">{{ item.score ?? 0 }}</span>
      <span class="score-unit">%</span>
    </div>

    <div class="match-content">
      <div class="match-head">
        <h3 class="match-title">{{ title }}</h3>
        <el-tag v-if="item.ranking === 'coarse'" size="small" type="info" effect="plain" round>粗排</el-tag>
        <el-tag v-else-if="item.ranking === 'rerank'" size="small" type="success" effect="plain" round>精排</el-tag>
      </div>

      <p v-if="subtitle" class="match-subtitle">{{ subtitle }}</p>
      <p v-if="item.distance_text" class="match-distance">{{ item.distance_text }}</p>

      <div v-if="extra" class="match-extra">{{ extra }}</div>

      <div v-if="item.matched_skills?.length" class="match-skills">
        <el-tag
          v-for="skill in item.matched_skills"
          :key="skill"
          size="small"
          effect="light"
          round
          class="skill-chip"
        >
          {{ skill }}
        </el-tag>
      </div>

      <div class="match-actions">
        <slot name="actions" />
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  item: { type: Object, required: true },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  extra: { type: String, default: '' },
})

const scoreClass = computed(() => {
  if (props.item.ranking === 'rerank') return 'score-rerank'
  if ((props.item.score ?? 0) >= 60) return 'score-good'
  return 'score-coarse'
})
</script>

<style scoped>
.match-card {
  display: flex;
  gap: 16px;
  padding: 16px 18px;
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 12px;
  transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.match-card:hover {
  border-color: #c6d4f0;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  transform: translateY(-1px);
}

.score-ring {
  flex-shrink: 0;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  line-height: 1;
}

.score-coarse {
  background: linear-gradient(135deg, #f0f2f5 0%, #e4e7ed 100%);
  color: #606266;
}

.score-good {
  background: linear-gradient(135deg, #e8f4ff 0%, #d9ecff 100%);
  color: #409eff;
}

.score-rerank {
  background: linear-gradient(135deg, #e8faf0 0%, #d1f2e1 100%);
  color: #059669;
}

.score-value {
  font-size: 18px;
}

.score-unit {
  font-size: 10px;
  margin-top: 2px;
  opacity: 0.85;
}

.match-content {
  flex: 1;
  min-width: 0;
}

.match-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.match-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.35;
}

.match-subtitle {
  margin: 0 0 4px;
  font-size: 13px;
  color: #64748b;
}

.match-distance {
  margin: 0 0 6px;
  font-size: 12px;
  color: #2563eb;
}

.match-extra {
  margin-bottom: 8px;
  font-size: 13px;
  color: #ef4444;
  font-weight: 600;
}

.match-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.skill-chip {
  border: none;
  background: #f1f5f9;
  color: #475569;
}

.match-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  flex-wrap: wrap;
}
</style>
