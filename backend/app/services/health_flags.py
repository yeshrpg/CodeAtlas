def _get(obj, *names):
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    raise AttributeError(f"none of {names} found on {obj!r}")

def analyze_health(components, edges):
    ids = {_get(c, "id", "component_id") for c in components}
    edge_pairs = {(_get(e, "source", "from_id", "from_"), _get(e, "target", "to_id", "to_"))
                  for e in edges}

    adj = {i: set() for i in ids}
    for a, b in edge_pairs:
        adj[a].add(b)

    cycles = []
    for start in ids:
        stack = [(start, [start])]
        seen_paths = set()
        while stack:
            node, path = stack.pop()
            for nxt in adj[node]:
                if nxt == start and len(path) > 1:
                    key = tuple(sorted(path))
                    if key not in seen_paths:
                        seen_paths.add(key)
                        cycles.append(path)
                elif nxt not in path:
                    stack.append((nxt, path + [nxt]))

    incoming = {i: 0 for i in ids}
    outgoing = {i: 0 for i in ids}
    for a, b in edge_pairs:
        incoming[b] += 1
        outgoing[a] += 1

    dead = [i for i in ids if incoming[i] == 0 and outgoing[i] == 0]

    return {
        "cycles": cycles,
        "dead_components": dead,
        "summary": f"{len(cycles)} circular dependency group(s), {len(dead)} disconnected/unused component(s)"
    }