import type { Analysis } from '../types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Static list for now; the real list can come from the backend later.
const DEMO_REPOS = ['demo-fastapi', 'demo-react', 'demo-go-cli']

interface DemoDropdownProps {
  loading: boolean
  onLoadingChange: (loading: boolean) => void
  onResult: (analysis: Analysis) => void
  onError: (message: string) => void
}

function DemoDropdown({
  loading,
  onLoadingChange,
  onResult,
  onError,
}: DemoDropdownProps) {
  const handleSelect = async (name: string) => {
    if (!name || loading) return
    onLoadingChange(true)
    try {
      const res = await fetch(`${API_URL}/demo/${name}`)
      if (!res.ok) {
        onError(`Demo request failed: ${res.status} ${res.statusText}`)
        return
      }
      const data = (await res.json()) as Analysis
      onResult(data)
    } catch (err) {
      onError(
        err instanceof Error
          ? `Demo request failed: ${err.message}`
          : 'Demo request failed: unknown error',
      )
    } finally {
      onLoadingChange(false)
    }
  }

  return (
    <label className="demo-dropdown">
      Demo repos:{' '}
      <select
        defaultValue=""
        disabled={loading}
        onChange={(e) => {
          void handleSelect(e.target.value)
          e.target.value = ''
        }}
      >
        <option value="" disabled>
          Select a demo…
        </option>
        {DEMO_REPOS.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
    </label>
  )
}

export default DemoDropdown
