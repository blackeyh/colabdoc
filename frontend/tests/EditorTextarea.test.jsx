import React from 'react'
import { act, render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import EditorTextarea from '../src/components/editor/EditorTextarea'

const doc = {
  type: 'doc',
  content: [
    {
      type: 'paragraph',
      content: [{ type: 'text', text: 'Remote cursor coverage matters.' }],
    },
  ],
}

describe('EditorTextarea remote cursor rendering', () => {
  it('renders collaborator cursor labels inside the editor', async () => {
    const { container } = render(
      <EditorTextarea
        content={doc}
        canEdit
        role="editor"
        remoteCursors={{
          7: { start: 1, end: 7, name: 'Nora' },
        }}
        onChange={() => {}}
        onCursorChange={() => {}}
        onSelectionChange={() => {}}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('Nora')).toBeInTheDocument()
    })
    expect(container.querySelector('.remote-selection')).toBeTruthy()
  })

  it('merges concurrent snapshots from two editor instances', async () => {
    const firstRef = React.createRef()
    const secondRef = React.createRef()

    render(
      <div>
        <EditorTextarea
          ref={firstRef}
          content={doc}
          canEdit
          role="editor"
          remoteCursors={{}}
          onChange={() => {}}
          onCollabUpdate={() => {}}
          onInitialSnapshot={() => {}}
          onCursorChange={() => {}}
          onSelectionChange={() => {}}
        />
        <EditorTextarea
          ref={secondRef}
          content={doc}
          canEdit
          role="editor"
          remoteCursors={{}}
          onChange={() => {}}
          onCollabUpdate={() => {}}
          onInitialSnapshot={() => {}}
          onCursorChange={() => {}}
          onSelectionChange={() => {}}
        />
      </div>,
    )

    await waitFor(() => {
      expect(firstRef.current?.getFullSyncUpdate()).toBeTruthy()
      expect(secondRef.current?.getFullSyncUpdate()).toBeTruthy()
    })

    let firstSnapshot
    let secondSnapshot

    await act(async () => {
      firstRef.current.insertAtRange({ start: 1, end: 1 }, 'Alice ')
      firstSnapshot = firstRef.current.getFullSyncUpdate()

      secondRef.current.insertAtRange({ start: 1, end: 1 }, 'Bob ')
      secondSnapshot = secondRef.current.getFullSyncUpdate()

      firstRef.current.applyRemoteUpdate(secondSnapshot)
      secondRef.current.applyRemoteUpdate(firstSnapshot)
    })

    await waitFor(() => {
      const firstText = firstRef.current.getEditor().getText()
      const secondText = secondRef.current.getEditor().getText()
      expect(firstText).toContain('Alice')
      expect(firstText).toContain('Bob')
      expect(secondText).toContain('Alice')
      expect(secondText).toContain('Bob')
      expect(secondText).toBe(firstText)
    })
  })
})
