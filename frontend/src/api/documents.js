// documents.js 封装所有与"论文文档"相关的后端接口
// 包括：查找 PDF 源、启动处理、查询状态、重试、读取章节与 chunks

import client from './client'

/**
 * 查找某篇论文可用的开放获取 PDF 源
 * 对应后端接口：GET /api/papers/{paper_id}/full-text-sources
 *
 * @param {number} paperId
 * @returns {Promise<Array<{source_url, source_format, access_type, licence}>>}
 */
export async function getFullTextSources(paperId) {
  const response = await client.get(`/papers/${paperId}/full-text-sources`)
  return response.data.sources
}

/**
 * 启动某篇论文的 PDF 下载 + 解析
 * 对应后端接口：POST /api/papers/{paper_id}/documents
 * 后端返回 202，异步在后台处理，需要轮询状态
 *
 * @param {number} paperId
 * @param {string} sourceUrl - 必须是后端返回的源之一
 * @returns {Promise<object>} document 状态对象
 */
export async function startDocumentProcessing(paperId, sourceUrl) {
  const response = await client.post(`/papers/${paperId}/documents`, {
    source_url: sourceUrl,
  })
  return response.data
}

/**
 * 查询某个 document 的处理状态
 * 对应后端接口：GET /api/documents/{document_id}
 *
 * @param {number} documentId
 * @returns {Promise<object>}
 */
export async function getDocumentStatus(documentId) {
  const response = await client.get(`/documents/${documentId}`)
  return response.data
}

/**
 * 重试失败的 document 处理
 * 对应后端接口：POST /api/documents/{document_id}/retry
 *
 * @param {number} documentId
 * @returns {Promise<object>}
 */
export async function retryDocument(documentId) {
  const response = await client.post(`/documents/${documentId}/retry`)
  return response.data
}

/**
 * 获取某个 document 的章节列表
 * 对应后端接口：GET /api/documents/{document_id}/sections
 * 需要 parsing_status === 'completed' 才能调用，否则后端返回 409
 *
 * @param {number} documentId
 * @returns {Promise<Array>}
 */
export async function getDocumentSections(documentId) {
  const response = await client.get(`/documents/${documentId}/sections`)
  return response.data.sections
}

/**
 * 获取某个 section 的所有 chunks（原文片段）
 * 对应后端接口：GET /api/sections/{section_id}/chunks
 *
 * @param {number} sectionId
 * @returns {Promise<Array>}
 */
export async function getSectionChunks(sectionId) {
  const response = await client.get(`/sections/${sectionId}/chunks`)
  return response.data.chunks
}

/**
 * 手动上传 PDF 到某篇已保存论文
 * 对应后端接口：POST /api/papers/{paper_id}/documents/upload
 *
 * @param {number} paperId
 * @param {File} file - 浏览器 File 对象（来自 <input type="file">）
 * @returns {Promise<object>} 新建的 document 状态对象
 */
export async function uploadDocument(paperId, file) {
  // 用 FormData 构造 multipart/form-data 请求体
  const formData = new FormData()
  formData.append('file', file)
  // 后端要求 confirmed=true，表示用户确认该 PDF 属于这篇论文
  formData.append('confirmed', 'true')

  const response = await client.post(
    `/papers/${paperId}/documents/upload`,
    formData,
    {
      // 让浏览器自动设置 multipart boundary，不要手动设置 Content-Type
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  )
  return response.data
}