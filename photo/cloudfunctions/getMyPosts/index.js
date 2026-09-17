const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

exports.main = async () => {
  const { OPENID } = cloud.getWXContext()
  if (!OPENID) {
    return { ok: false, code: 'AUTH', message: '登录失败' }
  }
  try {
    const res = await db.collection('photos')
      .where({ ownerId: OPENID })
      .orderBy('createdAt', 'desc')
      .limit(50)
      .get()
    return { ok: true, list: res.data || [] }
  } catch (err) {
    return { ok: false, code: 'NETWORK', message: '作品加载失败' }
  }
}
