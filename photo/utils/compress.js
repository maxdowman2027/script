const config = require('../config')

function compressImage(src, quality) {
  const q = quality == null ? config.compressQuality : quality
  return new Promise(function (resolve, reject) {
    if (!src) {
      reject(new Error('MISSING_IMAGE'))
      return
    }
    wx.compressImage({
      src: src,
      quality: q,
      success(res) {
        resolve(res.tempFilePath || src)
      },
      fail() {
        resolve(src)
      }
    })
  })
}

module.exports = { compressImage }
