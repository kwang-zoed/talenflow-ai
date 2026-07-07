<template>
  <div class="resume-recommend-page">
    <header class="page-hero">
      <el-button text class="back-btn" @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回岗位
      </el-button>
      <div class="hero-text">
        <h1>智能推荐简历</h1>
        <p v-if="jobInfo?.title">
          {{ jobInfo.title }}
          <span v-if="jobInfo.company"> · {{ jobInfo.company }}</span>
        </p>
      </div>
    </header>

    <div class="compare-layout">
      <aside class="ref-column">
        <RecommendReferencePanel
          mode="job"
          :data="jobInfo || {}"
          :loading="jobLoading"
          title="职位要求"
          badge="对照"
          badge-type="primary"
          empty-text="加载职位信息中..."
        />
      </aside>

      <main class="list-column">
        <section class="list-panel" v-loading="pageLoading && recommendedResumes.length === 0">
          <div class="list-panel-header">
            <div class="header-title">
              <span class="header-main">匹配简历</span>
              <el-tag v-if="sessionStatus === 'rerank_queued'" size="small" type="info" effect="plain" round>
                排队中
              </el-tag>
              <el-tag v-else-if="sessionStatus === 'reranking'" size="small" type="warning" effect="plain" round>
                精排中
              </el-tag>
              <el-tag v-else-if="rerankApplied" size="small" type="success" effect="plain" round>
                已精排
              </el-tag>
              <el-tag v-else-if="rerankAvailable && !rerankApplied" size="small" type="warning" effect="plain" round>
                精排已完成
              </el-tag>
              <el-tag v-else size="small" type="info" effect="plain" round>
                粗排
              </el-tag>
              <span v-if="recommendedResumes.length" class="count-text">
                已展示 {{ recommendedResumes.length }}<template v-if="poolTotal != null"> / {{ poolLabel }} {{ poolTotal }}</template> 人
              </span>
            </div>
            <div class="header-actions">
              <el-button
                v-if="showRerankButton"
                type="primary"
                size="small"
                round
                :loading="applyingRerank"
                :disabled="sessionStatus === 'reranking' || sessionStatus === 'rerank_queued'"
                @click="applyRerankSort"
              >
                {{ rerankButtonLabel }}
              </el-button>
              <el-button circle size="small" :loading="pageLoading" @click="startSession(true)">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </div>

          <div ref="scrollRef" class="scroll-container" @scroll="onScroll">
            <el-empty v-if="recommendedResumes.length === 0 && !pageLoading" description="暂无推荐简历">
              <el-button type="primary" round @click="startSession(true)">开始推荐</el-button>
            </el-empty>

            <div v-else class="match-list">
              <RecommendMatchCard
                v-for="(item, index) in recommendedResumes"
                :key="item.resume?.id || index"
                :item="item"
                :title="item.resume?.name || '未知'"
                :subtitle="[item.candidate_city || item.resume?.residence_city, item.resume?.title, item.resume?.experience_years != null ? `${item.resume.experience_years} 年经验` : ''].filter(Boolean).join(' · ')"
              >
                <template #actions>
                  <el-button type="primary" link @click="openResumeDetail(item)">查看对照</el-button>
                </template>
              </RecommendMatchCard>

              <div v-if="loadingMore" class="load-more-hint">
                <el-icon class="is-loading"><Refresh /></el-icon> 加载更多...
              </div>
              <div
                v-else-if="hasMore && recommendedResumes.length"
                ref="loadMoreSentinelRef"
                class="load-more-hint"
              >
                向下滚动加载更多<template v-if="poolTotal != null">（{{ poolLabel }}共 {{ poolTotal }} 人）</template>
              </div>
              <div v-else-if="!hasMore && recommendedResumes.length" class="load-more-hint muted">
                已加载全部推荐<template v-if="poolTotal != null">（{{ poolLabel }}共 {{ poolTotal }} 人）</template>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>

    <el-dialog
      v-model="detailVisible"
      title="简历与职位对照"
      width="960px"
      class="compare-dialog"
      destroy-on-close
      align-center
    >
      <div class="dialog-compare">
        <div class="dialog-ref">
          <RecommendReferencePanel mode="job" :data="jobInfo || {}" title="职位要求" badge="JD" compact />
        </div>
        <div v-if="resumeDetail" class="dialog-detail">
          <div class="dialog-detail-head">候选人简历</div>
          <RecommendDetailFields :rows="resumeDetailRows" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>



