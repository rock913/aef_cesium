import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { Resvg } from '@resvg/resvg-js'
import sharp from 'sharp'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const uiDir = path.resolve(__dirname, '../public/zero2x/ui')

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true })
}

async function renderSvgToWebp({
  inputSvg,
  outputWebp,
  width,
  height,
  quality = 86,
}) {
  const svgPath = path.resolve(uiDir, inputSvg)
  const outPath = path.resolve(uiDir, outputWebp)

  if (!fs.existsSync(svgPath)) {
    throw new Error(`Missing SVG: ${svgPath}`)
  }

  const svg = fs.readFileSync(svgPath)
  const resvg = new Resvg(svg, {
    fitTo: {
      mode: 'width',
      value: width,
    },
  })

  const png = resvg.render().asPng()

  // Crop/fit to exact cinematic aspect (16:9) and apply gentle filmic grading.
  const img = sharp(png)
    .resize(width, height, { fit: 'cover', position: 'centre' })
    .modulate({ saturation: 1.12, brightness: 0.96 })
    .sharpen({ sigma: 0.6 })
    .webp({ quality })

  await img.toFile(outPath)
  return outPath
}

async function main() {
  ensureDir(uiDir)

  const requiredWebps = [
    'act2_geogpt.webp',
    'act2_astronomy.webp',
    'act3_genos.webp',
    'act3_oneporous.webp',
  ]

  // Default behavior: just verify assets exist (these are often design-provided renders).
  // Set RENDER_FROM_SVG=1 to generate fallback WebPs from legacy SVG posters.
  const renderFromSvg = String(process.env.RENDER_FROM_SVG || '') === '1'

  const missing = requiredWebps.filter((f) => !fs.existsSync(path.resolve(uiDir, f)))
  if (missing.length === 0 && !renderFromSvg) {
    for (const f of requiredWebps) {
      // eslint-disable-next-line no-console
      console.log(`✅ present ${path.relative(process.cwd(), path.resolve(uiDir, f))}`)
    }
    return
  }

  if (!renderFromSvg) {
    throw new Error(
      `Missing WebP assets in ${uiDir}: ${missing.join(', ')}. ` +
      'Add design-provided renders, or run with RENDER_FROM_SVG=1 to generate fallbacks.'
    )
  }

  // Fallback generator: render from legacy SVG posters if available.
  // NOTE: This is only meant to unblock local dev; for production-grade visuals,
  // replace the output WebPs with your final renders but keep filenames stable.
  const targets = [
    {
      inputSvg: 'act2_earth.svg',
      outputWebp: 'act2_geogpt.webp',
      width: 1920,
      height: 1080,
      quality: 86,
    },
    {
      inputSvg: 'act3_dna.svg',
      outputWebp: 'act3_genos.webp',
      width: 1920,
      height: 1080,
      quality: 86,
    },
  ]

  for (const t of targets) {
    const out = await renderSvgToWebp(t)
    // eslint-disable-next-line no-console
    console.log(`✅ wrote ${path.relative(process.cwd(), out)}`)
  }

  // eslint-disable-next-line no-console
  console.log('ℹ️  Reminder: provide real renders for act2_astronomy.webp and act3_oneporous.webp')
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error('❌ render:posters failed:', err)
  process.exit(1)
})
