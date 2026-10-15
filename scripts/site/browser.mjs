// SPDX-License-Identifier: AGPL-3.0-or-later
// Browser checks use a temporary local server unless SITE_URL is supplied.
import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { once } from 'node:events';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import { checkThemes } from './themes.mjs';

const root = fileURLToPath(new URL('../../site/', import.meta.url));
const routes = ['/', '/imvault/', '/witmoot/', '/songstead/', '/principles/', '/imvault/docs/', '/witmoot/docs/', '/songstead/docs/', '/404.html'];
const screenshotDir = process.env.SCREENSHOT_DIR;
let server;
let browser;
let checks = 0;
function check(condition, message) { assert.ok(condition, message); checks++; }

try {
  for (const url of ['http://example.org', 'http://127.0.0.1.example.org', 'https://127.0.0.1', 'file:///tmp/demo', 'http://user:password@127.0.0.1']) {
    const result = spawnSync(process.execPath, [fileURLToPath(new URL('./capture-imvault.mjs', import.meta.url)), url], { timeout: 5000 });
    check(result.status === 1, `Screenshot capture refuses unsafe destination: ${url}`);
  }
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
        if (['/imvault/', '/witmoot/', '/songstead/'].includes(route)) {
          const height = await page.evaluate(() => document.documentElement.scrollHeight);
          check(height < (width >= 1100 ? 4300 : 6000), `${route}: product page length at ${width}px (${height}px)`);
        }
        if (route === '/' && width === 1440) {
          const cards = await page.locator('.project').evaluateAll(cards => cards.map(card => {
            const box = card.getBoundingClientRect();
            return { top: box.top, width: box.width };
          }));
          check(cards.length === 3 && cards.every(card => Math.abs(card.width-cards[0].width) < 1 && Math.abs(card.top-cards[0].top) < 1), 'Three equal app cards on desktop');
        }
        if (route === '/' || route === '/songstead/') {
          const screenshot = await page.locator('img[src="/assets/songstead-recent.webp"]').evaluate(image => {
            const box = image.getBoundingClientRect();
            return { width: box.width, height: box.height, naturalWidth: image.naturalWidth, naturalHeight: image.naturalHeight };
          });
          check(screenshot.width > 0 && screenshot.naturalWidth === 1280 && screenshot.naturalHeight === 1289, `${route}: real Songstead screenshot at ${width}px`);
          if (route === '/songstead/') {
            check(Math.abs(screenshot.width / screenshot.height - 1280 / 1289) < 0.01, `Songstead screenshot preserves its full aspect ratio at ${width}px`);
            check(await page.getByRole('link', { name: 'View the full Songstead screenshot' }).getAttribute('href') === '/assets/songstead-recent.webp', 'Full screenshot link');
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
  check(await page.getByRole('link',{name:'Songstead 0.10.0',exact:true}).isVisible(), 'Songstead release version is visible');
  for (const [app,name,version] of [['imvault','Imvault','0.19.0'],['witmoot','Witmoot','0.18.0'],['songstead','Songstead','0.10.0']]) {
    for (const route of ['/',`/${app}/`]) {
      await page.goto(base+route);
      const release=page.getByRole('link',{name:`${name} ${version}`,exact:true});
      check(await release.isVisible(),`${name} version is visible on ${route} without JavaScript`);
      check(await release.getAttribute('href')===`https://github.com/airencracken/${app}/releases/tag/v${version}`,`${name} version links to matching release notes`);
    }
  }
  await page.goto(base+'/');
  const ariseRelease=page.getByRole('link',{name:'Arise 0.0.42',exact:true});
  check(await ariseRelease.isVisible(),'Arise release is visible alongside its experimental status');
  check(await ariseRelease.getAttribute('href')==='https://github.com/airencracken/arise/releases/tag/v0.0.42','Arise release links to matching notes');
  for (const app of ['imvault', 'witmoot', 'songstead']) {
    await page.goto(base+`/${app}/`);
    await page.getByRole('link', { name: 'Documentation', exact: true }).click();
    check(new URL(page.url()).pathname === `/${app}/docs/`, `${app}: documentation navigation without JavaScript`);
    await page.getByRole('link', { name: 'Back up', exact: true }).click();
    check(new URL(page.url()).hash === '#backups', `${app}: backup topic navigation without JavaScript`);
    check(await page.getByRole('heading', { name: 'Back up and recover.', exact: true }).isVisible(), `${app}: recovery guidance is readable`);
  }
  await page.goto(base+'/songstead/');
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
