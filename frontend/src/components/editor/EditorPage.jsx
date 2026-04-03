import React, { useState, useEffect, useRef, useCallback } from 'react'
import { apiFetch } from '../../api'
import { useWebSocket } from '../../hooks/useWebSocket'
import EditorBar from './EditorBar'
import EditorTextarea from './EditorTextarea'
import Sidebar from './sidebar/Sidebar'

export default function EditorPage({ initialDoc, currentUser, onBack, showToast }) {
  const [doc, setDoc] = useState(initialDoc)
  const [content, setContent] = useState('')
  const [role, setRole] = useState(null)
  const [wsStatus, setWsStatus] = useState('connecting')
  const [activeUsers, setActiveUsers] = useState([])
  // remoteCursors: { [userId]: { start, end, name } }
  const [remoteCursors, setRemoteCursors] = useState({})
  const [versions, setVersions] = useState([])
  const [permissions, setPermissions] = useState([])
  const [selection, setSelection] = useState({ start: 0, end: 0, text: '' })
  const saveTimerRef = useRef(null)
  const contentRef = useRef(content)
  contentRef.current = content

  const docId = doc?.id
  const canEdit = ['editor', 'owner'].includes(role)
  const isOwner = role === 'owner'

  // ─── WebSocket message handler ────────────────────────────────────────────
  const handleWsMessage = useCallback((msg) => {
    switch (msg.type) {
      case 'init':
        // Covers both first connect and reconnect/resync
        setRole(msg.role)
        setContent(msg.content?.text ?? '')
        setActiveUsers(msg.active_users ?? [])
        break

      case 'update': {
        const incoming = msg.content?.text ?? ''
        setContent(prev => prev !== incoming ? incoming : prev)
        setWsStatus('saved')
        setTimeout(() => setWsStatus(s => s === 'saved' ? 'connected' : s), 2000)
        break
      }

      case 'user_joined':
        setActiveUsers(prev =>
          prev.find(u => u.id === msg.user.id) ? prev : [...prev, msg.user]
        )
        break

      case 'user_left':
        setActiveUsers(prev => prev.filter(u => u.id !== msg.user.id))
        setRemoteCursors(prev => {
          const next = { ...prev }
          delete next[msg.user.id]
          return next
        })
        break

      case 'cursor':
        setRemoteCursors(prev => ({
          ...prev,
          [msg.user.id]: { ...msg.position, name: msg.user.name },
        }))
        break

      default:
        break
    }
  }, [])

  const { send, disconnect } = useWebSocket({
    docId,
    onMessage: handleWsMessage,
    onStatusChange: setWsStatus,
    enabled: !!docId,
  })

  // ─── Load REST data ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!docId) return
    apiFetch(`/documents/${docId}`)
      .then(d => {
        setDoc(d)
        setContent(d.content?.text ?? '')
      })
      .catch(e => {
        showToast(e.message, 'error')
        onBack()
      })
    loadPermissions()
    loadVersions()
  }, [docId]) // eslint-disable-line react-hooks/exhaustive-deps

  async function loadPermissions() {
    try {
      const data = await apiFetch(`/documents/${docId}/permissions`)
      setPermissions(data.permissions ?? [])
    } catch (_) {}
  }

  async function loadVersions() {
    try {
      const data = await apiFetch(`/documents/${docId}/versions`)
      setVersions(data.versions ?? [])
    } catch (_) {}
  }

  // ─── Editor actions ────────────────────────────────────────────────────────
  function onContentChange(newText) {
    if (!canEdit) {
      const msg =
        role === 'viewer'    ? 'You have viewer access — this document is read-only.' :
        role === 'commenter' ? 'Commenters cannot edit document text.' :
                               'You do not have permission to edit this document.'
      showToast(msg, 'warning')
      return
    }
    setContent(newText)
    clearTimeout(saveTimerRef.current)
    setWsStatus('typing')
    saveTimerRef.current = setTimeout(() => {
      send({ type: 'update', content: { text: newText }, save_version: false })
      setWsStatus('saved')
    }, 600)
  }

  function onCursorChange(position) {
    send({ type: 'cursor', position })
  }

  function handleSelectionChange(nextSelection) {
    setSelection(nextSelection)
  }

  function handleSaveVersion() {
    if (!canEdit) {
      showToast('Only editors and owners can save versions.', 'warning')
      return
    }
    send({ type: 'update', content: { text: contentRef.current }, save_version: true })
    setTimeout(loadVersions, 500)
  }

  async function handleSaveTitle(title) {
    if (!canEdit || !title || title === doc?.title) return
    try {
      await apiFetch(`/documents/${docId}`, { method: 'PUT', body: JSON.stringify({ title }) })
      setDoc(prev => ({ ...prev, title }))
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  // ─── Permission actions ────────────────────────────────────────────────────
  async function handleGrantPermission(userId, permRole) {
    if (!isOwner) {
      showToast('Only the owner can manage permissions.', 'warning')
      return
    }
    try {
      await apiFetch(`/documents/${docId}/permissions`, {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, role: permRole }),
      })
      loadPermissions()
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  async function handleUpdatePermission(userId, permRole) {
    if (!isOwner) {
      showToast('Only the owner can manage permissions.', 'warning')
      return
    }
    try {
      await apiFetch(`/documents/${docId}/permissions/${userId}`, {
        method: 'PUT',
        body: JSON.stringify({ role: permRole }),
      })
      loadPermissions()
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  async function handleRevokePermission(userId) {
    if (!isOwner) {
      showToast('Only the owner can manage permissions.', 'warning')
      return
    }
    if (!window.confirm("Remove this user's access?")) return
    try {
      await apiFetch(`/documents/${docId}/permissions/${userId}`, { method: 'DELETE' })
      loadPermissions()
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  // ─── Version restore ───────────────────────────────────────────────────────
  async function handleRestoreVersion(versionNumber) {
    if (!canEdit) {
      showToast('Only editors and owners can restore versions.', 'warning')
      return
    }
    try {
      const data = await apiFetch(
        `/documents/${docId}/versions/restore/${versionNumber}`,
        { method: 'POST' },
      )
      const newText = data.document.content?.text ?? ''
      setContent(newText)
      send({ type: 'update', content: { text: newText }, save_version: false })
      loadVersions()
      showToast(`Restored to version ${versionNumber}`, 'success')
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  function handleBack() {
    disconnect()
    onBack()
  }

  function handleAcceptAISuggestion(suggestion) {
    if (!canEdit) {
      showToast('You need edit access to apply an AI suggestion.', 'warning')
      return
    }
    const start = selection.start ?? 0
    const end = selection.end ?? start
    const nextContent = contentRef.current.slice(0, start) + suggestion + contentRef.current.slice(end)
    setSelection({
      start,
      end: start + suggestion.length,
      text: suggestion,
    })
    onContentChange(nextContent)
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <EditorBar
        doc={doc}
        role={role}
        wsStatus={wsStatus}
        canEdit={canEdit}
        onBack={handleBack}
        onSaveTitle={handleSaveTitle}
        onSaveVersion={handleSaveVersion}
      />
      <div className="flex flex-1 overflow-hidden">
        <EditorTextarea
          content={content}
          canEdit={canEdit}
          role={role}
          remoteCursors={remoteCursors}
          onChange={onContentChange}
          onCursorChange={onCursorChange}
          onSelectionChange={handleSelectionChange}
        />
        <Sidebar
          role={role}
          isOwner={isOwner}
          activeUsers={activeUsers}
          remoteCursors={remoteCursors}
          permissions={permissions}
          versions={versions}
          docId={docId}
          currentUser={currentUser}
          selectedText={selection.text}
          context={content.slice(0, 500)}
          onGrantPermission={handleGrantPermission}
          onUpdatePermission={handleUpdatePermission}
          onRevokePermission={handleRevokePermission}
          onRestoreVersion={handleRestoreVersion}
          onAcceptAISuggestion={handleAcceptAISuggestion}
          showToast={showToast}
        />
      </div>
    </div>
  )
}
