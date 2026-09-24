const BLOCK_WORDS = ['色情', '暴力', '赌博', '毒品', '政治谣言']

function containsBlockWord(text) {
  const raw = String(text || '')
  return BLOCK_WORDS.some((word) => raw.indexOf(word) >= 0)
}

async function msgSecCheck(cloud, openid, content) {
  if (containsBlockWord(content)) {
    return { pass: false, traceId: 'local-block', source: 'local' }
  }
  try {
    const res = await cloud.openapi.security.msgSecCheck({
      openid: openid,
      scene: 2,
      version: 2,
      content: String(content || '').slice(0, 2500)
    })
    const pass = !res.result || res.result.suggest === 'pass' || res.errCode === 0
    return { pass: pass, traceId: res.trace_id || res.traceId || '', source: 'openapi' }
  } catch (err) {
    return { pass: false, traceId: '', source: 'openapi-error', error: err.message }
  }
}

async function imgSecCheck(cloud, fileContent) {
  try {
    const res = await cloud.openapi.security.imgSecCheck({
      media: {
        contentType: 'image/jpeg',
        value: fileContent
      }
    })
    return { pass: res.errCode === 0, traceId: res.trace_id || '', source: 'openapi' }
  } catch (err) {
    return { pass: false, traceId: '', source: 'openapi-error', error: err.message }
  }
}

async function mediaCheckAsync(cloud, openid, mediaUrl) {
  const res = await cloud.openapi.security.mediaCheckAsync({
    openid: openid,
    scene: 2,
    version: 2,
    media_type: 2,
    media_url: mediaUrl
  })
  return {
    traceId: res.trace_id || res.traceId || '',
    errCode: res.errcode == null ? res.errCode : res.errcode
  }
}

module.exports = { containsBlockWord, msgSecCheck, imgSecCheck, mediaCheckAsync }
