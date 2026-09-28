// SPDX-License-Identifier: AGPL-3.0-or-later
// Browser checks use a temporary local server unless SITE_URL is supplied.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';

const root = fileURLToPath(new URL('../../site/', import.meta.url));
const routes = ['/', '/imvault/', '/witmoot/', '/404.html'];
const screenshotDir = process.env.SCREENSHOT_DIR;
let server;
let browser;
let checks = 0;
function check(condition, message) { assert.ok(condition, message); checks++; }

try {
  let base = process.env.SITE_URL;
  if (!base) {
    server = spawn('python3', ['-u', '-c', `
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
import sys
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=sys.argv[1]))
print(server.server_address[1], flush=True)
server.serve_forever()
`, root], { stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    const port = await new Promise((resolvePort, reject) => {
      const timer = setTimeout(() => reject(new Error('Preview server did not start')), 10000);
      server.once('error', error => { clearTimeout(timer); reject(error); });
      server.once('exit', code => { clearTimeout(timer); reject(new Error(`Preview server exited: ${code}`)); });
      server.stdout.on('data', chunk => {
        output += chunk;
        if (/^\d+\n/.test(output)) { clearTimeout(timer); resolvePort(Number(output.trim())); }
      });
      server.stderr.on('data', () => {});
    });
    base = `http://127.0.0.1:${port}`;
  }
  browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
  if (screenshotDir) await mkdir(screenshotDir, { recursive: true });
  for (const width of [320, 390, 768, 1440]) {
    const context = await browser.newContext({ viewport: { width, height: 960 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    const problems = [];
    page.on('pageerror', error => problems.push(error.message));
    page.on('requestfailed', request => problems.push(request.url()));
    page.on('response', response => { if (response.status() >= 400 && !response.url().endsWith('/404.html')) problems.push(`${response.status()} ${response.url()}`); });
    for (const route of routes) {
      const response = await page.goto(new URL(route, base).href);
      check(response.ok() || (route === '/404.html' && response.status() === 404), `${route} should load`);
      await page.evaluate(async () => {
        await Promise.all([...document.images].map(image => { image.loading = 'eager'; return image.decode(); }));
      });
      check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${route}: overflow at ${width}px`);
      check(await page.locator('h1').count() === 1, `${route}: one main heading`);
      const accessibility = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'best-practice']).analyze();
      assert.deepEqual(accessibility.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) })), [], `${route}: accessibility at ${width}px`);
      checks++;
      if (screenshotDir && [390, 1440].includes(width)) {
        const name = route === '/' ? 'home' : route.replaceAll('/', '').replace('.html', '');
        await page.screenshot({ path: resolve(screenshotDir, `${name}-${width}.png`), fullPage: true });
      }
    }
    check(problems.length === 0, `Browser errors: ${problems.join(', ')}`);
    await context.close();
  }
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await page.goto(base);
  await page.keyboard.press('Tab');
  check(await page.locator('.skip-link').evaluate(el => el === document.activeElement), 'Skip link is first keyboard stop');
  await page.keyboard.press('Enter');
  check(await page.locator('main').evaluate(el => el === document.activeElement), 'Skip link focuses main content');
  const question = page.getByText('Can I sign up for an account here?', { exact: true });
  await question.focus();
  await page.keyboard.press('Enter');
  check(await page.locator('details').first().getAttribute('open') !== null, 'FAQ opens with keyboard and JavaScript disabled');
  await page.keyboard.press('Enter');
  check(await page.locator('details').first().getAttribute('open') === null, 'FAQ closes with keyboard');
  await page.getByRole('link', { name: 'Meet Imvault' }).click();
  check(new URL(page.url()).pathname === '/imvault/', 'Imvault navigation works without JavaScript');
  await page.getByRole('link', { name: 'Meet Witmoot' }).click();
  check(new URL(page.url()).pathname === '/witmoot/', 'Cross-project navigation works without JavaScript');
  await page.getByRole('link', { name: 'Comfyware home' }).click();
  check(new URL(page.url()).pathname === '/', 'Home navigation works without JavaScript');
  await context.close();
  console.log(`Passed ${checks} browser checks, including accessibility at four viewport widths and navigation without JavaScript.`);
} finally {
  if (browser) await browser.close();
  if (server && server.exitCode === null) { const exited = once(server, 'exit'); server.kill(); await exited; }
}
