const { wrap } = require('./error')
const config = require('../config')

function sleep(ms) {
  return new Promise(function (resolve) {
    setTimeout(resolve, ms)
  })
}

async function withRetry(task, options) {
  const retries = options && options.retries != null ? options.retries : config.requestRetries
  const delay = (options && options.delay) || 400
  let lastErr = null
  for (let i = 0; i <= retries; i += 1) {
    try {
      return await task(i)
    } catch (err) {
      lastErr = wrap(err)
      if (i === retries) break
      await sleep(delay * (i + 1))
    }
  }
  throw lastErr
}

module.exports = { withRetry, sleep }
