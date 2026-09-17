function debounce(fn, wait) {
  let timer = null
  const waitMs = wait == null ? 300 : wait
  return function debounced() {
    const ctx = this
    const args = arguments
    if (timer) clearTimeout(timer)
    timer = setTimeout(function () {
      timer = null
      fn.apply(ctx, args)
    }, waitMs)
  }
}

function createLock() {
  const inflight = new Set()
  return {
    acquire(key) {
      const lockKey = key == null ? '__default__' : String(key)
      if (inflight.has(lockKey)) return false
      inflight.add(lockKey)
      return true
    },
    release(key) {
      inflight.delete(key == null ? '__default__' : String(key))
    },
    has(key) {
      return inflight.has(key == null ? '__default__' : String(key))
    }
  }
}

module.exports = { debounce, createLock }
