<template>
  <el-container class="admin-layout" style="height: 100vh">
    <!-- 左侧侧边栏 -->
    <el-aside width="200px" class="sidebar">
      <div class="logo">蒲公英 - HR工作台</div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#2c3e50"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <!-- 1. 工作台/概览 -->
        <el-menu-item index="/hr/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <span>工作台</span>
        </el-menu-item>

        <!-- 2. 核心功能：任务管理 (发布任务、查看进度) -->
        <el-menu-item index="/hr/tasks">
          <el-icon><Briefcase /></el-icon>
          <span>任务管理</span>
        </el-menu-item>

        <!-- 3. 核心功能：投递/接单审核 -->
        <el-menu-item index="/hr/applications">
          <el-icon><Tickets /></el-icon>
          <span>投递审核</span>
          <!-- 如果有待处理数量，可以在这里加个徽标 -->
        </el-menu-item>

        <!-- 4. 岗位管理 -->
        <el-menu-item index="/hr/jobs">
          <el-icon><FolderOpened /></el-icon>
          <span>岗位管理</span>
        </el-menu-item>

        <!-- 5. 历史/记录 -->
        <el-menu-item index="/hr/finance">
          <el-icon><Clock /></el-icon>
          <span>结算记录</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="el-dropdown-link">
              <!-- 动态显示用户名或默认HR -->
              {{ userName }} <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容区域 -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
// 引入图标
import { HomeFilled, Briefcase, Tickets, FolderOpened, Clock, ArrowDown } from '@element-plus/icons-vue'

import { useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import { ElMessageBox, ElMessage } from 'element-plus'
import { computed } from 'vue'

const router = useRouter()
const userStore = useUserStore()

// 计算属性：从 Store 中获取用户名，如果没有则默认为 'HR专员'
const userName = computed(() => {
  return userStore.name || 'HR专员'
})

// 处理下拉菜单命令
const handleCommand = (command) => {
  if (command === 'logout') {
    handleLogout()
  }
}

// 处理退出登录
const handleLogout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  userStore.logout()
  router.push('/login')
  ElMessage.success('已安全退出')
}
</script>

<style scoped>
.admin-layout {
  background-color: #f0f2f5;
}

.sidebar {
  background-color: #2c3e50;
  color: white;
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  font-size: 18px;
  font-weight: bold;
  color: #fff;
  border-bottom: 1px solid #3e5165;
  background-color: #2c3e50;
}

.header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0,21,41,.08);
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.header-right {
  cursor: pointer;
}

.main-content {
  margin: 20px;
  background: #fff;
  padding: 20px;
  border-radius: 4px;
  overflow-y: auto;
}
</style>