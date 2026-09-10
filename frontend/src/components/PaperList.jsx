// 遍历论文数组并渲染多个 PaperCard
// 如果数组为空，则不渲染任何内容

import PaperCard from './PaperCard'

function PaperList({ papers }) {
  // 空数组或未定义时直接返回 null
  if (!papers || papers.length === 0) {
    return null
  }

  return (
    <div className="paper-list">
      {papers.map((paper) => (
        // 使用 openalex_id 作为 key，保证列表渲染的稳定性
        <PaperCard key={paper.openalex_id} paper={paper} />
      ))}
    </div>
  )
}

export default PaperList