<script setup>

import { ref, computed, onUnmounted, watch, nextTick } from 'vue'

import { useRouter, useRoute } from 'vue-router'

import { ElMessage } from 'element-plus'

import { Refresh, ArrowLeft } from '@element-plus/icons-vue'

import RecommendReferencePanel from '@/components/RecommendReferencePanel.vue'
import RecommendMatchCard from '@/components/RecommendMatchCard.vue'
import RecommendDetailFields from '@/components/RecommendDetailFields.vue'

import {
  createRecommendSession,

  getRecommendSessionMore,

  getRecommendSessionStatus,

  applyRecommendSessionRerank,

  getHrResumeDetail,

  getHrJobs,

} from '@/api/hrRecommend'

import {
  upsertCoarseRecommendTask,
  startRerankRecommendTask,
  markRerankRecommendApplied,
  subscribeSessionRerank,
  getLatestRecommendSessionForJob,
  getRecommendTasksForJob,
} from '@/utils/hrRecommendSessionTaskRunner'



const PAGE_SIZE = 10
const APPLY_RERANK_LIMIT = 50



const props = defineProps({

  jobId: { type: [String, Number], required: true },

})



const router = useRouter()
const route = useRoute()

const scrollRef = ref(null)
const loadMoreSentinelRef = ref(null)

let unwatchRerank = null
let pageEpoch = 0
let loadMoreObserver = null
let fillGuard = 0



const jobInfo = ref(null)

const jobLoading = ref(false)

const recommendedResumes = ref([])

const pageLoading = ref(false)

const loadingMore = ref(false)

const detailVisible = ref(false)

const resumeDetail = ref(null)



const sessionId = ref(null)

const hasMore = ref(false)

const ranking = ref('coarse')

const sessionStatus = ref('coarse_ready')

const rerankAvailable = ref(false)

const rerankApplied = ref(false)

const applyingRerank = ref(false)

const coarseTotal = ref(null)
const rerankTotal = ref(null)

const poolTotal = computed(() => {
  if (rerankApplied.value && rerankTotal.value != null) return rerankTotal.value
  return coarseTotal.value
})

const poolLabel = computed(() => (rerankApplied.value ? '精排池' : '粗排池'))

const numericJobId = computed(() => Number(props.jobId))

const showRerankButton = computed(() => !!sessionId.value && !rerankApplied.value)

const rerankButtonLabel = computed(() => {
  if (sessionStatus.value === 'rerank_queued') return '排队中...'
  if (sessionStatus.value === 'reranking') return '精排中...'
  if (applyingRerank.value) return '应用中...'
  if (rerankAvailable.value && !rerankApplied.value) return '应用精排'
  return '启用精排'
})

const CACHE_SCHEMA_VERSION = 'v2'

const CACHE_KEY_PREFIX = computed(() => `resume_recommend_${CACHE_SCHEMA_VERSION}_${numericJobId.value}_`)

/** 旧版缓存：有城市文案但距离未计算（升级距离功能前的 session/队列数据） */
const needsDistanceRefresh = (items) => {
  if (!Array.isArray(items) || !items.length) return false
  return items.some((item) => {
    if (item?.distance_km != null) return false
    if (item?.distance_text === '远程') return false
    const city = item?.candidate_city || item?.resume?.residence_city
    if (!city) return false
    return item?.distance_text == null || item?.distance_text === '未填写所在地'
  })
}

const shownResumeIds = computed(() =>
  recommendedResumes.value.map((x) => x.resume?.id).filter(Boolean)
)

const resumeDetailRows = computed(() => {
  const r = resumeDetail.value
  if (!r) return []
  return [
    { label: '姓名', value: r.name },
    { label: '职位', value: r.title },
    { label: '电话', value: r.phone },
    { label: '邮箱', value: r.email },
    { label: '学历', value: r.education },
    { label: '经验', value: r.experience_years != null ? `${r.experience_years} 年` : '' },
    { label: '技能', value: formatSkills(r.skills) },
    { label: '简介', value: r.summary, block: true },
    { label: '工作经历', value: r.work_experience, block: true, pre: true },
    { label: '项目经历', value: r.project_experience, block: true, pre: true },
  ]
})



const getCacheKey = (type) => `${CACHE_KEY_PREFIX.value}${type}`

