/**
 * Browser-API helpers for diagram export. Kept separate from the component
 * so the logic is unit-testable; no new dependencies.
 */

/**
 * Copy text to the clipboard. Returns true on success, false when the
 * Clipboard API is unavailable or the write is denied — the caller shows
 * a manual-copy fallback in that case.
 */
export async function copyMermaidCode(text: string): Promise<boolean> {
  try {
    const clipboard = navigator?.clipboard
    if (!clipboard?.writeText) return false
    await clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

/** Serialize an SVG element to an `image/svg+xml` Blob. */
export function serializeSvgToBlob(svgElement: Element): Blob {
  const serialized = new XMLSerializer().serializeToString(svgElement)
  return new Blob([serialized], { type: 'image/svg+xml' })
}

/** Trigger a file download for a Blob via a temporary anchor element. */
export function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
