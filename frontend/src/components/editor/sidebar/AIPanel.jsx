import React, { useEffect, useRef, useState } from 'react'
import { apiFetch } from '../../../api'

const ACTION_LABELS = {
  rewrite: 'Rewrite',
  summarize: 'Summarize',
  translate: 'Translate',
  restructure: 'Restructure',
  expand: 'Expand',
  grammar: 'Fix grammar',
}

export default function AIPanel({ docId, selectedText, context, canEdit, onAccept, showToast }) {
  const [loading, setLoading] = useState(false)
  const [suggestion, setSuggestion] = useState('')
  const [editable, setEditable] = useState('')
  const [action, setAction] = useState('')
  const [interactionId, setInteractionId] = useState(null)
  const abortRef = useRef(null)

  const hasSelection = (selectedText || '').trim().length > 0
  const wordCount = hasSelection ? selectedText.trim().split(/\s+/).length : 0

  useEffect(() => {
    // If the user changes selection, reset any pending suggestion state.
    if (!suggestion) return
    return () => {
      // no-op: intentional — suggestion clears via handlers.
    }
  }, [suggestion])

  function resetPanel() {
    setSuggestion('')
    setEditable('')
    setAction('')
    setInteractionId(null)
  }

  async function handleAction(nextAction) {
    if (!docId || !hasSelection) return
    // Cancel any existing in-flight call first.
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setLoading(true)
    setSuggestion('')
    setEditable('')
    setAction(nextAction)
    setInteractionId(null)
    try {
      const data = await apiFetch(`/documents/${docId}/ai/assist`, {
        method: 'POST',
        body: JSON.stringify({
          selected_text: selectedText,
          action: nextAction,
          context,
        }),
        signal: controller.signal,
      })
      setSuggestion(data.suggestion ?? '')
      setEditable(data.suggestion ?? '')
      setInteractionId(data.id ?? null)
    } catch (e) {
      if (e.name === 'AbortError') return // user cancelled, stay quiet
      showToast(e.message, 'error')
    } finally {
      if (abortRef.current === controller) abortRef.current = null
      setLoading(false)
    }
  }

  function handleCancel() {
    abortRef.current?.abort()
    abortRef.current = null
    setLoading(false)
    setAction('')
  }

  async function resolve(user_action, edited_text) {
    if (!docId || !interactionId) return
    try {
      await apiFetch(
        `/documents/${docId}/ai/interactions/${interactionId}/resolve`,
        {
          method: 'POST',
          body: JSON.stringify({ user_action, edited_text }),
        },
      )
    } catch (_) {
      // Resolve is best-effort logging; don't block UX.
    }
  }

  async function handleAccept() {
    if (!suggestion) return
    if (!canEdit) {
      showToast('You need edit access to apply an AI suggestion.', 'warning')
      return
    }
    const chosen = editable ?? suggestion
    const edited = chosen !== suggestion
    onAccept(chosen)
    await resolve(edited ? 'edited' : 'accepted', edited ? chosen : undefined)
    resetPanel()
  }

  async function handleReject() {
    await resolve('rejected')
    resetPanel()
  }

  return (
    <section>
      <h4 className="text-xs uppercase tracking-[0.08em] text-gray-400 font-semibold mb-3">AI Assistant</h4>
      <div className="border border-indigo-100 rounded-lg bg-indigo-50/40 p-3">
        {!hasSelection && !suggestion && !loading && (
          <p className="text-sm text-gray-500 leading-6">
            Select text in the editor, then pick an action.
          </p>
        )}

        {hasSelection && !suggestion && (
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
          <div className="space-y-2">
            <div className="text-sm text-indigo-700">
              {ACTION_LABELS[action] || 'AI'} in progress…
            </div>
            <button
              type="button"
              onClick={handleCancel}
              className="w-full rounded-md border border-indigo-200 bg-white px-3 py-1.5 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
            >
              Cancel
            </button>
          </div>
        )}

        {!!suggestion && !loading && (
          <div>
            <div className="mb-2 flex items-center justify-between text-[11px] uppercase tracking-[0.08em] text-gray-400">
              <span>Compare</span>
              <span className="rounded bg-indigo-100 px-2 py-0.5 text-indigo-700">
                {ACTION_LABELS[action] || action}
              </span>
            </div>
            <div className="grid grid-cols-1 gap-2 mb-3">
              <div className="rounded-md border border-gray-200 bg-white p-2">
                <div className="text-[10px] uppercase tracking-wide text-gray-400 mb-1">Original</div>
                <div className="max-h-28 overflow-y-auto whitespace-pre-wrap break-words text-sm text-gray-700">
                  {selectedText}
                </div>
              </div>
              <div className="rounded-md border border-indigo-200 bg-white p-2">
                <div className="text-[10px] uppercase tracking-wide text-gray-400 mb-1">Suggestion (editable)</div>
                <textarea
                  value={editable}
                  onChange={e => setEditable(e.target.value)}
                  className="w-full max-h-52 min-h-[4rem] resize-y border-none outline-none bg-transparent text-sm leading-6 text-gray-800"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleAccept}
                className="flex-1 rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
              >
                {editable !== suggestion ? 'Accept edited' : 'Accept'}
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