const syncPoolMeta = (res) => {
  const coarse = res?.coarse_total ?? res?.coarseTotal
  const rerank = res?.rerank_total ?? res?.rerankTotal
  if (coarse != null) coarseTotal.value = coarse
  if (rerank != null) rerankTotal.value = rerank
}

const updateHasMore = (res, shownCount = recommendedResumes.value.length) => {
  if (res?.has_more != null) {
    hasMore.value = !!res.has_more
    return
  }
  const applied = !!(res?.rerank_applied ?? rerankApplied.value)
  const total = applied
    ? (res?.rerank_total ?? res?.rerankTotal ?? rerankTotal.value)
    : (res?.coarse_total ?? res?.coarseTotal ?? coarseTotal.value)
  hasMore.value = total != null ? shownCount < total : false
}

const saveSessionCache = () => {

  try {

    sessionStorage.setItem(getCacheKey('session_id'), sessionId.value || '')

    sessionStorage.setItem(getCacheKey('result'), JSON.stringify(recommendedResumes.value))

    sessionStorage.setItem(getCacheKey('ranking'), ranking.value || 'coarse')

    sessionStorage.setItem(getCacheKey('rerank_applied'), rerankApplied.value ? '1' : '0')

    sessionStorage.setItem(getCacheKey('time'), String(Date.now()))

  } catch (_) {}

}

const SESSION_CACHE_TTL_MS = 50 * 60 * 1000

const loadSessionCache = () => {

  try {

    const sid = sessionStorage.getItem(getCacheKey('session_id'))

    const raw = sessionStorage.getItem(getCacheKey('result'))

    const result = raw ? JSON.parse(raw) : null

    const savedAt = Number(sessionStorage.getItem(getCacheKey('time')) || 0)

    if (!sid || !savedAt || Date.now() - savedAt > SESSION_CACHE_TTL_MS) {

      return null

    }

    if (needsDistanceRefresh(result)) {

      return null

    }

    return sid ? {
      sessionId: sid,
      result,
      ranking: sessionStorage.getItem(getCacheKey('ranking')) || 'coarse',
      rerankApplied: sessionStorage.getItem(getCacheKey('rerank_applied')) === '1',
    } : null

  } catch {

    return null

  }

}

const clearSessionCache = () => {

  try {

    sessionStorage.removeItem(getCacheKey('session_id'))

    sessionStorage.removeItem(getCacheKey('result'))

    sessionStorage.removeItem(getCacheKey('ranking'))

    sessionStorage.removeItem(getCacheKey('rerank_applied'))

    sessionStorage.removeItem(getCacheKey('time'))

  } catch (_) {}

}






const goBack = () => router.push('/hr/jobs')



const formatSkills = (skills) => {

  if (Array.isArray(skills)) return skills.join('、') || '-'

  return skills || '-'

}



const loadJobInfo = async () => {

  jobLoading.value = true

  try {

    const res = await getHrJobs()

    const list = Array.isArray(res) ? res : (res.data || [])

    jobInfo.value = list.find((j) => Number(j.id) === numericJobId.value) || { title: `职位 #${numericJobId.value}` }

  } catch {

    jobInfo.value = { title: `职位 #${numericJobId.value}` }

  } finally {

    jobLoading.value = false

  }

}



const mergeResults = (items) => {

  const seen = new Set(shownResumeIds.value)

  const merged = [...recommendedResumes.value]

  for (const item of items || []) {

    const id = item.resume?.id

    if (!id || seen.has(id)) continue

    seen.add(id)

    merged.push(item)

  }

  recommendedResumes.value = merged

}



const applyRerankResults = async () => {
  const sid = sessionId.value
  if (!sid) return false
  const limit = Math.min(Math.max(recommendedResumes.value.length, PAGE_SIZE), APPLY_RERANK_LIMIT)
  const res = await applyRecommendSessionRerank(sid, limit)
  if (sessionId.value !== sid) return false
  if (res.status === 'processing' || res.session_status === 'reranking' || res.session_status === 'rerank_queued') {
    return false
  }
  recommendedResumes.value = res.data || []
  updateHasMore(res)
  ranking.value = 'rerank'
  rerankApplied.value = true
  rerankAvailable.value = true
  sessionStatus.value = 'rerank_ready'
  try {
    const statusRes = await getRecommendSessionStatus(sid)
    if (sessionId.value === sid) syncPoolMeta(statusRes)
  } catch (_) {}
  saveSessionCache()
  markRerankRecommendApplied({
    sessionId: sid,
    resultCount: recommendedResumes.value.length,
    result: recommendedResumes.value,
  })
  if (scrollRef.value) scrollRef.value.scrollTop = 0
  scheduleScrollCheck()
  return true
}

