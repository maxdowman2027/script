const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

const BLOCK_WORDS = ['色情', '暴力', '赌博', '毒品', '政治谣言']

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext()
  const content = String(event.content || '')
  const type = event.type === 'img' ? 'img' : 'msg'
  try {
    if (type === 'msg') {
      if (BLOCK_WORDS.some((word) => content.indexOf(word) >= 0)) {
        return { ok: true, pass: false, type: type }
      }
      const res = await cloud.openapi.security.msgSecCheck({
        openid: OPENID,
        scene: 2,
        version: 2,
        content: content.slice(0, 2500)
      })
      const pass = !res.result || res.result.suggest === 'pass' || res.errCode === 0
      return { ok: true, pass: pass, type: type, traceId: res.trace_id || '' }
    }
    return { ok: false, code: 'INVALID', message: '图片审核请走发布流程' }
  } catch (err) {
    return { ok: false, code: 'SECURITY_FAIL', message: '内容未通过安全审核' }
  }
}
