const { containsBlockWord } = require('./security')
const config = require('../config')

const OPENID = 'mock-openid'

const PHOTOS = [
  {
    _id: 'p1',
    _openid: 'u_aria',
    authorName: '林栖',
    title: '山脊一线天',
    tags: ['风景', '旅行'],
    sceneKey: '风景|golden|geo-30.25-120.15',
    sceneTags: ['风景'],
    likeCount: 128,
    status: 'published',
    width: 1200,
    height: 1600,
    coverColor: '#3A4A3C',
    geo: { latitude: 30.25, longitude: 120.15 },
    createdAt: Date.now() - 3600 * 1000 * 8
  },
  {
    _id: 'p2',
    _openid: 'u_bo',
    authorName: '北岛',
    title: '巷口暖光',
    tags: ['街拍', '人像'],
    sceneKey: '街拍|day|geo-31.23-121.47',
    sceneTags: ['街拍', '人像'],
    likeCount: 96,
    status: 'published',
    width: 1200,
    height: 1500,
    coverColor: '#6B4A32',
    geo: { latitude: 31.23, longitude: 121.47 },
    createdAt: Date.now() - 3600 * 1000 * 20
  },
  {
    _id: 'p3',
    _openid: 'u_chen',
    authorName: '澄空',
    title: '玻璃幕墙几何',
    tags: ['建筑'],
    sceneKey: '建筑|day|geo-22.54-114.06',
    sceneTags: ['建筑'],
    likeCount: 211,
    status: 'published',
    width: 1600,
    height: 1200,
    coverColor: '#2C3E50',
    createdAt: Date.now() - 3600 * 1000 * 30
  },
  {
    _id: 'p4',
    _openid: 'u_dusk',
    authorName: '暮色',
    title: '江岸夜色',
    tags: ['夜景', '风景'],
    sceneKey: '夜景|night|geo-30.59-114.30',
    sceneTags: ['夜景', '风景'],
    likeCount: 174,
    status: 'published',
    width: 1200,
    height: 1800,
    coverColor: '#1B2430',
    createdAt: Date.now() - 3600 * 1000 * 5
  },
  {
    _id: 'p5',
    _openid: 'u_east',
    authorName: '东篱',
    title: '窗边侧脸',
    tags: ['人像'],
    sceneKey: '人像|morning|geo-39.90-116.40',
    sceneTags: ['人像'],
    likeCount: 67,
    status: 'published',
    width: 1200,
    height: 1600,
    coverColor: '#8A6A55',
    createdAt: Date.now() - 3600 * 1000 * 48
  },
  {
    _id: 'p6',
    _openid: 'u_fog',
    authorName: '薄雾',
    title: '雨后石板路',
    tags: ['街拍', '风景'],
    sceneKey: '街拍|morning|geo-30.25-120.15',
    sceneTags: ['街拍', '风景'],
    likeCount: 88,
    status: 'published',
    width: 1200,
    height: 1500,
    coverColor: '#4A5560',
    createdAt: Date.now() - 3600 * 1000 * 12
  },
  {
    _id: 'p7',
    _openid: 'u_gold',
    authorName: '金羽',
    title: '海岸剪影',
    tags: ['风景', '旅行'],
    sceneKey: '风景|golden|geo-22.27-113.57',
    sceneTags: ['风景'],
    likeCount: 305,
    status: 'published',
    width: 1600,
    height: 1000,
    coverColor: '#C47A3A',
    createdAt: Date.now() - 3600 * 1000 * 72
  },
  {
    _id: 'p8',
    _openid: 'u_hall',
    authorName: '廊桥',
    title: '中庭对称',
    tags: ['建筑'],
    sceneKey: '建筑|day|geo-31.23-121.47',
    sceneTags: ['建筑'],
    likeCount: 54,
    status: 'published',
    width: 1200,
    height: 1600,
    coverColor: '#3E3A36',
    createdAt: Date.now() - 3600 * 1000 * 16
  },
  {
    _id: 'p9',
    _openid: OPENID,
    ownerId: OPENID,
    authorName: '我',
    title: '练习构图',
    tags: ['静物'],
    sceneKey: '静物|day|geo-unknown',
    sceneTags: ['静物'],
    likeCount: 3,
    status: 'published',
    width: 1200,
    height: 1200,
    coverColor: '#5C5346',
    createdAt: Date.now() - 3600 * 1000 * 2
  },
  {
    _id: 'p10',
    _openid: 'u_ink',
    authorName: '墨白',
    title: '天台风场',
    tags: ['人像', '建筑'],
    sceneKey: '人像|day|geo-23.13-113.26',
    sceneTags: ['人像', '建筑'],
    likeCount: 142,
    status: 'published',
    width: 1200,
    height: 1700,
    coverColor: '#4A3F55',
    createdAt: Date.now() - 3600 * 1000 * 40
  }
]

