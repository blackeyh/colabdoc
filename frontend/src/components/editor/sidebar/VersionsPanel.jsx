import React from 'react'

export default function VersionsPanel({ versions, canEdit, onRestore }) {
  async function handleRestore(versionNumber) {
    if (!window.confirm(`Restore to version ${versionNumber}?`)) return
    await onRestore(versionNumber)
  }

  return (
    <div>
      <h4 className="text-xs uppercase tracking-wide text-gray-400 font-semibold mb-2">
        Versions
      </h4>
      {versions.length === 0 ? (
        <p className="text-xs text-gray-400">No saved versions</p>
      ) : (
        versions.map(v => (
          <div key={v.version_number} className="flex items-center justify-between mb-1.5 text-xs text-gray-600">
            <span>
              v{v.version_number} — {new Date(v.created_at).toLocaleTimeString()}
            </span>
            <button
              onClick={() => handleRestore(v.version_number)}
              disabled={!canEdit}
              className="text-indigo-500 hover:underline disabled:opacity-40 disabled:cursor-not-allowed"
              title={!canEdit ? 'Only editors and owners can restore versions.' : undefined}
            >
              Restore
            </button>
          </div>
        ))
      )}
    </div>
  )
}
