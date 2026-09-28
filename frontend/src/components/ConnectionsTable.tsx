import type { AnalysisConnection, ComponentEdge } from '../types'

interface MockConnectionsTableProps {
  connections: AnalysisConnection[]
  labelOf: (componentId: string) => string
  edges?: never
}

interface RealConnectionsTableProps {
  edges: ComponentEdge[]
  labelOf: (componentId: string) => string
  connections?: never
}

type ConnectionsTableProps =
  | MockConnectionsTableProps
  | RealConnectionsTableProps

function ConnectionsTable(props: ConnectionsTableProps) {
  const { labelOf } = props

  // Stage B3 real path: all `edges[]` with resolved names, import counts
  // and evidence counts — independent of selection.
  if (props.edges !== undefined) {
    const all = Array.isArray(props.edges) ? props.edges : []
    return (
      <section
        className="connections-table-section"
        aria-label="All connections"
      >
        <h2>Connections ({all.length})</h2>
        {all.length > 0 ? (
          <table className="fallback-table connections-table">
            <thead>
              <tr>
                <th>From</th>
                <th>To</th>
                <th>Imports</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {all.map((e, i) => (
                <tr key={`${e?.source_id}-${e?.target_id}-${i}`}>
                  <td>{labelOf(e.source_id)}</td>
                  <td>{labelOf(e.target_id)}</td>
                  <td>{e.import_count}</td>
                  <td>{Array.isArray(e.evidence) ? e.evidence.length : 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="empty-note">no connections</p>
        )}
      </section>
    )
  }

  // Legacy mock path (Compare tab) — unchanged.
  const all = Array.isArray(props.connections) ? props.connections : []

  return (
    <section className="connections-table-section" aria-label="All connections">
      <h2>Connections</h2>
      {all.length > 0 ? (
        <table className="fallback-table connections-table">
          <thead>
            <tr>
              <th>From</th>
              <th>To</th>
              <th>Weight</th>
            </tr>
          </thead>
          <tbody>
            {all.map((c, i) => (
              <tr key={`${c?.from}-${c?.to}-${i}`}>
                <td>{labelOf(c.from)}</td>
                <td>{labelOf(c.to)}</td>
                <td>{c.weight}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty-note">none</p>
      )}
    </section>
  )
}

export default ConnectionsTable