const likes = new Set(['p1', 'p7'])
const auditLogs = []
let lastPublishAt = 0
let photoSeq = 100

function clonePhoto(photo, likedSet) {
  const item = Object.assign({}, photo)
  item.liked = likedSet.has(photo._id)
  item.coverUrl = photo.coverUrl || ''
  item.fileID = photo.fileID || ''
  item.thumbFileID = photo.thumbFileID || ''
  return item
}

function publishedList() {
  return PHOTOS.filter((item) => item.status === 'published')
}

function sortFeed(list, sort) {
  const copy = list.slice()
  if (sort === 'hot') {
    copy.sort((a, b) => b.likeCount - a.likeCount || b.createdAt - a.createdAt)
  } else {
    copy.sort((a, b) => b.createdAt - a.createdAt)
  }
  return copy
}

function login() {
  return {
    ok: true,
    isMock: true,
    openid: OPENID,
    nickName: '光影练习生',
    avatarUrl: '',
    likedIds: Array.from(likes)
  }
}

function getFeed(data) {
  const sort = data.sort === 'new' ? 'new' : 'hot'
  const pageSize = data.pageSize || config.feedPageSize
  const sorted = sortFeed(publishedList(), sort)
  let start = 0
  if (data.cursor && data.cursor.id) {
    const idx = sorted.findIndex((item) => item._id === data.cursor.id)
    start = idx >= 0 ? idx + 1 : 0
  }
  const slice = sorted.slice(start, start + pageSize).map((item) => clonePhoto(item, likes))
  const last = slice[slice.length - 1]
  return {
    ok: true,
    list: slice,
    hasMore: start + slice.length < sorted.length,
    nextCursor: last ? { id: last._id, createdAt: last.createdAt, likeCount: last.likeCount } : null,
    fromCache: false
  }
}

function getSceneRecommend(data) {
  const sceneTag = data.sceneTag || (data.sceneKey ? String(data.sceneKey).split('|')[0] : '')
  const limit = data.limit || config.recommendLimit
  const geo = data.geo
  let matched = publishedList()
  if (geo && geo.latitude != null) {
    const near = matched.filter((item) => item.geo && Math.abs(item.geo.latitude - geo.latitude) < 0.2)
    if (near.length) matched = near
  }
  matched = matched.filter((item) => {
    if (sceneTag && sceneTag !== 'general') {
      return (item.sceneTags || item.tags || []).indexOf(sceneTag) >= 0
    }
    return true
  })
  if (!matched.length) matched = publishedList()
  matched = sortFeed(matched, 'hot').slice(0, limit).map((item) => clonePhoto(item, likes))
  return { ok: true, list: matched, fallback: !sceneTag, source: geo ? 'geo' : 'tag' }
}

function getPhotoDetail(data) {
  const photo = PHOTOS.find((item) => item._id === data.photoId)
  if (!photo) {
    const err = new Error('内容不存在或已下架')
    err.code = 'NOT_FOUND'
    throw err
  }
  if (photo.status !== 'published' && photo._openid !== OPENID && photo.ownerId !== OPENID) {
    const err = new Error('内容不存在或已下架')
    err.code = 'NOT_FOUND'
    throw err
  }
  return { ok: true, photo: clonePhoto(photo, likes) }
}

