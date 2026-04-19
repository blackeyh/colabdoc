import React, { useState, useEffect, useRef, useCallback } from 'react'
import { apiFetch, apiRaw } from '../../api'
import { useWebSocket } from '../../hooks/useWebSocket'
import EditorBar from './EditorBar'
import EditorTextarea from './EditorTextarea'
import Sidebar from './sidebar/Sidebar'
import { toTiptap, extractPlainText, EMPTY_TIPTAP_DOC } from '../../lib/contentCompat'

const SAVE_DEBOUNCE_MS = 600
const TYPING_THROTTLE_MS = 2000

function fallbackExportFilename(title, format) {
  const normalized = (title || 'document')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return `${normalized || 'document'}.${format}`
}

function getFilenameFromHeaders(headers, fallback) {
  const disposition = headers.get('content-disposition') || ''
  const match = disposition.match(/filename="([^"]+)"/i)
  return match?.[1] || fallback
}

export default function EditorPage({ initialDoc, currentUser, onBack, showToast }) {
  const [doc, setDoc] = useState(initialDoc)
  const [content, setContent] = useState(EMPTY_TIPTAP_DOC)
  const [role, setRole] = useState(null)
  const [wsStatus, setWsStatus] = useState('connecting')
  const [activeUsers, setActiveUsers] = useState([])
  const [typingUsers, setTypingUsers] = useState({})
  const [remoteCursors, setRemoteCursors] = useState({})
  const [versions, setVersions] = useState([])
  const [permissions, setPermissions] = useState([])
  const [selection, setSelection] = useState({ start: 0, end: 0, text: '' })
  const saveTimerRef = useRef(null)
  const typingEmittedAtRef = useRef(0)
  const contentRef = useRef(content)
  contentRef.current = content
  const offlineQueueRef = useRef(null)
  const wsStatusRef = useRef(wsStatus)
  wsStatusRef.current = wsStatus
  const editorRef = useRef(null)

  const docId = doc?.id
  const canEdit = ['editor', 'owner'].includes(role)
  const isOwner = role === 'owner'

  // ─── WebSocket message handler ────────────────────────────────────────────
  const handleWsMessage = useCallback((msg) => {
    switch (msg.type) {
      case 'init':
        setRole(msg.role)
        setContent(toTiptap(msg.content))
        setActiveUsers(msg.active_users ?? [])
        break

      case 'update': {
        setContent(toTiptap(msg.content))
        setWsStatus('saved')
        setTimeout(() => setWsStatus(s => (s === 'saved' ? 'connected' : s)), 2000)
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
        setTypingUsers(prev => {
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

      case 'typing': {
        const uid = msg.user?.id
        if (!uid) break
        setTypingUsers(prev => ({
          ...prev,
          [uid]: { name: msg.user.name, ts: Date.now() },
        }))
        break
      }

      default:
        break
    }
  }, [])

  const flushOfflineQueue = useCallback(() => {
    if (!offlineQueueRef.current) return
    const pending = offlineQueueRef.current
    offlineQueueRef.current = null
    send({ type: 'update', content: pending, save_version: false })
    setWsStatus('saved')
  }, [])

  const handleReconnect = useCallback(async () => {
    if (!docId) return
    try {
      const fresh = await apiFetch(`/documents/${docId}`)
      setDoc(fresh)
      setContent(toTiptap(fresh.content))
    } catch (_) {
      // Permission/network errors bubble up via status change; no toast spam.
    }
    flushOfflineQueue()
  }, [docId, flushOfflineQueue])

  const handleStatusChange = useCallback((status) => {
    setWsStatus(prev => {
      if (status === 'connected' && prev !== 'connected') {
        // Ran onopen — re-sync after reconnect.
        queueMicrotask(handleReconnect)
      }
      return status
    })
    if (status === 'disconnected' || status === 'reconnecting') {
      // Keep offline indicator visible until connected.
    }
  }, [handleReconnect])

  const { send, disconnect } = useWebSocket({
    docId,
    onMessage: handleWsMessage,
    onStatusChange: handleStatusChange,
    enabled: !!docId,
  })

  // ─── Expire typing indicators ──────────────────────────────────────────────
  useEffect(() => {
    const timer = setInterval(() => {
      setTypingUsers(prev => {
        const now = Date.now()
        let changed = false
        const next = {}
        for (const [uid, info] of Object.entries(prev)) {
          if (now - info.ts < 3000) next[uid] = info
          else changed = true
        }
        return changed ? next : prev
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // ─── Load REST data ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!docId) return
    apiFetch(`/documents/${docId}`)
      .then(d => {
        setDoc(d)
        setContent(toTiptap(d.content))
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

  function emitTypingPing() {
    const now = Date.now()
    if (now - typingEmittedAtRef.current < TYPING_THROTTLE_MS) return
    typingEmittedAtRef.current = now
    send({ type: 'typing' })
  }

  function sendUpdate(json) {
    if (wsStatusRef.current === 'connected') {
      try {
        send({ type: 'update', content: json, save_version: false })
        setWsStatus('saved')
      } catch (_) {
        setWsStatus('error')
      }
    } else {
      // Offline queue — last-write-wins single slot.
      offlineQueueRef.current = json
      setWsStatus('offline')
    }
  }

  // ─── Editor actions ────────────────────────────────────────────────────────
  function onContentChange(nextJson) {
    if (!canEdit) {
      const msg =
        role === 'viewer'    ? 'You have viewer access — this document is read-only.' :
        role === 'commenter' ? 'Commenters cannot edit document text.' :
                               'You do not have permission to edit this document.'
      showToast(msg, 'warning')
      return
    }
    setContent(nextJson)
    emitTypingPing()
    clearTimeout(saveTimerRef.current)
    setWsStatus('saving')
    saveTimerRef.current = setTimeout(() => sendUpdate(nextJson), SAVE_DEBOUNCE_MS)
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
    send({ type: 'update', content: contentRef.current, save_version: true })
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

  async function handleExport(format) {
    try {
      const res = await apiRaw(`/documents/${docId}/export?format=${format}`)
      const blob = await res.blob()
      const fallback = fallbackExportFilename(doc?.title, format)
      const filename = getFilenameFromHeaders(res.headers, fallback)
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      showToast(`Exported document as ${format.toUpperCase()}.`, 'success')
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
      const restored = toTiptap(data.document.content)
      setContent(restored)
      send({ type: 'update', content: restored, save_version: false })
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
    if (!editorRef.current) return
    editorRef.current.insertAtSelection(suggestion)
    // insertAtSelection triggers onUpdate → onContentChange → sendUpdate.
  }

  const contextForAI = extractPlainText(content).slice(0, 4000)

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
        onExport={handleExport}
      />
      <div className="flex flex-1 overflow-hidden">
        <EditorTextarea
          ref={editorRef}
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
          typingUsers={typingUsers}
          remoteCursors={remoteCursors}
          permissions={permissions}
          versions={versions}
          docId={docId}
          currentUser={currentUser}
          selectedText={selection.text}
          context={contextForAI}
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
