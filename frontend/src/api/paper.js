/**
 * 删除已保存的论文
 * 对应后端接口：DELETE /api/papers/{paper_id}
 *
 * @param {number} paperId - 资料库中的论文 ID
 * @returns {Promise<void>} 后端返回 204，无 body
 */
export async function deletePaper(paperId) {
    await client.delete(`/papers/${paperId}`)
  }