import { getSchema } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import * as Y from 'yjs'
import { prosemirrorJSONToYDoc, yDocToProsemirrorJSON } from 'y-prosemirror'
import { EMPTY_TIPTAP_DOC, toTiptap } from './contentCompat'

export const CRDT_FIELD = 'content'
export const COLLAB_REMOTE_ORIGIN = 'remote'
export const COLLAB_SNAPSHOT_ORIGIN = 'snapshot'

function buildSchemaExtensions() {
  return [StarterKit.configure({ history: false })]
}

const COLLAB_SCHEMA = getSchema(buildSchemaExtensions())

export function buildCollaborativeExtensions(Collaboration) {
  return [
    StarterKit.configure({ history: false }),
    Collaboration.configure({
      document: null,
    }),
  ]
}

export function encodeBytesToBase64(bytes) {
  let binary = ''
  bytes.forEach(byte => {
    binary += String.fromCharCode(byte)
  })
  return btoa(binary)
}

export function decodeBase64ToBytes(value) {
  if (!value) return new Uint8Array()
  const binary = atob(value)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }
  return bytes
}

export function createYDocFromSnapshot(snapshot) {
  const ydoc = new Y.Doc()
  if (snapshot) {
    Y.applyUpdate(ydoc, decodeBase64ToBytes(snapshot), COLLAB_SNAPSHOT_ORIGIN)
  }
  return ydoc
}

export function createSnapshotFromContent(content) {
  const seed = toTiptap(content) || EMPTY_TIPTAP_DOC
  const ydoc = prosemirrorJSONToYDoc(COLLAB_SCHEMA, seed, CRDT_FIELD)
  const snapshot = encodeBytesToBase64(Y.encodeStateAsUpdate(ydoc))
  ydoc.destroy()
  return snapshot
}

export function getSnapshotFromYDoc(ydoc) {
  return encodeBytesToBase64(Y.encodeStateAsUpdate(ydoc))
}

export function applySnapshotToYDoc(ydoc, snapshot, origin = COLLAB_SNAPSHOT_ORIGIN) {
  if (!snapshot) return
  Y.applyUpdate(ydoc, decodeBase64ToBytes(snapshot), origin)
}

export function applyIncrementalUpdate(ydoc, encodedUpdate, origin = COLLAB_REMOTE_ORIGIN) {
  if (!encodedUpdate) return
  Y.applyUpdate(ydoc, decodeBase64ToBytes(encodedUpdate), origin)
}

export function getContentFromYDoc(ydoc) {
  const json = yDocToProsemirrorJSON(ydoc, CRDT_FIELD)
  if (json?.type === 'doc') return json
  return EMPTY_TIPTAP_DOC
}
