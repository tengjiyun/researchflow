// PaperDetailPage.jsx 展示单篇已保存论文的完整信息，并支持 PDF 处理流程
//
// 完整流程：
//   1. 加载论文详情（含已有的 documents）
//   2. 如果没有 document，显示 "Find PDF Sources" 按钮
//   3. 查出可用源后，用户选择一个 → POST 创建 document
//   4. 开始轮询 document 状态，直到 completed 或 failed
//   5. 解析完成后，加载 sections 并在页面上展示，可展开查看 chunks
//
// 状态机：
//   pending / processing → 轮询中
//   completed            → 加载 sections
//   failed               → 显示 Retry 按钮

import { useState, useEffect } from 'react'
import { getSavedPaper } from '../api/papers'
import {
  getFullTextSources,
  startDocumentProcessing,
  getDocumentStatus,
  retryDocument,
  getDocumentSections,
  getSectionChunks,
} from '../api/documents'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

// 轮询间隔：2 秒
const POLL_INTERVAL_MS = 2000

function PaperDetailPage({ paperId, onBack }) {
  // ---------- 论文基本信息 ----------
  const [paper, setPaper] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // ---------- PDF 源查找 ----------
  const [sources, setSources] = useState(null) // null = 还没查过
  const [loadingSources, setLoadingSources] = useState(false)
  const [sourceError, setSourceError] = useState(null)
  const [starting, setStarting] = useState(false)

  // ---------- 当前活跃的 document ----------
  const [activeDocumentId, setActiveDocumentId] = useState(null)
  const [activeDocument, setActiveDocument] = useState(null)
  const [polling, setPolling] = useState(false)
  const [processingError, setProcessingError] = useState(null)

  // ---------- 解析结果：章节与 chunks ----------
  const [sections, setSections] = useState([])
  const [chunksBySection, setChunksBySection] = useState({})
  const [expandedSectionId, setExpandedSectionId] = useState(null)
  const [loadingChunksFor, setLoadingChunksFor] = useState(null)

  // ---------- Effect 1：加载论文详情 ----------
  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const result = await getSavedPaper(paperId)
        setPaper(result)
      } catch (err) {
        setError(
          err.response?.data?.error?.message ||
            'Failed to load paper details. Please try again.'
        )
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [paperId])

  // ---------- Effect 2：论文加载后，检查是否已有 document ----------
  // 如果已有的 document 已经完成/失败，直接拉一次完整状态；否则开始轮询
  useEffect(() => {
    if (!paper || !paper.documents || paper.documents.length === 0) return
    const latest = paper.documents[0]
    setActiveDocumentId(latest.id)

    const isFinished =
      latest.parsing_status === 'completed' ||
      latest.retrieval_status === 'failed' ||
      latest.parsing_status === 'failed'

    if (isFinished) {
      getDocumentStatus(latest.id)
        .then((doc) => {
          setActiveDocument(doc)
          if (doc.parsing_status === 'completed') {
            loadParsedContent(doc.id)
          }
        })
        .catch(() => {})
    } else {
      setPolling(true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paper])

  // ---------- Effect 3：轮询 document 状态 ----------
  // 使用递归 setTimeout 而非 setInterval，避免请求堆积
  useEffect(() => {
    if (!activeDocumentId || !polling) return
    let cancelled = false
    let timer = null

    const poll = async () => {
      try {
        const updated = await getDocumentStatus(activeDocumentId)
        if (cancelled) return
        setActiveDocument(updated)

        if (updated.parsing_status === 'completed') {
          setPolling(false)
          loadParsedContent(activeDocumentId)
        } else if (
          updated.retrieval_status === 'failed' ||
          updated.parsing_status === 'failed'
        ) {
          setPolling(false)
        } else {
          timer = setTimeout(poll, POLL_INTERVAL_MS)
        }
      } catch (err) {
        // 网络临时出错，等更长时间再试，不打断轮询
        if (!cancelled) {
          timer = setTimeout(poll, POLL_INTERVAL_MS * 2)
        }
      }
    }

    timer = setTimeout(poll, POLL_INTERVAL_MS)

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [activeDocumentId, polling])

  // ---------- 加载解析后的章节 ----------
  const loadParsedContent = async (documentId) => {
    try {
      const list = await getDocumentSections(documentId)
      setSections(list)
    } catch (err) {
      console.warn('Failed to load sections:', err)
    }
  }

  // ---------- 事件：查找 PDF 源 ----------
  const handleFindSources = async () => {
    setLoadingSources(true)
    setSourceError(null)
    try {
      const list = await getFullTextSources(paperId)
      setSources(list)
    } catch (err) {
      setSourceError(
        err.response?.data?.error?.message ||
          'Failed to find full-text sources. Please try again.'
      )
    } finally {
      setLoadingSources(false)
    }
  }

  // ---------- 事件：开始处理某个源 ----------
  const handleStartProcessing = async (sourceUrl) => {
    setStarting(true)
    setProcessingError(null)
    try {
      const doc = await startDocumentProcessing(paperId, sourceUrl)
      setActiveDocumentId(doc.id)
      setActiveDocument(doc)
      setPolling(true)
      setSources(null) // 清空源列表，切换到处理视图
    } catch (err) {
      setProcessingError(
        err.response?.data?.error?.message ||
          'Failed to start document processing. Please try again.'
      )
    } finally {
      setStarting(false)
    }
  }

  // ---------- 事件：重试失败的 document ----------
  const handleRetry = async () => {
    if (!activeDocumentId) return
    setProcessingError(null)
    try {
      const doc = await retryDocument(activeDocumentId)
      setActiveDocument(doc)
      setPolling(true)
    } catch (err) {
      setProcessingError(
        err.response?.data?.error?.message ||
          'Failed to retry processing. Please try again.'
      )
    }
  }

  // ---------- 事件：展开某个章节，加载其 chunks ----------
  const handleToggleSection = async (sectionId) => {
    // 已展开则收起
    if (expandedSectionId === sectionId) {
      setExpandedSectionId(null)
      return
    }
    setExpandedSectionId(sectionId)

    // 已经加载过就跳过
    if (chunksBySection[sectionId]) return

    setLoadingChunksFor(sectionId)
    try {
      const list = await getSectionChunks(sectionId)
      setChunksBySection((prev) => ({ ...prev, [sectionId]: list }))
    } catch (err) {
      console.warn('Failed to load chunks:', err)
    } finally {
      setLoadingChunksFor(null)
    }
  }

  // ---------- 早期返回：加载中 / 错误 ----------
  if (loading) {
    return (
      <div className="paper-detail-page">
        <button type="button" className="back-button" onClick={onBack}>
          ← Back to Library
        </button>
        <LoadingSpinner />
      </div>
    )
  }
  if (error) {
    return (
      <div className="paper-detail-page">
        <button type="button" className="back-button" onClick={onBack}>
          ← Back to Library
        </button>
        <ErrorMessage message={error} />
      </div>
    )
  }
  if (!paper) return null

  // ---------- 派生状态 ----------
  const isProcessing =
    activeDocument &&
    (activeDocument.retrieval_status === 'pending' ||
      activeDocument.retrieval_status === 'processing' ||
      activeDocument.parsing_status === 'pending' ||
      activeDocument.parsing_status === 'processing')

  const isFailed =
    activeDocument &&
    (activeDocument.retrieval_status === 'failed' ||
      activeDocument.parsing_status === 'failed')

  const isCompleted = activeDocument?.parsing_status === 'completed'

  return (
    <div className="paper-detail-page">
      {/* 返回按钮 */}
      <button type="button" className="back-button" onClick={onBack}>
        ← Back to Library
      </button>

      <article className="paper-detail">
        {/* 标题 */}
        <h2 className="paper-detail-title">{paper.title}</h2>

        {/* 作者 */}
        <p className="paper-detail-authors">
          {paper.authors && paper.authors.length > 0
            ? paper.authors.join(', ')
            : 'Unknown authors'}
        </p>

        {/* 元信息 */}
        <div className="paper-detail-meta">
          {paper.publication_year && <span>Year: {paper.publication_year}</span>}
          {paper.venue && <span>Venue: {paper.venue}</span>}
          {paper.citation_count !== undefined && (
            <span>Citations: {paper.citation_count}</span>
          )}
        </div>

        {/* 外部链接 */}
        <div className="paper-detail-links">
          {paper.doi && (
            <a href={paper.doi} target="_blank" rel="noopener noreferrer">
              DOI
            </a>
          )}
          {paper.landing_page_url && (
            <a
              href={paper.landing_page_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              View Paper
            </a>
          )}
        </div>

        {/* 摘要 */}
        {paper.abstract && (
          <section className="paper-detail-section">
            <h3>Abstract</h3>
            <p>{paper.abstract}</p>
          </section>
        )}

        {/* ---------- Full-Text Documents 区块 ---------- */}
        <section className="paper-detail-section">
          <h3>Full-Text Documents</h3>

          {processingError && <ErrorMessage message={processingError} />}

          {/* 情况 1：还没查过源，也没有 document → 显示按钮 */}
          {!activeDocument && !sources && (
            <div className="document-actions">
              <p className="empty-hint">No full-text document attached yet.</p>
              <button
                type="button"
                className="find-sources-button"
                onClick={handleFindSources}
                disabled={loadingSources}
              >
                {loadingSources ? 'Searching...' : 'Find PDF Sources'}
              </button>
            </div>
          )}

          {/* 情况 2：正在查源 */}
          {loadingSources && <LoadingSpinner />}

          {/* 情况 3：查源失败 */}
          {sourceError && <ErrorMessage message={sourceError} />}

          {/* 情况 4：源列表已返回 */}
          {sources && (
            <div className="source-list">
              {sources.length === 0 && (
                <p className="empty-hint">
                  No open-access PDF sources were found for this paper.
                </p>
              )}
              {sources.length > 0 && (
                <>
                  <p>Choose a source to start PDF processing:</p>
                  <ul>
                    {sources.map((source) => (
                      <li key={source.source_url} className="source-item">
                        <a
                          href={source.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {source.source_url}
                        </a>
                        {source.licence && (
                          <span className="source-licence">
                            Licence: {source.licence}
                          </span>
                        )}
                        <button
                          type="button"
                          className="start-button"
                          onClick={() => handleStartProcessing(source.source_url)}
                          disabled={starting}
                        >
                          {starting ? 'Starting...' : 'Start Processing'}
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}

          {/* 情况 5：有活跃 document，展示状态 */}
          {activeDocument && (
            <div className="document-status">
              <p>
                <strong>Document #{activeDocument.id}</strong>
              </p>
              <ul>
                <li>Retrieval: {activeDocument.retrieval_status}</li>
                <li>Parsing: {activeDocument.parsing_status}</li>
                {activeDocument.page_count != null && (
                  <li>Pages: {activeDocument.page_count}</li>
                )}
                {activeDocument.file_size_bytes != null && (
                  <li>
                    Size: {Math.round(activeDocument.file_size_bytes / 1024)} KB
                  </li>
                )}
                {activeDocument.error_message && (
                  <li className="error-line">
                    Error: {activeDocument.error_code} —{' '}
                    {activeDocument.error_message}
                  </li>
                )}
              </ul>

              {isProcessing && <p className="processing-hint">Processing…</p>}

              {isFailed && (
                <button
                  type="button"
                  className="retry-button"
                  onClick={handleRetry}
                >
                  Retry Processing
                </button>
              )}
            </div>
          )}

          {/* 情况 6：解析完成 → 展示章节列表 */}
          {isCompleted && sections.length > 0 && (
            <div className="sections-block">
              <h4>Extracted Sections ({sections.length})</h4>
              <ul className="section-list">
                {sections.map((section) => (
                  <li key={section.id} className="section-item">
                    <button
                      type="button"
                      className="section-toggle"
                      onClick={() => handleToggleSection(section.id)}
                    >
                      <span className="section-type">
                        {section.section_type}
                      </span>
                      {section.original_heading && (
                        <span className="section-heading">
                          {section.original_heading}
                        </span>
                      )}
                      <span className="section-pages">
                        p.{section.start_page}
                        {section.end_page !== section.start_page
                          ? `–${section.end_page}`
                          : ''}
                      </span>
                      <span className="section-expand">
                        {expandedSectionId === section.id ? '▼' : '▶'}
                      </span>
                    </button>

                    {expandedSectionId === section.id && (
                      <div className="section-chunks">
                        {loadingChunksFor === section.id && <LoadingSpinner />}
                        {chunksBySection[section.id]?.map((chunk) => (
                          <div key={chunk.id} className="chunk-item">
                            <div className="chunk-meta">
                              Chunk #{chunk.sequence_number} (p.
                              {chunk.start_page})
                            </div>
                            <p className="chunk-text">{chunk.source_text}</p>
                          </div>
                        ))}
                        {chunksBySection[section.id]?.length === 0 && (
                          <p className="empty-hint">
                            No chunks in this section.
                          </p>
                        )}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </article>
    </div>
  )
}

export default PaperDetailPage