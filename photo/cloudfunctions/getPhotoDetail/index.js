const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext()
  const photoId = event.photoId
  if (!photoId) {
    return { ok: false, code: 'NOT_FOUND', message: '内容不存在或已下架' }
  }
  try {
    const doc = await db.collection('photos').doc(photoId).get()
    const photo = doc.data
    if (!photo) {
      return { ok: false, code: 'NOT_FOUND', message: '内容不存在或已下架' }
    }
    const isOwner = photo._openid === OPENID || photo.ownerId === OPENID
    if (photo.status !== 'published' && !isOwner) {
      return { ok: false, code: 'NOT_FOUND', message: '内容不存在或已下架' }
    }
    let liked = false
    if (OPENID) {
      const likeRes = await db.collection('likes').where({ _openid: OPENID, photoId: photoId }).limit(1).get()
      liked = !!(likeRes.data && likeRes.data.length)
    }
    return { ok: true, photo: Object.assign({}, photo, { liked: liked }) }
  } catch (err) {
    return { ok: false, code: 'NOT_FOUND', message: '内容不存在或已下架' }
  }
}
