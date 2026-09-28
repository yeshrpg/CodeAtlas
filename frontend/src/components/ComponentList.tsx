import type { Component } from '../types'
import ComponentBadges from './LabelBadge'

interface ComponentListProps {
  components: Component[]
  selectedId: string | null
  onSelect: (componentId: string) => void
}

/**
 * Stage B3: list-driven drill-down entry point for real analyses. One row
 * per `components[]` entry; clicking a row opens the side panel for that
 * component (replaces node-click for real data).
 */
function ComponentList({ components, selectedId, onSelect }: ComponentListProps) {
  const all = Array.isArray(components) ? components : []

  return (
    <section className="component-list-section" aria-label="Components">
      <h2>Components ({all.length})</h2>
      {all.length > 0 ? (
        <ul className="component-list">
          {all.map((c) => {
            const files = Array.isArray(c.files) ? c.files : []
            const selected = c.id === selectedId
            return (
              <li key={c.id}>
                <button
                  type="button"
                  className={
                    selected ? 'component-row selected' : 'component-row'
                  }
                  aria-current={selected ? 'true' : undefined}
                  onClick={() => onSelect(c.id)}
                >
                  <span className="component-row-main">
                    <strong>{c.label?.name ?? c.id}</strong>
                    <span className="component-row-summary">
                      {c.label?.summary ?? ''}
                    </span>
                  </span>
                  <span className="component-row-meta">
                    <span className="stat-chip">
                      {files.length} {files.length === 1 ? 'file' : 'files'}
                    </span>
                    <span className="component-row-path">{c.folder_path}</span>
                    <ComponentBadges
                      source={c.label?.source}
                      isOtherMerge={c.is_other_merge}
                    />
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      ) : (
        <p className="empty-note">no components</p>
      )}
    </section>
  )
}

export default ComponentList
