// 搜索页面的核心组件,组合了 SearchBar、PaperList、LoadingSpinner 和 ErrorMessage
// 并负责管理以下状态：
//   - papers：搜索结果列表
//   - loading：是否正在加载
//   - error：错误信息
//   - hasSearched：是否已经执行过搜索（用于区分初始状态和空结果）

import { useState } from 'react'
import SearchBar from '../components/SearchBar'
import PaperList from '../components/PaperList'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

function SearchPage() {
  const [papers, setPapers] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [hasSearched, setHasSearched] = useState(false)

  // 当用户提交搜索时由 SearchBar 触发
  const handleSearch = async (query) => {
    console.log('Search triggered with query:', query)
    setLoading(true)
    setError(null)
    setHasSearched(true)

    try {
      // TODO: 后续替换为真实 API 调用
      // 现在先模拟一个空结果，确保页面结构能正常渲染
      // const result = await searchPapers(query, 1)
      // setPapers(result.papers)
      setPapers([])
    } catch (err) {
      setError('Failed to search papers. Please try again.')
      setPapers([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="search-page">
      {/* 搜索框 */}
      <SearchBar onSearch={handleSearch} disabled={loading} />

      {/* 加载状态 */}
      {loading && <LoadingSpinner />}

      {/* 错误提示 */}
      {!loading && error && <ErrorMessage message={error} />}

      {/* 空结果提示：只有在搜索过、无错误、无结果时才显示 */}
      {!loading && !error && hasSearched && papers.length === 0 && (
        <div className="empty-state">
          <p>No papers found. Try a different search term.</p>
        </div>
      )}

      {/* 结果列表 */}
      {!loading && !error && papers.length > 0 && (
        <PaperList papers={papers} />
      )}
    </div>
  )
}

export default SearchPage