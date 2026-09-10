// 整体页面布局（标题 + 主内容区）
// 目前只渲染 SearchPage，后续可以加入导航或路由切换

import SearchPage from './pages/SearchPage'

function App() {
  return (
    <div className="app">
      {/* 页面顶部标题区域 */}
      <header className="app-header">
        <h1>ResearchFlow</h1>
        <p>AI-Assisted Research Information Management System</p>
      </header>

      {/* 页面主内容区域 */}
      <main className="app-main">
        <SearchPage />
      </main>
    </div>
  )
}

export default App