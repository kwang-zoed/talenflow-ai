<template>
  <div class="dashboard-container">
    <!-- 顶部关键指标卡片 -->
    <el-row :gutter="20" class="mb-5">
      <el-col :span="6" v-for="item in statsData" :key="item.label">
        <el-card shadow="hover" class="stats-card">
          <div class="card-content">
            <div class="icon-box" :style="{ backgroundColor: item.color }">
              <el-icon :size="24" color="#fff"><component :is="item.icon" /></el-icon>
            </div>
            <div class="text-box">
              <div class="label">{{ item.label }}</div>
              <div class="value">{{ item.value }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20">
      <!-- 折线图：简历增长趋势 -->
      <el-col :span="16">
        <el-card shadow="hover" header="简历投递趋势 (近7天)">
          <div ref="lineChartRef" style="height: 400px; width: 100%;"></div>
        </el-card>
      </el-col>

      <!-- 饼图：职位状态分布 -->
      <el-col :span="8">
        <el-card shadow="hover" header="职位状态占比">
          <div ref="pieChartRef" style="height: 400px; width: 100%;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import * as echarts from 'echarts/core';
import { BarChart, LineChart, PieChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, TitleComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

// 注册组件
echarts.use([BarChart, LineChart, PieChart, GridComponent, TooltipComponent, TitleComponent, LegendComponent, CanvasRenderer]);

import axios from '../../utils/request'; 

// --- 数据定义 ---
const statsData = ref([
  { label: '注册用户', value: 0, icon: 'User', color: '#409EFF' },
  { label: '发布职位', value: 0, icon: 'Briefcase', icon: 'Suitcase', color: '#67C23A' },
  { label: '简历总数', value: 0, icon: 'Document', color: '#E6A23C' },
  { label: '待审核简历', value: 0, icon: 'Timer', color: '#F56C6C' },
]);

const lineChartRef = ref(null);
const pieChartRef = ref(null);
let lineChart = null;
let pieChart = null;

// --- 获取统计概览 ---
const fetchStats = async () => {
  try {
    const res = await axios.get('/admin/stats/overview');
    const data = res;
    
    // 更新卡片数据
    statsData.value[0].value = data.users;
    statsData.value[1].value = data.jobs;
    statsData.value[2].value = data.resumes;
    statsData.value[3].value = data.pending_resumes;
  } catch (error) {
    console.error('获取统计数据失败', error);
  }
};

// --- 初始化折线图 (简历趋势) ---
const initLineChart = async () => {
  lineChart = echarts.init(lineChartRef.value);
  const res = await axios.get('/admin/stats/resume-trend');
  
  const dates = res.map(item => item.date);
  const counts = res.map(item => item.count);

  const option = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: { type: 'value' },
    series: [{
      data: counts,
      type: 'line',
      smooth: true,
      areaStyle: { opacity: 0.1 },
      itemStyle: { color: '#409EFF' }
    }]
  };
  lineChart.setOption(option);
};

// --- 初始化饼图 (职位分布) ---
const initPieChart = async () => {
  pieChart = echarts.init(pieChartRef.value);
  const res = await axios.get('/admin/stats/job-distribution');
  
  const option = {
    tooltip: { trigger: 'item' },
    legend: { bottom: 'bottom' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      data: res
    }]
  };
  pieChart.setOption(option);
};

// --- 生命周期 ---
onMounted(() => {
  fetchStats();
  initLineChart();
  initPieChart();
  
  // 窗口大小改变时重绘图表
  window.addEventListener('resize', () => {
    lineChart?.resize();
    pieChart?.resize();
  });
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', () => {});
  lineChart?.dispose();
  pieChart?.dispose();
});
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100%;
}

.stats-card .card-content {
  display: flex;
  align-items: center;
}

.icon-box {
  width: 50px;
  height: 50px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
}

.text-box .label {
  font-size: 14px;
  color: #999;
  margin-bottom: 5px;
}

.text-box .value {
  font-size: 24px;
  font-weight: bold;
  color: #333;
}
</style>