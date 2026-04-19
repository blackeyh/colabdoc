import React, { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { EMPTY_TIPTAP_DOC } from '../../lib/contentCompat'

const CURSOR_COLORS = [
  '#ef4444', '#f97316', '#eab308', '#22c55e',
  '#06b6d4', '#8b5cf6', '#ec4899', '#14b8a6',
]
const colorCache = {}
let colorIdx = 0
function cursorColor(userId) {
  if (!colorCache[userId]) {
    colorCache[userId] = CURSOR_COLORS[colorIdx % CURSOR_COLORS.length]
    colorIdx++
  }
  return colorCache[userId]
}

const remoteCursorPluginKey = new PluginKey('remote-cursor-decorations')

function hexToRgba(hex, alpha) {
  const normalized = hex.replace('#', '')
  if (normalized.length !== 6) return `rgba(99, 102, 241, ${alpha})`
  const value = Number.parseInt(normalized, 16)
  const r = (value >> 16) & 255
  const g = (value >> 8) & 255
  const b = value & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function clampPosition(pos, max) {
  if (!Number.isFinite(pos)) return 1
  return Math.min(Math.max(Math.trunc(pos), 1), Math.max(max, 1))
}

function createCursorWidget(name, color) {
  const root = document.createElement('span')
  root.className = 'remote-cursor-widget'
  root.contentEditable = 'false'
  root.style.position = 'relative'
  root.style.display = 'inline-block'
  root.style.width = '0'
  root.style.pointerEvents = 'none'

  const caret = document.createElement('span')
  caret.className = 'remote-cursor-caret'
  caret.style.position = 'absolute'
  caret.style.left = '-1px'
  caret.style.top = '-0.15em'
  caret.style.height = '1.4em'
  caret.style.borderLeft = `2px solid ${color}`
  caret.style.borderRadius = '999px'

  const label = document.createElement('span')
  label.className = 'remote-cursor-label'
  label.textContent = name || 'Collaborator'
  label.style.position = 'absolute'
  label.style.left = '-1px'
  label.style.top = '-2.1em'
  label.style.transform = 'translateX(-10%)'
  label.style.background = color
  label.style.color = '#ffffff'
  label.style.fontSize = '11px'
  label.style.lineHeight = '1'
  label.style.fontWeight = '600'
  label.style.padding = '4px 6px'
  label.style.borderRadius = '999px'
  label.style.whiteSpace = 'nowrap'
  label.style.boxShadow = '0 6px 18px rgba(15, 23, 42, 0.18)'

  root.appendChild(caret)
  root.appendChild(label)
  return root
}

function buildRemoteCursorPlugin(remoteCursors) {
  return new Plugin({
    key: remoteCursorPluginKey,
    props: {
      decorations(state) {
        const maxPos = Math.max(state.doc.content.size, 1)
        const decorations = []

        Object.entries(remoteCursors || {}).forEach(([uid, cursor]) => {
          if (!cursor) return
          const color = cursorColor(uid)
          const rawStart = Number.isFinite(cursor.start) ? cursor.start : 1
          const rawEnd = Number.isFinite(cursor.end) ? cursor.end : rawStart
          const from = clampPosition(Math.min(rawStart, rawEnd), maxPos)
          const to = clampPosition(Math.max(rawStart, rawEnd), maxPos)

          if (to > from) {
            decorations.push(
              Decoration.inline(from, to, {
                class: 'remote-selection',
                style: `background-color: ${hexToRgba(color, 0.18)}; border-bottom: 2px solid ${color};`,
              }),
            )
          }

          decorations.push(
            Decoration.widget(
              to,
              () => createCursorWidget(cursor.name, color),
              { side: 1, ignoreSelection: true },
            ),
          )
        })

        return DecorationSet.create(state.doc, decorations)
      },
    },
  })
}

function readOnlyMessage(role) {
  if (role === 'viewer')    return 'You have viewer access — this document is read-only.'
  if (role === 'commenter') return 'Commenters cannot edit document text.'
  return null
}

function Toolbar({ editor, disabled }) {
  if (!editor) return null
  const btn = (active, onClick, label, key) => (
    <button
      key={key}
      type="button"
      onMouseDown={e => e.preventDefault()}
      onClick={onClick}
      disabled={disabled}
      className={`px-2 py-1 text-sm rounded border transition ${
        active
          ? 'bg-indigo-100 border-indigo-300 text-indigo-700'
          : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
      } disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      {label}
    </button>
  )

  return (
    <div className="flex flex-wrap gap-1 border-b border-gray-200 bg-white px-4 py-2 flex-shrink-0">
      {btn(editor.isActive('bold'),   () => editor.chain().focus().toggleBold().run(),   <b>B</b>,    'b')}
      {btn(editor.isActive('italic'), () => editor.chain().focus().toggleItalic().run(), <i>I</i>,   'i')}
      {btn(editor.isActive('heading', { level: 1 }), () => editor.chain().focus().toggleHeading({ level: 1 }).run(), 'H1', 'h1')}
      {btn(editor.isActive('heading', { level: 2 }), () => editor.chain().focus().toggleHeading({ level: 2 }).run(), 'H2', 'h2')}
      {btn(editor.isActive('bulletList'),  () => editor.chain().focus().toggleBulletList().run(),  '• List',  'ul')}
      {btn(editor.isActive('orderedList'), () => editor.chain().focus().toggleOrderedList().run(), '1. List', 'ol')}
      {btn(editor.isActive('codeBlock'),   () => editor.chain().focus().toggleCodeBlock().run(),   '</>',     'code')}
      {btn(false, () => editor.chain().focus().undo().run(), '↶ Undo', 'undo')}
      {btn(false, () => editor.chain().focus().redo().run(), '↷ Redo', 'redo')}
    </div>
  )
}

const EditorTextarea = forwardRef(function EditorTextarea(
  {
    content,
    canEdit,
    role,
    remoteCursors,
    onChange,
    onCursorChange,
    onSelectionChange,
  },
  ref,
) {
  const skipNextUpdateRef = useRef(false)
  const lastLocalJsonRef = useRef(null)

  const editor = useEditor({
    extensions: [StarterKit],
    content: content || EMPTY_TIPTAP_DOC,
    editable: !!canEdit,
    onUpdate: ({ editor: ed }) => {
      if (skipNextUpdateRef.current) {
        skipNextUpdateRef.current = false
        return
      }
      const json = ed.getJSON()
      lastLocalJsonRef.current = json
      onChange?.(json)
    },
    onSelectionUpdate: ({ editor: ed }) => {
      const { from, to } = ed.state.selection
      const text = ed.state.doc.textBetween(from, to, '\n')
      onCursorChange?.({ start: from, end: to })
      onSelectionChange?.({ start: from, end: to, text })
    },
  })

  useEffect(() => {
    if (!editor) return
    editor.setEditable(!!canEdit)
  }, [editor, canEdit])

  useEffect(() => {
    if (!editor) return
    editor.unregisterPlugin(remoteCursorPluginKey)
    if (remoteCursors && Object.keys(remoteCursors).length > 0) {
      editor.registerPlugin(buildRemoteCursorPlugin(remoteCursors))
    }
    return () => {
      editor.unregisterPlugin(remoteCursorPluginKey)
    }
  }, [editor, remoteCursors])

  // Apply external content changes (WS updates, version restores) without
  // recursing through onUpdate.
  useEffect(() => {
    if (!editor || !content) return
    const current = editor.getJSON()
    if (JSON.stringify(current) === JSON.stringify(content)) return
    skipNextUpdateRef.current = true
    editor.commands.setContent(content, false)
  }, [editor, content])

  useImperativeHandle(ref, () => ({
    getEditor: () => editor,
    insertAtSelection: (text) => {
      if (!editor || typeof text !== 'string') return
      const { from, to } = editor.state.selection
      editor.chain().focus().insertContentAt({ from, to }, text).run()
    },
    getSelectedText: () => {
      if (!editor) return ''
      const { from, to } = editor.state.selection
      return editor.state.doc.textBetween(from, to, '\n')
    },
  }), [editor])

  const msg = !canEdit ? readOnlyMessage(role) : null

  return (
    <div className="flex-1 flex flex-col overflow-hidden relative">
      {msg && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-sm text-amber-700 flex-shrink-0">
          {msg}
        </div>
      )}

      <Toolbar editor={editor} disabled={!canEdit} />

      <div className={`flex-1 overflow-auto ${canEdit ? 'bg-white' : 'bg-gray-100'}`}>
        <EditorContent
          editor={editor}
          className="prose max-w-3xl mx-auto px-8 py-6 focus:outline-none"
        />
      </div>
    </div>
  )
})

export default EditorTextarea
