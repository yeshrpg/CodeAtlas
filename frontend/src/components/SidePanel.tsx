import { useEffect, useState } from 'react'
import ConnectionsList from './ConnectionsList'
import ParsedFileView from './ParsedFileView'
import ComponentBadges from './LabelBadge'
import { findParsedFile } from '../lib/realDrilldown'
import type {
  AnalysisComponent,
  AnalysisConnection,
  Component,
  ComponentEdge,
  ParsedFile,
} from '../types'

interface MockSidePanelProps {
  component: AnalysisComponent
  connections: AnalysisConnection[]
  labelOf: (componentId: string) => string
  onClose: () => void
  onOpenDetailView: (componentId: string) => void
  edges?: never
  parsedFiles?: never
}

interface RealSidePanelProps {
  component: Component
  edges: ComponentEdge[]
  parsedFiles: ParsedFile[]
  labelOf: (componentId: string) => string
  onClose: () => void
  onOpenDetailView?: never
  connections?: never
}

type SidePanelProps = MockSidePanelProps | RealSidePanelProps

/**
 * Stage B3 real path: side panel for a real component, opened by
 * ComponentList click (not node click). No L2/detail view — the backend
 * doesn't provide per-component diagram data.
 */
function RealSidePanelContent({
  component,
  edges,
  parsedFiles,
  labelOf,
  onClose,
}: {
  component: Component
  edges: ComponentEdge[]
  parsedFiles: ParsedFile[]
  labelOf: (componentId: string) => string
  onClose: () => void
}) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  // Reset file view whenever a different component is selected.
  useEffect(() => {
    setSelectedFile(null)
  }, [component.id])

  const files = Array.isArray(component.files) ? component.files : []

  return (
    <aside className="side-panel" aria-label="Details panel">
      <div className="side-panel-header">
        <button
          type="button"
          className="error-dismiss"
          onClick={onClose}
          aria-label="Close panel"
        >
          ✕
        </button>
      </div>

      {selectedFile ? (
        <ParsedFileView
          filePath={selectedFile}
          parsed={findParsedFile(parsedFiles, selectedFile)}
          onBack={() => setSelectedFile(null)}
          backLabel={component.label?.name ?? component.id}
        />
      ) : (
        <div className="component-view">
          <h2>{component.label?.name ?? component.id}</h2>
          <p className="component-meta">
            <span className="stat-chip">{component.folder_path}</span>{' '}
            <ComponentBadges
              source={component.label?.source}
              isOtherMerge={component.is_other_merge}
            />
          </p>
          <p>{component.label?.summary ?? ''}</p>

          <h3>Files ({files.length})</h3>
          {files.length > 0 ? (
            <ul className="file-list">
              {files.map((f) => (
                <li key={f}>
                  <button
                    type="button"
                    className="link-button file-button"
                    onClick={() => setSelectedFile(f)}
                  >
                    <code>{f}</code>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-note">none</p>
          )}

          <ConnectionsList
            componentId={component.id}
            edges={edges}
            labelOf={labelOf}
          />
        </div>
      )}
    </aside>
  )
}

function SidePanel(props: SidePanelProps) {
  // Stage B3 real path (Analyze tab, list-driven).
  if (props.edges !== undefined) {
    return (
      <RealSidePanelContent
        component={props.component}
        edges={props.edges}
        parsedFiles={Array.isArray(props.parsedFiles) ? props.parsedFiles : []}
        labelOf={props.labelOf}
        onClose={props.onClose}
      />
    )
  }

  return (
    <MockSidePanel
      component={props.component}
      connections={props.connections}
      labelOf={props.labelOf}
      onClose={props.onClose}
      onOpenDetailView={props.onOpenDetailView}
    />
  )
}

function MockSidePanel({
  component,
  connections,
  labelOf,
  onClose,
  onOpenDetailView,
}: {
  component: AnalysisComponent
  connections: AnalysisConnection[]
  labelOf: (componentId: string) => string
  onClose: () => void
  onOpenDetailView: (componentId: string) => void
}) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  // Reset file view whenever a different component is selected.
  useEffect(() => {
    setSelectedFile(null)
  }, [component.id])

  const files = Array.isArray(component.files) ? component.files : []
  const detail = selectedFile
    ? component.file_details?.[selectedFile]
    : undefined

  return (
    <aside className="side-panel" aria-label="Details panel">
      <div className="side-panel-header">
        <button
          type="button"
          className="error-dismiss"
          onClick={onClose}
          aria-label="Close panel"
        >
          ✕
        </button>
      </div>

      {selectedFile ? (
        <div className="file-view">
          <button
            type="button"
            className="link-button"
            onClick={() => setSelectedFile(null)}
          >
            ← Back to {component.label}
          </button>
          <h2 className="file-path">{selectedFile}</h2>

          <h3>Symbols</h3>
          {detail && detail.symbols.length > 0 ? (
            <ul>
              {detail.symbols.map((s) => (
                <li key={s}>
                  <code>{s}</code>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-note">none</p>
          )}

          <h3>Imports</h3>
          {detail && detail.imports.length > 0 ? (
            <table className="fallback-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Line</th>
                  <th>From</th>
                </tr>
              </thead>
              <tbody>
                {detail.imports.map((imp, i) => (
                  <tr key={`${imp.name}:${imp.line}:${i}`}>
                    <td>
                      <code>{imp.name}</code>
                    </td>
                    <td>{imp.line}</td>
                    <td>{imp.from ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="empty-note">none</p>
          )}

          <h3>Importers</h3>
          {detail && detail.importers.length > 0 ? (
            <ul>
              {detail.importers.map((f) => (
                <li key={f}>
                  <code>{f}</code>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-note">none</p>
          )}
        </div>
      ) : (
        <div className="component-view">
          <h2>{component.label}</h2>
          <p className="component-meta">
            <span className="stat-chip">layer: {component.layer}</span>{' '}
            <span className="stat-chip">
              labels: {component.label_source}
            </span>
          </p>
          <p>{component.summary}</p>

          <h3>Files ({files.length})</h3>
          {files.length > 0 ? (
            <ul className="file-list">
              {files.map((f) => (
                <li key={f}>
                  <button
                    type="button"
                    className="link-button file-button"
                    onClick={() => setSelectedFile(f)}
                  >
                    <code>{f}</code>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-note">none</p>
          )}

          <ConnectionsList
            componentId={component.id}
            connections={connections}
            labelOf={labelOf}
          />

          <button
            type="button"
            className="analyze-button detail-view-button"
            onClick={() => onOpenDetailView(component.id)}
          >
            Open detail view
          </button>
        </div>
      )}
    </aside>
  )
}

export default SidePanel
