const ROUTES = {
  index: '/pages/index/index',
  camera: '/packageCamera/pages/camera/camera',
  preview: '/packageCamera/pages/preview/preview',
  detail: '/packageCommunity/pages/detail/detail',
  me: '/packageProfile/pages/me/me'
}

function buildQuery(params) {
  return Object.keys(params || {})
    .filter((key) => params[key] !== undefined && params[key] !== null && params[key] !== '')
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(String(params[key]))}`)
    .join('&')
}

function navigate(url, failMsg) {
  wx.navigateTo({
    url,
    fail() {
      wx.showToast({ title: failMsg || '页面打开失败', icon: 'none' })
    }
  })
}

function toCamera(params) {
  const query = buildQuery({
    sceneHint: params && params.sceneHint,
    from: (params && params.from) || 'index'
  })
  navigate(query ? `${ROUTES.camera}?${query}` : ROUTES.camera, '无法打开相机')
}

function toPreview(payload) {
  if (!payload || !payload.tempFilePath) {
    wx.showToast({ title: '缺少预览图片，请重新拍摄', icon: 'none' })
    return
  }
  const app = getApp()
  app.globalData.previewPayload = payload
  const query = buildQuery({
    hasPayload: 1,
    sceneKey: payload.sceneKey,
    width: payload.width,
    height: payload.height
  })
  navigate(`${ROUTES.preview}?${query}`, '无法打开预览')
}

function readPreviewPayload() {
  const app = getApp()
  const payload = app.globalData && app.globalData.previewPayload
  if (!payload || !payload.tempFilePath) {
    return { ok: false, error: '缺少预览图片，请重新拍摄' }
  }
  return { ok: true, data: payload }
}

function clearPreviewPayload() {
  const app = getApp()
  if (app && app.globalData) {
    app.globalData.previewPayload = null
  }
}

function toDetail(photoId) {
  if (!photoId) {
    wx.showToast({ title: '照片不存在', icon: 'none' })
    return
  }
  navigate(`${ROUTES.detail}?photoId=${encodeURIComponent(photoId)}`, '无法打开详情')
}

function toMe() {
  navigate(ROUTES.me, '无法打开个人中心')
}

function backToIndexAfterPublish(photoId) {
  const query = buildQuery({ published: 1, photoId: photoId || '' })
  wx.reLaunch({
    url: query ? `${ROUTES.index}?${query}` : ROUTES.index,
    fail() {
      wx.showToast({ title: '返回首页失败', icon: 'none' })
    }
  })
}

module.exports = {
  ROUTES,
  toCamera,
  toPreview,
  readPreviewPayload,
  clearPreviewPayload,
  toDetail,
  toMe,
  backToIndexAfterPublish
}
