function hourBucket() {
  const hour = new Date().getHours()
  if (hour < 6) return 'night'
  if (hour < 10) return 'morning'
  if (hour < 17) return 'day'
  if (hour < 19) return 'golden'
  return 'night'
}

function geoGrid(lat, lng) {
  if (lat == null || lng == null || Number.isNaN(Number(lat))) return 'geo-unknown'
  return `geo-${Number(lat).toFixed(2)}-${Number(lng).toFixed(2)}`
}

function buildSceneKey(options) {
  const sceneTag = (options && options.sceneTag) || 'general'
  const time = hourBucket()
  const geo = options && options.geo
  const grid = geo ? geoGrid(geo.latitude, geo.longitude) : 'geo-unknown'
  return `${sceneTag}|${time}|${grid}`
}

function parseSceneKey(sceneKey) {
  const parts = String(sceneKey || '').split('|')
  return {
    sceneTag: parts[0] || 'general',
    time: parts[1] || '',
    geo: parts[2] || 'geo-unknown'
  }
}

module.exports = { hourBucket, geoGrid, buildSceneKey, parseSceneKey }
