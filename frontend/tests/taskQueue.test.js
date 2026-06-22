import { describe, expect, it, vi } from 'vitest'
import { TaskQueue } from '../src/utils/taskQueue.js'

describe('TaskQueue (Milestone 4)', () => {
  it('runs tasks sequentially in enqueue order', async () => {
    const q = new TaskQueue()
    const calls = []

    const t1 = vi.fn(async () => {
      calls.push('t1:start')
      await new Promise((r) => setTimeout(r, 20))
      calls.push('t1:end')
      return 1
    })

    const t2 = vi.fn(async () => {
      calls.push('t2:start')
      calls.push('t2:end')
      return 2
    })

    const p1 = q.enqueue(t1)
    const p2 = q.enqueue(t2)

    const r1 = await p1
    const r2 = await p2

    expect(r1).toBe(1)
    expect(r2).toBe(2)
    expect(calls).toEqual(['t1:start', 't1:end', 't2:start', 't2:end'])
  })

  it('cancel() skips pending tasks', async () => {
    const q = new TaskQueue()
    const calls = []

    q.enqueue(async () => {
      calls.push('a')
      await new Promise((r) => setTimeout(r, 20))
      calls.push('a:done')
    })

    const p2 = q.enqueue(async () => {
      calls.push('b')
    })

    q.cancel('user')

    await new Promise((r) => setTimeout(r, 35))
    await expect(p2).rejects.toThrow(/cancel/i)
    expect(calls).toEqual(['a', 'a:done'])
  })
})