const resetPageState = () => {
  teardownLoadMoreObserver()
  unwatchRerank?.()
  unwatchRerank = null
  applyingRerank.value = false
  sessionStatus.value = 'coarse_ready'
  rerankAvailable.value = false
  rerankApplied.value = false
  ranking.value = 'coarse'
  hasMore.value = false
  coarseTotal.value = null
  rerankTotal.value = null
  sessionId.value = null
  recommendedResumes.value = []
  pageLoading.value = false
}

const teardownLoadMoreObserver = () => {
  loadMoreObserver?.disconnect()
  loadMoreObserver = null
}

const setupLoadMoreObserver = async () => {
  teardownLoadMoreObserver()
  if (!hasMore.value || !recommendedResumes.value.length) return
  await nextTick()
  const root = scrollRef.value
  const target = loadMoreSentinelRef.value
  if (!root || !target) return
  loadMoreObserver = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting) && hasMore.value && !loadingMore.value) {
        loadMore()
      }
    },
    { root, rootMargin: '80px', threshold: 0 }
  )
  loadMoreObserver.observe(target)
}

const ensureScrollFill = async () => {
  const guard = ++fillGuard
  await nextTick()
  let prevCount = recommendedResumes.value.length
  while (guard === fillGuard) {
    const el = scrollRef.value
    if (!el || !hasMore.value || loadingMore.value || pageLoading.value) break
    if (el.scrollHeight > el.clientHeight + 80) break
    await loadMore()
    if (!hasMore.value) break
    await nextTick()
    const nextCount = recommendedResumes.value.length
    if (nextCount <= prevCount) break
    prevCount = nextCount
  }
}

const scheduleScrollCheck = () => {
  nextTick(async () => {
    await setupLoadMoreObserver()
    await ensureScrollFill()
    await setupLoadMoreObserver()
  })
}

const beginRerankWatch = () => {
  if (!sessionId.value) return
  const watchedId = sessionId.value
  unwatchRerank?.()
  unwatchRerank = subscribeSessionRerank(watchedId, {
    onUpdate: (res) => {
      if (sessionId.value !== watchedId) return
      sessionStatus.value = res.session_status || sessionStatus.value
      rerankAvailable.value = !!(res.rerank_available ?? (sessionStatus.value === 'rerank_ready'))
    },
    onReady: async () => {
      if (sessionId.value !== watchedId) return
      rerankAvailable.value = true
      sessionStatus.value = 'rerank_ready'
      if (rerankApplied.value) return
      applyingRerank.value = true
      try {
        const ok = await applyRerankResults()
        if (ok && sessionId.value === watchedId) {
          ElMessage.success('已按精排结果重新排序')
        }
      } finally {
        if (sessionId.value === watchedId) {
          applyingRerank.value = false
        }
      }
    },
    onError: () => {
      if (sessionId.value !== watchedId) return
      sessionStatus.value = 'coarse_ready'
      rerankAvailable.value = false
      ElMessage.error('精排失败，请稍后重试')
    },
  })
}

const applyRerankSort = async () => {
  if (!sessionId.value || applyingRerank.value) return
  const sid = sessionId.value
  const jobId = numericJobId.value
  applyingRerank.value = true

  try {
    if (sessionStatus.value === 'rerank_ready' && rerankAvailable.value) {
      const ok = await applyRerankResults()
      if (ok && sessionId.value === sid) ElMessage.success('已按精排结果重新排序')
      return
    }

    const limit = Math.min(Math.max(recommendedResumes.value.length, PAGE_SIZE), APPLY_RERANK_LIMIT)
    const res = await applyRecommendSessionRerank(sid, limit)
    if (sessionId.value !== sid) return

    if (res.status === 'processing' || res.session_status === 'reranking' || res.session_status === 'rerank_queued') {
      sessionStatus.value = res.session_status || 'rerank_queued'
      startRerankRecommendTask({
        sessionId: sid,
        jobId,
        jobTitle: jobInfo.value?.title,
      })
      beginRerankWatch()
      ElMessage.info('精排已启动，完成后将自动更新排序')
      return
    }

    const ok = await applyRerankResults()
    if (ok && sessionId.value === sid) ElMessage.success('已按精排结果重新排序')
  } catch (error) {
    if (sessionId.value !== sid) return
    const detail = error?.response?.data?.detail || error.message || '未知错误'
    ElMessage.error('应用精排失败: ' + detail)
  } finally {
    if (sessionId.value === sid) {
      applyingRerank.value = false
    }
  }
}



