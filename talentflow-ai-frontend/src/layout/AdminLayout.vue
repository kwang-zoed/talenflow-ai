<template>
  <el-container class="admin-layout" style="height: 100vh">
    <!-- 左侧侧边栏 -->
    <el-aside width="200px" class="sidebar">
      <div class="logo">蒲公英管理后台</div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#2c3e50"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/admin/dashboard">
          <el-icon><DataLine /></el-icon>
          <span>数据统计</span>
        </el-menu-item>

        <el-menu-item index="/admin/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>

        <el-menu-item index="/admin/projects">
          <el-icon><Document /></el-icon>
          <span>项目管理</span>
        </el-menu-item>

        <el-menu-item index="/admin/jobs">
          <el-icon><Briefcase /></el-icon>
          <span>职位管理</span>
        </el-menu-item>

        <!-- 新增：简历管理菜单项 -->
        <el-menu-item index="/admin/resumes">
          <el-icon><Tickets /></el-icon>
          <span>简历管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="el-dropdown-link">
              管理员 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
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
// 引入新增的 Tickets 图标
import { DataLine, User, Document, Briefcase, ArrowDown, Tickets } from '@element-plus/icons-vue'

import { useRouter } from 'vue-router'
import { useUserStore } from '../store/user' // 路径根据你的项目结构调整
import { ElMessageBox, ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

// 处理下拉菜单命令
const handleCommand = (command) => {
  console.log('收到命令:', command)
  if (command === 'logout') {
    handleLogout()
  }
}

// 处理退出登录
const handleLogout = () => {
  console.log('执行退出登录')
  // 直接清除，先跳过确认框验证逻辑
  userStore.logout()
  router.push('/login')
  ElMessage.success('已安全退出')
}
</script>

<style scoped>
/* ... 原有样式保持不变 ... */
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
}

.header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0,21,41,.08);
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.main-content {
  margin: 20px;
  background: #fff;
  padding: 20px;
  border-radius: 4px;
}
</style>