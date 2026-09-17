const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

async function loadOrCreateUser(openid) {
  const ref = db.collection('users').doc(openid)
  try {
    const got = await ref.get()
    if (got && got.data) {
      return got.data
    }
  } catch (e) {
    // missing doc
  }
  const old = await db.collection('users').where({ _openid: openid }).limit(1).get()
  const base = {
    nickName: (old.data[0] && old.data[0].nickName) || '摄影师',
    avatarUrl: (old.data[0] && old.data[0].avatarUrl) || '',
    createdAt: (old.data[0] && old.data[0].createdAt) || Date.now(),
    postCount: (old.data[0] && old.data[0].postCount) || 0,
    lastPublishAt: (old.data[0] && old.data[0].lastPublishAt) || 0
  }
  await ref.set({ data: base })
  return base
}

exports.main = async () => {
  const { OPENID } = cloud.getWXContext()
  if (!OPENID) {
    return { ok: false, code: 'AUTH', message: '登录失败' }
  }
  try {
    const profile = await loadOrCreateUser(OPENID)
    const likes = await db.collection('likes').where({ _openid: OPENID }).field({ photoId: true }).get()
    return {
      ok: true,
      isMock: false,
      openid: OPENID,
      nickName: profile.nickName || '摄影师',
      avatarUrl: profile.avatarUrl || '',
      likedIds: (likes.data || []).map((item) => item.photoId)
    }
  } catch (err) {
    return { ok: false, code: 'DB', message: '用户初始化失败' }
  }
}
