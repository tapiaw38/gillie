import { describe, it, expect } from 'vitest'
import { findUnresolvedParams, orderNodesByGraph } from '@/components/workflow/workflowGraph'
import type { WorkflowStep } from '@/types/workflow.types'

const node = (id: string) => ({ id })

const step = (partial: Partial<WorkflowStep> & { name: string }): WorkflowStep => ({
  description: '',
  url: 'https://api.test/x',
  method: 'GET',
  required_params: [],
  ...partial,
})

describe('orderNodesByGraph', () => {
  it('follows the arrows instead of the order nodes were created in', () => {
    const nodes = [node('c'), node('a'), node('b')]
    const edges = [
      { source: 'a', target: 'b' },
      { source: 'b', target: 'c' },
    ]

    expect(orderNodesByGraph(nodes, edges).map((n) => n.id)).toEqual(['a', 'b', 'c'])
  })

  it('keeps unconnected nodes rather than dropping them', () => {
    const nodes = [node('a'), node('b'), node('loose')]
    const edges = [{ source: 'a', target: 'b' }]

    expect(orderNodesByGraph(nodes, edges).map((n) => n.id).sort()).toEqual(['a', 'b', 'loose'])
  })

  it('survives a cycle without losing a step', () => {
    const nodes = [node('a'), node('b')]
    const edges = [
      { source: 'a', target: 'b' },
      { source: 'b', target: 'a' },
    ]

    expect(orderNodesByGraph(nodes, edges)).toHaveLength(2)
  })

  it('ignores edges pointing at nodes that no longer exist', () => {
    const nodes = [node('a')]
    const edges = [{ source: 'a', target: 'deleted' }]

    expect(orderNodesByGraph(nodes, edges).map((n) => n.id)).toEqual(['a'])
  })
})

describe('findUnresolvedParams', () => {
  it('flags a placeholder nothing provides', () => {
    const steps = [step({ name: 'charge', url: 'https://api.test/b/{booking_id}' })]

    expect(findUnresolvedParams(steps, [])).toEqual(['booking_id'])
  })

  it('accepts a value mapped by an earlier step', () => {
    const steps = [
      step({ name: 'create', response_mapping: { booking_id: 'data.id' } }),
      step({ name: 'charge', url: 'https://api.test/b/{booking_id}' }),
    ]

    expect(findUnresolvedParams(steps, [])).toEqual([])
  })

  it('does not flag the values the engine always injects', () => {
    const steps = [
      step({ name: 'me', url: 'https://api.test/{user_id}', headers: { A: 'Bearer {auth_token}' } }),
    ]

    expect(findUnresolvedParams(steps, [])).toEqual([])
  })

  it('checks the body template too', () => {
    const steps = [step({ name: 'send', body_template: '{"to": "{email}"}' })]

    expect(findUnresolvedParams(steps, [])).toEqual(['email'])
  })

  it('only looks backwards, never at a later step', () => {
    const steps = [
      step({ name: 'charge', url: 'https://api.test/b/{booking_id}' }),
      step({ name: 'create', response_mapping: { booking_id: 'data.id' } }),
    ]

    expect(findUnresolvedParams(steps, [])).toEqual(['booking_id'])
  })
})
