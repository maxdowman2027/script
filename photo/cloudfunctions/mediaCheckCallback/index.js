const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()
const _ = db.command

function parseEvent(event) {
  const payload = event && (event.body || event)
  const result = payload.result || {}
  return {
    traceId: payload.trace_id || payload.traceId || '',
    suggest: result.suggest || '',
    errcode: payload.errcode,
    eventName: payload.Event || payload.action || payload.MsgType || ''
  }
}

function isPass(parsed) {
  if (parsed.suggest) {
    return parsed.suggest === 'pass'
  }
  return parsed.errcode === 0
}

exports.main = async (event) => {
  const parsed = parseEvent(event || {})
  if (!parsed.traceId) {
    return { ok: true, skipped: true }
  }

  const found = await db.collection('photos').where({ asyncTraceId: parsed.traceId }).limit(1).get()
  const photo = found.data && found.data[0]
  if (!photo) {
    return { ok: true, skipped: true, traceId: parsed.traceId }
  }

  const pass = isPass(parsed)
  await db.collection('audit_logs').add({
    data: {
      photoId: photo._id,
      type: 'img-async',
      pass: pass,
      traceId: parsed.traceId,
      createdAt: Date.now()
    }
  })

  if (pass) {
    await db.collection('photos').doc(photo._id).update({
      data: { asyncAudit: 'pass' }
    })
    return { ok: true, photoId: photo._id, pass: true }
  }

  const wasPublished = photo.status === 'published'
  await db.collection('photos').doc(photo._id).update({
    data: {
      status: 'rejected',
      asyncAudit: 'rejected'
    }
  })
  try {
    await cloud.deleteFile({
      fileList: [photo.fileID, photo.thumbFileID].filter(Boolean)
    })
  } catch (e) {
    // ignore cleanup failure
  }
  if (wasPublished && photo.ownerId) {
    try {
      await db.collection('users').doc(photo.ownerId).update({
        data: { postCount: _.inc(-1) }
      })
    } catch (e) {
      // ignore count drift
    }
  }
  return { ok: true, photoId: photo._id, pass: false }
}
