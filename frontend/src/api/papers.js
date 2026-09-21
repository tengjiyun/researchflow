// papers.js 封装所有与“论文”相关的后端接口
// 组件只调用这里的函数，不直接使用 axios
// 好处：接口路径或参数有变化时，只改这里

import client from './client'

/**
 * 搜索学术论文
 * 对应后端接口：GET /api/papers/search
 *
 * @param {string} query - 搜索关键词
 * @param {number} page - 页码，从 1 开始，默认 1
 * @returns {Promise<{papers: Array, page: number, has_more: boolean}>}
 */
export async function searchPapers(query, page = 1) {
  const response = await client.get('/papers/search', {
    params: {
      q: query,
      page: page,
    },
  })
  return response.data
}