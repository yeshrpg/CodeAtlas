def analyze_health(components, connections):
    ids = {c["id"] for c in components}
    edges = {(c["from"], c["to"]) for c in connections}

    adj = {i: set() for i in ids}
    for a, b in edges:
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
    for a, b in edges:
        incoming[b] += 1
        outgoing[a] += 1

    dead = [c["id"] for c in components
            if incoming[c["id"]] == 0 and outgoing[c["id"]] == 0]

    return {
        "cycles": cycles,
        "dead_components": dead,
        "summary": f"{len(cycles)} circular dependency group(s), {len(dead)} disconnected/unused component(s)"
    }