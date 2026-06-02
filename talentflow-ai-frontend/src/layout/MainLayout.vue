<template>
  <el-container class="layout-container" style="height: 100vh">
    <!-- 左侧菜单 -->
    <el-aside width="240px" class="sidebar">
      <div class="logo">
        <el-icon :size="24" color="#F7BA2A"><umbrella /></el-icon>
        <span>蒲公英部落</span>
      </div>

      <el-menu
        :default-active="$route.path"
        router
        background-color="#2c3e50"
        text-color="#bfcbd9"
        active-text-color="#F7BA2A"
        :collapse="false"
      >
         <!-- 成长中心 (主入口) -->
        <el-menu-item index="/dashboard/tasks">
          <el-icon><DataAnalysis /></el-icon>
          <span>成长中心</span>
        </el-menu-item>

        <el-menu-item index="/square">
          <el-icon><chat-dot-round /></el-icon>
          <span>蒲公英广场</span>
        </el-menu-item>

        <el-menu-item index="/charging">
          <el-icon><video-camera /></el-icon>
          <span>免费充电站</span>
        </el-menu-item>

        <el-menu-item index="/startup">
          <el-icon><briefcase /></el-icon>
          <span>创业集市</span>
        </el-menu-item>

        <el-menu-item index="/referral">
          <el-icon><trophy /></el-icon>
          <span>伯乐内推</span>
        </el-menu-item>

        <el-menu-item index="/insights">
          <el-icon><trend-charts /></el-icon>
          <span>职场风向标</span>
        </el-menu-item>
      </el-menu>

      <div class="user-info">
        <el-button type="danger" link @click="handleLogout">退出部落</el-button>
      </div>
    </el-aside>

    <!-- 右侧内容 -->
    <el-container>
      <el-header class="header">
        <div class="header-right">
          <el-dropdown>
            <span class="el-dropdown-link">
              <el-avatar :size="30" src="https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png" />
              部落成员
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>个人中心</el-dropdown-item>
                <el-dropdown-item>设置</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <!-- 这里会显示上面配置的具体页面 -->
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


// 处理退出登录
const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '退出提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    // 清除 LocalStorage
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    // 清除 Pinia 中的状态
    userStore.logout()
    // 跳转到登录页
    await router.push('/login')
    ElMessage.success('已安全退出')
  } catch (error) {
    // 取消退出或出错
  }
}
</script>

<style scoped>
.layout-container {
  background-color: #f0f2f5;
}
.sidebar {
  background-color: #2c3e50;
  display: flex;
  flex-direction: column;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  font-weight: bold;
  border-bottom: 1px solid #3b5066;
}
.logo .el-icon {
  margin-right: 8px;
}
.user-info {
  margin-top: auto;
  padding: 20px;
  border-top: 1px solid #3b5066;
  text-align: center;
}
.header {
  background-color: #fff;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  box-shadow: 0 1px 4px rgba(0,21,41,.08);
}
.main-content {
  padding: 20px;
  overflow-y: auto;
}
.page-container {
  background: #fff;
  padding: 24px;
  border-radius: 8px;
  min-height: 100%;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,.05);
}
</style>