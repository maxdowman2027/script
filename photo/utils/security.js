const { BLOCK_WORDS } = require('../constants/tags')

function containsBlockWord(text) {
  const raw = String(text || '')
  return BLOCK_WORDS.some((word) => raw.indexOf(word) >= 0)
}

module.exports = { containsBlockWord }
