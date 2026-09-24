const cloud = require('wx-server-sdk')
const { msgSecCheck, imgSecCheck, mediaCheckAsync } = require('./security')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()
const _ = db.command

const RATE_MS = 3000

async function ensureUser(openid) {
  const ref = db.collection('users').doc(openid)
  try {
    const got = await ref.get()
    if (got && got.data) return
  } catch (e) {
    // create below
  }
  await ref.set({
    data: {
      nickName: '摄影师',
      avatarUrl: '',
      createdAt: Date.now(),
      postCount: 0,
      lastPublishAt: 0
    }
  })
}

async function consumeRateLimit(openid, now) {
  await db.runTransaction(async (transaction) => {
    const userDoc = await transaction.collection('users').doc(openid).get()
    const user = userDoc.data
    if (!user) {
      const err = new Error('AUTH')
      err.code = 'AUTH'
      throw err
    }
    if (user.lastPublishAt && now - user.lastPublishAt < RATE_MS) {
      const err = new Error('RATE_LIMIT')
      err.code = 'RATE_LIMIT'
      throw err
    }
    await transaction.collection('users').doc(openid).update({
      data: { lastPublishAt: now }
    })
  })
}

async function writeAudit(photoId, type, result) {
  await db.collection('audit_logs').add({
    data: {
      photoId: photoId || '',
      type: type,
      pass: !!result.pass,
      traceId: result.traceId || '',
      createdAt: Date.now()
    }
  })
}

function toGeoPoint(geo) {
  if (!geo || geo.latitude == null || geo.longitude == null) return null
  const lat = Number(geo.latitude)
  const lng = Number(geo.longitude)
  if (Number.isNaN(lat) || Number.isNaN(lng)) return null
  return new db.Geo.Point(lng, lat)
}

async function rejectPhoto(photoId, fileID, thumbFileID) {
  if (photoId) {
    await db.collection('photos').doc(photoId).update({
      data: { status: 'rejected' }
    })
  }
  const files = [fileID, thumbFileID].filter(Boolean)
  if (files.length) {
    try {
      await cloud.deleteFile({ fileList: files })
    } catch (e) {
      // ignore cleanup failure
    }
  }
}

async function startAsyncImageCheck(openid, photoId, fileID) {
  const urlRes = await cloud.getTempFileURL({ fileList: [fileID] })
  const item = urlRes.fileList && urlRes.fileList[0]
  if (!item || !item.tempFileURL) {
    throw new Error('NO_MEDIA_URL')
  }
  const asyncRes = await mediaCheckAsync(cloud, openid, item.tempFileURL)
  await db.collection('photos').doc(photoId).update({
    data: {
      asyncTraceId: asyncRes.traceId || '',
      asyncAudit: 'pending'
    }
  })
  await writeAudit(photoId, 'img-async-submit', {
    pass: true,
    traceId: asyncRes.traceId || ''
  })
}

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext()
  if (!OPENID) {
    return { ok: false, code: 'AUTH', message: '登录失败' }
  }

  const tags = Array.isArray(event.tags) ? event.tags.slice(0, 8) : []
  const title = String(event.title || '未命名作品').slice(0, 40)
  const fileID = event.fileID
  const thumbFileID = event.thumbFileID || fileID
  if (!fileID) {
    return { ok: false, code: 'MISSING_IMAGE', message: '图片丢失，请重新拍摄' }
  }

  const now = Date.now()
  let photoId = ''
  try {
    await ensureUser(OPENID)
    await consumeRateLimit(OPENID, now)

    const addRes = await db.collection('photos').add({
      data: {
        fileID: fileID,
        thumbFileID: thumbFileID,
        tags: tags,
        sceneKey: event.sceneKey || '',
        sceneTags: event.sceneTags || tags,
        geo: toGeoPoint(event.geo),
        likeCount: 0,
        status: 'pending',
        ownerId: OPENID,
        width: event.width || 0,
        height: event.height || 0,
        title: title,
        authorName: event.authorName || '摄影师',
        createdAt: now
      }
    })
    photoId = addRes._id

    const msg = await msgSecCheck(cloud, OPENID, title + ' ' + tags.join(' '))
    await writeAudit(photoId, 'msg', msg)
    if (!msg.pass) {
      await rejectPhoto(photoId, fileID, thumbFileID)
      return { ok: false, code: 'SECURITY_FAIL', message: '内容未通过安全审核' }
    }

    const download = await cloud.downloadFile({ fileID: thumbFileID || fileID })
    const img = await imgSecCheck(cloud, download.fileContent)
    await writeAudit(photoId, 'img', img)
    if (!img.pass) {
      await rejectPhoto(photoId, fileID, thumbFileID)
      return { ok: false, code: 'SECURITY_FAIL', message: '内容未通过安全审核' }
    }

    await db.collection('photos').doc(photoId).update({
      data: { status: 'published' }
    })
    await db.collection('users').doc(OPENID).update({
      data: { postCount: _.inc(1) }
    })
    try {
      await startAsyncImageCheck(OPENID, photoId, fileID)
    } catch (e) {
      await writeAudit(photoId, 'img-async-submit', { pass: false, traceId: '' })
    }
    return { ok: true, photoId: photoId, status: 'published' }
  } catch (err) {
    if (err && err.code === 'RATE_LIMIT') {
      return { ok: false, code: 'RATE_LIMIT', message: '发布过于频繁，请稍后再试' }
    }
    if (photoId) {
      try {
        await rejectPhoto(photoId, fileID, thumbFileID)
      } catch (e) {
        // ignore
      }
    }
    return { ok: false, code: 'PUBLISH_FAIL', message: '发布失败，请重试' }
  }
}
