const config = require('./config')
const cloud = require('./utils/cloud')
const cache = require('./utils/cache')
const { showError } = require('./utils/error')

App({
  globalData: {
    cloudEnvId: config.cloudEnvId,
    previewPayload: null,
    user: null,
    likedIds: [],
    booting: true
  },

  onLaunch() {
    this.boot()
  },

  async boot() {
    this.globalData.booting = true
    this.globalData.likedIds = cache.readLikes()
    try {
      cloud.init()
      const res = await cloud.call('login', {})
      this.globalData.user = res || {}
      if (res && Array.isArray(res.likedIds)) {
        this.globalData.likedIds = res.likedIds
        cache.saveLikes(res.likedIds)
      }
    } catch (e) {
      showError('AUTH')
    } finally {
      this.globalData.booting = false
    }
  }
})
