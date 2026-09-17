const cloud = require('../../utils/cloud')
const cache = require('../../utils/cache')
const nav = require('../../contracts/navigation')
const likeUtil = require('../../utils/like')
const { createLock, debounce } = require('../../utils/debounce')
const { showError } = require('../../utils/error')
const config = require('../../config')

const likeLock = createLock()

Page({
  data: {
    sort: 'hot',
    list: [],
    hasMore: true,
    loading: false,
    loadError: false,
    fromCache: false,
    shooting: false,
    pageBusy: false,
    likeBusyMap: {}
  },

  cursor: null,

  onLoad(options) {
    this.loadFeedDebounced = debounce(this.loadFeed.bind(this), 280)
    if (options && options.published === '1') {
      wx.showToast({ title: '已发布到社区', icon: 'success' })
    }
    this.resetAndLoad()
  },

  onShow() {
    if (this.data.list.length) return
    this.resetAndLoad()
  },

  onPullDownRefresh() {
    this.resetAndLoad().finally(() => wx.stopPullDownRefresh())
  },

  onReachBottom() {
    if (!this.data.hasMore || this.data.loading) return
    this.loadFeed(false)
  },

  async resetAndLoad() {
    this.cursor = null
    this.setData({ hasMore: true, loadError: false, fromCache: false })
    await this.loadFeed(true)
  },

  async loadFeed(reset) {
    if (this.data.loading) return
    this.setData({ loading: true, loadError: false })
    try {
      const res = await cloud.call('getFeed', {
        sort: this.data.sort,
        pageSize: config.feedPageSize,
        cursor: reset ? null : this.cursor
      })
      const next = res.list || []
      const list = reset ? next : this.data.list.concat(next)
      this.cursor = res.nextCursor || null
      this.setData({
        list: list,
        hasMore: !!res.hasMore,
        loading: false,
        fromCache: false
      })
      if (reset) cache.saveFeed(this.data.sort, list)
    } catch (err) {
      const cached = reset ? cache.readFeed() : null
      if (cached && cached.list && cached.list.length) {
        this.setData({
          list: cached.list,
          loading: false,
          loadError: false,
          hasMore: false,
          fromCache: true
        })
        wx.showToast({ title: '已显示缓存内容', icon: 'none' })
        return
      }
      this.setData({ loading: false, loadError: true })
      showError((err && err.code) || 'NETWORK')
    }
  },

  onSort(e) {
    const sort = e.currentTarget.dataset.sort
    if (!sort || sort === this.data.sort) return
    this.setData({ sort: sort, list: [] })
    this.cursor = null
    this.loadFeedDebounced(true)
  },

  onStartShoot() {
    if (this.data.shooting) return
    this.setData({ shooting: true })
    nav.toCamera({ from: 'index' })
    setTimeout(() => this.setData({ shooting: false }), 600)
  },

  onOpenMe() {
    nav.toMe()
  },

  onOpenDetail(e) {
    nav.toDetail(e.detail.photoId)
  },

  onEmptyAction() {
    if (this.data.loadError) {
      this.resetAndLoad()
      return
    }
    this.onStartShoot()
  },

  async onLike(e) {
    const photoId = e.detail.photoId
    if (!likeLock.acquire(photoId)) return
    const map = Object.assign({}, this.data.likeBusyMap, { [photoId]: true })
    this.setData({ likeBusyMap: map })
    const current = this.data.list.find((item) => item._id === photoId) || {}
    const optimistic = likeUtil.applyLikeToList(
      this.data.list,
      photoId,
      !current.liked,
      Math.max(0, (current.likeCount || 0) + (current.liked ? -1 : 1))
    )
    this.setData({ list: optimistic })
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
