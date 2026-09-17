const cloud = require('../../../utils/cloud')
const cache = require('../../../utils/cache')
const nav = require('../../../contracts/navigation')
const likeUtil = require('../../../utils/like')
const { createLock } = require('../../../utils/debounce')
const { showError } = require('../../../utils/error')

const likeLock = createLock()

Page({
  data: {
    user: {},
    list: [],
    loading: false,
    fromCache: false,
    cloudTip: '',
    likeBusyMap: {}
  },

  onShow() {
    const app = getApp()
    this.setData({
      user: (app && app.globalData && app.globalData.user) || {},
      cloudTip: cloud.isMock() ? '当前为本地 Mock，配置 cloudEnvId 后接入云开发' : '已连接云开发'
    })
    this.loadMine()
  },

  onPullDownRefresh() {
    this.loadMine().finally(() => wx.stopPullDownRefresh())
  },

  async loadMine() {
    this.setData({ loading: true })
    try {
      const res = await cloud.call('getMyPosts', {})
      const list = res.list || []
      this.setData({ list: list, loading: false, fromCache: false })
      cache.saveMyPosts(list)
    } catch (err) {
      const cached = cache.readMyPosts()
      this.setData({
        list: cached,
        loading: false,
        fromCache: !!cached.length
      })
      if (!cached.length) showError((err && err.code) || 'NETWORK')
    }
  },

  onOpenDetail(e) {
    nav.toDetail(e.detail.photoId)
  },

  onShoot() {
    nav.toCamera({ from: 'me' })
  },

  async onLike(e) {
    const photoId = e.detail.photoId
    if (!likeLock.acquire(photoId)) return
    const map = Object.assign({}, this.data.likeBusyMap, { [photoId]: true })
    this.setData({ likeBusyMap: map })
    const current = this.data.list.find((item) => item._id === photoId) || {}
    this.setData({
      list: likeUtil.applyLikeToList(
        this.data.list,
        photoId,
        !current.liked,
        Math.max(0, (current.likeCount || 0) + (current.liked ? -1 : 1))
      )
    })
    try {
      const res = await likeUtil.toggleLike(photoId, current.liked, current.likeCount || 0)
      this.setData({
        list: likeUtil.applyLikeToList(this.data.list, photoId, res.liked, res.likeCount)
      })
    } catch (err) {
      this.setData({
        list: likeUtil.applyLikeToList(this.data.list, photoId, current.liked, current.likeCount || 0)
      })
    } finally {
      const nextMap = Object.assign({}, this.data.likeBusyMap)
      delete nextMap[photoId]
      this.setData({ likeBusyMap: nextMap })
      likeLock.release(photoId)
    }
  }
})
