// CollectionsPanel.jsx 管理所有集合（分组）
// 用于 LibraryPage 顶部，提供：
//   - 展示所有集合及论文数
//   - 创建新集合
//   - 重命名 / 删除集合
//
// 说明：本组件只管理集合本身，不负责"按集合筛选论文"
// （筛选功能需要配合 library query 增强，另一步实现）

import { useState, useEffect } from 'react'
import {
  listCollections,
  createCollection,
  renameCollection,
  deleteCollection,
} from '../api/collections'
import LoadingSpinner from './LoadingSpinner'
import ErrorMessage from './ErrorMessage'

function CollectionsPanel() {
  const [collections, setCollections] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // 新建集合
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)

  // 正在重命名 / 删除的集合 id
  const [busyId, setBusyId] = useState(null)

  // 是否展开列表
  const [expanded, setExpanded] = useState(true)

  // ---------- 加载集合列表 ----------
  const loadCollections = async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await listCollections()
      setCollections(list)
    } catch (err) {
      setError(
        err.response?.data?.error?.message ||
          'Failed to load collections. Please try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCollections()
  }, [])

  // ---------- 创建集合 ----------
  const handleCreate = async (e) => {
    e.preventDefault()
    const name = newName.trim()
    if (!name) return

    setCreating(true)
    setError(null)
    try {
      await createCollection(name)
      setNewName('')
      await loadCollections()
    } catch (err) {
      // 后端可能返回 409（重名）
      setError(
        err.response?.data?.error?.message ||
          'Failed to create the collection. Please try again.'
      )
    } finally {
      setCreating(false)
    }
  }

  // ---------- 重命名 ----------
  const handleRename = async (collection) => {
    // 用 prompt 简化交互；CSS 阶段可以换成 inline 编辑
    const newValue = window.prompt('Rename collection:', collection.name)
    if (newValue === null) return
    const trimmed = newValue.trim()
    if (!trimmed || trimmed === collection.name) return

    setBusyId(collection.id)
    setError(null)
    try {
      await renameCollection(collection.id, trimmed)
      await loadCollections()
    } catch (err) {
      setError(
        err.response?.data?.error?.message ||
          'Failed to rename the collection. Please try again.'
      )
    } finally {
      setBusyId(null)
    }
  }

  // ---------- 删除 ----------
  const handleDelete = async (collection) => {
    const confirmed = window.confirm(
      `Delete collection "${collection.name}"? Papers inside will not be deleted.`
    )
    if (!confirmed) return

    setBusyId(collection.id)
    setError(null)
    try {
      await deleteCollection(collection.id)
      await loadCollections()
    } catch (err) {
      setError(
        err.response?.data?.error?.message ||
          'Failed to delete the collection. Please try again.'
      )
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section className="collections-panel">
      <div className="collections-header">
        <h3>Collections</h3>
        <button
          type="button"
          className="toggle-button"
          onClick={() => setExpanded((prev) => !prev)}
        >
          {expanded ? 'Hide' : 'Show'}
        </button>
      </div>

      {!expanded && collections.length > 0 && (
        <p className="collections-summary">
          {collections.length} collection
          {collections.length !== 1 ? 's' : ''}
        </p>
      )}

      {expanded && (
        <>
          {/* 创建新集合 */}
          <form className="collection-create-form" onSubmit={handleCreate}>
            <input
              type="text"
              className="collection-input"
              placeholder="New collection name..."
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              disabled={creating}
              maxLength={100}
            />
            <button
              type="submit"
              className="collection-create-button"
              disabled={creating || !newName.trim()}
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
          </form>

          {error && <ErrorMessage message={error} />}

          {loading && <LoadingSpinner />}

          {!loading && collections.length === 0 && (
            <p className="empty-hint">
              No collections yet. Create one to organise your papers.
            </p>
          )}

          {!loading && collections.length > 0 && (
            <ul className="collection-list">
              {collections.map((collection) => (
                <li key={collection.id} className="collection-item">
                  <span className="collection-name">
                    {collection.name}
                  </span>
                  <span className="collection-count">
                    {collection.paper_count} paper
                    {collection.paper_count !== 1 ? 's' : ''}
                  </span>
                  <button
                    type="button"
                    className="collection-rename"
                    onClick={() => handleRename(collection)}
                    disabled={busyId === collection.id}
                  >
                    Rename
                  </button>
                  <button
                    type="button"
                    className="collection-delete"
                    onClick={() => handleDelete(collection)}
                    disabled={busyId === collection.id}
                  >
                    {busyId === collection.id ? 'Working...' : 'Delete'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  )
}

export default CollectionsPanel