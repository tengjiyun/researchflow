// 展示单篇论文的信息,接收一个 paper 对象，字段与后端返回的 PaperSearchItem 对应
// 纯展示组件，不管理任何状态

function PaperCard({ paper }) {
    return (
      <div className="paper-card">
        {/* 论文标题 */}
        <h3 className="paper-card-title">{paper.title}</h3>
  
        {/* 作者列表，用逗号连接；如果没有作者则显示 Unknown authors */}
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
  
        {/* 摘要，如果存在才显示 */}
        {paper.abstract && (
          <p className="paper-card-abstract">{paper.abstract}</p>
        )}
  
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
      </div>
    )
  }
  
  export default PaperCard