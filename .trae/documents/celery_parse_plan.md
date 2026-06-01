# 文档解析接口 Celery 异步化计划

> 需求目标：/jobs/batch-parse 和 /jobs/parse 同步接口改 Celery 任务队列
> - 用户离开解析页面不会中断任务执行
> - 居中顶部显示进度消息（含进度百分比）
> - 进程完成后消息提示点击跳转回解析弹窗

---

## 总体架构参考

已有的成功模式可直接复用：[job_recommend.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/user/job_recommend.py) + [JobCockpit.vue](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-frontend/src/views/user/dashboard/JobCockpit.vue)

| 组件 | 推荐接口模式 | 解析接口目标 |
|-----|-------------|-------------|
| **提交** | `POST /user/recommend/submit` → `task_id` | `POST /admin/jobs/parse/submit` → `task_id` |
| **轮询** | `GET /user/recommend/status/{task_id}` | `GET /admin/jobs/parse/status/{task_id}` |
| **进度** | Celery `update_state` meta | Celery `update_state(meta={'current': N, 'total': N})` |

---

## Phase 1: 后端 Celery Task 改造

### 1.1 新增解析任务 worker

**文件**：[recommendation_service.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/services/recommendation_service.py)（新增长任务）

```python
# ========== 新增：文档解析异步长任务 ==========
@celery_app.task(bind=True)
def parse_document_task(self, file_content: bytes, filename: str, is_batch: bool = False):
    """后台任务：单个/批量文档解析（支持 update_state 进度）"""
    
    #  ========== 模拟阶段进度上报 ==========
    self.update_state(
        state='PROGRESS',
        meta={
            'current': 1, 
            'total': 4,
            'message': '正在提取文本内容...',
            'percent': 25
        }
    )
    
    # ========== 1) 调用现有 extract_text_from_file ==========
    full_text = extract_text_from_file(file_content, filename)  # 复用业务逻辑
    
    self.update_state(
        state='PROGRESS',
        meta={
            'current': 2, 
            'total': 4,
            'message': '正在调用 LLM 分析...',
            'percent': 50
        }
    )
    
    # ========== 2) 调用 LLM Prompt 解析（复用 parse_llm_result） ==========
    llm = get_llm()
    llm_output = llm.invoke(final_prompt)
    result = parse_llm_result(llm_output.content)
    
    self.update_state(
        state='PROGRESS',
        meta={
            'current': 3, 
            'total': 4,
            'message': '正在整理解析结果...',
            'percent': 75
        }
    )
    
    # ========== 3) clean_job_data 清洗 ==========
    cleaned = clean_job_data(result)
    
    self.update_state(
        state='PROGRESS',
        meta={
            'current': 4, 
            'total': 4,
            'message': '完成',
            'percent': 100
        }
    )
    
    return {
        "filename": filename,
        "is_batch": is_batch,
        "result": result,
        "cleaned": cleaned
    }
```

### 1.2 新增后端路由：提交 + 状态查询

**文件**：[job_manage.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/admin/job_manage.py) 末尾追加

```python
# ========== ========== Celery 异步文档解析：提交 + 轮询 ========== ==========
@router.post("/jobs/parse/submit")
async def submit_parse_task(
    file: UploadFile = File(...),
    is_batch: bool = Form(False),
    current_user: UserDB = Depends(deps.get_current_active_admin)
):
    """提交文档解析任务 → 立即返回 task_id（用户可离开页面）"""
    contents = await file.read()
    filename = file.filename
    
    # 异步启动 Celery Worker
    task = parse_document_task.delay(contents, filename, is_batch)
    
    print(f"[parse submit] 任务已提交: task_id={task.id}, file={filename}")
    return {
        "task_id": task.id,
        "filename": filename,
        "message": "解析任务已提交，正在后台执行"
    }


@router.get("/jobs/parse/status/{task_id}")
def get_parse_status(task_id: str, current_user=Depends(deps.get_current_active_admin)):
    """轮询解析任务进度与结果"""
    result = AsyncResult(task_id)
    
    print(f"[parse status] 轮询: task_id={task_id}, state={result.state}")
    
    if result.state == 'PENDING':
        return {"status": "processing", "message": "任务排队中...", "percent": 0}
    
    elif result.state == 'PROGRESS':
        meta = result.info
        return {
            "status": "processing",
            "message": meta.get("message", "正在解析..."),
            "percent": meta.get("percent", 0),
            "current": meta.get("current", 0),
            "total": meta.get("total", 1)
        }
    
    elif result.state == 'SUCCESS':
        return {
            "status": "success",
            "message": "解析完成",
            "percent": 100,
            "data": result.result  # 返回完整解析结果供前端填充
        }
    
    elif result.state == 'FAILURE':
        return {
            "status": "error",
            "message": f"解析失败: {str(result.info)}"
        }
    
    return {"status": "processing", "message": result.state}
```

---

## Phase 2: 前端交互改造

### 2.1 API 层：新增 parse 轮询

**文件**：[src/api/job.js](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-frontend/src/api/job.js)（新增方法）

