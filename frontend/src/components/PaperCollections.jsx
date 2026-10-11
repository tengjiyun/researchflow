// PaperCollections.jsx 用于 PaperDetailPage
// 展示这篇论文属于哪些集合，并允许勾选/取消勾选
//
// 交互：checkbox 列表
//   - 勾选：调用 addPaperToCollection
//   - 取消勾选：调用 removePaperFromCollection

import { useState, useEffect } from 'react'
import {
  listCollections,
  listPaperCollections,
  addPaperToCollection,
  removePaperFromCollection,
} from '../api/collections'
import LoadingSpinner from './LoadingSpinner'
import ErrorMessage from './ErrorMessage'

function PaperCollections({ paperId }) {
  // 所有可用集合
  const [allCollections, setAllCollections] = useState([])
  // 当前论文所属的集合 id Set
  const [memberIds, setMemberIds] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  // 正在处理的集合 id
  const [busyId, setBusyId] = useState(null)

  // ---------- 加载所有集合 + 该论文所属集合 ----------
  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [all, mine] = await Promise.all([
          listCollections(),
          listPaperCollections(paperId),
        ])
        setAllCollections(all)
        setMemberIds(new Set(mine.map((c) => c.id)))
      } catch (err) {
        setError(
          err.response?.data?.error?.message ||
            'Failed to load collections. Please try again.'
        )
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [paperId])

  // ---------- 切换勾选状态 ----------
  const handleToggle = async (collectionId, currentlyMember) => {
    setBusyId(collectionId)
    setError(null)
    try {
      if (currentlyMember) {
        await removePaperFromCollection(collectionId, paperId)
        setMemberIds((prev) => {
          const next = new Set(prev)
          next.delete(collectionId)
          return next
        })
      } else {
        await addPaperToCollection(collectionId, paperId)
        setMemberIds((prev) => new Set(prev).add(collectionId))
      }
    } catch (err) {
      setError(
        err.response?.data?.error?.message ||
          'Failed to update the collection. Please try again.'
      )
    } finally {
      setBusyId(null)
    }
  }

  if (loading) {
    return (
      <section className="paper-detail-section">
        <h3>Collections</h3>
        <LoadingSpinner />
      </section>
    )
  }

  return (
    <section className="paper-detail-section">
      <h3>Collections</h3>

      {error && <ErrorMessage message={error} />}

      {allCollections.length === 0 && (
        <p className="empty-hint">
          No collections yet. Create one from the Library page.
        </p>
      )}

      {allCollections.length > 0 && (
        <ul className="paper-collections-list">
          {allCollections.map((collection) => {
            const isMember = memberIds.has(collection.id)
            return (
              <li key={collection.id} className="paper-collection-item">
                <label>
                  <input
                    type="checkbox"
                    checked={isMember}
                    disabled={busyId === collection.id}
                    onChange={() => handleToggle(collection.id, isMember)}
                  />
                  <span className="paper-collection-name">
                    {collection.name}
                  </span>
                </label>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

export default PaperCollections