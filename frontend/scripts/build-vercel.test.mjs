import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const script = fileURLToPath(new URL('./build-vercel.mjs', import.meta.url));

for (const value of ['', 'not-a-url', 'http://backend.example/api/v1', 'https://user:pass@backend.example/api/v1',
  'https://backend.example/api/v1?token=secret', 'https://backend.example/api/v2']) {
  test(`Vercel build rejects invalid API_BASE_URL: ${value || '(empty)'}`, () => {
    const result = spawnSync(process.execPath, [script], {
      env: { ...process.env, API_BASE_URL: value },
      encoding: 'utf8',
    });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /API_BASE_URL/);
  });
}

test('Vercel serves the Angular browser output with an SPA fallback', () => {
  const config = JSON.parse(readFileSync(new URL('../vercel.json', import.meta.url), 'utf8'));
  assert.equal(config.outputDirectory, 'dist/frontend/browser');
  assert.deepEqual(config.rewrites, [{ source: '/(.*)', destination: '/index.html' }]);
});
