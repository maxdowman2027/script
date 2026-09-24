const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

const COLLECTIONS = ['users', 'photos', 'likes', 'audit_logs']

exports.main = async () => {
  const created = []
  const existed = []
  const failed = []
  for (let i = 0; i < COLLECTIONS.length; i += 1) {
    const name = COLLECTIONS[i]
    try {
      await db.createCollection(name)
      created.push(name)
    } catch (err) {
      const msg = (err && (err.errMsg || err.message)) || ''
      if (/exist|already/i.test(msg)) {
        existed.push(name)
      } else {
        try {
          await db.collection(name).limit(1).get()
          existed.push(name)
        } catch (e) {
          failed.push({ name: name, message: msg || 'create failed' })
        }
      }
    }
  }
  return { ok: failed.length === 0, created: created, existed: existed, failed: failed }
}
