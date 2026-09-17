const nav = require('../../../contracts/navigation')
const cloud = require('../../../utils/cloud')
const { compressImage } = require('../../../utils/compress')
const { createLock } = require('../../../utils/debounce')
const { showError } = require('../../../utils/error')
const { containsBlockWord } = require('../../../utils/security')
const { PUBLISH_TAGS } = require('../../../constants/tags')
const cache = require('../../../utils/cache')
const config = require('../../../config')

const publishLock = createLock()

Page({
  data: {
    ok: true,
    error: '',
    tempFilePath: '',
    title: '',
    allTags: PUBLISH_TAGS,
    selectedMap: {},
    customTag: '',
    publishing: false,
    payload: null
  },

  onLoad() {
    const res = nav.readPreviewPayload()
    if (!res.ok) {
      this.setData({ ok: false, error: res.error })
      return
    }
    const payload = res.data
    const selectedMap = {}
    ;(payload.sceneTags || []).forEach((tag) => {
      selectedMap[tag] = true
    })
    this.setData({
      ok: true,
      tempFilePath: payload.tempFilePath,
      payload: payload,
      selectedMap: selectedMap
    })
  },

  onUnload() {
    if (!this.data.publishing) {
      nav.clearPreviewPayload()
    }
  },

  onBackCamera() {
    wx.navigateBack({ fail: () => nav.toCamera({ from: 'preview' }) })
  },

  onTitle(e) {
    this.setData({ title: e.detail.value })
  },

  onCustomInput(e) {
    this.setData({ customTag: e.detail.value })
  },

  onToggleTag(e) {
    const tag = e.currentTarget.dataset.tag
    const selectedMap = Object.assign({}, this.data.selectedMap)
    if (selectedMap[tag]) delete selectedMap[tag]
    else selectedMap[tag] = true
    this.setData({ selectedMap: selectedMap })
  },

  onAddCustom(e) {
    const tag = String((e.detail && e.detail.value) || this.data.customTag || '').trim()
    if (!tag) return
    if (containsBlockWord(tag)) {
      showError('SECURITY_FAIL')
      return
    }
    const selectedMap = Object.assign({}, this.data.selectedMap)
    selectedMap[tag] = true
    const allTags = this.data.allTags.indexOf(tag) >= 0 ? this.data.allTags : this.data.allTags.concat([tag])
    this.setData({ selectedMap: selectedMap, allTags: allTags, customTag: '' })
  },

  selectedTags() {
    return Object.keys(this.data.selectedMap)
  },

  async onPublish() {
    if (this.data.publishing || !publishLock.acquire('publish')) return
    const payload = this.data.payload
    if (!payload || !this.data.tempFilePath) {
      publishLock.release('publish')
      showError('MISSING_IMAGE')
      return
    }
    const tags = this.selectedTags()
    const title = (this.data.title || '').trim() || '未命名作品'
    if (containsBlockWord(title) || containsBlockWord(tags.join(' '))) {
      publishLock.release('publish')
      showError('SECURITY_FAIL')
      return
    }
    this.setData({ publishing: true })
    try {
      const compressed = await compressImage(this.data.tempFilePath, config.compressQuality)
      const thumb = await compressImage(compressed, config.thumbQuality)
      const stamp = Date.now()
      const uploaded = await cloud.uploadFile(`photos/${stamp}.jpg`, compressed)
      const uploadedThumb = await cloud.uploadFile(`photos/${stamp}_thumb.jpg`, thumb)
      const res = await cloud.call('publishPhoto', {
        fileID: uploaded.fileID,
        thumbFileID: uploadedThumb.fileID,
        tempFilePath: compressed,
        tags: tags,
        title: title,
        sceneKey: payload.sceneKey,
        sceneTags: payload.sceneTags || tags,
        geo: payload.geo,
        width: payload.width,
        height: payload.height
      })
      const mine = cache.readMyPosts()
      cache.saveMyPosts([{
        _id: res.photoId,
        title: title,
        tags: tags,
        coverUrl: compressed,
        likeCount: 0,
        status: 'published',
        createdAt: Date.now()
      }].concat(mine))
      nav.clearPreviewPayload()
      nav.backToIndexAfterPublish(res.photoId)
    } catch (err) {
      showError((err && err.code) || 'PUBLISH_FAIL')
      this.setData({ publishing: false })
    } finally {
      publishLock.release('publish')
    }
  }
})
