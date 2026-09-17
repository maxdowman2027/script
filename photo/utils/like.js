const cloud = require('./cloud')
const cache = require('./cache')
const { showError } = require('./error')

function getLikedIds() {
  const app = getApp()
  return (app && app.globalData && app.globalData.likedIds) || cache.readLikes()
}

function setLikedIds(ids) {
  const app = getApp()
  if (app && app.globalData) {
    app.globalData.likedIds = ids
  }
  cache.saveLikes(ids)
}

function applyLikeToList(list, photoId, liked, likeCount) {
  return (list || []).map((item) => {
    if (item._id !== photoId) return item
    return Object.assign({}, item, { liked: liked, likeCount: likeCount })
  })
}

async function toggleLike(photoId, currentLiked, currentCount) {
  if (!photoId) {
    throw { code: 'LIKE_FAIL' }
  }
  const nextLiked = !currentLiked
  const nextCount = Math.max(0, (currentCount || 0) + (nextLiked ? 1 : -1))
  const ids = getLikedIds().slice()
  if (nextLiked && ids.indexOf(photoId) < 0) ids.push(photoId)
  if (!nextLiked) {
    const idx = ids.indexOf(photoId)
    if (idx >= 0) ids.splice(idx, 1)
  }
  setLikedIds(ids)
  try {
    const res = await cloud.call('toggleLike', { photoId: photoId })
    const liked = res.liked
    const likeCount = res.likeCount
    const confirmed = getLikedIds().slice()
    if (liked && confirmed.indexOf(photoId) < 0) confirmed.push(photoId)
    if (!liked) {
      const i = confirmed.indexOf(photoId)
      if (i >= 0) confirmed.splice(i, 1)
    }
    setLikedIds(confirmed)
    return { liked: liked, likeCount: likeCount }
  } catch (err) {
    const rollback = getLikedIds().slice()
    if (currentLiked && rollback.indexOf(photoId) < 0) rollback.push(photoId)
    if (!currentLiked) {
      const i = rollback.indexOf(photoId)
      if (i >= 0) rollback.splice(i, 1)
    }
    setLikedIds(rollback)
    showError((err && err.code) || 'LIKE_FAIL')
    throw err
  }
}

module.exports = { toggleLike, applyLikeToList, getLikedIds }
