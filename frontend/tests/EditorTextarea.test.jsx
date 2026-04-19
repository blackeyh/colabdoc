import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
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
})
