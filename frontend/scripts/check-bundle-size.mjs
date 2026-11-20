// Bundle budgets (docs/04 §7, D-21): initial JS < 250 KB gz, map <= 475 KB gz.
// Sizes are the gzipped JS each load actually pulls in (a chunk plus its static imports).
import { readFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { join, resolve } from 'node:path';

const BUDGETS = { initial: 250, map: 475 };
const dist = process.argv[2]
  ? resolve(process.argv[2])
  : new URL('../dist/', import.meta.url).pathname;
const manifest = JSON.parse(readFileSync(join(dist, '.vite/manifest.json'), 'utf8'));

function closure(key, seen = new Set(), dynamic = false) {
  const chunk = manifest[key];
  if (!chunk || seen.has(chunk.file)) return seen;
  seen.add(chunk.file);
  for (const dep of chunk.imports ?? []) closure(dep, seen, dynamic);
  // react-map-gl loads maplibre-gl with import(), so the map budget follows dynamic imports.
  if (dynamic) for (const dep of chunk.dynamicImports ?? []) closure(dep, seen, dynamic);
  return seen;
}

const kb = (file) => gzipSync(readFileSync(join(dist, file))).length / 1024;
const entryKey = Object.keys(manifest).find((k) => manifest[k].isEntry);
const initial = closure(entryKey);
const mapKey = Object.keys(manifest).find((k) => k.includes('features/map/MapView'));
const map = [...closure(mapKey, new Set(), true)].filter((f) => !initial.has(f));

let failed = false;
for (const [name, files] of [
  ['initial', [...initial]],
  ['map', map],
]) {
  const total = files.reduce((sum, f) => sum + kb(f), 0);
  const ok = name === 'initial' ? total < BUDGETS[name] : total <= BUDGETS[name];
  if (!ok) failed = true;
  const verdict = ok ? 'ok' : 'OVER';
  process.stdout.write(
    `${name} JS: ${total.toFixed(1)} KB gz (budget ${BUDGETS[name]}) ${verdict}\n`,
  );
  for (const f of files) process.stdout.write(`  ${f}: ${kb(f).toFixed(1)} KB\n`);
}
if (failed) process.exit(1);
