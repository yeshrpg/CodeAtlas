import type { ImportRef } from '../types'

interface UnresolvedImportsProps {
  imports: ImportRef[] | null | undefined
}

/**
 * Stage B5: honest display of imports the backend couldn't resolve — shown
 * plainly, never guessed. Always visible in real mode (like ConnectionsTable),
 * never tied to component selection. Neutral/informational styling: this is
 * intentional reporting, not an error state.
 */
function UnresolvedImports({ imports }: UnresolvedImportsProps) {
  // Defend against missing data — the type says present, runtime may vary.
  const all = Array.isArray(imports) ? imports : []

  return (
    <section className="unresolved-section" aria-label="Unresolved imports">
      <h2>Unresolved imports ({all.length})</h2>
      {all.length === 0 ? (
        <p className="empty-note">
          No unresolved imports — every import resolved to a file in the repo.
        </p>
      ) : (
        <>
          <p className="empty-note">
            Imports the analyzer couldn&apos;t match to a file in the repo —
            shown as-is, never guessed.
          </p>
          <details>
            <summary>
              Show {all.length} unresolved{' '}
              {all.length === 1 ? 'import' : 'imports'}
            </summary>
            <ul className="evidence-list">
              {all.map((imp, i) => (
                <li key={`${imp.module}:${imp.line}:${i}`}>
                  <code>{imp.raw}</code>{' '}
                  <span className="unresolved-meta">
                    line {imp.line} · module {imp.module}
                  </span>
                </li>
              ))}
            </ul>
          </details>
        </>
      )}
    </section>
  )
}

export default UnresolvedImports
