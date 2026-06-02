import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path' // 引入 path 模块

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'), // 保持原有的 alias
    },
  },
  server: {
    // 【核心配置】设置代理
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', // 你的 FastAPI 后端地址（请确认你的后端端口是 8000）
        changeOrigin: true, // 允许跨域
        rewrite: (path) => path.replace(/^\/api/, '/api'), // 重写路径（这里其实不需要改，保留即可）
      },
    },
  },
})