// SPDX-License-Identifier: AGPL-3.0-or-later
// Capture an isolated `make demo` instance with a visible first GIF frame.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const base = new URL(process.argv[2] || 'http://127.0.0.1:8080');
assert.equal(base.protocol, 'http:');
assert.equal(base.hostname, '127.0.0.1', 'Use an isolated local demo only');
assert.equal(base.username + base.password, '', 'Use a local demo URL without credentials');
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
try {
  const page = await browser.newPage({ viewport: { width: 1120, height: 900 }, colorScheme: 'light', reducedMotion: 'reduce' });
  await page.route('**/*', route => new URL(route.request().url()).origin === base.origin ? route.continue() : route.abort());
  async function login(username) {
    await page.context().clearCookies();
    await page.goto(new URL('/login', base).href);
    await page.locator('input[name="username"]').fill(username);
    await page.locator('input[name="password"]').fill('demo-password');
    await Promise.all([page.waitForURL(url => url.pathname !== '/login'), page.locator('form button[type="submit"]').click()]);
  }
  await login('freya');
  const sample = await readFile(new URL('../../design/screenshots/animation.gif', import.meta.url));
  await page.evaluate(async bytes => {
    const token = document.querySelector('meta[name="csrf-token"]').content;
    const keyResponse = await fetch('/settings/api-keys', { method: 'POST', headers: { 'HX-Request': 'true' },
      body: new URLSearchParams({ csrf_token: token, name: 'local screenshot fixture' }) });
    if (!keyResponse.ok) throw new Error('Could not create demo key');
    const key = (await keyResponse.text()).match(/value="(imv_[A-Za-z0-9]*_[A-Za-z0-9]*)"/)[1];
    const headers = { Authorization: `Bearer ${key}` };
    const response = await fetch('/api/v1/files?limit=100', { headers });
    if (!response.ok) throw new Error('Could not list demo files');
    for (const file of (await response.json()).files) {
      if (file.name === 'animation.gif') {
        const removed = await fetch(`/api/v1/files/${file.id}`, { method: 'DELETE', headers });
        if (!removed.ok) throw new Error('Could not replace demo animation');
      }
    }
    const body = new FormData();
    body.append('files', new Blob([new Uint8Array(bytes)], { type: 'image/gif' }), 'animation.gif');
    body.append('visibility', 'members');
    const uploaded = await fetch('/api/v1/upload', { method: 'POST', headers, body });
    if (!uploaded.ok) throw new Error('Could not upload demo animation');
  }, [...sample]);
  await login('demo');
  await page.goto(new URL('/recent', base).href);
  await page.locator('.grid .card').first().waitFor();
  await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(image => image.decode())); });
  await page.screenshot({ path: process.argv[3] || '/tmp/imvault-gallery.png' });
} finally {
  await browser.close();
}
