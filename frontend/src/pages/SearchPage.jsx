// SearchPage.jsx 是搜索页面的核心组件
// 负责组合 SearchBar / PaperList / LoadingSpinner / ErrorMessage
// 并管理以下状态：
//   - papers：搜索结果列表
//   - loading：是否正在搜索
//   - error：搜索错误信息
//   - hasSearched：是否已经搜索过（区分初始状态和空结果）
//   - savedIds：已保存论文的 openalex_id 集合（用于显示 Saved 状态）
//   - savingId：正在保存中的论文 openalex_id
//   - saveError：保存失败时的错误信息

import { useState, useEffect } from 'react'
import SearchBar from '../components/SearchBar'
import PaperList from '../components/PaperList'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import { searchPapers, savePaper, listSavedPapers } from '../api/papers'

function SearchPage() {
  const [papers, setPapers] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [hasSearched, setHasSearched] = useState(false)

  // 保存相关的状态
  const [savedIds, setSavedIds] = useState(new Set())
  const [savingId, setSavingId] = useState(null)
  const [saveError, setSaveError] = useState(null)

  // 页面首次加载时，拉取已保存论文列表，建立 savedIds 集合
  // 这样如果用户搜索到已经保存过的论文，按钮会直接显示为 Saved
  useEffect(() => {
    async function loadSaved() {
      try {
        const result = await listSavedPapers()
        const ids = new Set(result.papers.map((paper) => paper.openalex_id))
        setSavedIds(ids)
      } catch (err) {
        // 这里只警告，不打断页面，避免因为后端临时不可用导致整个页面崩溃
        console.warn('Failed to load saved papers:', err)
      }
    }
    loadSaved()
  }, [])

  // 搜索处理
  const handleSearch = async (query) => {
    setLoading(true)
    setError(null)
    setHasSearched(true)

    try {
      const result = await searchPapers(query, 1)
      setPapers(result.papers)
    } catch (err) {
      const message =
        err.response?.data?.error?.message ||
        'Failed to search papers. Please try again.'
      setError(message)
      setPapers([])
    } finally {
      setLoading(false)
    }
  }

  // 保存处理
  const handleSave = async (paper) => {
    setSavingId(paper.openalex_id)
    setSaveError(null)

    try {
      await savePaper(paper)
      // 保存成功，把 openalex_id 加入已保存集合
      setSavedIds((prev) => new Set(prev).add(paper.openalex_id))
    } catch (err) {
      const status = err.response?.status
      if (status === 409) {
        // 409 说明论文已经在资料库中，视同已保存
        setSavedIds((prev) => new Set(prev).add(paper.openalex_id))
      } else {
        const message =
          err.response?.data?.error?.message ||
          'Failed to save this paper. Please try again.'
        setSaveError(message)
      }
    } finally {
      setSavingId(null)
    }
  }

  return (
    <div className="search-page">
      {/* 搜索框 */}
      <SearchBar onSearch={handleSearch} disabled={loading} />

      {/* 搜索加载状态 */}
      {loading && <LoadingSpinner />}

      {/* 搜索错误 */}
      {!loading && error && <ErrorMessage message={error} />}

      {/* 保存错误 */}
      {!loading && !error && saveError && <ErrorMessage message={saveError} />}

      {/* 空结果提示 */}
      {!loading && !error && hasSearched && papers.length === 0 && (
        <div className="empty-state">
          <p>No papers found. Try a different search term.</p>
        </div>
      )}

      {/* 结果列表 */}
      {!loading && !error && papers.length > 0 && (
        <PaperList
          papers={papers}
          savedIds={savedIds}
          savingId={savingId}
          onSave={handleSave}
        />
      )}
    </div>
  )
}

export default SearchPage