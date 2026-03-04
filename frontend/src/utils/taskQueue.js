function _toCancelError(reason) {
  const msg = reason ? `TaskQueue cancelled: ${reason}` : 'TaskQueue cancelled'
  const err = new Error(msg)
  err.name = 'TaskQueueCancelledError'
  return err
}

export class TaskQueue {
  constructor() {
    this._running = false
    this._queue = []
    this._cancelToken = 0
  }

  get size() {
    return this._queue.length
  }

  get running() {
    return this._running
  }

  cancel(reason) {
    this._cancelToken += 1
    const err = _toCancelError(reason)
    const pending = this._queue
    this._queue = []
    for (const item of pending) {
      try {
        queueMicrotask(() => {
          try {
            item.reject(err)
          } catch (_) {
            // ignore
          }
        })
      } catch (_) {
        // ignore
      }
    }
  }

  enqueue(taskFn) {
    const fn = typeof taskFn === 'function' ? taskFn : null
    if (!fn) return Promise.reject(new Error('TaskQueue expects a function'))

    const token = this._cancelToken
    const p = new Promise((resolve, reject) => {
      this._queue.push({ fn, resolve, reject, token })
      this._pump().catch((e) => {
        // This should never happen because individual tasks are wrapped.
        try {
          reject(e)
        } catch (_) {
          // ignore
        }
      })
    })
    // Mark as handled to avoid "unhandled rejection" warnings when a task is
    // cancelled/rejected before the caller attaches their handler.
    p.catch(() => {})
    return p
  }

  async _pump() {
    if (this._running) return
    this._running = true

    try {
      while (this._queue.length) {
        const item = this._queue.shift()
        if (!item) continue

        if (item.token !== this._cancelToken) {
          item.reject(_toCancelError('cancelled'))
          continue
        }

        try {
          const v = await item.fn()
          item.resolve(v)
        } catch (e) {
          item.reject(e)
        }
      }
    } finally {
      this._running = false
    }
  }
}
