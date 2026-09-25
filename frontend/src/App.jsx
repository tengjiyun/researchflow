// App.jsx 是应用的根组件
// 负责整体布局（标题 + Tab 导航 + 主内容区）
// 用本地 state 在两个页面之间切换，不引入路由库

import { useState } from 'react'
import SearchPage from './pages/SearchPage'
import LibraryPage from './pages/LibraryPage'

function App() {
  // 当前激活的页面：'search' 或 'library'
  const [activeTab, setActiveTab] = useState('search')

  return (
    <div className="app">
      {/* 页面顶部标题区域 */}
      <header className="app-header">
        <h1>ResearchFlow</h1>
        <p>AI-Assisted Research Information Management System</p>
      </header>

      {/* Tab 导航 */}
      <nav className="app-tabs">
        <button
          type="button"
          className={activeTab === 'search' ? 'app-tab active' : 'app-tab'}
          onClick={() => setActiveTab('search')}
        >
          Search
        </button>
        <button
          type="button"
          className={activeTab === 'library' ? 'app-tab active' : 'app-tab'}
          onClick={() => setActiveTab('library')}
        >
          My Library
        </button>
      </nav>

      {/* 主内容区：根据 activeTab 渲染不同页面 */}
      <main className="app-main">
        {activeTab === 'search' ? <SearchPage /> : <LibraryPage />}
      </main>
    </div>
  )
}

export default App