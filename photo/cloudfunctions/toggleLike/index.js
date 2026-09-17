const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()
const _ = db.command

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext()
  const photoId = event.photoId
  if (!OPENID || !photoId) {
    return { ok: false, code: 'LIKE_FAIL', message: '点赞同步失败' }
  }
  const likeId = `${OPENID}_${photoId}`
  try {
    const result = await db.runTransaction(async (transaction) => {
      const photoDoc = await transaction.collection('photos').doc(photoId).get()
      const photo = photoDoc.data
      if (!photo || photo.status !== 'published') {
        throw new Error('NOT_FOUND')
      }
      let liked = false
      try {
        const likeDoc = await transaction.collection('likes').doc(likeId).get()
        liked = !!(likeDoc && likeDoc.data)
      } catch (e) {
        liked = false
      }
      if (liked) {
        await transaction.collection('likes').doc(likeId).remove()
        await transaction.collection('photos').doc(photoId).update({
          data: { likeCount: _.inc(-1) }
        })
        return { liked: false, likeCount: Math.max(0, (photo.likeCount || 0) - 1) }
      }
      await transaction.collection('likes').doc(likeId).set({
        data: {
          photoId: photoId,
          createdAt: Date.now()
        }
      })
      await transaction.collection('photos').doc(photoId).update({
        data: { likeCount: _.inc(1) }
      })
      return { liked: true, likeCount: (photo.likeCount || 0) + 1 }
    })
    return { ok: true, liked: result.liked, likeCount: result.likeCount }
  } catch (err) {
    return { ok: false, code: 'LIKE_FAIL', message: '点赞同步失败' }
  }
}
