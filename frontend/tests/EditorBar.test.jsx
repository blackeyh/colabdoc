import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import EditorBar from '../src/components/editor/EditorBar'

const baseProps = {
  doc: { title: 'My Doc' },
  role: 'editor',
  canEdit: true,
  onBack: () => {},
  onSaveTitle: () => {},
  onSaveVersion: () => {},
  onExport: () => {},
}

describe('EditorBar status labels', () => {
  it('renders the Saving label', () => {
    render(<EditorBar {...baseProps} wsStatus="saving" />)
    expect(screen.getByText(/Saving/i)).toBeInTheDocument()
  })

  it('renders the Saved label', () => {
    render(<EditorBar {...baseProps} wsStatus="saved" />)
    expect(screen.getByText(/^Saved$/)).toBeInTheDocument()
  })

  it('renders the Offline label with queued message', () => {
    render(<EditorBar {...baseProps} wsStatus="offline" />)
    expect(screen.getByText(/Offline/i)).toBeInTheDocument()
    expect(screen.getByText(/edits queued/i)).toBeInTheDocument()
  })

  it('renders the Save failed label for error', () => {
    render(<EditorBar {...baseProps} wsStatus="error" />)
    expect(screen.getByText(/Save failed/i)).toBeInTheDocument()
  })

  it('renders the Disconnected label', () => {
    render(<EditorBar {...baseProps} wsStatus="disconnected" />)
    expect(screen.getByText(/Disconnected/i)).toBeInTheDocument()
  })

  it('renders the role badge', () => {
    render(<EditorBar {...baseProps} wsStatus="connected" role="commenter" />)
    expect(screen.getByText('commenter')).toBeInTheDocument()
  })

  it('renders export controls for accessible documents', () => {
    render(<EditorBar {...baseProps} wsStatus="connected" canEdit={false} role="viewer" />)
    expect(screen.getByLabelText(/Export format/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Export/i })).toBeInTheDocument()
  })

  it('calls onExport with the selected format', async () => {
    const onExport = vi.fn()
    const user = userEvent.setup()
    render(<EditorBar {...baseProps} wsStatus="connected" onExport={onExport} />)

    await user.selectOptions(screen.getByLabelText(/Export format/i), 'txt')
    await user.click(screen.getByRole('button', { name: /Export/i }))

    expect(onExport).toHaveBeenCalledWith('txt')
  })
})
