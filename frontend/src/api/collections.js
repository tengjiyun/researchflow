// collections.js 封装集合（分组）相关的后端接口

import client from './client'

/**
 * 列出所有集合
 * 对应后端接口：GET /api/collections
 *
 * @returns {Promise<Array<{id, name, paper_count, created_at, updated_at}>>}
 */
export async function listCollections() {
  const response = await client.get('/collections')
  return response.data.collections
}

/**
 * 创建新集合
 * 对应后端接口：POST /api/collections
 *
 * @param {string} name
 * @returns {Promise<object>} Collection
 */
export async function createCollection(name) {
  const response = await client.post('/collections', { name })
  return response.data
}

/**
 * 重命名集合
 * 对应后端接口：PATCH /api/collections/{id}
 *
 * @param {number} collectionId
 * @param {string} name
 * @returns {Promise<object>} Collection
 */
export async function renameCollection(collectionId, name) {
  const response = await client.patch(`/collections/${collectionId}`, { name })
  return response.data
}

/**
 * 删除集合（不影响论文本身，只删除分组）
 * 对应后端接口：DELETE /api/collections/{id}
 *
 * @param {number} collectionId
 * @returns {Promise<void>}
 */
export async function deleteCollection(collectionId) {
  await client.delete(`/collections/${collectionId}`)
}

/**
 * 把论文加入集合（幂等，重复添加不会报错）
 * 对应后端接口：PUT /api/collections/{id}/papers/{paper_id}
 *
 * @param {number} collectionId
 * @param {number} paperId
 * @returns {Promise<void>}
 */
export async function addPaperToCollection(collectionId, paperId) {
  await client.put(`/collections/${collectionId}/papers/${paperId}`)
}

/**
 * 把论文从集合移除（幂等）
 * 对应后端接口：DELETE /api/collections/{id}/papers/{paper_id}
 *
 * @param {number} collectionId
 * @param {number} paperId
 * @returns {Promise<void>}
 */
export async function removePaperFromCollection(collectionId, paperId) {
  await client.delete(`/collections/${collectionId}/papers/${paperId}`)
}

/**
 * 查询某篇论文属于哪些集合
 * 对应后端接口：GET /api/papers/{paper_id}/collections
 *
 * @param {number} paperId
 * @returns {Promise<Array<object>>}
 */
export async function listPaperCollections(paperId) {
  const response = await client.get(`/papers/${paperId}/collections`)
  return response.data.collections
}