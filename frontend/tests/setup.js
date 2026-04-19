import '@testing-library/jest-dom/vitest'

if (!globalThis.localStorage || typeof globalThis.localStorage.clear !== 'function') {
  let store = {}
  globalThis.localStorage = {
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null
    },
    setItem(key, value) {
      store[key] = String(value)
    },
    removeItem(key) {
      delete store[key]
    },
    clear() {
      store = {}
    },
    key(index) {
      return Object.keys(store)[index] ?? null
    },
    get length() {
      return Object.keys(store).length
    },
  }
}
