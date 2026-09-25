// LibraryPage.jsx 展示已保存的论文列表
// 功能：
//   - 页面加载时拉取已保存论文
//   - 每篇论文可以删除（带确认弹窗）
//   - 处理加载中 / 空状态 / 错误

import { useState, useEffect } from 'react'
import { listSavedPapers, deletePaper } from '../api/papers'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

function LibraryPage() {
  const [papers, setPapers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  // 正在删除中的论文 id（用于禁用按钮、显示 Deleting...）
  const [deletingId, setDeletingId] = useState(null)

  // 拉取已保存论文列表
  const loadLibrary = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await listSavedPapers()
      setPapers(result.papers)
    } catch (err) {
      const message =
        err.response?.data?.error?.message ||
        'Failed to load your library. Please try again.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  // 首次进入页面时加载
  useEffect(() => {
    loadLibrary()
  }, [])

  // 删除单篇论文
  const handleDelete = async (paperId) => {
    // 删除是不可逆操作，先弹确认框
    const confirmed = window.confirm(
      'Are you sure you want to remove this paper from your library?'
    )
    if (!confirmed) return

    setDeletingId(paperId)
    setError(null)

    try {
      await deletePaper(paperId)
      // 删除成功后从本地列表中过滤掉这条
      setPapers((prev) => prev.filter((paper) => paper.id !== paperId))
    } catch (err) {
      const message =
        err.response?.data?.error?.message ||
        'Failed to delete this paper. Please try again.'
      setError(message)
    } finally {
      setDeletingId(null)
    }
  }

  // 加载中：显示 loading
  if (loading) {
    return (
      <div className="library-page">
        <h2>My Research Library</h2>
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className="library-page">
      <h2>My Research Library</h2>

      {/* 错误提示 */}
      {error && <ErrorMessage message={error} />}

      {/* 空状态 */}
      {!error && papers.length === 0 && (
        <div className="empty-state">
          <p>No saved papers yet. Search and save papers to see them here.</p>
        </div>
      )}

      {/* 论文列表 */}
      {!error && papers.length > 0 && (
        <div className="library-list">
          <p className="library-count">{papers.length} saved papers</p>

          {papers.map((paper) => (
            <div key={paper.id} className="library-item">
              <div className="library-item-info">
                <h3 className="library-item-title">{paper.title}</h3>
                <div className="library-item-meta">
                  {paper.publication_year && (
                    <span>Year: {paper.publication_year}</span>
                  )}
                  {paper.venue && <span>Venue: {paper.venue}</span>}
                  {/* document_status 是后端返回的文档处理状态，可能为 null */}
                  {paper.document_status && (
                    <span>Document: {paper.document_status}</span>
                  )}
                </div>
              </div>

              <button
                type="button"
                className="library-item-delete"
                onClick={() => handleDelete(paper.id)}
                disabled={deletingId === paper.id}
              >
                {deletingId === paper.id ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default LibraryPage