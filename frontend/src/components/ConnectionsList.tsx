import type { AnalysisConnection } from '../types'

interface ConnectionsListProps {
  componentId: string
  connections: AnalysisConnection[]
  labelOf: (componentId: string) => string
}

function ConnectionItem({
  conn,
  labelOf,
}: {
  conn: AnalysisConnection
  labelOf: (componentId: string) => string
}) {
  const evidence = Array.isArray(conn.evidence) ? conn.evidence : []
  return (
    <li className="connection-item">
      <details>
        <summary>
          {labelOf(conn.from)} → {labelOf(conn.to)}
          <span className="stat-chip weight-chip">weight: {conn.weight}</span>
        </summary>
        {evidence.length > 0 ? (
          <ul className="evidence-list">
            {evidence.map((e, i) => (
              <li key={`${e.file}:${e.line}:${i}`}>
                <code>
                  {e.file}:{e.line}
                </code>{' '}
                <span className="evidence-text">{e.text}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="empty-note">none</p>
        )}
      </details>
    </li>
  )
}

function ConnectionsList({
  componentId,
  connections,
  labelOf,
}: ConnectionsListProps) {
  const all = Array.isArray(connections) ? connections : []
  const incoming = all.filter((c) => c && c.to === componentId)
  const outgoing = all.filter((c) => c && c.from === componentId)

  return (
    <div className="connections-list">
      <h3>Connections</h3>
      <h4>Incoming ({incoming.length})</h4>
      {incoming.length > 0 ? (
        <ul>
          {incoming.map((c, i) => (
            <ConnectionItem
              key={`${c.from}-${c.to}-${i}`}
              conn={c}
              labelOf={labelOf}
            />
          ))}
        </ul>
      ) : (
        <p className="empty-note">none</p>
      )}
      <h4>Outgoing ({outgoing.length})</h4>
      {outgoing.length > 0 ? (
        <ul>
          {outgoing.map((c, i) => (
            <ConnectionItem
              key={`${c.from}-${c.to}-${i}`}
              conn={c}
              labelOf={labelOf}
            />
          ))}
        </ul>
      ) : (
        <p className="empty-note">none</p>
      )}
    </div>
  )
}

export default ConnectionsList
