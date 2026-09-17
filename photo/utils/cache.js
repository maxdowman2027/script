const FEED_KEY = 'feed_cache_v1'
const LIKE_KEY = 'like_set_v1'
const MY_POSTS_KEY = 'my_posts_cache_v1'

function saveFeed(sort, list) {
  try {
    wx.setStorageSync(FEED_KEY, {
      sort: sort,
      list: (list || []).slice(0, 20),
      ts: Date.now()
    })
  } catch (e) {
    // ignore quota errors
  }
}

function readFeed() {
  try {
    return wx.getStorageSync(FEED_KEY) || null
  } catch (e) {
    return null
  }
}

function saveLikes(ids) {
  try {
    const arr = ids && ids.forEach ? Array.from(ids) : ids || []
    wx.setStorageSync(LIKE_KEY, arr)
  } catch (e) {
    // ignore
  }
}

function readLikes() {
  try {
    const arr = wx.getStorageSync(LIKE_KEY) || []
    return Array.isArray(arr) ? arr : []
  } catch (e) {
    return []
  }
}

function saveMyPosts(list) {
  try {
    wx.setStorageSync(MY_POSTS_KEY, (list || []).slice(0, 30))
  } catch (e) {
    // ignore
  }
}

function readMyPosts() {
  try {
    return wx.getStorageSync(MY_POSTS_KEY) || []
  } catch (e) {
    return []
  }
}

module.exports = {
  saveFeed,
  readFeed,
  saveLikes,
  readLikes,
  saveMyPosts,
  readMyPosts
}
