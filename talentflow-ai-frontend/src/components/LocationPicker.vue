<template>
  <div class="location-picker">
    <el-cascader
      v-model="regionPath"
      :options="CHINA_REGION_OPTIONS"
      :props="{ expandTrigger: 'hover' }"
      clearable
      filterable
      :placeholder="cityPlaceholder"
      style="width: 100%"
      :show-all-levels="true"
      @change="emitChange"
    />
    <el-input
      v-if="showAddress"
      v-model="addressValue"
      class="address-input"
      :placeholder="addressPlaceholder"
      clearable
      @input="emitChange"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { CHINA_REGION_OPTIONS, pathFromRegionLabel, regionLabelFromPath } from '@/data/chinaRegions'

const props = defineProps({
  city: { type: String, default: '' },
  address: { type: String, default: '' },
  showAddress: { type: Boolean, default: true },
  cityPlaceholder: { type: String, default: '请选择省 / 市 / 区' },
  addressPlaceholder: { type: String, default: '详细地址（选填，可提高距离精度）' },
})

const emit = defineEmits(['update:city', 'update:address', 'change'])

const regionPath = ref(pathFromRegionLabel(props.city))
const addressValue = ref(props.address || '')

watch(
  () => [props.city, props.address],
  ([city, address]) => {
    regionPath.value = pathFromRegionLabel(city)
    addressValue.value = address || ''
  }
)

function emitChange() {
  const city = regionLabelFromPath(regionPath.value)
  emit('update:city', city)
  emit('update:address', addressValue.value)
  emit('change', { city, address: addressValue.value })
}
</script>

<style scoped>
.location-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
</style>
