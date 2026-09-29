import type { AnalysisResult } from '../types'

export const API_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/** Single synchronous POST /analyze — allow at least 120s for large repos. */
export const ANALYZE_TIMEOUT_MS = 120_000

/** Generic message for HTTP 422 — never expose the raw validation error. */
export const INVALID_REPO_MESSAGE =
  'Could not analyze that repository — please check the repo name and try again.'

/** Thrown by analyzeRepo when the server rejects the request as invalid (422). */
export class AnalyzeValidationError extends Error {
  constructor() {
    super(INVALID_REPO_MESSAGE)
    this.name = 'AnalyzeValidationError'
  }
}

/**
 * Parse whatever the user pastes into separate owner/name strings.
 * Accepts bare `owner/repo`, full `https://github.com/owner/repo` URLs
 * (http, www., trailing slash, `.git` suffix, extra path segments like
 * /tree/<ref>), scheme-less `github.com/owner/repo`, and SSH-style
 * `git@github.com:owner/repo(.git)` pastes. Query strings and fragments
 * copied from browser address bars (`?tab=...`, `#readme`) are ignored,
 * and host matching is case-insensitive.
 * A URL on any other host (e.g. gitlab.com) is rejected — the backend
 * only analyzes GitHub repos, so it must never silently become the owner.
 * Returns null when no owner/name pair can be extracted.
 */
export function parseRepoUrl(input: string): { owner: string; name: string } | null {
  let rest = input.trim()
  if (!rest) return null

  // SSH-style paste: `git@github.com:owner/repo(.git)`.
  const ssh = rest.match(/^git@github\.com:(.+)$/i)
  if (ssh) {
    rest = ssh[1]
  } else {
    const schemeStripped = rest.replace(/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//, '')
    if (schemeStripped !== rest) {
      // A scheme was present, so a host must follow — and only
      // github.com (optionally www.) is accepted.
      const hostMatch = schemeStripped.match(/^(www\.)?github\.com\/(.+)$/i)
      if (!hostMatch) return null
      rest = hostMatch[2]
    } else {
      // No scheme: bare `owner/repo`, or a scheme-less github URL.
      rest = rest.replace(/^www\./i, '').replace(/^github\.com\//i, '')
    }
  }

  // Drop query string / fragment copied from browser address bars.
  rest = rest.split(/[?#]/, 1)[0]
  if (!rest) return null

  // Extra path segments (e.g. /tree/<ref>) are ignored.
  const segments = rest.split('/').filter(Boolean)
  const [owner, name] = segments
  if (!owner || !name) return null
  // A scheme-less `host.tld/owner/repo` paste (e.g. gitlab.com) is not a
  // bare `owner/repo` — its first segment must not look like a hostname.
  if (segments.length > 2 && owner.includes('.')) return null
  // A bare username or anything with whitespace/URL junk is not a repo.
  if (!/^[A-Za-z0-9_.-]+$/.test(owner)) return null
  const cleanName = name.replace(/\.git$/i, '')
  if (!/^[A-Za-z0-9_.-]+$/.test(cleanName)) return null
  return { owner, name: cleanName }
}

/**
 * Wake-up ping for the (cold-starting) backend. Fire-and-forget by design:
 * never blocks the UI and never surfaces errors — a failed ping is skipped
 * silently, it is not a dependency of anything.
 */
export function wakeBackend(): void {
  try {
    void fetch(`${API_URL}/health`, { method: 'GET' }).catch(() => {
      // Intentionally silent — wake-up ping only.
    })
  } catch {
    // fetch itself shouldn't throw synchronously, but stay silent regardless.
  }
}

export interface AnalyzeParams {
  owner: string
  name: string
  ref?: string
}

/**
 * One synchronous POST /analyze call. No polling, no SSE, no job-queue
 * logic — the backend holds the request open until the analysis settles.
 *
 * Request contract (B7 live-verified: the backend 422s anything else and its
 * error detail names `owner`/`name` as required — docs/api-spec.md's
 * `{repo_url}` is stale and does NOT match the deployed backend).
 * Callers pass owner/name separately (parsed from the URL input).
 *
 * Resolves with the full AnalysisResult for ANY settled analysis, including
 * `status: "failed"` (callers must check `result.status`). Rejects on HTTP
 * errors (422 → AnalyzeValidationError), network failures, and timeouts.
 */
export async function analyzeRepo(
  owner: string,
  name: string,
  ref?: string,
): Promise<AnalysisResult> {
  const params: AnalyzeParams = { owner, name }
  const cleanRef = ref?.trim()
  if (cleanRef) params.ref = cleanRef

  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), ANALYZE_TIMEOUT_MS)
  try {
    let res: Response
    try {
      // TEMPORARY DIAGNOSTIC (browser "Failed to fetch" investigation):
      // log the exact request before sending. In particular `apiBase`
      // reveals whether VITE_API_URL is set in this build or the
      // localhost fallback is in effect. Remove once confirmed.
      // eslint-disable-next-line no-console
      console.log('[CodeAtlas diagnostic] POST /analyze request:', {
        url: `${API_URL}/analyze`,
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
        apiBase: API_URL,
        apiBaseFromEnv: import.meta.env.VITE_API_URL ?? '(unset)',
      })
      res = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
        signal: controller.signal,
      })
      // TEMPORARY DIAGNOSTIC: log what came back (if anything did).
      // eslint-disable-next-line no-console
      console.log(
        '[CodeAtlas diagnostic] POST /analyze response:',
        res.status,
        res.statusText,
      )
    } catch (err) {
      // TEMPORARY DIAGNOSTIC: a fetch-level throw (TypeError "Failed to
      // fetch") means the request never got an HTTP response — typically
      // CORS preflight rejection or unreachable base URL. Log verbatim.
      // eslint-disable-next-line no-console
      console.error('[CodeAtlas diagnostic] POST /analyze fetch threw:', err)
      if (err instanceof DOMException && err.name === 'AbortError') {
        throw new Error(
          'Analyze request timed out — the repo may be too large. Please try again.',
        )
      }
      throw new Error(
        err instanceof Error
          ? `Analyze request failed: ${err.message}`
          : 'Analyze request failed: network error',
      )
    }

    if (res.status === 422) throw new AnalyzeValidationError()
    if (!res.ok) {
      throw new Error(`Analyze request failed: ${res.status} ${res.statusText}`)
    }
    return (await res.json()) as AnalysisResult
  } finally {
    window.clearTimeout(timer)
  }
}

/**
 * Pure helper mapping a settled AnalysisResult to the error message that
 * should appear in the error banner, or null when there is no error.
 * `status: "failed"` surfaces the backend's error string verbatim.
 */
export function analyzeResultError(result: AnalysisResult): string | null {
  if (result.status === 'failed') {
    return result.error ?? 'Analysis failed.'
  }
  return null
}
