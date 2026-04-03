import React, { useState, useEffect } from 'react'
import { apiFetch } from '../../api'
import NewDocModal from './NewDocModal'

export default function Dashboard({ currentUser, onLogout, onOpenDoc, showToast }) {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [showNewDoc, setShowNewDoc] = useState(false)

  async function loadDocuments() {
    setLoading(true)
    try {
      const data = await apiFetch('/documents')
      setDocs(data.documents || [])
    } catch (e) {
      showToast(e.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadDocuments() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleLogout() {
    try { await apiFetch('/auth/logout', { method: 'POST' }) } catch (_) {}
    onLogout()
  }

  async function handleDelete(e, id) {
    e.stopPropagation()
    if (!window.confirm('Delete this document?')) return
    try {
      await apiFetch(`/documents/${id}`, { method: 'DELETE' })
      setDocs(prev => prev.filter(d => d.id !== id))
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Topbar */}
      <div className="bg-white border-b border-gray-200 px-8 py-3 flex justify-between items-center">
        <h2 className="text-indigo-600 font-bold text-lg">ColabDoc</h2>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-gray-600">{currentUser?.name}</span>
          <button
            onClick={handleLogout}
            className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded text-sm transition"
          >
            Sign out
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">My Documents</h3>
          <button
            onClick={() => setShowNewDoc(true)}
            className="bg-indigo-500 hover:bg-indigo-600 text-white px-4 py-1.5 rounded text-sm transition"
          >
            + New Document
          </button>
        </div>

        {loading ? (
          <p className="text-gray-400 text-sm">Loading…</p>
        ) : docs.length === 0 ? (
          <p className="text-gray-400 text-sm">No documents yet. Create one!</p>
        ) : (
          <div className="flex flex-col gap-3">
            {docs.map(doc => (
              <div
                key={doc.id}
                onClick={() => onOpenDoc(doc)}
                className="bg-white rounded-lg px-5 py-4 shadow-sm flex justify-between items-center cursor-pointer hover:shadow-md transition"
              >
                <div>
                  <div className="font-semibold">{doc.title}</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    Updated {new Date(doc.updated_at).toLocaleString()}
                  </div>
                </div>
                <div onClick={e => e.stopPropagation()}>
                  {doc.owner_id === currentUser?.id && (
                    <button
                      onClick={e => handleDelete(e, doc.id)}
                      className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded text-sm transition"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <NewDocModal
        open={showNewDoc}
        onClose={() => setShowNewDoc(false)}
        onCreated={doc => { setShowNewDoc(false); onOpenDoc(doc) }}
        showToast={showToast}
      />
    </div>
  )
}