const startSession = async (forceRefresh = false, preferSessionId = null, epoch = pageEpoch) => {
  const jobIdAtStart = numericJobId.value
  const isStale = () => pageEpoch !== epoch || numericJobId.value !== jobIdAtStart

  if (forceRefresh) {
    unwatchRerank?.()
    unwatchRerank = null
    applyingRerank.value = false
    sessionStatus.value = 'coarse_ready'
    clearSessionCache()
    sessionId.value = null
    recommendedResumes.value = []
    rerankApplied.value = false
    rerankAvailable.value = false
    coarseTotal.value = null
  }



  const restoreSessionFromTask = async (task) => {
    if (!task?.sessionId || isStale()) return false
    if (needsDistanceRefresh(task.result)) return false
    const statusRes = await getRecommendSessionStatus(task.sessionId)
    if (isStale()) return false
    sessionId.value = task.sessionId
    recommendedResumes.value = Array.isArray(task.result) ? task.result : []
    ranking.value = task.ranking || statusRes.ranking || 'coarse'
    rerankApplied.value = !!(statusRes.rerank_applied ?? task.rerank_applied ?? task.ranking === 'rerank')
    rerankAvailable.value = !!(statusRes.rerank_available ?? (statusRes.session_status === 'rerank_ready'))
    sessionStatus.value = statusRes.session_status || 'coarse_ready'
    syncPoolMeta(statusRes)
    if (rerankApplied.value) ranking.value = 'rerank'
    updateHasMore(statusRes, recommendedResumes.value.length)
    saveSessionCache()
    if (sessionStatus.value === 'reranking' || sessionStatus.value === 'rerank_queued') beginRerankWatch()
    scheduleScrollCheck()
    return true
  }

  if (!forceRefresh && preferSessionId) {
    const queueTask = getRecommendTasksForJob(numericJobId.value)
      .find((t) => t.sessionId === preferSessionId)
    if (queueTask) {
      try {
        if (await restoreSessionFromTask(queueTask)) return
      } catch {
        clearSessionCache()
      }
    }
  }

  if (!forceRefresh) {

    const cached = loadSessionCache()

    if (cached?.sessionId && Array.isArray(cached.result) && cached.result.length) {

      try {

        const statusRes = await getRecommendSessionStatus(cached.sessionId)
        if (isStale()) return

        if (needsDistanceRefresh(cached.result)) {
          clearSessionCache()
        } else {
          sessionId.value = cached.sessionId
          recommendedResumes.value = cached.result
          ranking.value = statusRes.ranking || cached.ranking || 'coarse'
          rerankApplied.value = !!(statusRes.rerank_applied ?? cached.rerankApplied)
          rerankAvailable.value = !!(statusRes.rerank_available ?? (statusRes.session_status === 'rerank_ready'))
          sessionStatus.value = statusRes.session_status || 'coarse_ready'
          syncPoolMeta(statusRes)
          if (rerankApplied.value) ranking.value = 'rerank'
          updateHasMore(statusRes, cached.result.length)
          if (sessionStatus.value === 'reranking' || sessionStatus.value === 'rerank_queued') {
            beginRerankWatch()
          }
          scheduleScrollCheck()
          return
        }

      } catch {

        clearSessionCache()

      }

    }

    const queueTask = getLatestRecommendSessionForJob(numericJobId.value)
    if (queueTask?.sessionId && Array.isArray(queueTask.result) && queueTask.result.length) {
      try {
        if (await restoreSessionFromTask(queueTask)) return
      } catch {
        // fall through to create new session
      }
    }

  }



  pageLoading.value = true

  try {
    const res = await createRecommendSession(jobIdAtStart, PAGE_SIZE)
    if (isStale()) return

    sessionId.value = res.session_id

    recommendedResumes.value = res.data || []

    hasMore.value = !!res.has_more

    ranking.value = res.ranking || 'coarse'

    sessionStatus.value = res.session_status || 'coarse_ready'

    syncPoolMeta(res)

    rerankApplied.value = false

    rerankAvailable.value = false

    saveSessionCache()

    upsertCoarseRecommendTask({
      sessionId: res.session_id,
      jobId: jobIdAtStart,
      jobTitle: jobInfo.value?.title || `职位 #${numericJobId.value}`,
      resultCount: res.coarse_total ?? (res.data || []).length,
      result: res.data || [],
    })

  } catch (error) {

    ElMessage.error('加载推荐简历失败: ' + (error.message || '未知错误'))

  } finally {

    pageLoading.value = false
    if (!isStale()) scheduleScrollCheck()

  }

}



