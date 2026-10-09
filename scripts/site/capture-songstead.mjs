// SPDX-License-Identifier: AGPL-3.0-or-later
// Capture the real application using only a disposable demo database.
import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { createServer } from 'node:net';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const binary = process.env.SONGSTEAD_BINARY;
assert.ok(binary, 'Set SONGSTEAD_BINARY to a built Songstead executable');
const destination = fileURLToPath(new URL('../../site/assets/songstead-recent.png', import.meta.url));
const directory = await mkdtemp(resolve(tmpdir(), 'songstead-screenshot-'));
const environment = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('SONGSTEAD_')));
const password = 'demo-password';
let app;
let browser;
try {
  const version = spawnSync(binary, ['--version'], { env: environment, encoding: 'utf8' });
  assert.equal(version.status, 0);
  assert.equal(version.stdout.trim(), 'songstead 0.4.1');
  for (const username of ['alice', 'bobby', 'carol']) {
    const result = spawnSync(binary, ['create-user', '--data-dir', directory, '--username', username, '--password-stdin'],
      { input: `${password}\n`, env: environment, encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
  }
  const listener = createServer();
  listener.listen(0, '127.0.0.1');
  await once(listener, 'listening');
  const port = listener.address().port;
  await new Promise((done, reject) => listener.close(error => error ? reject(error) : done()));
  const base = `http://127.0.0.1:${port}`;
  app = spawn(binary, ['serve', '--addr', `127.0.0.1:${port}`, '--data-dir', directory],
    { env: environment, stdio: ['ignore', 'ignore', 'pipe'] });
  let errors = '';
  app.stderr.on('data', chunk => { errors += chunk; });
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (app.exitCode !== null) throw new Error(`Demo exited: ${errors}`);
    try { ready = (await fetch(`${base}/healthz`)).ok; } catch {}
    if (ready) break;
    await new Promise(done => setTimeout(done, 100));
  }
  assert.ok(ready, 'Demo did not become healthy');
  browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
  const contexts = new Map();
  for (const username of ['alice', 'bobby', 'carol']) {
    const context = await browser.newContext({ colorScheme: 'light', viewport: { width: 1280, height: 960 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.route('**/*', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort());
    await page.goto(`${base}/login`);
    await page.getByLabel('Username', { exact: true }).fill(username);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.waitForURL('**/shelf');
    contexts.set(username, page);
  }
  const examples = [
    ['bobby', 'A little room for the rain', 'Juniper House', 'album', 'This feels like the walk home after a really good evening.', 'Folk', 'Acoustic, rainy-day'],
    ['carol', 'Slow Saturday', 'The Window Seats', 'track', 'For making coffee with absolutely nowhere to be.', 'Jazz', 'Instrumental, warm'],
    ['bobby', 'Northbound', 'Quiet Company', 'track', 'The drums at 2:43 made me think of you.', 'Indie rock', 'Live'],
    ['alice', 'Evening light', 'Soft Signals', 'album', 'A small discovery from last week. No need to hurry.', 'Ambient', 'Late-night'],
  ];
  for (const [username, title, artist, kind, note, genre, tags] of examples) {
    const page = contexts.get(username);
    await page.goto(`${base}/recommendations/new`);
    await page.getByLabel('Music link', { exact: true }).fill(`https://music.example.com/${title.toLowerCase().replaceAll(' ', '-')}`);
    await page.locator('select[name=audience]').selectOption('members');
    await page.locator('select[name=kind]').selectOption(kind);
    await page.getByLabel('Title, if you know it', { exact: true }).fill(title);
    await page.getByLabel('Artist', { exact: true }).fill(artist);
    await page.getByLabel('Genre', { exact: true }).fill(genre);
    await page.getByLabel('Tags', { exact: true }).fill(tags);
    await page.getByLabel('A note, if you like', { exact: true }).fill(note);
    await page.getByRole('button', { name: 'Share recommendation', exact: true }).click();
    await page.waitForURL(/\/recommendations\/\d+$/);
  }
  // Fictional, local artwork fixtures demonstrate the cached thumbnail routes.
  const seeded = spawnSync('python3', ['-c', `
import sqlite3,struct,zlib,sys
from pathlib import Path
def chunk(kind,data):
    return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
def cover(colors):
    width=320; height=240
    rows=[]
    for y in range(height):
        row=bytearray()
        for x in range(width): row.extend(colors[((x//64)+(y//60))%len(colors)])
        rows.append(b'\\0'+row)
    return b'\\x89PNG\\r\\n\\x1a\\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')
with sqlite3.connect(Path(sys.argv[1])/'songstead.db') as db:
    db.execute('UPDATE recommendations SET created_at=1791457200-id*86400')
    for title,colors in [('A little room for the rain',[(51,82,68),(185,204,180),(139,148,115)]),('Slow Saturday',[(46,71,94),(213,177,125),(156,92,62)]),('Northbound',[(51,56,67),(109,126,147),(144,67,68)])]:
        db.execute('INSERT INTO media_artwork(media_id,content) SELECT id,? FROM media WHERE title=?',(cover(colors),title))
`, directory], { encoding: 'utf8' });
  assert.equal(seeded.status, 0, seeded.stderr);
  const page = contexts.get('alice');
  await page.goto(`${base}/recent?layout=tiles&discovery=all`);
  await page.getByRole('heading', { name: 'Recent', exact: true }).waitFor();
  assert.equal(await page.locator('.recommendations > .panel').count(), 4);
  assert.ok(await page.getByText('Evening light', { exact: true }).count());
  assert.ok(await page.getByText('Slow Saturday', { exact: true }).count());
  assert.equal(await page.locator('[type="password"]').count(), 0);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  assert.equal(await page.locator('.recommendations.tiles').count(), 1);
  assert.equal(await page.locator('.artwork-placeholder').count(), 1);
  for (const image of await page.locator('.tile-artwork img[src$="/thumbnail"]').all()) {
    await image.scrollIntoViewIfNeeded();
    await image.evaluate(async element => { await element.decode(); });
  }
  await page.evaluate(() => scrollTo(0,0));
  await page.screenshot({ path: destination, fullPage: true });
  console.log('Captured Songstead Recent with four fictional recommendations and three demo accounts.');
} finally {
  if (browser) await browser.close();
  if (app && app.exitCode === null) { const exited = once(app, 'exit'); app.kill(); await exited; }
  await rm(directory, { recursive: true, force: true });
}
