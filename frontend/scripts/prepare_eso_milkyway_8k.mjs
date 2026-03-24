import fs from 'node:fs';
import path from 'node:path';
import sharp from 'sharp';

function getArg(name, fallback) {
  const prefix = `--${name}=`;
  const idx = process.argv.findIndex((a) => a === `--${name}` || a.startsWith(prefix));
  if (idx === -1) return fallback;
  const token = process.argv[idx];
  if (token.startsWith(prefix)) return token.slice(prefix.length);
  return process.argv[idx + 1] ?? fallback;
}

function toInt(value, fallback) {
  const n = Number.parseInt(String(value), 10);
  return Number.isFinite(n) ? n : fallback;
}

const src = getArg('src', '');
const out = getArg('out', '');
const width = toInt(getArg('width', 8192), 8192);
const height = toInt(getArg('height', 4096), 4096);
const quality = toInt(getArg('quality', 90), 90);
const minBytes = toInt(getArg('min-bytes', 1_000_000), 1_000_000);
const cleanSource = String(getArg('clean-source', '0')) === '1';

if (!src || !out) {
  console.error(
    'Usage: node scripts/prepare_eso_milkyway_8k.mjs --src <path> --out <path> [--width 8192 --height 4096 --quality 90 --min-bytes 1000000 --clean-source 1]'
  );
  process.exit(2);
}

if (!fs.existsSync(src)) {
  console.error('Missing src:', src);
  process.exit(1);
}

const outDir = path.dirname(out);
fs.mkdirSync(outDir, { recursive: true });

const tmp = `${out}.tmp`;
try {
  fs.unlinkSync(tmp);
} catch {}

await sharp(src)
  .resize(width, height, { fit: 'fill' })
  .jpeg({ quality })
  .toFile(tmp);

const st = fs.statSync(tmp);
if (st.size < minBytes) {
  try {
    fs.unlinkSync(tmp);
  } catch {}
  throw new Error(`Generated file too small: ${st.size} bytes`);
}

const meta = await sharp(tmp).metadata();
if (meta.width !== width || meta.height !== height) {
  try {
    fs.unlinkSync(tmp);
  } catch {}
  throw new Error(`Unexpected output dimensions: ${meta.width}x${meta.height}`);
}

fs.renameSync(tmp, out);

if (cleanSource) {
  try {
    fs.unlinkSync(src);
  } catch {}
}

console.log('OK', out, `${meta.width}x${meta.height}`, 'bytes', st.size);
