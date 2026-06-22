export function normalizeSdssTriples(data) {
  if (!Array.isArray(data)) return { flat: [], count: 0 }

  // Format A: flat array: [ra, dec, z, ra, dec, z, ...]
  if (data.length && typeof data[0] === 'number') {
    const n = Math.floor(data.length / 3)
    const out = new Array(n * 3)
    for (let i = 0; i < n; i += 1) {
      const ra = Number(data[i * 3])
      const dec = Number(data[i * 3 + 1])
      const z = Number(data[i * 3 + 2])
      out[i * 3] = ra
      out[i * 3 + 1] = dec
      out[i * 3 + 2] = z
    }
    return { flat: out, count: n }
  }

  // Format B: 2D triples: [[ra, dec, z], ...]
  const out = []
  for (const row of data) {
    if (!Array.isArray(row) || row.length < 3) continue
    const ra = Number(row[0])
    const dec = Number(row[1])
    const z = Number(row[2])
    if (!Number.isFinite(ra) || !Number.isFinite(dec)) continue
    out.push(ra, dec, Number.isFinite(z) ? z : 0)
  }
  return { flat: out, count: Math.floor(out.length / 3) }
}
