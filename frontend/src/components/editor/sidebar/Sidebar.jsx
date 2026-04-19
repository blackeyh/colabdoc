import React, { useState } from 'react'
import AIPanel from './AIPanel'
import AIHistoryPanel from './AIHistoryPanel'
import ActiveUsers from './ActiveUsers'
import PermissionsPanel from './PermissionsPanel'
import VersionsPanel from './VersionsPanel'

export default function Sidebar({
  role, isOwner, activeUsers, typingUsers, remoteCursors,
  permissions, versions, docId, currentUser,
  selectedText, context,
  onGrantPermission, onUpdatePermission, onRevokePermission,
  onRestoreVersion, onAcceptAISuggestion, showToast,
}) {
  const canEdit = ['editor', 'owner'].includes(role)
  const [historyVersion, setHistoryVersion] = useState(0)

  function handleHistoryChange() {
    setHistoryVersion(version => version + 1)
  }

  return (
    <div className="w-64 border-l border-gray-200 bg-white overflow-y-auto flex flex-col gap-5 p-4 flex-shrink-0">
      <AIPanel
        docId={docId}
        selectedText={selectedText}
        context={context}
        canUseAI={canEdit}
        onAccept={onAcceptAISuggestion}
        onHistoryChange={handleHistoryChange}
        showToast={showToast}
      />
      <hr className="border-gray-100" />
      <AIHistoryPanel docId={docId} enabled={!!role} refreshKey={historyVersion} />
      <hr className="border-gray-100" />
      <ActiveUsers
        activeUsers={activeUsers}
        typingUsers={typingUsers}
        remoteCursors={remoteCursors}
      />
      <hr className="border-gray-100" />
      <PermissionsPanel
        isOwner={isOwner}
        permissions={permissions}
        onGrant={onGrantPermission}
        onUpdate={onUpdatePermission}
        onRevoke={onRevokePermission}
        showToast={showToast}
      />
      <hr className="border-gray-100" />
      <VersionsPanel
        versions={versions}
        canEdit={canEdit}
        onRestore={onRestoreVersion}
      />
    </div>
  )
}
