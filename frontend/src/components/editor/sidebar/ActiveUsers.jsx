import React from 'react'

const COLORS = [
  '#ef4444', '#f97316', '#eab308', '#22c55e',
  '#06b6d4', '#8b5cf6', '#ec4899', '#14b8a6',
]
const colorCache = {}
let idx = 0
function getColor(userId) {
  if (!colorCache[userId]) {
    colorCache[userId] = COLORS[idx % COLORS.length]
    idx++
  }
  return colorCache[userId]
}

export default function ActiveUsers({ activeUsers, remoteCursors }) {
  return (
    <div>
      <h4 className="text-xs uppercase tracking-wide text-gray-400 font-semibold mb-2">
        Active Users
      </h4>
      {activeUsers.length === 0 ? (
        <p className="text-xs text-gray-400">Just you</p>
      ) : (
        activeUsers.map(u => {
          const cursor = remoteCursors[u.id]
          const color = getColor(u.id)
          return (
            <div key={u.id} className="flex items-center gap-2 mb-1.5">
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: color }}
              />
              <span className="text-sm flex-1 truncate">{u.name}</span>
              <span className="text-xs text-gray-400 bg-gray-100 rounded px-1.5 py-0.5">
                {u.role}
              </span>
              {cursor != null && (
                <span
                  className="text-xs font-mono"
                  style={{ color }}
                  title={`Cursor at character ${cursor.start}`}
                >
                  :{cursor.start}
                </span>
              )}
            </div>
          )
        })
      )}
    </div>
  )
}
