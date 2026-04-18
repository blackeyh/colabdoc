// Bridge between the legacy {text: ""} content shape and Tiptap's JSON doc.
//
// The backend stores Document.content as JSONB; old rows may still be
// {text: ""}. New rows written by the Tiptap editor are {type:"doc", ...}.
// These helpers keep both shapes round-trippable during the transition.

const EMPTY_DOC = { type: 'doc', content: [{ type: 'paragraph' }] }

function textToDoc(text) {
  const trimmed = (text || '').replace(/\r\n/g, '\n')
  if (!trimmed) return EMPTY_DOC
  const paragraphs = trimmed.split('\n\n').map(chunk => {
    const content = chunk.length
      ? [{ type: 'text', text: chunk }]
      : undefined
    const node = { type: 'paragraph' }
    if (content) node.content = content
    return node
  })
  return { type: 'doc', content: paragraphs }
}

export function toTiptap(content) {
  if (!content) return EMPTY_DOC
  if (typeof content === 'object' && content.type === 'doc') return content
  if (typeof content === 'object' && typeof content.text === 'string') {
    return textToDoc(content.text)
  }
  if (typeof content === 'string') return textToDoc(content)
  return EMPTY_DOC
}

export function isTiptapDoc(value) {
  return !!(value && typeof value === 'object' && value.type === 'doc')
}

export function extractPlainText(content) {
  if (!content) return ''
  if (typeof content === 'string') return content
  if (typeof content.text === 'string' && !content.type) return content.text
  if (isTiptapDoc(content)) {
    const parts = []
    const walk = (node) => {
      if (!node) return
      if (node.type === 'text' && typeof node.text === 'string') parts.push(node.text)
      if (Array.isArray(node.content)) node.content.forEach(walk)
      if (node.type === 'paragraph' || node.type === 'heading') parts.push('\n')
    }
    walk(content)
    return parts.join('').trim()
  }
  return ''
}

export const EMPTY_TIPTAP_DOC = EMPTY_DOC
