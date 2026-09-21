// client.js 创建并导出一个统一的 axios 实例
// 所有对后端的请求都通过它发出，好处是：
//   1. 统一管理 baseURL（现在用 Vite 代理转发到后端）
//   2. 统一设置超时、请求头等
//   3. 后续要加拦截器（如自动加 token）时只改这一处

import axios from 'axios'

const client = axios.create({
  // 因为 vite.config.js 里配置了 /api 代理到后端 8000 端口
  // 所以这里只要用相对路径 /api 即可
  baseURL: '/api',
  timeout: 15000,  // 15 秒超时
  headers: {
    'Content-Type': 'application/json',
  },
})

export default client