const cloud = require('wx-server-sdk')
const { msgSecCheck, imgSecCheck } = require('./security')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()
const _ = db.command

const RATE_MS = 3000
const lastPublish = new Map()

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext()
  if (!OPENID) {
    return { ok: false, code: 'AUTH', message: '登录失败' }
  }
  const now = Date.now()
  const last = lastPublish.get(OPENID) || 0
  if (now - last < RATE_MS) {
    return { ok: false, code: 'RATE_LIMIT', message: '发布过于频繁，请稍后再试' }
  }

  const tags = Array.isArray(event.tags) ? event.tags.slice(0, 8) : []
  const title = String(event.title || '未命名作品').slice(0, 40)
  const fileID = event.fileID
  const thumbFileID = event.thumbFileID || fileID
  if (!fileID) {
    return { ok: false, code: 'MISSING_IMAGE', message: '图片丢失，请重新拍摄' }
  }

  const photoIdHolder = { id: '' }
  try {
    const msg = await msgSecCheck(cloud, OPENID, title + ' ' + tags.join(' '))
    await db.collection('audit_logs').add({
      data: {
        photoId: '',
        type: 'msg',
        pass: msg.pass,
        traceId: msg.traceId || '',
        createdAt: now
      }
    })
    if (!msg.pass) {
      return { ok: false, code: 'SECURITY_FAIL', message: '内容未通过安全审核' }
    }

    const download = await cloud.downloadFile({ fileID: thumbFileID || fileID })
    const img = await imgSecCheck(cloud, download.fileContent)
    await db.collection('audit_logs').add({
      data: {
        photoId: '',
        type: 'img',
        pass: img.pass,
        traceId: img.traceId || '',
        createdAt: now
      }
    })
    if (!img.pass) {
      try {
        await cloud.deleteFile({ fileList: [fileID, thumbFileID].filter(Boolean) })
      } catch (e) {
        // ignore cleanup failure
      }
      return { ok: false, code: 'SECURITY_FAIL', message: '内容未通过安全审核' }
    }

    const addRes = await db.collection('photos').add({
      data: {
        fileID: fileID,
        thumbFileID: thumbFileID,
        tags: tags,
        sceneKey: event.sceneKey || '',
        sceneTags: event.sceneTags || tags,
        geo: event.geo || null,
        likeCount: 0,
        status: 'published',
        width: event.width || 0,
        height: event.height || 0,
        title: title,
        authorName: event.authorName || '摄影师',
        createdAt: now
      }
    })
    photoIdHolder.id = addRes._id
    lastPublish.set(OPENID, now)
    await db.collection('users').where({ _openid: OPENID }).update({
      data: { postCount: _.inc(1) }
    })
    return { ok: true, photoId: addRes._id }
  } catch (err) {
    return { ok: false, code: 'PUBLISH_FAIL', message: '发布失败，请重试' }
  }
}
