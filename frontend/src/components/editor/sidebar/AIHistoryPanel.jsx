import React, { useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../../../api'

const PAGE_SIZE = 10

const ACTION_LABEL = {
  rewrite: 'Rewrite',
  summarize: 'Summarize',
  translate: 'Translate',
  restructure: 'Restructure',
  expand: 'Expand',
  grammar: 'Grammar',
}

const USER_ACTION_BADGE = {
  accepted: 'bg-green-100 text-green-700',
  edited:   'bg-blue-100 text-blue-700',
  rejected: 'bg-red-100 text-red-700',
  pending:  'bg-gray-100 text-gray-600',
}

function formatDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString()
  } catch (_) {
    return iso
  }
}

export default function AIHistoryPanel({ docId, enabled = true, refreshKey = 0 }) {
  const [entries, setEntries] = useState([])
  const [offset, setOffset] = useState(0)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadPage = useCallback(async (nextOffset, replace) => {
    if (!docId || !enabled) return
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch(
        `/documents/${docId}/ai/history?limit=${PAGE_SIZE}&offset=${nextOffset}`,
      )
      const next = data.history ?? []
      setTotal(data.total ?? 0)
      setEntries(prev => (replace ? next : [...prev, ...next]))
      setOffset(nextOffset + next.length)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [docId, enabled])

  useEffect(() => {
    setEntries([])
    setOffset(0)
    setTotal(0)
    if (!enabled) return
    loadPage(0, true)
  }, [docId, enabled, refreshKey, loadPage])

  return (
    <section>
      <h4 className="text-xs uppercase tracking-[0.08em] text-gray-400 font-semibold mb-3">
        AI History
      </h4>
      {enabled && (
        <>
          {error && <p className="text-xs text-red-500 mb-2">{error}</p>}
          {entries.length === 0 && !loading && (
            <p className="text-xs text-gray-400">No document AI interactions yet.</p>
          )}
          <ul className="space-y-2">
            {entries.map(entry => (
              <li key={entry.id} className="rounded-md border border-gray-200 bg-white p-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-indigo-700">
                    {ACTION_LABEL[entry.action] || entry.action || 'AI'}
                  </span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded ${
                      USER_ACTION_BADGE[entry.user_action] || 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {entry.user_action || entry.status || '—'}
                  </span>
                </div>
                <div className="text-[11px] text-gray-400 mb-1 space-y-0.5">
                  <div>{formatDate(entry.created_at)}</div>
                  <div>
                    {(entry.user_name || 'Unknown user')}
                    {entry.model_name ? ` • ${entry.model_name}` : ''}
                    {entry.provider_name ? ` • ${entry.provider_name}` : ''}
                  </div>
                </div>
                {entry.selected_text && (
                  <div className="text-[11px] text-gray-500 italic line-clamp-2 whitespace-pre-wrap break-words">
                    “{entry.selected_text}”
                  </div>
                )}
                <details className="mt-2 text-[11px] text-gray-600">
                  <summary className="cursor-pointer select-none text-gray-500">
                    Details
                  </summary>
                  <div className="mt-2 space-y-2">
                    {entry.prompt_text && (
                      <div>
                        <div className="mb-1 uppercase tracking-[0.08em] text-gray-400">Prompt</div>
                        <pre className="max-h-28 overflow-y-auto whitespace-pre-wrap rounded border border-gray-100 bg-gray-50 p-2 text-[11px]">
                          {entry.prompt_text}
                        </pre>
                      </div>
                    )}
                    {entry.suggestion && (
                      <div>
                        <div className="mb-1 uppercase tracking-[0.08em] text-gray-400">Response</div>
                        <pre className="max-h-28 overflow-y-auto whitespace-pre-wrap rounded border border-gray-100 bg-gray-50 p-2 text-[11px]">
                          {entry.suggestion}
                        </pre>
                      </div>
                    )}
                    {entry.final_text && (
                      <div>
                        <div className="mb-1 uppercase tracking-[0.08em] text-gray-400">Applied text</div>
                        <pre className="max-h-28 overflow-y-auto whitespace-pre-wrap rounded border border-gray-100 bg-gray-50 p-2 text-[11px]">
                          {entry.final_text}
                        </pre>
                      </div>
                    )}
                    {entry.status && (
                      <div className="text-[11px] text-gray-500">
                        Provider status: {entry.status}
                      </div>
                    )}
                  </div>
                </details>
              </li>
            ))}
          </ul>
          {offset < total && (
            <button
              type="button"
              disabled={loading}
              onClick={() => loadPage(offset, false)}
              className="mt-2 w-full rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-60"
            >
              {loading ? 'Loading…' : `Load more (${total - offset} left)`}
            </button>
          )}
        </>
      )}
      {!enabled && (
        <p className="text-xs text-gray-400">
          History loads once your document access is ready.
        </p>
      )}
    </section>
  )
}
