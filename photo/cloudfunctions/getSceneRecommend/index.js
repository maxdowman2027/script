const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

exports.main = async (event) => {
  const sceneTag = event.sceneTag || ''
  const sceneKey = event.sceneKey || ''
  const limit = Math.min(Number(event.limit) || 3, 6)
  try {
    let where = { status: 'published' }
    if (sceneTag && sceneTag !== 'general') {
      where = {
        status: 'published',
        sceneTags: sceneTag
      }
    } else if (sceneKey) {
      where = {
        status: 'published',
        sceneKey: db.RegExp({ regexp: '^' + String(sceneKey).split('|')[0], options: 'i' })
      }
    }
    let res = await db.collection('photos').where(where).orderBy('likeCount', 'desc').limit(limit).get()
    if (!res.data.length) {
      res = await db.collection('photos').where({ status: 'published' }).orderBy('likeCount', 'desc').limit(limit).get()
    }
    return { ok: true, list: res.data, fallback: !sceneTag || sceneTag === 'general' }
  } catch (err) {
    return { ok: false, code: 'NETWORK', message: '推荐加载失败' }
  }
}
