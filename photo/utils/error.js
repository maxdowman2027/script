const MESSAGES = {
  NETWORK: '网络异常，请稍后重试',
  EMPTY: '暂无内容',
  TIMEOUT: '请求超时，请检查网络',
  AUTH: '登录未完成，部分功能暂不可用',
  PERMISSION_CAMERA: '需要相机权限才能拍摄',
  PERMISSION_LOCATION: '未授权定位，将使用通用场景推荐',
  PUBLISH_FAIL: '发布失败，请重试',
  SECURITY_FAIL: '内容未通过安全审核',
  LIKE_FAIL: '点赞同步失败',
  MISSING_IMAGE: '图片丢失，请重新拍摄',
  RATE_LIMIT: '操作过于频繁，请稍后再试',
  NOT_FOUND: '内容不存在或已下架'
}

function showError(codeOrMsg, fallback) {
  const title = MESSAGES[codeOrMsg] || codeOrMsg || fallback || MESSAGES.NETWORK
  wx.showToast({ title, icon: 'none', duration: 2200 })
}

function wrap(err) {
  if (err && err.code && MESSAGES[err.code]) {
    return {
      code: err.code,
      message: err.message || MESSAGES[err.code],
      raw: err
    }
  }
  const msg = (err && (err.errMsg || err.message)) || ''
  if (/timeout/i.test(msg)) {
    return { code: 'TIMEOUT', message: MESSAGES.TIMEOUT, raw: err }
  }
  if (/fail|network/i.test(msg)) {
    return { code: 'NETWORK', message: MESSAGES.NETWORK, raw: err }
  }
  return { code: err && err.code ? err.code : 'UNKNOWN', message: msg || MESSAGES.NETWORK, raw: err }
}

module.exports = { MESSAGES, showError, wrap }
