const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

exports.main = async () => {
  const { OPENID } = cloud.getWXContext()
  if (!OPENID) {
    return { ok: false, code: 'AUTH', message: '登录失败' }
  }
  try {
    const users = db.collection('users')
    const existed = await users.where({ _openid: OPENID }).limit(1).get()
    let profile = existed.data[0]
    if (!profile) {
      await users.add({
        data: {
          nickName: '摄影师',
          avatarUrl: '',
          createdAt: Date.now(),
          postCount: 0
        }
      })
      profile = { nickName: '摄影师', avatarUrl: '' }
    }
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
