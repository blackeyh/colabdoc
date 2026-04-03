import React, { useRef, useCallback } from 'react'

// Returns a stable color for each collaborator cursor
const CURSOR_COLORS = [
  '#ef4444', '#f97316', '#eab308', '#22c55e',
  '#06b6d4', '#8b5cf6', '#ec4899', '#14b8a6',
]
const colorCache = {}
let colorIdx = 0
function cursorColor(userId) {
  if (!colorCache[userId]) {
    colorCache[userId] = CURSOR_COLORS[colorIdx % CURSOR_COLORS.length]
    colorIdx++
  }
  return colorCache[userId]
}

function readOnlyMessage(role) {
  if (role === 'viewer')    return 'You have viewer access — this document is read-only.'
  if (role === 'commenter') return 'Commenters cannot edit document text.'
  return null
}

export default function EditorTextarea({ content, canEdit, role, remoteCursors, onChange, onCursorChange }) {
  const taRef = useRef(null)

  const handleChange = useCallback(e => onChange(e.target.value), [onChange])

  const emitCursor = useCallback(() => {
    const ta = taRef.current
    if (!ta) return
    onCursorChange({ start: ta.selectionStart, end: ta.selectionEnd })
  }, [onCursorChange])

  const msg = !canEdit ? readOnlyMessage(role) : null

  return (
    <div className="flex-1 flex flex-col overflow-hidden relative">
      {msg && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-sm text-amber-700 flex-shrink-0">
          {msg}
        </div>
      )}

      <textarea
        ref={taRef}
        value={content}
        onChange={handleChange}
        onSelect={emitCursor}
        onClick={emitCursor}
        onKeyUp={emitCursor}
        readOnly={!canEdit}
        placeholder="Start writing…"
        className={`flex-1 resize-none border-none outline-none p-8 text-base leading-relaxed font-sans ${canEdit ? 'bg-gray-50' : 'bg-gray-100 cursor-default'}`}
      />

      {/* Collaborator cursor badges */}
      {Object.keys(remoteCursors).length > 0 && (
        <div className="absolute bottom-3 left-3 flex flex-wrap gap-1.5 pointer-events-none">
          {Object.entries(remoteCursors).map(([uid, cursor]) => (
            <span
              key={uid}
              className="text-xs px-2 py-0.5 rounded-full text-white shadow-sm"
              style={{ backgroundColor: cursorColor(uid) }}
              title={`${cursor.name} — char ${cursor.start}`}
            >
              {cursor.name} :{cursor.start}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
