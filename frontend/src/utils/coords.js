export function formatLatLon(lat, lon, digits = 5) {
  const latNum = Number(lat)
  const lonNum = Number(lon)
  const d = Number(digits)
  const usedDigits = Number.isFinite(d) ? Math.max(0, Math.min(10, Math.trunc(d))) : 5

  if (!Number.isFinite(latNum) || !Number.isFinite(lonNum)) return '—'

  return `${latNum.toFixed(usedDigits)}, ${lonNum.toFixed(usedDigits)}`
}
