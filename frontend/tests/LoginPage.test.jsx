import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../src/api', () => ({
  apiFetch: vi.fn(),
  setTokens: vi.fn(),
}))

import LoginPage from '../src/components/auth/LoginPage'
import { apiFetch, setTokens } from '../src/api'

describe('LoginPage', () => {
  beforeEach(() => {
    apiFetch.mockReset()
    setTokens.mockReset()
    localStorage.clear()
  })

  it('posts credentials, stores tokens, and invokes onLogin', async () => {
    apiFetch.mockResolvedValueOnce({
      access_token: 'acc-123',
      refresh_token: 'ref-456',
      user: { id: 1, name: 'Alice', email: 'alice@example.com' },
    })
    const onLogin = vi.fn()

    render(<LoginPage onLogin={onLogin} onGoRegister={() => {}} />)

    await userEvent.type(screen.getByPlaceholderText(/you@example\.com/i), 'alice@example.com')
    await userEvent.type(screen.getByPlaceholderText('••••••••'), 'password123')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(apiFetch).toHaveBeenCalledWith(
      '/auth/login',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(setTokens).toHaveBeenCalledWith({
      access_token: 'acc-123',
      refresh_token: 'ref-456',
    })
    expect(onLogin).toHaveBeenCalledWith(
      expect.objectContaining({ email: 'alice@example.com' }),
    )
    expect(localStorage.getItem('user')).toContain('Alice')
  })

  it('shows an error message when the API rejects the login', async () => {
    apiFetch.mockRejectedValueOnce(new Error('Wrong email or password'))
    const onLogin = vi.fn()

    render(<LoginPage onLogin={onLogin} onGoRegister={() => {}} />)

    await userEvent.type(screen.getByPlaceholderText(/you@example\.com/i), 'bad@example.com')
    await userEvent.type(screen.getByPlaceholderText('••••••••'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText(/Wrong email or password/)).toBeInTheDocument()
    expect(onLogin).not.toHaveBeenCalled()
  })
})
