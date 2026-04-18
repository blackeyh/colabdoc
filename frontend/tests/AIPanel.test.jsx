import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../src/api', () => ({
  apiFetch: vi.fn(),
}))

import AIPanel from '../src/components/editor/sidebar/AIPanel'
import { apiFetch } from '../src/api'

const baseProps = {
  docId: 42,
  context: 'the whole document',
  canEdit: true,
  showToast: vi.fn(),
}

describe('AIPanel', () => {
  beforeEach(() => {
    apiFetch.mockReset()
    baseProps.showToast.mockReset?.()
  })

  it('shows a hint when no text is selected', () => {
    render(<AIPanel {...baseProps} selectedText="" onAccept={vi.fn()} />)
    expect(screen.getByText(/Select text in the editor/i)).toBeInTheDocument()
  })

  it('fetches a suggestion and renders the compare view', async () => {
    apiFetch.mockResolvedValueOnce({ id: 7, suggestion: 'improved text' })
    const onAccept = vi.fn()

    render(<AIPanel {...baseProps} selectedText="hello there" onAccept={onAccept} />)

    await userEvent.click(screen.getByRole('button', { name: /Rewrite/i }))

    expect(apiFetch).toHaveBeenCalledWith(
      '/documents/42/ai/assist',
      expect.objectContaining({ method: 'POST' }),
    )
    // Compare view renders the editable suggestion
    expect(await screen.findByDisplayValue('improved text')).toBeInTheDocument()
    expect(screen.getAllByText('hello there').length).toBeGreaterThan(0)
  })

  it('accepting an unedited suggestion logs user_action=accepted', async () => {
    apiFetch
      .mockResolvedValueOnce({ id: 7, suggestion: 'improved text' })
      .mockResolvedValueOnce({}) // resolve
    const onAccept = vi.fn()

    render(<AIPanel {...baseProps} selectedText="hello there" onAccept={onAccept} />)
    await userEvent.click(screen.getByRole('button', { name: /Rewrite/i }))
    await userEvent.click(await screen.findByRole('button', { name: /^Accept$/ }))

    expect(onAccept).toHaveBeenCalledWith('improved text')
    expect(apiFetch).toHaveBeenLastCalledWith(
      '/documents/42/ai/interactions/7/resolve',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('"user_action":"accepted"'),
      }),
    )
  })

  it('editing then accepting logs user_action=edited with edited_text', async () => {
    apiFetch
      .mockResolvedValueOnce({ id: 9, suggestion: 'seed text' })
      .mockResolvedValueOnce({}) // resolve
    const onAccept = vi.fn()

    render(<AIPanel {...baseProps} selectedText="x y z" onAccept={onAccept} />)
    await userEvent.click(screen.getByRole('button', { name: /Summarize/i }))
    const textarea = await screen.findByDisplayValue('seed text')
    await userEvent.clear(textarea)
    await userEvent.type(textarea, 'my edit')
    await userEvent.click(screen.getByRole('button', { name: /Accept edited/i }))

    expect(onAccept).toHaveBeenCalledWith('my edit')
    const lastCall = apiFetch.mock.calls.at(-1)
    expect(lastCall[0]).toBe('/documents/42/ai/interactions/9/resolve')
    expect(lastCall[1].body).toContain('"user_action":"edited"')
    expect(lastCall[1].body).toContain('"edited_text":"my edit"')
  })

  it('rejecting logs user_action=rejected', async () => {
    apiFetch
      .mockResolvedValueOnce({ id: 3, suggestion: 'never used' })
      .mockResolvedValueOnce({}) // resolve

    render(<AIPanel {...baseProps} selectedText="hi" onAccept={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: /Rewrite/i }))
    await userEvent.click(await screen.findByRole('button', { name: /^Reject$/ }))

    const lastCall = apiFetch.mock.calls.at(-1)
    expect(lastCall[0]).toBe('/documents/42/ai/interactions/3/resolve')
    expect(lastCall[1].body).toContain('"user_action":"rejected"')
  })
})
