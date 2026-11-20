// Fails if the initial JS (entry chunk + its static imports) exceeds the budget (docs/04 §7).
import { readFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { join } from 'node:path';

const INITIAL_BUDGET_KB = 250;
const dist = new URL('../dist/', import.meta.url).pathname;
const manifest = JSON.parse(readFileSync(join(dist, '.vite/manifest.json'), 'utf8'));
const entry = Object.values(manifest).find((c) => c.isEntry);
const seen = new Set();
const visit = (key) => {
  const chunk = manifest[key] ?? Object.values(manifest).find((c) => c.file === key);
  if (!chunk || seen.has(chunk.file)) return;
  seen.add(chunk.file);
  (chunk.imports ?? []).forEach(visit);
};
visit(Object.keys(manifest).find((k) => manifest[k] === entry));
let total = 0;
for (const file of seen) {
  const kb = gzipSync(readFileSync(join(dist, file))).length / 1024;
  total += kb;
  process.stdout.write(`${file}: ${kb.toFixed(1)} KB gz\n`);
}
process.stdout.write(`initial JS: ${total.toFixed(1)} KB gz (budget ${INITIAL_BUDGET_KB})\n`);
if (total > INITIAL_BUDGET_KB) process.exit(1);
