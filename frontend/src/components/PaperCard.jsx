// PaperCard.jsx 用于展示单篇论文的信息
// 接收一个 paper 对象，字段与后端返回的 PaperSearchItem 对应
// 保存相关的三个属性：
//   - isSaved：是否已保存（true 时按钮禁用并显示 Saved）
//   - isSaving：是否正在保存中（true 时显示 Saving...）
//   - onSave：点击保存按钮时的回调，会把当前 paper 对象传出去

function PaperCard({ paper, isSaved, isSaving, onSave }) {
  // 根据状态决定按钮文案
  const buttonText = isSaved ? 'Saved' : isSaving ? 'Saving...' : 'Save'

  return (
    <div className="paper-card">
      {/* 论文标题 */}
      <h3 className="paper-card-title">{paper.title}</h3>

      {/* 作者列表，用逗号连接；没有作者时显示 Unknown authors */}
      <p className="paper-card-authors">
        {paper.authors && paper.authors.length > 0
          ? paper.authors.join(', ')
          : 'Unknown authors'}
      </p>

      {/* 元信息：年份、期刊、引用次数 */}
      <div className="paper-card-meta">
        {paper.publication_year && <span>Year: {paper.publication_year}</span>}
        {paper.venue && <span>Venue: {paper.venue}</span>}
        {paper.citation_count !== undefined && (
          <span>Citations: {paper.citation_count}</span>
        )}
      </div>

      {/* 摘要（若存在才显示） */}
      {paper.abstract && <p className="paper-card-abstract">{paper.abstract}</p>}

      {/* 外部链接：DOI 和原文链接 */}
      <div className="paper-card-links">
        {paper.doi && (
          <a href={paper.doi} target="_blank" rel="noopener noreferrer">
            DOI
          </a>
        )}
        {paper.landing_page_url && (
          <a href={paper.landing_page_url} target="_blank" rel="noopener noreferrer">
            View Paper
          </a>
        )}
      </div>

      {/* 操作区：保存按钮 */}
      <div className="paper-card-actions">
        <button
          type="button"
          className="paper-card-save-button"
          onClick={() => onSave(paper)}
          disabled={isSaved || isSaving}
        >
          {buttonText}
        </button>
      </div>
    </div>
  )
}

export default PaperCard