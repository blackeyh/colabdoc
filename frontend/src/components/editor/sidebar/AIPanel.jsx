import React, { useEffect, useRef, useState } from 'react'
import { apiFetch, apiStream } from '../../../api'

const ACTION_LABELS = {
  rewrite: 'Rewrite',
  summarize: 'Summarize',
  translate: 'Translate',
  restructure: 'Restructure',
  expand: 'Expand',
  grammar: 'Fix grammar',
}

function parseEventBlock(block) {
  const lines = block.split(/\r?\n/)
  let event = 'message'
  const dataLines = []
  for (const line of lines) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  if (!dataLines.length) return null
  return {
    event,
    data: JSON.parse(dataLines.join('\n')),
  }
}

export default function AIPanel({
  docId,
  selectedText,
  selectedRange,
  context,
  canUseAI,
  onAccept,
  onHistoryChange,
  showToast,
}) {
  const [loading, setLoading] = useState(false)
  const [suggestion, setSuggestion] = useState('')
  const [editable, setEditable] = useState('')
  const [action, setAction] = useState('')
  const [interactionId, setInteractionId] = useState(null)
  const [streamNotice, setStreamNotice] = useState('')
  const abortRef = useRef(null)
  const requestedRangeRef = useRef(null)

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
    setStreamNotice('')
    requestedRangeRef.current = null
  }

  async function handleAction(nextAction) {
    if (!docId || !hasSelection) return
    if (!canUseAI) {
      showToast('Only editors and owners can use AI suggestions.', 'warning')
      return
    }
    // Cancel any existing in-flight call first.
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setLoading(true)
    setSuggestion('')
    setEditable('')
    setAction(nextAction)
    setInteractionId(null)
    setStreamNotice('')
    requestedRangeRef.current = selectedRange ? { ...selectedRange } : null
    let partial = ''
    let sawDone = false
    try {
      const response = await apiStream(`/documents/${docId}/ai/assist/stream`, {
        method: 'POST',
        headers: { Accept: 'text/event-stream' },
        body: JSON.stringify({
          selected_text: selectedText,
          action: nextAction,
          context,
        }),
        signal: controller.signal,
      })
      const reader = response.body?.getReader()
      if (!reader) throw new Error('Streaming response unavailable')
      const decoder = new TextDecoder()
      let buffer = ''

      const processBlock = (block) => {
        const parsed = parseEventBlock(block)
        if (!parsed) return
        const { event, data } = parsed
        if (event === 'meta') {
          setInteractionId(data.id ?? null)
          onHistoryChange?.()
          return
        }
        if (event === 'delta') {
          partial += data.chunk ?? ''
          setSuggestion(partial)
          return
        }
        if (event === 'done') {
          sawDone = true
          const full = data.suggestion ?? partial
          setInteractionId(data.id ?? null)
          setSuggestion(full)
          setEditable(full)
          return
        }
        if (event === 'error') {
          const partialText = data.partial ?? partial
          setInteractionId(data.id ?? null)
          setSuggestion(partialText)
          setEditable(partialText)
          setStreamNotice('Generation failed after a partial response. Review before applying.')
          throw new Error(data.message || 'AI stream failed')
        }
      }

      while (true) {
        const { value, done } = await reader.read()
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
        let boundary = buffer.indexOf('\n\n')
        while (boundary !== -1) {
          const block = buffer.slice(0, boundary)
          buffer = buffer.slice(boundary + 2)
          processBlock(block)
          boundary = buffer.indexOf('\n\n')
        }
        if (done) break
      }

      if (!sawDone && partial) {
        setEditable(partial)
        setStreamNotice('Generation ended early. Partial output is shown below.')
      }
    } catch (e) {
      if (e.name === 'AbortError') return
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
    resetPanel()
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
      onHistoryChange?.()
    } catch (_) {
      // Resolve is best-effort logging; don't block UX.
    }
  }

  async function handleAccept() {
    if (!suggestion) return
    if (!canUseAI) {
      showToast('You need edit access to apply an AI suggestion.', 'warning')
      return
    }
    const chosen = editable ?? suggestion
    const edited = chosen !== suggestion
    onAccept(chosen, requestedRangeRef.current)
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
          <div className="space-y-3">
            {!canUseAI && (
              <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
                Only editors and owners can use AI suggestions on this document.
              </p>
            )}
            <div className="grid grid-cols-2 gap-2">
            {Object.entries(ACTION_LABELS).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => handleAction(key)}
                disabled={!canUseAI}
                className="rounded-md border border-indigo-200 bg-white px-3 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
              >
                {label}
              </button>
            ))}
          </div>
          </div>
        )}

        {loading && (
          <div className="space-y-2">
            <div className="text-sm text-indigo-700">
              {ACTION_LABELS[action] || 'AI'} in progress…
            </div>
            {!!suggestion && (
              <div className="max-h-40 overflow-y-auto rounded-md border border-indigo-200 bg-white p-3 text-sm whitespace-pre-wrap break-words text-gray-700">
                {suggestion}
              </div>
            )}
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
            {streamNotice && (
              <p className="mb-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
                {streamNotice}
              </p>
            )}
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
