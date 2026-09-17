const { withRetry } = require('./request')
const mock = require('./mock-store')

let inited = false
let useMock = true

function getEnvId() {
  try {
    const app = getApp()
    return (app && app.globalData && app.globalData.cloudEnvId) || ''
  } catch (e) {
    return ''
  }
}

function isPlaceholderEnv(envId) {
  return !envId || envId === 'YOUR_CLOUD_ENV_ID'
}

function init() {
  if (inited) return useMock
  const envId = getEnvId()
  if (wx.cloud && !isPlaceholderEnv(envId)) {
    try {
      wx.cloud.init({ env: envId, traceUser: true })
      useMock = false
      inited = true
      return useMock
    } catch (e) {
      useMock = true
    }
  }
  useMock = true
  inited = true
  return useMock
}

function isMock() {
  init()
  return useMock
}

function call(name, data) {
  init()
  if (useMock) {
    return withRetry(function () {
      return mock.invoke(name, data || {})
    }, { retries: 1 })
  }
  return withRetry(function () {
    return new Promise(function (resolve, reject) {
      wx.cloud.callFunction({
        name: name,
        data: data || {},
        success(res) {
          const result = res && res.result
          if (result && result.ok === false) {
            const err = new Error(result.message || 'CLOUD_FAIL')
            err.code = result.code || 'NETWORK'
            reject(err)
            return
          }
          resolve(result)
        },
        fail: reject
      })
    })
  }, { retries: 2 })
}

function uploadFile(cloudPath, filePath) {
  init()
  if (useMock) {
    return mock.uploadFile(cloudPath, filePath)
  }
  return new Promise(function (resolve, reject) {
    wx.cloud.uploadFile({
      cloudPath: cloudPath,
      filePath: filePath,
      success: resolve,
      fail: reject
    })
  })
}

module.exports = { init, isMock, call, uploadFile }
