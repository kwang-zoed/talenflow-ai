<template>
  <div class="dashboard-container">
    <!-- 二级菜单：切换工作台与驾驶舱 -->
    <div class="sub-header">
      <!-- 
        注意：index 必须填写完整的路由 Path，而不是组件名 
        因为开启了 router 属性，点击会自动触发 router.push(index)
      -->
      <el-menu 
        mode="horizontal" 
        :default-active="$route.path" 
        router 
        class="sub-menu"
      >
        <!-- 实战工作台 -->
        <el-menu-item index="/dashboard/tasks">
          <el-icon><Briefcase /></el-icon>
          实战工作台
        </el-menu-item>

        <!-- 求职驾驶舱 -->
        <el-menu-item index="/dashboard/jobs">
          <el-icon><TrendCharts /></el-icon>
          求职驾驶舱
        </el-menu-item>
        <el-menu-item index="/dashboard/profile">
          <el-icon><Location /></el-icon>
          我的所在地
        </el-menu-item>
      </el-menu>
    </div>

    <!-- 内容区域 -->
    <div class="main-content">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { Briefcase, TrendCharts, Location } from '@element-plus/icons-vue'
</script>

<style scoped>
.dashboard-container {
  background-color: #f5f7fa;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sub-header {
  background: #fff;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  z-index: 10;
}

.sub-menu {
  border-bottom: none;
  padding-left: 20px;
}

.main-content {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}
</style>