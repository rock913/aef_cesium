// Astronomy coordinate helpers for OneAstronomy.
// Conventions:
// - Right Ascension (RA) in degrees, range [0, 360)
// - Declination (Dec) in degrees, range [-90, 90]
// - Equatorial unit vector: x=RA0/Dec0, y=RA90/Dec0, z=Dec90

export function degToRad(deg) {
  return (deg * Math.PI) / 180;
}

export function radToDeg(rad) {
  return (rad * 180) / Math.PI;
}

export function normalizeAngle0To360(deg) {
  const v = deg % 360;
  return v < 0 ? v + 360 : v;
}

export function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

export function raDecToUnitVector(raDeg, decDeg) {
  const ra = degToRad(normalizeAngle0To360(raDeg));
  const dec = degToRad(clamp(decDeg, -90, 90));

  const cosDec = Math.cos(dec);
  return {
    x: cosDec * Math.cos(ra),
    y: cosDec * Math.sin(ra),
    z: Math.sin(dec),
  };
}

export function unitVectorToRaDec({ x, y, z }) {
  const len = Math.hypot(x, y, z) || 1;
  const nx = x / len;
  const ny = y / len;
  const nz = z / len;

  const ra = Math.atan2(ny, nx);
  const dec = Math.asin(clamp(nz, -1, 1));

  return {
    raDeg: normalizeAngle0To360(radToDeg(ra)),
    decDeg: radToDeg(dec),
  };
}

/**
 * Log-scale distance for rendering.
 *
 * We intentionally use log10(1 + d) to keep the mapping:
 * - monotonic
 * - defined at d=0
 * - non-negative
 */
export function logScaleDistance(distanceMpc, { distanceScale = 1, minDistanceMpc = 0 } = {}) {
  const d = Math.max(minDistanceMpc, Number(distanceMpc) || 0);
  return distanceScale * Math.log10(1 + d);
}

export function raDecDistanceToCartesian(
  raDeg,
  decDeg,
  distanceMpc,
  { distanceScale = 1, minDistanceMpc = 0 } = {}
) {
  const dir = raDecToUnitVector(raDeg, decDeg);
  const r = logScaleDistance(distanceMpc, { distanceScale, minDistanceMpc });
  return {
    x: dir.x * r,
    y: dir.y * r,
    z: dir.z * r,
    r,
    dir,
  };
}
