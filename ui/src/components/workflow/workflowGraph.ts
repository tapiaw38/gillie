import type { WorkflowStep } from '@/types/workflow.types'

export interface GraphNode {
  id: string
}

export interface GraphEdge {
  source: string
  target: string
}

/**
 * Order nodes by following the edges the user drew.
 *
 * The backend runs steps as a flat list, so what leaves the editor has to be
 * that list in the order the arrows describe. Exporting the raw node array
 * meant execution followed the order nodes happened to be created in, and the
 * connections on screen decided nothing.
 *
 * Nodes left over by a cycle are appended so nothing silently disappears.
 */
export const orderNodesByGraph = <T extends GraphNode>(nodes: T[], edges: GraphEdge[]): T[] => {
  const incoming = new Map<string, number>(nodes.map((n) => [n.id, 0]))
  const outgoing = new Map<string, string[]>(nodes.map((n) => [n.id, []]))

  for (const edge of edges) {
    if (!incoming.has(edge.target) || !outgoing.has(edge.source)) continue
    incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1)
    outgoing.get(edge.source)!.push(edge.target)
  }

  const byId = new Map(nodes.map((n) => [n.id, n]))
  const queue = nodes.filter((n) => incoming.get(n.id) === 0).map((n) => n.id)
  const sorted: T[] = []

  while (queue.length) {
    const id = queue.shift()!
    const node = byId.get(id)
    if (node) sorted.push(node)
    for (const next of outgoing.get(id) ?? []) {
      const left = (incoming.get(next) ?? 1) - 1
      incoming.set(next, left)
      if (left === 0) queue.push(next)
    }
  }

  if (sorted.length < nodes.length) {
    for (const node of nodes) {
      if (!sorted.includes(node)) sorted.push(node)
    }
  }
  return sorted
}

const PLACEHOLDER_RE = /\{([A-Za-z_][A-Za-z0-9_]*)\}/g

/** Values the engine puts in the context of every run. */
const IMPLICIT_PARAMS = ['user_id', 'profile_id', 'auth_token']

/**
 * Placeholders a step uses that nothing before it provides.
 *
 * Without this the mistake only surfaces at runtime, as a request sent to a
 * URL with `{token}` still in it.
 */
export const findUnresolvedParams = (steps: WorkflowStep[], inputParams: string[] = []): string[] => {
  const available = new Set([...inputParams, ...IMPLICIT_PARAMS])
  const unresolved = new Set<string>()

  for (const step of steps) {
    const text = [step.url, step.body_template ?? '', ...Object.values(step.headers ?? {})].join(' ')
    for (const match of text.matchAll(PLACEHOLDER_RE)) {
      if (!available.has(match[1])) unresolved.add(match[1])
    }
    for (const key of Object.keys(step.response_mapping ?? {})) available.add(key)
  }
  return [...unresolved]
}
