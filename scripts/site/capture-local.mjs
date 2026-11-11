// SPDX-License-Identifier: AGPL-3.0-or-later
// Capture only an explicitly started, disposable offline demonstration.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const [app, address, destination] = process.argv.slice(2);
assert.ok(['folkweave', 'tidings', 'witmoot'].includes(app));
assert.ok(destination, 'Provide a local output PNG path');
const base = new URL(address);
assert.equal(base.protocol, 'http:');
assert.equal(base.hostname, '127.0.0.1', 'Use a disposable loopback demo only');
assert.equal(base.username + base.password + base.search + base.hash, '');
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: app === 'witmoot' ? 1233 : 1000 }, colorScheme: 'light', reducedMotion: 'reduce' });
  const problems = [];
  page.on('pageerror', error => problems.push(error.message));
  await page.route('**/*', route => new URL(route.request().url()).origin === base.origin ? route.continue() : route.abort());
  await page.goto(new URL('/login', base).href);
  await page.getByLabel('Username', { exact: true }).fill('demo');
  await page.getByLabel('Password', { exact: true }).fill(app === 'folkweave' ? 'folkweave-demo-only' : 'demo-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.waitForURL(url => url.pathname !== '/login');
  if (app === 'folkweave') {
    await page.locator('#post-body').fill('A slow afternoon by the garden, and a walk down to the sea. A few photographs to keep.');
    const names = ['garden-table.jpg', 'coastal-walk.jpg'];
    await page.locator('#photos').setInputFiles(await Promise.all(names.map(async name => ({ name, mimeType: 'image/jpeg', buffer: await readFile(new URL('../../design/demo-assets/' + name, import.meta.url)) }))));
    await page.getByRole('button', { name: 'Share', exact: true }).click();
    await page.locator('#feed .post').first().getByText('A slow afternoon by the garden, and a walk down to the sea. A few photographs to keep.', { exact: true }).waitFor();
  }
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].filter(image => image.getBoundingClientRect().top < innerHeight).map(image => image.decode()));
  });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  assert.deepEqual(problems, []);
  await page.screenshot({ path: destination });
  console.log(`Captured ${app}'s current interface with its offline demo.`);
} finally {
  await browser.close();
}
