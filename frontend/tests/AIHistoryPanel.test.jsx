import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../src/api', () => ({
  apiFetch: vi.fn(),
}))

import AIHistoryPanel from '../src/components/editor/sidebar/AIHistoryPanel'
import { apiFetch } from '../src/api'

describe('AIHistoryPanel', () => {
  beforeEach(() => {
    apiFetch.mockReset()
  })

  it('renders document-level AI metadata and details', async () => {
    apiFetch.mockResolvedValueOnce({
      total: 1,
      history: [
        {
          id: 4,
          user_name: 'Alice',
          action: 'rewrite',
          selected_text: 'Original snippet',
          prompt_text: 'Prompt body',
          provider_name: 'null',
          model_name: 'null-provider',
          suggestion: 'Suggested rewrite',
          status: 'completed',
          user_action: 'accepted',
          final_text: 'Suggested rewrite',
          created_at: '2026-04-19T08:00:00Z',
        },
      ],
    })

    render(<AIHistoryPanel docId={42} enabled />)

    expect(await screen.findByText(/Alice/)).toBeInTheDocument()
    expect(screen.getByText(/null-provider/)).toBeInTheDocument()
    expect(screen.getByText(/Original snippet/)).toBeInTheDocument()
    expect(screen.getByText('Details')).toBeInTheDocument()
  })
})