```javascript
// ========== 文档解析异步提交 + 轮询（参考 pollRecommendResult 同构） ==========
export const submitParseTask = (file, isBatch = false) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('is_batch', isBatch)
  return request({
    url: '/admin/jobs/parse/submit',
    method: 'POST',
    headers: { 'Content-Type': 'multipart/form-data' },
    data: formData
  })
}

export const getParseTaskStatus = (taskId) => {
  return request({
    url: `/admin/jobs/parse/status/${taskId}`,
    method: 'GET'
  })
}

export const pollParseTaskResult = (taskId, maxTime = 180000) => {
  // 同 pollRecommendResult 指数退避轮询模式
  let cancelled = false
  const promise = new Promise((resolve, reject) => {
    let start = Date.now()
    const attempt = async (delay = 1500) => {
      if (cancelled) return reject(new Error('已取消'))
      if (Date.now() - start > maxTime) return reject(new Error('超时'))
      
      const res = await getParseTaskStatus(taskId)
      const data = res.data
      
      if (data.status === 'success') {
        resolve(data.data)
      } else if (data.status === 'processing') {
        // 向外暴露 onProgress 回调给进度条
        if (promise.onProgress) {
          promise.onProgress(data)
        }
        const next = Math.min(delay * 1.5, 5000)
        setTimeout(() => attempt(next), delay)
      } else {
        reject(new Error(data.message || '失败'))
      }
    }
    attempt()
  })
  promise.cancel = () => cancelled = true
  return promise
}
```

### 2.2 全局顶部进度条组件

**文件**：`src/components/GlobalTaskProgress.vue`（新组件）

```vue
<template>
  <Transition name="slide-down">
    <div 
      v-if="visible" 
      class="fixed top-0 left-0 right-0 z-[9999] bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-3 px-6 shadow-lg"
    >
      <div class="max-w-5xl mx-auto flex items-center justify-between">
        <div class="flex items-center gap-4">
          <el-icon class="text-xl" :loading="percent < 100">
            <Promotion v-if="percent < 100" />
            <CircleCheck v-else />
          </el-icon>
          
          <div>
            <div class="font-medium">{{ message }}</div>
            <div class="text-xs opacity-80 mt-0.5">
              {{ percent < 100 ? `进度: ${percent}%` : '点击返回解析弹窗' }}
            </div>
          </div>
        </div>
        
        <div class="w-56 h-2 bg-white/20 rounded-full overflow-hidden">
          <div 
            class="h-full bg-white rounded-full transition-all duration-500 ease-out"
            :style="{ width: `${percent}%` }"
          />
        </div>
        
        <el-button 
          v-if="percent === 100" 
          type="success" 
          size="small" 
          text
          @click="handleClickToFill"
        >
          前往填充表单
        </el-button>
        
        <el-button 
          v-if="percent < 100" 
          type="info" 
          size="small" 
          text
          class="text-white/80"
          @click="visible = false"
        >
          后台继续运行
        </el-button>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref } from 'vue'
import { Promotion, CircleCheck } from '@element-plus/icons-vue'

const visible = ref(false)
const message = ref('正在解析文档...')
const percent = ref(0)
const taskData = ref(null)
const emit = defineEmits(['clickToFill'])

export function showProgress(msg = '正在后台执行...') {
  visible.value = true
  message.value = msg
  percent.value = 0
}

export function updateProgress(data) {
  message.value = data.message || message.value
  percent.value = data.percent || 0
  if (data.status === 'success') {
    taskData.value = data.data
  }
}

export function hideProgress() {
  visible.value = false
}

function handleClickToFill() {
  emit('clickToFill', taskData.value)
  visible.value = false
}
</script>
```

### 2.3 AdminJob.vue 对接进度条与弹窗回填

**文件**：[src/views/admin/AdminJob.vue](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-frontend/src/views/admin/AdminJob.vue)

```javascript
// ========== 原解析流程（改异步） ==========
const handleParse = async (rawFile) => {
  isParsing.value = true
  try {
    // 1) 立即提交任务，不等结果
    const submitRes = await submitParseTask(rawFile, false)
    const taskId = submitRes.data?.task_id || submitRes.task_id
    console.log('[parse] 任务提交成功 task_id:', taskId)
    
    // 2) 打开全局进度条（用户此时切页也不阻塞）
    const progressRef = inject('parseProgress')
    if (progressRef) {
      progressRef.showProgress(`正在后台解析: ${rawFile.name}`)
    }
    
    // 3) 开启轮询
    const poll = pollParseTaskResult(taskId)
    parseTaskPoll.value = poll
    
    poll.onProgress = (statusData) => {
      if (progressRef) {
        progressRef.updateProgress(statusData)
      }
    }
    
    // 4) 轮询结束自动填弹窗
    const finalResult = await poll
    Object.assign(parseForm, finalResult.cleaned) 
    Object.assign(parseForm, {
      title: finalResult.result.title,
      company: finalResult.result.company,
      ...
    })
    
    // 弹窗保持常开
    dialogVisible.value = true
    isParsing.value = false
    
  } catch (err) {
    console.error('parse err:', err)
  }
}

onUnmounted(() => {
  if (parseTaskPoll.value?.cancel) {
    parseTaskPoll.value.cancel()  // 组件销毁只取消前端轮询，后端 Celery 继续
  }
})
```

---

## Phase 3: App.vue 挂载全局进度条

```vue
<GlobalTaskProgress 
  ref="progressBar" 
  @click-to-fill="handleParseComplete"
/>

provide('parseProgress', {
  showProgress: (msg) => {
    progressBar.value?.showProgress(msg)
    router.push('/admin/jobs')  // 也可以不切页，让用户自行浏览其他模块
  },
  updateProgress: (data) => progressBar.value?.updateProgress(data),
  hideProgress: () => progressBar.value?.hideProgress()
})
```

---

## 验收标准

| 测试项 | 预期结果 |
|-------|---------|
| **上传文件点解析** | 立即返回 task_id 并显示顶部进度条 |
| **进度条可读** | message / percent / 进度条随 Celery update_state 平滑增长 |
| **切页再回来** | 进度条继续显示（或可点击跳回解析列表已完成任务） |
| **解析完成** | 进度条定格 100%，右侧按钮点击后弹出新建职位表单并回填所有解析字段 |
| **后端日志** | `worker` 控制台输出解析执行过程，`api` 输出轮询记录 |