const loadMore = async () => {

  if (!sessionId.value || !hasMore.value || loadingMore.value || pageLoading.value) return

  loadingMore.value = true

  try {

    const res = await getRecommendSessionMore(sessionId.value, shownResumeIds.value, PAGE_SIZE)

    const beforeCount = recommendedResumes.value.length
    mergeResults(res.data || [])
    updateHasMore(res)
    if (recommendedResumes.value.length === beforeCount) {
      hasMore.value = false
    }

    ranking.value = res.ranking || ranking.value

    sessionStatus.value = res.session_status || sessionStatus.value

    saveSessionCache()

  } catch (error) {

    ElMessage.error('加载更多失败: ' + (error.message || '未知错误'))

  } finally {

    loadingMore.value = false
    if (!hasMore.value) {
      teardownLoadMoreObserver()
    } else {
      scheduleScrollCheck()
    }

  }

}



const onScroll = () => {

  const el = scrollRef.value

  if (!el || !hasMore.value || loadingMore.value) return

  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 80) {

    loadMore()

  }

}



const openResumeDetail = async (item) => {

  const id = item.resume?.id

  if (!id) return

  try {

    const res = await getHrResumeDetail(id)

    resumeDetail.value = res.data || res

    detailVisible.value = true

  } catch {

    ElMessage.error('获取简历详情失败')

  }

}



const initPage = async () => {
  resetPageState()
  const epoch = ++pageEpoch
  const jobId = numericJobId.value
  await loadJobInfo()
  if (pageEpoch !== epoch || numericJobId.value !== jobId) return
  const preferSessionId = typeof route.query.sessionId === 'string' ? route.query.sessionId : null
  await startSession(false, preferSessionId, epoch)
}

watch(
  () => [route.params.jobId, route.query.sessionId, route.query._r],
  () => {
    if (route.name !== 'HrResumeRecommend') return
    initPage()
  },
  { immediate: true }
)



onUnmounted(() => {
  teardownLoadMoreObserver()
  unwatchRerank?.()
  unwatchRerank = null
})

</script>



<style scoped>
.resume-recommend-page {
  max-width: 1320px;
  margin: 0 auto;
  padding: 4px 4px 0;
  height: calc(100vh - 140px);
  display: flex;
  flex-direction: column;
  min-height: 0;
  box-sizing: border-box;
}

.page-hero {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid #e2e8f0;
  border-radius: 14px;
}

.back-btn {
  color: #64748b;
  flex-shrink: 0;
}

.hero-text h1 {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}

.hero-text p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.compare-layout {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 20px;
  align-items: stretch;
}

.ref-column {
  flex: 0 0 360px;
  max-width: 360px;
  position: sticky;
  top: 12px;
  align-self: flex-start;
  max-height: calc(100vh - 100px);
}

.list-column {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.list-panel {
  flex: 1;
  min-height: 0;
  max-height: calc(100vh - 220px);
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.list-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
  background: #fafbfc;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.header-main {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.count-text {
  font-size: 12px;
  color: #94a3b8;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.scroll-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 20px 20px;
}

.match-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.load-more-hint {
  text-align: center;
  padding: 16px 0 4px;
  color: #3b82f6;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.load-more-hint.muted {
  color: #94a3b8;
}

.dialog-compare {
  display: flex;
  gap: 20px;
  align-items: stretch;
  min-height: 460px;
}

.dialog-ref {
  flex: 0 0 340px;
  max-height: 560px;
  overflow: hidden;
}

.dialog-detail {
  flex: 1;
  min-width: 0;
  max-height: 560px;
  overflow-y: auto;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px 18px;
}

.dialog-detail-head {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e2e8f0;
}

@media (max-width: 960px) {
  .compare-layout {
    flex-direction: column;
  }
  .ref-column {
    flex: none;
    max-width: none;
    width: 100%;
    position: static;
    max-height: 380px;
  }
  .dialog-compare {
    flex-direction: column;
  }
  .dialog-ref {
    flex: none;
    width: 100%;
    max-height: 280px;
  }
}
</style>

