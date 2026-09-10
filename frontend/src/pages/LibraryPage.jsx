// 资料库页面的骨架,暂时只展示标题和占位内容
// 等后端实现保存接口后，再补充：展示已保存论文、删除、筛选等功能

function LibraryPage() {
    return (
      <div className="library-page">
        <h2>My Research Library</h2>
  
        <div className="library-content">
          {/* TODO: 展示已保存的论文列表 */}
          <p>No saved papers yet.</p>
        </div>
      </div>
    )
  }
  
  export default LibraryPage