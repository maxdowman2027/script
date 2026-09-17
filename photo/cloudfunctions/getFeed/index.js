const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()
const _ = db.command

function encodeCursor(doc) {
  if (!doc) return null
  return {
    id: doc._id,
    createdAt: doc.createdAt,
    likeCount: doc.likeCount || 0
  }
}

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext()
  const sort = event.sort === 'new' ? 'new' : 'hot'
  const pageSize = Math.min(Number(event.pageSize) || 10, 20)
  const cursor = event.cursor || null

  try {
    let query = db.collection('photos').where({ status: 'published' })
    if (sort === 'hot') {
      if (cursor && cursor.id) {
        query = db.collection('photos').where(_.and([
          { status: 'published' },
          _.or([
            { likeCount: _.lt(cursor.likeCount) },
            {
              likeCount: cursor.likeCount,
              createdAt: _.lt(cursor.createdAt)
            },
            {
              likeCount: cursor.likeCount,
              createdAt: cursor.createdAt,
              _id: _.lt(cursor.id)
            }
          ])
        ]))
      }
      const res = await query.orderBy('likeCount', 'desc').orderBy('createdAt', 'desc').orderBy('_id', 'desc').limit(pageSize).get()
      return await attachLiked(res.data, OPENID, pageSize)
    }

    if (cursor && cursor.id) {
      query = db.collection('photos').where(_.and([
        { status: 'published' },
        _.or([
          { createdAt: _.lt(cursor.createdAt) },
          { createdAt: cursor.createdAt, _id: _.lt(cursor.id) }
        ])
      ]))
    }
    const res = await query.orderBy('createdAt', 'desc').orderBy('_id', 'desc').limit(pageSize).get()
    return await attachLiked(res.data, OPENID, pageSize)
  } catch (err) {
    return { ok: false, code: 'NETWORK', message: '信息流加载失败' }
  }
}

async function attachLiked(list, openid, pageSize) {
  const ids = list.map((item) => item._id)
  let likedSet = new Set()
  if (openid && ids.length) {
    const likeRes = await db.collection('likes').where({
      _openid: openid,
      photoId: _.in(ids)
    }).field({ photoId: true }).get()
    likedSet = new Set((likeRes.data || []).map((item) => item.photoId))
  }
  const mapped = list.map((item) => Object.assign({}, item, { liked: likedSet.has(item._id) }))
  const last = mapped[mapped.length - 1]
  return {
    ok: true,
    list: mapped,
    hasMore: mapped.length === pageSize,
    nextCursor: encodeCursor(last)
  }
}
