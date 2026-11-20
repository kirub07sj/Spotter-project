import assert from 'node:assert/strict';
import { randomBytes } from 'node:crypto';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const checker = fileURLToPath(new URL('./check-bundle-size.mjs', import.meta.url));

function check(entryKb, mapKb, dependencyKb = 0, shared = false, dynamic = false) {
  const dist = mkdtempSync(join(tmpdir(), 'spotter-bundle-'));
  try {
    mkdirSync(join(dist, '.vite'));
    const manifest = {
      'index.html': { file: 'entry.js', isEntry: true, imports: shared ? ['dependency'] : [] },
      'src/features/map/MapView.tsx': {
        file: 'map.js',
        [dynamic ? 'dynamicImports' : 'imports']: dependencyKb ? ['dependency'] : [],
      },
      dependency: { file: 'dependency.js' },
    };
    writeFileSync(join(dist, '.vite/manifest.json'), JSON.stringify(manifest));
    // Incompressible bytes make the test independent of application/minifier versions.
    for (const [file, size] of [
      ['entry.js', entryKb],
      ['map.js', mapKb],
      ['dependency.js', dependencyKb],
    ]) {
      writeFileSync(join(dist, file), randomBytes(size * 1024));
    }
    return spawnSync(process.execPath, [checker, dist], { encoding: 'utf8' });
  } finally {
    rmSync(dist, { recursive: true, force: true });
  }
}

test('D-21 accepts a map below 475 KB and rejects one above it', () => {
  const within = check(100, 474);
  assert.equal(within.status, 0, within.stdout + within.stderr);
  const over = check(100, 476);
  assert.equal(over.status, 1, over.stdout + over.stderr);
});

test('the initial JavaScript limit remains 250 KB', () => {
  assert.equal(check(249, 100).status, 0);
  assert.equal(check(251, 100).status, 1);
});

test('map imports and dynamic imports count toward its budget', () => {
  assert.equal(check(100, 200, 300).status, 1);
  assert.equal(check(100, 200, 300, false, true).status, 1);
});

test('shared imports already loaded by the entry are counted only once', () => {
  assert.equal(check(100, 400, 100, true).status, 0);
});
