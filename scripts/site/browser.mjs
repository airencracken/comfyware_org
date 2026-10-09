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
import { checkThemes } from './themes.mjs';

const root = fileURLToPath(new URL('../../site/', import.meta.url));
const routes = ['/', '/imvault/', '/witmoot/', '/songstead/', '/principles/', '/404.html'];
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
  const assetPage = await browser.newPage();
  await assetPage.goto(base);
  for (const [asset, budget] of [['comfy-robot.webp', 45000], ['comfy-robot.png', 100000]]) {
    const result = await assetPage.evaluate(async asset => {
      const response = await fetch(`/assets/${asset}`);
      const blob = await response.blob();
      const image = await createImageBitmap(blob);
      const canvas = document.createElement('canvas');
      canvas.width = image.width;
      canvas.height = image.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(image, 0, 0);
      return { ok: response.ok, bytes: blob.size, width: image.width, height: image.height,
        corner: ctx.getImageData(0, 0, 1, 1).data[3], center: ctx.getImageData(340, 340, 1, 1).data[3] };
    }, asset);
    check(result.ok && result.bytes <= budget, `${asset}: download budget`);
    check(result.width === 680 && result.height === 680, `${asset}: decodes at intended resolution`);
    check(result.corner === 0 && result.center >= 250, `${asset}: transparent margin and visible artwork`);
  }
  await assetPage.close();
  if (screenshotDir) await mkdir(screenshotDir, { recursive: true });
  for (const colorScheme of ['light', 'dark']) {
    for (const width of [320, 390, 768, 1440]) {
      const context = await browser.newContext({ colorScheme, viewport: { width, height: 960 }, reducedMotion: 'reduce' });
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
        if (route === '/' || route === '/songstead/') {
          const screenshot = await page.locator('img[src="/assets/songstead-recent.png"]').evaluate(image => {
            const box = image.getBoundingClientRect();
            return { width: box.width, height: box.height, naturalWidth: image.naturalWidth, naturalHeight: image.naturalHeight };
          });
          check(screenshot.width > 0 && screenshot.naturalWidth === 1280 && screenshot.naturalHeight === 1183, `${route}: real Songstead screenshot at ${width}px`);
          if (route === '/songstead/') {
            check(Math.abs(screenshot.width / screenshot.height - 1280 / 1183) < 0.01, `Songstead screenshot preserves its full aspect ratio at ${width}px`);
            check(await page.getByRole('link', { name: 'View the full Songstead screenshot' }).getAttribute('href') === '/assets/songstead-recent.png', 'Full screenshot link');
          }
        }
        const accessibility = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'best-practice']).analyze();
        assert.deepEqual(accessibility.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) })), [], `${route}: ${colorScheme} accessibility at ${width}px`);
        checks++;
        if (screenshotDir && [390, 1440].includes(width)) {
          const name = route === '/' ? 'home' : route.replaceAll('/', '').replace('.html', '');
          await page.screenshot({ path: resolve(screenshotDir, `${name}-${colorScheme}-${width}.png`), fullPage: true });
        }
      }
      check(problems.length === 0, `Browser errors: ${problems.join(', ')}`);
      await context.close();
    }
  }
  await checkThemes(browser, base, check);
  const context = await browser.newContext({ javaScriptEnabled: false, colorScheme: 'dark', viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await page.goto(base);
  check(!await page.getByLabel('Color theme').isVisible(), 'No inactive theme control without JavaScript');
  check(await page.locator('html').evaluate(el => getComputedStyle(el).colorScheme) === 'dark', 'System dark mode works without JavaScript');
  await page.emulateMedia({ colorScheme: 'light' });
  check(await page.locator('html').evaluate(el => getComputedStyle(el).colorScheme) === 'light', 'System changes work without JavaScript');
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
  await page.getByRole('link', { name: 'Meet Songstead' }).click();
  check(new URL(page.url()).pathname === '/songstead/', 'Songstead navigation works without JavaScript');
  check(await page.getByText('Songstead · Music recommendations · 0.3.1', { exact: false }).count() > 0, 'Songstead release version is visible');
  const privacyQuestion = page.getByText('Who can see what I share?', { exact: true });
  await privacyQuestion.focus();
  await page.keyboard.press('Enter');
  check(await page.getByText('Everyone here means people signed in to your Songstead installation.', { exact: false }).isVisible(), 'Songstead audience explanation opens with the keyboard without JavaScript');
  await page.keyboard.press('Enter');
  check(!await page.getByText('Everyone here means people signed in to your Songstead installation.', { exact: false }).isVisible(), 'Songstead audience explanation closes with the keyboard');
  await page.getByRole('link', { name: 'Comfyware home' }).click();
  await page.getByRole('link', { name: 'Read the Comfyware principles' }).click();
  check(new URL(page.url()).origin === new URL(base).origin && new URL(page.url()).pathname === '/principles/', 'Principles open as a page on this site without JavaScript');
  check(await page.getByRole('heading', { name: 'Local sovereignty', exact: true }).count() === 1, 'The principles page contains the full principles');
  await page.getByRole('link', { name: 'Back to Comfyware' }).click();
  check(new URL(page.url()).pathname === '/' && new URL(page.url()).hash === '#about', 'Principles link back to the homepage approach section');
  await context.close();
  console.log(`Passed ${checks} browser checks, including both themes at four viewport widths, saved preferences, and navigation without JavaScript.`);
} finally {
  if (browser) await browser.close();
  if (server && server.exitCode === null) { const exited = once(server, 'exit'); server.kill(); await exited; }
}
