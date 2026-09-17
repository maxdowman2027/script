const nav = require('../../../contracts/navigation')
const cloud = require('../../../utils/cloud')
const { buildSceneKey } = require('../../../utils/scene')
const { compressImage } = require('../../../utils/compress')
const { createLock, debounce } = require('../../../utils/debounce')
const { showError, MESSAGES } = require('../../../utils/error')
const { SCENE_TAGS } = require('../../../constants/tags')
const config = require('../../../config')

const shutterLock = createLock()

Page({
  data: {
    cameraOk: true,
    cameraError: MESSAGES.PERMISSION_CAMERA,
    devicePosition: 'back',
    sceneTags: SCENE_TAGS,
    sceneTag: '风景',
    sceneHint: '',
    recommends: [],
    capturing: false,
    geo: null
  },

  onLoad(options) {
    const sceneHint = (options && options.sceneHint) || ''
    const sceneTag = SCENE_TAGS.indexOf(sceneHint) >= 0 ? sceneHint : '风景'
    this.setData({ sceneHint: sceneHint, sceneTag: sceneTag })
    this.fetchRecommendDebounced = debounce(this.fetchRecommend.bind(this), 500)
    this.ensureCamera()
    this.tryLocation()
    this.fetchRecommend()
  },

  ensureCamera() {
    wx.getSetting({
      success: (res) => {
        const ok = !res.authSetting || res.authSetting['scope.camera'] !== false
        if (!ok) {
          this.setData({ cameraOk: false, cameraError: MESSAGES.PERMISSION_CAMERA })
        }
      }
    })
  },

  tryLocation() {
    wx.getLocation({
      type: 'gcj02',
      success: (res) => {
        this.setData({
          geo: { latitude: res.latitude, longitude: res.longitude }
        })
        this.fetchRecommendDebounced()
      },
      fail: () => {
        wx.showToast({ title: MESSAGES.PERMISSION_LOCATION, icon: 'none' })
      }
    })
  },

  onCameraError() {
    this.setData({ cameraOk: false, cameraError: MESSAGES.PERMISSION_CAMERA })
  },

  onOpenSetting() {
    wx.openSetting({
      success: (res) => {
        if (res.authSetting && res.authSetting['scope.camera']) {
          this.setData({ cameraOk: true })
        }
      }
    })
  },

  onSelectTag(e) {
    const tag = e.currentTarget.dataset.tag
    if (!tag || tag === this.data.sceneTag) return
    this.setData({ sceneTag: tag })
    this.fetchRecommendDebounced()
  },

  onFlip() {
    this.setData({
      devicePosition: this.data.devicePosition === 'back' ? 'front' : 'back'
    })
  },

  onRefreshReco() {
    this.fetchRecommend()
  },

  async fetchRecommend() {
    const sceneKey = buildSceneKey({
      sceneTag: this.data.sceneTag,
      geo: this.data.geo
    })
    try {
      const res = await cloud.call('getSceneRecommend', {
        sceneKey: sceneKey,
        sceneTag: this.data.sceneTag,
        geo: this.data.geo,
        maxDistance: config.geoMaxDistance,
        limit: config.recommendLimit
      })
      this.setData({ recommends: (res.list || []).slice(0, 3) })
    } catch (err) {
      this.setData({ recommends: [] })
    }
  },

  onOpenRecommend(e) {
    const id = e.currentTarget.dataset.id
    if (!id) return
    nav.toDetail(id)
  },

  onShutter() {
    if (this.data.capturing || !this.data.cameraOk) return
    if (!shutterLock.acquire('shutter')) return
    this.setData({ capturing: true })
    const ctx = wx.createCameraContext()
    if (!ctx) {
      this.setData({ capturing: false })
      shutterLock.release('shutter')
      showError('PERMISSION_CAMERA')
      return
    }
    ctx.takePhoto({
      quality: 'high',
      success: (res) => {
        this.afterCapture(res.tempImagePath)
      },
      fail: () => {
        this.setData({ capturing: false })
        shutterLock.release('shutter')
        showError('MISSING_IMAGE')
      }
    })
  },

  async afterCapture(tempImagePath) {
    try {
      const compressed = await compressImage(tempImagePath, config.compressQuality)
      const sceneKey = buildSceneKey({
        sceneTag: this.data.sceneTag,
        geo: this.data.geo
      })
      nav.toPreview({
        tempFilePath: compressed,
        width: 0,
        height: 0,
        sceneKey: sceneKey,
        sceneTags: [this.data.sceneTag],
        geo: this.data.geo,
        recommendIds: this.data.recommends.map((item) => item._id)
      })
    } catch (err) {
      showError('MISSING_IMAGE')
    } finally {
      this.setData({ capturing: false })
      shutterLock.release('shutter')
    }
  }
})
