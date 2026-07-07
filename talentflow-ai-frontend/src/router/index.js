import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../store/user'

// --- 布局组件 ---
import MainLayout from '../layout/MainLayout.vue'
import AdminLayout from '../layout/AdminLayout.vue'
import HRLayout from '../layout/HRLayout.vue'

// --- 页面组件 ---
// 1. 用户端
import LoginView from '../views/LoginView.vue'
import Square from '../views/Square.vue'
import Charging from '../views/Charging.vue'
import Startup from '../views/Startup.vue'
import Referral from '../views/Referral.vue'
import Insights from '../views/Insights.vue'

// Phase 1: Dashboard 子模块
import DashboardLayout from '../views/user/dashboard/DashboardLayout.vue'
import TaskBoard from '../views/user/dashboard/TaskBoard.vue'
import JobCockpit from '../views/user/dashboard/JobCockpit.vue'
import TaskDetail from '../views/user/dashboard/TaskDetail.vue'
import ResumeManager from '../views/user/dashboard/ResumeManager.vue'
import UserProfileSettings from '../views/user/dashboard/UserProfileSettings.vue'
import Applications from '../views/user/dashboard/Applications.vue'
import JobList from '../views/user/dashboard/JobList.vue'

// 2. 管理端
import AdminDashboard from '../views/admin/Dashboard.vue'
import AdminUsers from '../views/admin/Users.vue'
import AdminProjects from '../views/admin/Projects.vue'
import AdminJobs from '../views/admin/Jobs.vue'
import AdminResumes from '../views/admin/Resumes.vue'


// 3.hr管理端
import HrDashboard from '../views/hr/Dashboard.vue'
import HrApplications from '../views/hr/Applications.vue'
import HrFinance from '../views/hr/Finance.vue'
import HrTask from '../views/hr/Task.vue'

// ==========================================
// 1. 类型声明扩展 (JS 写法)
// ==========================================
// 在 JS 中，我们通过 JSDoc 或者简单的忽略检查来告诉编辑器 meta 有哪些属性
/**
 * @typedef {Object} RouteMeta
 * @property {boolean} [isPublic] - 是否公开页面
 * @property {boolean} [requiresAuth] - 是否需要登录
 * @property {string} [role] - 需要的角色
 */

const routes = [
  // --- 公共路由 ---
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { isPublic: true } // 标记为公共页面
  },

  // --- 用户端路由 ---
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', redirect: '/dashboard/tasks' },

      // 蒲公英成长中心
      {
        path: 'dashboard',
        component: DashboardLayout,
        meta: { requiresAuth: true }, // 父级标记需要登录
        children: [
          { path: 'tasks', name: 'TaskBoard', component: TaskBoard },
          { path: 'jobs', name: 'JobCockpit', component: JobCockpit },
          { path: 'jobs/list', name: 'JobList', component: JobList },
          { path: 'tasks/:id', name: 'TaskDetail', component: TaskDetail },
          { path: 'resume', name: 'resumes', component: ResumeManager },
          { path: 'profile', name: 'UserProfile', component: UserProfileSettings },
          { path: 'applications', name: 'Applications', component: Applications },
        ]
      },
      // 其他用户页面 (如果不加 meta，默认为公开)
      { path: 'square', name: 'Square', component: Square },
      { path: 'charging', name: 'Charging', component: Charging },
      { path: 'startup', name: 'Startup', component: Startup },
      { path: 'referral', name: 'Referral', component: Referral },
      { path: 'insights', name: 'Insights', component: Insights },
    ]
  },

  // --- 管理后台路由 ---
  {
    path: '/admin',
    component: AdminLayout,
    meta: { requiresAuth: true, role: 'admin' }, // 标记需要管理员权限
    children: [
      { path: 'dashboard', component: AdminDashboard },
      { path: 'users', component: AdminUsers },
      
      // 用户详情页路由
      {
        path: 'users/:id',           // 1. 动态路径参数 :id
        name: 'UserDetail',     // 2. 命名路由，方便跳转
        component: () => import('../views/admin/user_detail.vue'), // 3. 懒加载详情页组件
        props: true,                 // 4. 关键配置：将 params 中的 id 作为 props 传给组件
        meta: { requiresAuth: true, role: 'admin' } // 5. 继承父级的权限控制
      },
      
      { path: 'projects', component: AdminProjects },
      { path: 'jobs', component: AdminJobs },
      { path: 'resumes', component: AdminResumes }
    ]
  },


  // 2. 新增：HR 路由
  {
    path: '/hr',
    component: HRLayout,
    meta: { requiresAuth: true, role: 'hr' }, // 标记需要 hr 角色
    redirect: '/hr/dashboard',
    children: [
      { path: 'dashboard', component: () => import('../views/hr/Dashboard.vue'), meta: { title: '工作台' } },
      { path: 'tasks', component: () => import('../views/hr/Task.vue'), meta: { title: '任务管理' } },
      { path: 'applications', component: () => import('../views/hr/Applications.vue'), meta: { title: '投递管理' } },
      { path: 'jobs', component: () => import('../views/hr/HrJobs.vue'), meta: { title: '岗位管理' } },
      {
        path: 'jobs/:jobId/recommend',
        name: 'HrResumeRecommend',
        component: () => import('../views/hr/ResumeRecommend.vue'),
        props: true,
        meta: { title: '简历推荐', role: 'hr' },
      },
      { path: 'finance', component: () => import('../views/hr/Finance.vue'), meta: { title: '财务结算' } }
    ]
  },

  // --- 404 重定向 ---
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard/tasks'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// ==========================================
// 2. 全局前置守卫（统一角色判断标准）
// ==========================================
router.beforeEach((to, from, next) => {
  try {
    const userStore = useUserStore()
    const token = userStore.token || localStorage.getItem('token')
    const rawRole = userStore.role
    
    const role = String(rawRole)
    
    // 后端角色约定：
    //  role=0 -> 求职者
    //  role=1 -> 管理员
    //  role=2 -> HR
    
    // 1. 公共页面（登录页）：已登录用户自动分流
    if (to.meta.isPublic) {
      if (token) {
        if (role === '1') {
          next('/admin/dashboard')
        } else if (role === '2') {
          next('/hr/dashboard')
        } else {
          next('/dashboard/tasks')
        }
      } else {
        next()
      }
      return
    }
    
    // 2. 需要登录的页面：无token踢去登录
    if (to.meta.requiresAuth) {
      if (!token) {
        next('/login')
        return
      }
      
      // 管理员专属
      if (to.meta.role === 'admin' || to.path.startsWith('/admin')) {
        if (role !== '1') {
          next('/dashboard/tasks')
          return
        }
      }
      
      // HR专属
      if (to.meta.role === 'hr' || to.path.startsWith('/hr')) {
        if (role !== '2') {
          next('/dashboard/tasks')
          return
        }
      }
    }
    
    next()
  } catch (e) {
    console.error('[Router Guard] 异常:', e)
    next()  // 守卫抛异常时也保证路由不卡死，避免白屏
  }
})

export default router