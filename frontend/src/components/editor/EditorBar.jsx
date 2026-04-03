import React, { useState, useEffect } from 'react'

const STATUS = {
  connecting:   { label: 'Connecting…',    cls: 'text-yellow-500' },
  connected:    { label: 'Connected',       cls: 'text-green-600' },
  reconnecting: { label: 'Reconnecting…',  cls: 'text-orange-500' },
  disconnected: { label: 'Disconnected',   cls: 'text-red-500' },
  error:        { label: 'Connection error', cls: 'text-red-500' },
  'no-permission': { label: 'No permission', cls: 'text-red-500' },
  typing:       { label: 'Typing…',         cls: 'text-gray-500' },
  saved:        { label: 'Saved',           cls: 'text-green-600' },
}

const ROLE_BADGE = {
  owner:     'bg-indigo-100 text-indigo-700',
  editor:    'bg-green-100 text-green-700',
  commenter: 'bg-yellow-100 text-yellow-700',
  viewer:    'bg-gray-100 text-gray-600',
}

export default function EditorBar({ doc, role, wsStatus, canEdit, onBack, onSaveTitle, onSaveVersion }) {
  const [title, setTitle] = useState(doc?.title || '')

  useEffect(() => {
    if (doc?.title) setTitle(doc.title)
  }, [doc?.title])

  const { label, cls } = STATUS[wsStatus] ?? { label: wsStatus, cls: 'text-gray-400' }

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-2.5 flex items-center gap-3 flex-shrink-0">
      <button onClick={onBack} className="text-indigo-500 hover:underline text-sm whitespace-nowrap">
        ← Back
      </button>

      <input
        className={`flex-1 border-none outline-none text-base font-semibold px-1 py-0.5 rounded transition ${canEdit ? 'focus:bg-indigo-50' : 'cursor-default text-gray-500'}`}
        value={title}
        onChange={e => setTitle(e.target.value)}
        onBlur={() => onSaveTitle(title)}
        disabled={!canEdit}
        placeholder="Document title"
      />

      {role && (
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ROLE_BADGE[role] ?? 'bg-gray-100 text-gray-600'}`}>
          {role}
        </span>
      )}

      <span className={`text-xs whitespace-nowrap ${cls}`}>{label}</span>

      {canEdit && (
        <button
          onClick={onSaveVersion}
          className="text-sm px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 transition whitespace-nowrap"
        >
          Save Version
        </button>
      )}
    </div>
  )
}
