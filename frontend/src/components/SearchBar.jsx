// 搜索输入组件收集用户输入，并通过 onSearch 回调把关键词传给父组件
// 自身不处理搜索结果，保持职责单一

import { useState } from 'react'

function SearchBar({ onSearch, disabled }) {
  // 用本地 state 保存用户当前输入的关键词
  const [query, setQuery] = useState('')

  // 表单提交时触发
  const handleSubmit = (e) => {
    e.preventDefault()  // 阻止表单默认刷新页面的行为
    const trimmed = query.trim()
    if (!trimmed) return  // 空字符串直接忽略
    onSearch(trimmed)     // 把关键词传给父组件处理
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <input
        type="text"
        id="paper-search-input"
        name="paper-search"
        className="search-bar-input"
        placeholder="Search for academic papers..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        disabled={disabled}  // 搜索中时禁用输入，避免重复提交
      />
      <button type="submit" className="search-bar-button" disabled={disabled}>
        Search
      </button>
    </form>
  )
}

export default SearchBar