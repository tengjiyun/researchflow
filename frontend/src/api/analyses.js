// analyses.js 封装全文分析相关的后端接口
// 包括：启动分析、查询状态、列历史、重试、列 findings、查 finding 详情

import client from './client'

/**
 * 启动某篇 document 的全文分析
 * 对应后端接口：POST /api/documents/{document_id}/analyses
 *
 * @param {number} documentId
 * @returns {Promise<object>} AnalysisStatus
 */
export async function startAnalysis(documentId) {
  const response = await client.post(`/documents/${documentId}/analyses`, {
    analysis_version: 'full-text-v1',
  })
  return response.data
}

/**
 * 查询某次分析的状态
 * 对应后端接口：GET /api/analyses/{analysis_id}
 *
 * @param {number} analysisId
 * @returns {Promise<object>} AnalysisStatus
 */
export async function getAnalysisStatus(analysisId) {
  const response = await client.get(`/analyses/${analysisId}`)
  return response.data
}

/**
 * 列出某篇 document 的所有分析记录（含历史）
 * 对应后端接口：GET /api/documents/{document_id}/analyses
 *
 * @param {number} documentId
 * @param {number} page
 * @param {number} pageSize
 * @returns {Promise<{analyses: Array, page: number, page_size: number, has_more: boolean}>}
 */
export async function listDocumentAnalyses(documentId, page = 1, pageSize = 20) {
  const response = await client.get(`/documents/${documentId}/analyses`, {
    params: { page, page_size: pageSize },
  })
  return response.data
}

/**
 * 重试失败的分析
 * 对应后端接口：POST /api/analyses/{analysis_id}/retry
 *
 * @param {number} analysisId
 * @returns {Promise<object>} AnalysisStatus
 */
export async function retryAnalysis(analysisId) {
  const response = await client.post(`/analyses/${analysisId}/retry`)
  return response.data
}

/**
 * 列出某次分析的所有 findings
 * 对应后端接口：GET /api/analyses/{analysis_id}/findings
 *
 * @param {number} analysisId
 * @param {string|null} findingType - 可选过滤，如 'methodology'
 * @returns {Promise<Array>} FindingSummary 数组
 */
export async function listFindings(analysisId, findingType = null) {
  const response = await client.get(`/analyses/${analysisId}/findings`, {
    params: findingType ? { finding_type: findingType } : {},
  })
  return response.data.findings
}

/**
 * 获取单条 finding 的完整信息（含 evidence 原文引用）
 * 对应后端接口：GET /api/findings/{finding_id}
 *
 * @param {number} findingId
 * @returns {Promise<object>} FindingDetail
 */
export async function getFinding(findingId) {
  const response = await client.get(`/findings/${findingId}`)
  return response.data
}