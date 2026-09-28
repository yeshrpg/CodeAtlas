import type { AnalysisConnection, ComponentEdge } from '../types'
import { incomingEdges, outgoingEdges } from '../lib/realDrilldown'

interface MockConnectionsListProps {
  componentId: string
  connections: AnalysisConnection[]
  labelOf: (componentId: string) => string
  edges?: never
}

interface RealConnectionsListProps {
  componentId: string
  edges: ComponentEdge[]
  labelOf: (componentId: string) => string
  connections?: never
}

type ConnectionsListProps =
  | MockConnectionsListProps
  | RealConnectionsListProps

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

function RealConnectionItem({
  edge,
  labelOf,
}: {
  edge: ComponentEdge
  labelOf: (componentId: string) => string
}) {
  // Evidence is a flat array of "path:line" strings — display as-is.
  const evidence = Array.isArray(edge.evidence) ? edge.evidence : []
  return (
    <li className="connection-item">
      <details>
        <summary>
          {labelOf(edge.source_id)} → {labelOf(edge.target_id)}
          <span className="stat-chip weight-chip">
            imports: {edge.import_count}
          </span>
        </summary>
        {evidence.length > 0 ? (
          <ul className="evidence-list">
            {evidence.map((e, i) => (
              <li key={`${e}:${i}`}>
                <code>{e}</code>
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

function ConnectionsList(props: ConnectionsListProps) {
  const { componentId, labelOf } = props

  // Stage B3 real path: filter `edges[]` by id match on either side.
  if (props.edges !== undefined) {
    const incoming = incomingEdges(props.edges, componentId)
    const outgoing = outgoingEdges(props.edges, componentId)
    return (
      <div className="connections-list">
        <h3>Connections</h3>
        {incoming.length + outgoing.length === 0 ? (
          <p className="empty-note">no connections</p>
        ) : (
          <>
            <h4>Incoming ({incoming.length})</h4>
            {incoming.length > 0 ? (
              <ul>
                {incoming.map((e, i) => (
                  <RealConnectionItem
                    key={`${e.source_id}-${e.target_id}-${i}`}
                    edge={e}
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
                {outgoing.map((e, i) => (
                  <RealConnectionItem
                    key={`${e.source_id}-${e.target_id}-${i}`}
                    edge={e}
                    labelOf={labelOf}
                  />
                ))}
              </ul>
            ) : (
              <p className="empty-note">none</p>
            )}
          </>
        )}
      </div>
    )
  }

  // Legacy mock path (Compare tab) — unchanged.
  const all = Array.isArray(props.connections) ? props.connections : []
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
