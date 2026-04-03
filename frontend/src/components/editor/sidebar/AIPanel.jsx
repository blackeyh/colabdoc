import React, { useState } from 'react'
import { apiFetch } from '../../../api'

const ACTION_LABELS = {
  rewrite: 'Rewrite',
  summarize: 'Summarize',
  translate: 'Translate',
  restructure: 'Restructure',
}

export default function AIPanel({ docId, selectedText, context, canEdit, onAccept, showToast }) {
  const [loading, setLoading] = useState(false)
  const [suggestion, setSuggestion] = useState('')
  const [action, setAction] = useState('')
  const hasSelection = selectedText.trim().length > 0
  const wordCount = selectedText.trim() ? selectedText.trim().split(/\s+/).length : 0

  async function handleAction(nextAction) {
    if (!docId || !hasSelection) return
    setLoading(true)
    setSuggestion('')
    setAction(nextAction)
    try {
      const data = await apiFetch(`/documents/${docId}/ai/assist`, {
        method: 'POST',
        body: JSON.stringify({
          selected_text: selectedText,
          action: nextAction,
          context,
        }),
      })
      setSuggestion(data.suggestion ?? '')
    } catch (e) {
      showToast(e.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  function handleAccept() {
    if (!suggestion) return
    if (!canEdit) {
      showToast('You need edit access to apply an AI suggestion.', 'warning')
      return
    }
    onAccept(suggestion)
    setSuggestion('')
    setAction('')
  }

  function handleReject() {
    setSuggestion('')
    setAction('')
  }

  return (
    <section>
      <h4 className="text-xs uppercase tracking-[0.08em] text-gray-400 font-semibold mb-3">AI Assistant</h4>
      <div className="border border-indigo-100 rounded-lg bg-indigo-50/40 p-3">
        {!hasSelection && !suggestion && !loading && (
          <p className="text-sm text-gray-500 leading-6">
            Select text in the editor, then choose rewrite, summarize, translate, or restructure.
          </p>
        )}

        {hasSelection && (
          <div className="mb-3 rounded-md border border-indigo-100 bg-white p-3">
            <div className="text-[11px] uppercase tracking-[0.08em] text-gray-400 mb-1">Selected text</div>
            <div className="text-sm text-gray-700 italic line-clamp-3 whitespace-pre-wrap break-words">
              {selectedText}
            </div>
            <div className="mt-2 text-[11px] text-gray-400">
              {wordCount} word{wordCount === 1 ? '' : 's'}
            </div>
          </div>
        )}

        {hasSelection && !loading && !suggestion && (
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(ACTION_LABELS).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => handleAction(key)}
                className="rounded-md border border-indigo-200 bg-white px-3 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
              >
                {label}
              </button>
            ))}
          </div>
        )}

        {loading && (
          <div className="text-sm text-indigo-700">
            {ACTION_LABELS[action] || 'AI'} in progress...
          </div>
        )}

        {!!suggestion && !loading && (
          <div>
            <div className="mb-2 flex items-center justify-between text-[11px] uppercase tracking-[0.08em] text-gray-400">
              <span>Suggestion</span>
              <span className="rounded bg-indigo-100 px-2 py-0.5 text-indigo-700">
                {ACTION_LABELS[action] || action}
              </span>
            </div>
            <div className="mb-3 max-h-52 overflow-y-auto whitespace-pre-wrap break-words rounded-md border border-indigo-200 bg-white p-3 text-sm leading-6 text-gray-800">
              {suggestion}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleAccept}
                className="flex-1 rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
              >
                Accept
              </button>
              <button
                type="button"
                onClick={handleReject}
                className="flex-1 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                Reject
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
