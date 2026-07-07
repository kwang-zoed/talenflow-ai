<template>
  <div class="reference-panel" :class="{ compact, [`theme-${mode}`]: true }">
    <div class="panel-top">
      <div class="panel-top-left">
        <span class="panel-icon">{{ mode === 'job' ? 'JD' : 'CV' }}</span>
        <span class="panel-title">{{ title }}</span>
      </div>
      <el-tag v-if="badge" size="small" :type="badgeType" effect="dark" round>{{ badge }}</el-tag>
    </div>

    <div class="panel-content">
      <div v-if="loading" class="panel-loading">
        <el-skeleton :rows="6" animated />
      </div>

      <el-empty v-else-if="!hasData" :description="emptyText" :image-size="72" />

      <template v-else>
        <h3 class="main-title">{{ mode === 'job' ? (data.title || '职位') : (data.name || '未命名') }}</h3>
        <p class="meta-line">
          <template v-if="mode === 'job'">
            <span v-if="data.company">{{ data.company }}</span>
            <span v-if="data.location"> · {{ data.location }}</span>
            <span v-if="data.work_address"> · {{ data.work_address }}</span>
          </template>
          <template v-else>
            <span>{{ data.title || '暂无职位标题' }}</span>
            <span v-if="data.residence_city"> · {{ data.residence_city }}</span>
          </template>
        </p>

        <div class="stat-chips">
          <template v-if="mode === 'job'">
            <span v-if="data.salary" class="chip chip-salary">{{ data.salary }}</span>
            <span v-if="data.experience_requirement" class="chip">{{ data.experience_requirement }}</span>
            <span v-if="data.education_requirement" class="chip">{{ data.education_requirement }}</span>
          </template>
          <template v-else>
            <span v-if="data.education" class="chip">{{ data.education }}</span>
            <span v-if="data.experience_years != null" class="chip">{{ data.experience_years }} 年经验</span>
          </template>
        </div>

        <div v-if="skillList.length" class="section">
          <div class="section-label">{{ mode === 'job' ? '技能要求' : '我的技能' }}</div>
          <div class="tags">
            <span v-for="s in skillList" :key="s" class="tag-pill">{{ s }}</span>
          </div>
        </div>

        <div v-if="mode === 'job' && data.description" class="section">
          <div class="section-label">职位描述</div>
          <div class="text-block">{{ data.description }}</div>
        </div>

        <div v-if="mode === 'resume' && data.summary" class="section">
          <div class="section-label">个人简介</div>
          <div class="text-block">{{ data.summary }}</div>
        </div>

        <div v-if="mode === 'resume' && data.work_experience" class="section">
          <div class="section-label">工作经历</div>
          <div class="text-block pre">{{ data.work_experience }}</div>
        </div>

        <div v-if="mode === 'resume' && data.project_experience" class="section">
          <div class="section-label">项目经历</div>
          <div class="text-block pre">{{ data.project_experience }}</div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  mode: { type: String, default: 'job' },
  data: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  title: { type: String, default: '对照参考' },
  badge: { type: String, default: '' },
  badgeType: { type: String, default: 'info' },
  emptyText: { type: String, default: '暂无数据' },
})

const hasData = computed(() => props.data && Object.keys(props.data).length > 0)

const skillList = computed(() => {
  const raw = props.data?.required_skills ?? props.data?.skills
  if (Array.isArray(raw)) return raw.filter(Boolean)
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw)
      return Array.isArray(parsed) ? parsed.filter(Boolean) : []
    } catch {
      return raw ? [raw] : []
    }
  }
  return []
})
</script>

<style scoped>
.reference-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  background: #fff;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.06);
}

.theme-job .panel-top {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
}

.theme-resume .panel-top {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
}

.panel-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.6);
}

.panel-top-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.panel-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  color: #3b82f6;
  flex-shrink: 0;
}

.theme-resume .panel-icon {
  color: #059669;
}

.panel-title {
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
}

.panel-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 18px 18px;
}

.panel-loading {
  padding: 8px 0;
}

.main-title {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
}

.meta-line {
  margin: 0 0 12px;
  color: #64748b;
  font-size: 13px;
}

.stat-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.chip {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  background: #f1f5f9;
  color: #475569;
}

.chip-salary {
  background: #fef2f2;
  color: #dc2626;
  font-weight: 600;
}

.section {
  margin-bottom: 14px;
}

.section-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #94a3b8;
  margin-bottom: 8px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-pill {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #475569;
}

.theme-job .tag-pill {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
}

.theme-resume .tag-pill {
  background: #ecfdf5;
  border-color: #a7f3d0;
  color: #047857;
}

.text-block {
  font-size: 13px;
  color: #475569;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
}

.text-block.pre {
  font-family: inherit;
}

.compact .text-block {
  max-height: 140px;
}

.compact .main-title {
  font-size: 16px;
}
</style>
