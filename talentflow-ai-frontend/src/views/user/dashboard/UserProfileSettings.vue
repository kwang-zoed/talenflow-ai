<template>
  <div class="profile-settings">
    <el-card shadow="never">
      <template #header>
        <div class="card-head">
          <h2>我的所在地</h2>
          <p>设置默认所在地后，新建简历可自动继承；推荐结果将显示与岗位的距离。</p>
        </div>
      </template>

      <el-form v-loading="loading" label-position="top" style="max-width: 560px">
        <el-form-item label="常住城市">
          <LocationPicker v-model:city="form.residence_city" v-model:address="form.residence_address" />
        </el-form-item>
        <el-form-item label="期望工作城市">
          <el-input v-model="form.expected_city" placeholder="如：深圳" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="saveProfile">保存</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import LocationPicker from '@/components/LocationPicker.vue'
import { getUserProfile, updateUserProfile } from '@/api/user'

const loading = ref(false)
const saving = ref(false)
const form = ref({
  residence_city: '',
  residence_address: '',
  expected_city: '',
})

onMounted(async () => {
  loading.value = true
  try {
    const res = await getUserProfile()
    form.value = {
      residence_city: res.residence_city || '',
      residence_address: res.residence_address || '',
      expected_city: res.expected_city || '',
    }
  } catch (e) {
    ElMessage.error('加载个人资料失败')
  } finally {
    loading.value = false
  }
})

async function saveProfile() {
  saving.value = true
  try {
    await updateUserProfile(form.value)
    ElMessage.success('所在地已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.profile-settings {
  max-width: 760px;
  margin: 0 auto;
}
.card-head h2 {
  margin: 0 0 6px;
  font-size: 18px;
}
.card-head p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}
</style>
