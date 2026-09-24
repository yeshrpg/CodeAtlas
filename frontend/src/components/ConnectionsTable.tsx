import type { AnalysisConnection } from '../types'

interface ConnectionsTableProps {
  connections: AnalysisConnection[]
  labelOf: (componentId: string) => string
}

function ConnectionsTable({ connections, labelOf }: ConnectionsTableProps) {
  const all = Array.isArray(connections) ? connections : []

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
