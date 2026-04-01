import React from 'react'

const TYPE_STYLES = {
  info:    'bg-blue-600',
  success: 'bg-green-600',
  error:   'bg-red-600',
  warning: 'bg-amber-500',
}

export default function Toast({ toasts }) {
  if (!toasts.length) return null
  return (
    <div className="fixed bottom-4 right-4 flex flex-col gap-2 z-50 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`${TYPE_STYLES[t.type] ?? TYPE_STYLES.info} text-white px-4 py-3 rounded-lg shadow-lg text-sm max-w-sm animate-slide-up`}
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}
