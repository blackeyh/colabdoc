import React, { useState, useRef } from 'react'
import { apiFetch } from '../../../api'

export default function PermissionsPanel({
  isOwner, permissions, onGrant, onUpdate, onRevoke, showToast,
}) {
  const [search, setSearch] = useState('')
  const [results, setResults] = useState([])
  const [showDrop, setShowDrop] = useState(false)
  const [selectedUser, setSelectedUser] = useState(null)
  const [selectedRole, setSelectedRole] = useState('editor')
  const searchTimer = useRef(null)

  async function handleSearch(q) {
    setSearch(q)
    clearTimeout(searchTimer.current)
    if (!q || q.length < 2) { setResults([]); setShowDrop(false); return }
    searchTimer.current = setTimeout(async () => {
      try {
        const data = await apiFetch(`/auth/users/search?q=${encodeURIComponent(q)}`)
        setResults(data.users || [])
        setShowDrop(true)
      } catch (_) {}
    }, 300)
  }

  function selectUser(u) {
    setSelectedUser(u)
    setSearch('')
    setResults([])
    setShowDrop(false)
  }

  async function handleGrant() {
    if (!selectedUser) {
      showToast('Search and select a user first.', 'warning')
      return
    }
    await onGrant(selectedUser.id, selectedRole)
    setSelectedUser(null)
  }

  return (
    <div>
      <h4 className="text-xs uppercase tracking-wide text-gray-400 font-semibold mb-2">
        Permissions
      </h4>

      {!isOwner && (
        <p className="text-xs text-amber-600 bg-amber-50 rounded px-2 py-1 mb-2">
          Only the owner can manage permissions.
        </p>
      )}

      {permissions.length === 0 ? (
        <p className="text-xs text-gray-400">No shared users</p>
      ) : (
        permissions.map(p => (
          <div key={p.user_id} className="flex items-center gap-1.5 mb-1.5 text-sm">
            <span className="flex-1 truncate text-sm">{p.user_name}</span>
            {isOwner ? (
              <>
                <select
                  value={p.role}
                  onChange={e => onUpdate(p.user_id, e.target.value)}
                  className="text-xs border border-gray-200 rounded px-1 py-0.5"
                >
                  <option value="editor">Editor</option>
                  <option value="commenter">Commenter</option>
                  <option value="viewer">Viewer</option>
                </select>
                <button
                  onClick={() => onRevoke(p.user_id)}
                  className="text-xs text-red-400 hover:text-red-600 px-1 leading-none"
                >
                  ✕
                </button>
              </>
            ) : (
              <span className="text-xs text-gray-400 bg-gray-100 rounded px-1.5 py-0.5">
                {p.role}
              </span>
            )}
          </div>
        ))
      )}

      {isOwner && (
        <div className="mt-3 space-y-2">
          <div className="relative">
            <input
              type="text"
              value={search}
              onChange={e => handleSearch(e.target.value)}
              onBlur={() => setTimeout(() => setShowDrop(false), 200)}
              placeholder="Search by name or email"
              className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-300"
            />
            {showDrop && results.length > 0 && (
              <div className="absolute top-full left-0 right-0 bg-white border border-gray-200 rounded shadow-lg z-10 max-h-36 overflow-y-auto">
                {results.map(u => (
                  <div
                    key={u.id}
                    onMouseDown={() => selectUser(u)}
                    className="px-3 py-1.5 text-xs cursor-pointer hover:bg-indigo-50"
                  >
                    {u.name}{' '}
                    <span className="text-gray-400">{u.email}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {selectedUser && (
            <div className="flex items-center justify-between bg-indigo-50 rounded px-2 py-1 text-xs">
              <span className="truncate">{selectedUser.name} ({selectedUser.email})</span>
              <button
                onClick={() => setSelectedUser(null)}
                className="ml-1 text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
          )}

          <select
            value={selectedRole}
            onChange={e => setSelectedRole(e.target.value)}
            className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
          >
            <option value="editor">Editor</option>
            <option value="commenter">Commenter</option>
            <option value="viewer">Viewer</option>
          </select>

          <button
            onClick={handleGrant}
            className="w-full bg-indigo-500 hover:bg-indigo-600 text-white text-xs py-1.5 rounded transition"
          >
            Add User
          </button>
        </div>
      )}
    </div>
  )
}