function getMyPosts() {
  const list = PHOTOS.filter((item) => item._openid === OPENID || item.ownerId === OPENID)
    .slice()
    .sort((a, b) => b.createdAt - a.createdAt)
    .map((item) => clonePhoto(item, likes))
  return { ok: true, list: list }
}

function toggleLike(data) {
  const photoId = data.photoId
  const photo = PHOTOS.find((item) => item._id === photoId)
  if (!photo || photo.status !== 'published') {
    const err = new Error('点赞同步失败')
    err.code = 'LIKE_FAIL'
    throw err
  }
  if (likes.has(photoId)) {
    likes.delete(photoId)
    photo.likeCount = Math.max(0, (photo.likeCount || 0) - 1)
    return { ok: true, liked: false, likeCount: photo.likeCount }
  }
  likes.add(photoId)
  photo.likeCount = (photo.likeCount || 0) + 1
  return { ok: true, liked: true, likeCount: photo.likeCount }
}

function publishPhoto(data) {
  const now = Date.now()
  if (lastPublishAt && now - lastPublishAt < config.publishIntervalMs) {
    const err = new Error('发布过于频繁，请稍后再试')
    err.code = 'RATE_LIMIT'
    throw err
  }
  lastPublishAt = now
  photoSeq += 1
  const photoId = 'p' + photoSeq
  const tags = Array.isArray(data.tags) ? data.tags : []
  const text = tags.join(' ') + ' ' + (data.title || '')
  const passMsg = !containsBlockWord(text)
  const photo = {
    _id: photoId,
    _openid: OPENID,
    authorName: '光影练习生',
    title: data.title || '未命名作品',
    tags: tags,
    sceneKey: data.sceneKey || 'general|day|geo-unknown',
    sceneTags: data.sceneTags || tags,
    geo: data.geo || null,
    likeCount: 0,
    status: 'pending',
    ownerId: OPENID,
    width: data.width || 0,
    height: data.height || 0,
    coverColor: '#3A3F4B',
    coverUrl: data.tempFilePath || '',
    fileID: data.fileID || data.tempFilePath || '',
    thumbFileID: data.thumbFileID || data.tempFilePath || '',
    createdAt: now
  }
  PHOTOS.unshift(photo)
  auditLogs.push({
    photoId: photoId,
    type: 'msg',
    pass: passMsg,
    traceId: 'mock-msg-' + now,
    createdAt: now
  })
  if (!passMsg) {
    photo.status = 'rejected'
    const err = new Error('内容未通过安全审核')
    err.code = 'SECURITY_FAIL'
    throw err
  }
  auditLogs.push({
    photoId: photoId,
    type: 'img',
    pass: true,
    traceId: 'mock-img-' + now,
    createdAt: now
  })
  photo.status = 'published'
  return { ok: true, photoId: photo._id, status: 'published', photo: clonePhoto(photo, likes) }
}

function contentCheck(data) {
  const pass = !containsBlockWord(data.content)
  return { ok: true, pass: pass, type: data.type || 'msg' }
}

function uploadFile(cloudPath, filePath) {
  return Promise.resolve({
    fileID: 'cloud://mock/' + cloudPath,
    localPath: filePath
  })
}

function invoke(name, data) {
  const payload = data || {}
  switch (name) {
    case 'login':
      return Promise.resolve(login())
    case 'getFeed':
      return Promise.resolve(getFeed(payload))
    case 'getSceneRecommend':
      return Promise.resolve(getSceneRecommend(payload))
    case 'getPhotoDetail':
      return Promise.resolve(getPhotoDetail(payload))
    case 'getMyPosts':
      return Promise.resolve(getMyPosts())
    case 'toggleLike':
      return Promise.resolve(toggleLike(payload))
    case 'publishPhoto':
      return Promise.resolve(publishPhoto(payload))
    case 'contentCheck':
      return Promise.resolve(contentCheck(payload))
    default: {
      const err = new Error('未知云函数')
      err.code = 'NETWORK'
      return Promise.reject(err)
    }
  }
}

module.exports = { invoke, uploadFile, containsBlockWord }
