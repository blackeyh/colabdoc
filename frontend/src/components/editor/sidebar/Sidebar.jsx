import React from 'react'
import AIPanel from './AIPanel'
import ActiveUsers from './ActiveUsers'
import PermissionsPanel from './PermissionsPanel'
import VersionsPanel from './VersionsPanel'

export default function Sidebar({
  role, isOwner, activeUsers, remoteCursors,
  permissions, versions, docId, currentUser,
  selectedText, context,
  onGrantPermission, onUpdatePermission, onRevokePermission,
  onRestoreVersion, onAcceptAISuggestion, showToast,
}) {
  const canEdit = ['editor', 'owner'].includes(role)

  return (
    <div className="w-64 border-l border-gray-200 bg-white overflow-y-auto flex flex-col gap-5 p-4 flex-shrink-0">
      <AIPanel
        docId={docId}
        selectedText={selectedText}
        context={context}
        canEdit={canEdit}
        onAccept={onAcceptAISuggestion}
        showToast={showToast}
      />
      <hr className="border-gray-100" />
      <ActiveUsers activeUsers={activeUsers} remoteCursors={remoteCursors} />
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
