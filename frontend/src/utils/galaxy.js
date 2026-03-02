function mulberry32(seed) {
  let a = seed >>> 0
  return function rand() {
    a |= 0
    a = (a + 0x6D2B79F5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n))
}

export function normalizeQuery(q) {
  return String(q || '').trim().toLowerCase()
}

export function defaultGalaxyClusters() {
  return [
    { id: 'wetlands', name: 'Wetlands / 湿地', hue: 195 },
    { id: 'hydrology', name: 'Hydrology / 水文', hue: 210 },
    { id: 'migration', name: 'Migration / 迁徙', hue: 140 },
    { id: 'climate', name: 'Climate / 气候', hue: 24 },
    { id: 'landuse', name: 'Land Use / 土地利用', hue: 280 },
    { id: 'biodiversity', name: 'Biodiversity / 生物多样性', hue: 55 },
  ]
}

export function generateGalaxyLayout({
  seed = 21,
  clusterCount = 6,
  radius = 1.0,
} = {}) {
  const rnd = mulberry32(seed)
  const centers = []
  const ring = radius * (0.58 + rnd() * 0.12)

  for (let i = 0; i < clusterCount; i += 1) {
    const a = (i / clusterCount) * Math.PI * 2 + rnd() * 0.22
    const r = ring * (0.88 + rnd() * 0.24)
    centers.push({
      x: Math.cos(a) * r,
      y: Math.sin(a) * r,
    })
  }

  return centers
}

export function generateGalaxyNodes({
  seed = 21,
  count = 900,
  clusters = defaultGalaxyClusters(),
  spread = 0.16,
} = {}) {
  const rnd = mulberry32(seed)
  const centers = generateGalaxyLayout({ seed, clusterCount: clusters.length, radius: 1.0 })

  const nodes = []
  const perCluster = Math.max(1, Math.floor(count / clusters.length))

  for (let ci = 0; ci < clusters.length; ci += 1) {
    const c = clusters[ci]
    const center = centers[ci]

    const localCount = ci === clusters.length - 1
      ? (count - (perCluster * (clusters.length - 1)))
      : perCluster

    for (let i = 0; i < localCount; i += 1) {
      // Gaussian-ish blob via sum of uniforms
      const dx = ((rnd() + rnd() + rnd()) / 3 - 0.5) * spread
      const dy = ((rnd() + rnd() + rnd()) / 3 - 0.5) * spread
      const jitter = 0.04 + rnd() * 0.06

      const x = center.x + dx * (0.65 + rnd())
      const y = center.y + dy * (0.65 + rnd())
      const mass = clamp(jitter, 0.03, 0.12)

      nodes.push({
        id: `${c.id}-${String(i).padStart(4, '0')}`,
        label: `${c.id}:${i}`,
        clusterId: c.id,
        x,
        y,
        mass,
      })
    }
  }

  return nodes
}

export function computeClusterStats(nodes, clusters = defaultGalaxyClusters()) {
  const stats = {}
  for (const c of clusters) {
    stats[c.id] = { id: c.id, name: c.name, hue: c.hue, count: 0, cx: 0, cy: 0 }
  }

  for (const n of nodes || []) {
    const s = stats[n.clusterId]
    if (!s) continue
    s.count += 1
    s.cx += Number(n.x || 0)
    s.cy += Number(n.y || 0)
  }

  for (const k of Object.keys(stats)) {
    const s = stats[k]
    if (s.count > 0) {
      s.cx /= s.count
      s.cy /= s.count
    }
  }

  return stats
}

export function matchGalaxyQuery(query, clusters = defaultGalaxyClusters()) {
  const q = normalizeQuery(query)
  if (!q) return ''

  // Friendly aliases for the demo narrative.
  const aliases = {
    poyang: 'wetlands',
    '鄱阳': 'wetlands',
    wetlands: 'wetlands',
    '湿地': 'wetlands',
    hydrology: 'hydrology',
    '水文': 'hydrology',
    migration: 'migration',
    '迁徙': 'migration',
    climate: 'climate',
    '气候': 'climate',
    landuse: 'landuse',
    '土地': 'landuse',
    biodiversity: 'biodiversity',
    '生物': 'biodiversity',
  }

  for (const [key, clusterId] of Object.entries(aliases)) {
    if (q.includes(String(key).toLowerCase())) return clusterId
  }

  // Match by cluster id/name
  for (const c of clusters) {
    const id = normalizeQuery(c.id)
    const name = normalizeQuery(c.name)
    if (q === id || q === name) return c.id
    if (id && q.includes(id)) return c.id
    if (name && q.includes(name)) return c.id
  }

  return ''
}
