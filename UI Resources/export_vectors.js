// Optional raster export for engines that cannot load SVG directly.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');
const root = __dirname;

async function main() {
  for (const size of [64, 128]) {
    const out = path.join(root, 'icons', `png${size}`);
    fs.mkdirSync(out, { recursive: true });
    for (const file of fs.readdirSync(path.join(root, 'icons')).filter(x => x.endsWith('.svg'))) {
      await sharp(path.join(root, 'icons', file)).resize(size, size)
        .png().toFile(path.join(out, file.replace(/\.svg$/, '.png')));
    }
  }
  const out = path.join(root, 'chrome', 'png');
  fs.mkdirSync(out, { recursive: true });
  for (const file of fs.readdirSync(path.join(root, 'chrome')).filter(x => x.endsWith('.svg'))) {
    await sharp(path.join(root, 'chrome', file)).png()
      .toFile(path.join(out, file.replace(/\.svg$/, '.png')));
  }
  console.log('Exported transparent PNG icons and chrome');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
