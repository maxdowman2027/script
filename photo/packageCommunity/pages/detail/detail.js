const cloud = require('../../../utils/cloud')
const likeUtil = require('../../../utils/like')
const { createLock } = require('../../../utils/debounce')
const { showError } = require('../../../utils/error')
const nav = require('../../../contracts/navigation')

const likeLock = createLock()

Page({
  data: {
    photo: null,
    loading: true,
    likeBusy: false
  },

  onLoad(options) {
    this.photoId = options && options.photoId
    this.fetchDetail()
  },

  onBack() {
    wx.navigateBack({
      fail() {
        wx.reLaunch({ url: nav.ROUTES.index })
      }
    })
  },

  onImgError() {
    const photo = Object.assign({}, this.data.photo, { coverUrl: '', fileID: '' })
    this.setData({ photo: photo })
  },

  async fetchDetail() {
    if (!this.photoId) {
      this.setData({ loading: false, photo: null })
      return
    }
    this.setData({ loading: true })
    try {
      const res = await cloud.call('getPhotoDetail', { photoId: this.photoId })
      this.setData({ photo: res.photo, loading: false })
    } catch (err) {
      this.setData({ loading: false, photo: null })
      showError((err && err.code) || 'NOT_FOUND')
    }
  },

  async onLike() {
    const photo = this.data.photo
    if (!photo || this.data.likeBusy || !likeLock.acquire(photo._id)) return
    this.setData({
      likeBusy: true,
      photo: Object.assign({}, photo, {
        liked: !photo.liked,
        likeCount: Math.max(0, (photo.likeCount || 0) + (photo.liked ? -1 : 1))
      })
    })
    try {
      const res = await likeUtil.toggleLike(photo._id, photo.liked, photo.likeCount || 0)
      this.setData({
        photo: Object.assign({}, this.data.photo, { liked: res.liked, likeCount: res.likeCount })
      })
    } catch (err) {
      this.setData({ photo: photo })
    } finally {
      this.setData({ likeBusy: false })
      likeLock.release(photo._id)
    }
  }
})
