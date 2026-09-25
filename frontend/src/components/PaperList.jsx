// PaperList 负责遍历论文数组并渲染多个 PaperCard
// 同时把保存相关的状态和回调透传给 PaperCard

import PaperCard from './PaperCard'

function PaperList({ papers, savedIds, savingId, onSave }) {
  // 空数组或未定义时直接返回 null
  if (!papers || papers.length === 0) {
    return null
  }

  return (
    <div className="paper-list">
      {papers.map((paper) => (
        // 使用 openalex_id 作为 key，保证列表渲染的稳定性
        <PaperCard
          key={paper.openalex_id}
          paper={paper}
          isSaved={savedIds?.has(paper.openalex_id)}
          isSaving={savingId === paper.openalex_id}
          onSave={onSave}
        />
      ))}
    </div>
  )
}

export default PaperList