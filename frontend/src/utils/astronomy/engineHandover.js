import { unitVectorToRaDec } from './coordinateMath.js';

function normalizeVector(v) {
  const len = Math.hypot(v.x, v.y, v.z) || 1;
  return { x: v.x / len, y: v.y / len, z: v.z / len };
}

function getCesiumVector(candidate) {
  if (!candidate) return null;
  const x = Number(candidate.x);
  const y = Number(candidate.y);
  const z = Number(candidate.z);
  if (![x, y, z].every(Number.isFinite)) return null;
  return { x, y, z };
}

/**
 * Sync a Cesium camera's orientation to a Three.js camera.
 *
 * This is intentionally dependency-free (no Cesium/Three imports).
 *
 * Expectations:
 * - `cesiumCamera` has `directionWC`/`direction` and `upWC`/`up` vectors.
 * - `threeCamera` has `.position` (x,y,z), `.up.set(x,y,z)` and `.lookAt(x,y,z)`.
 */
export function syncCesiumToThreeCamera(
  cesiumCamera,
  threeCamera,
  { forceOrigin = false, directionOverride = null } = {}
) {
  if (!cesiumCamera) {
    throw new Error('syncCesiumToThreeCamera: missing cesiumCamera');
  }
  if (!threeCamera) {
    throw new Error('syncCesiumToThreeCamera: missing threeCamera');
  }

  const dirRaw =
    getCesiumVector(directionOverride) ||
    getCesiumVector(cesiumCamera.directionWC) ||
    getCesiumVector(cesiumCamera.direction);
  const upRaw = getCesiumVector(cesiumCamera.upWC) || getCesiumVector(cesiumCamera.up);

  if (!dirRaw) {
    throw new Error('syncCesiumToThreeCamera: missing camera direction');
  }

  const dir = normalizeVector(dirRaw);
  const up = upRaw ? normalizeVector(upRaw) : { x: 0, y: 0, z: 1 };

  if (forceOrigin && threeCamera.position) {
    threeCamera.position.x = 0;
    threeCamera.position.y = 0;
    threeCamera.position.z = 0;
  }

  if (threeCamera.up && typeof threeCamera.up.set === 'function') {
    threeCamera.up.set(up.x, up.y, up.z);
  } else if (threeCamera.up) {
    threeCamera.up.x = up.x;
    threeCamera.up.y = up.y;
    threeCamera.up.z = up.z;
  }

  const px = Number(threeCamera.position?.x) || 0;
  const py = Number(threeCamera.position?.y) || 0;
  const pz = Number(threeCamera.position?.z) || 0;
  const tx = px + dir.x;
  const ty = py + dir.y;
  const tz = pz + dir.z;

  if (typeof threeCamera.lookAt === 'function') {
    threeCamera.lookAt(tx, ty, tz);
  }

  const { raDeg, decDeg } = unitVectorToRaDec(dir);
  return { direction: dir, up, raDeg, decDeg };
}
