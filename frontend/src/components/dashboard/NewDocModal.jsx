import React, { useState } from 'react'
import Modal from '../common/Modal'
import { apiFetch } from '../../api'

export default function NewDocModal({ open, onClose, onCreated, showToast }) {
  const [title, setTitle] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleCreate() {
    setError('')
    setLoading(true)
    try {
      const doc = await apiFetch('/documents', {
        method: 'POST',
        body: JSON.stringify({ title: title.trim() || 'Untitled' }),
      })
      setTitle('')
      onCreated(doc)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New Document">
      <div className="space-y-3">
        <div>
          <label className="block text-sm text-gray-500 mb-1">Title</label>
          <input
            type="text"
            autoFocus
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            placeholder="My Document"
            value={title}
            onChange={e => setTitle(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleCreate()}
          />
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded text-sm border border-gray-300 hover:bg-gray-50 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={loading}
            className="px-4 py-1.5 rounded text-sm bg-indigo-500 hover:bg-indigo-600 text-white disabled:opacity-60 transition"
          >
            {loading ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
