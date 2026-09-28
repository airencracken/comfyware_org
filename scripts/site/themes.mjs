// SPDX-License-Identifier: AGPL-3.0-or-later
// Exercise theme behavior through the public control, including restricted storage.
export async function checkThemes(browser, base, check) {
  const key = 'comfyware-theme';
  const colors = { light: 'rgb(247, 245, 237)', dark: 'rgb(24, 34, 30)' };
  async function expectTheme(page, theme, message) {
    await page.waitForFunction(expected => getComputedStyle(document.documentElement).backgroundColor === expected, colors[theme]);
    check(await page.locator('html').evaluate(el => getComputedStyle(el).colorScheme) === theme, message);
    await page.waitForFunction(color => [...document.querySelectorAll('meta[name="theme-color"]')].every(meta => meta.content === color), theme === 'dark' ? '#18221e' : '#f7f5ed');
    const meta = await page.locator('meta[name="theme-color"]').evaluateAll(elements => elements.map(el => el.content));
    check(meta.length === 2 && meta.every(value => value === (theme === 'dark' ? '#18221e' : '#f7f5ed')), `${message}: browser chrome`);
  }

  const context = await browser.newContext({ colorScheme: 'dark' });
  try {
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base);
    await expectTheme(page, 'dark', 'A fresh visit follows system dark mode');
    const picker = page.getByLabel('Color theme');
    check(await picker.inputValue() === 'system', 'System is the initial choice');
    await picker.focus();
    await page.keyboard.press('Home');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    await expectTheme(page, 'light', 'Keyboard selection switches to light');
    check(await page.evaluate(key => localStorage.getItem(key), key) === 'light', 'Explicit preference is saved');
    await page.reload();
    await expectTheme(page, 'light', 'Saved light preference survives reload on a dark device');
    await page.getByRole('link', { name: 'Meet Imvault' }).click();
    await expectTheme(page, 'light', 'Preference carries to project pages');
    check(await picker.inputValue() === 'light', 'Control reflects the saved preference');
    await page.emulateMedia({ colorScheme: 'light' });
    await picker.selectOption('dark');
    await expectTheme(page, 'dark', 'Explicit dark overrides a light device');
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.emulateMedia({ colorScheme: 'light' });
    await expectTheme(page, 'dark', 'A device change preserves an explicit preference');

    const other = await context.newPage();
    await other.goto(new URL('/witmoot/', base).href);
    await expectTheme(other, 'dark', 'A new tab receives the saved preference');
    await other.getByLabel('Color theme').selectOption('light');
    await expectTheme(page, 'light', 'Changes synchronize across open tabs');
    await other.getByLabel('Color theme').selectOption('system');
    await expectTheme(other, 'dark', 'System restores the second tab device preference');
    await expectTheme(page, 'light', 'System restores the first tab device preference');
    check(await page.evaluate(key => localStorage.getItem(key), key) === null, 'System clears the saved override');
    check(await picker.inputValue() === 'system', 'Removing the override updates the other tab control');
    await page.emulateMedia({ colorScheme: 'dark' });
    await expectTheme(page, 'dark', 'System follows a device change while the page is open');
    await picker.selectOption('dark');
    await other.evaluate(() => localStorage.clear());
    await page.waitForFunction(() => document.getElementById('theme').value === 'system');
    await page.emulateMedia({ colorScheme: 'light' });
    await expectTheme(page, 'light', 'Clearing storage restores system behavior across tabs');

    for (const value of ['', 'system', 'DARK', 'null', '{"theme":"dark"}', '<script>alert(1)</script>']) {
      await page.evaluate(({ key, value }) => localStorage.setItem(key, value), { key, value });
      await page.reload();
      check(await picker.inputValue() === 'system', 'Unrecognized stored preferences fall back to system');
      await expectTheme(page, 'light', 'Invalid storage does not alter theme behavior');
    }
    await picker.selectOption('dark');
    await page.emulateMedia({ media: 'print' });
    check(await page.locator('html').evaluate(el => getComputedStyle(el).backgroundColor) === colors.light, 'Printing uses the light palette even with dark selected');
    check(!await picker.isVisible(), 'Theme control stays out of print');
    check(errors.length === 0, `Theme errors: ${errors.join(', ')}`);
  } finally { await context.close(); }

  for (const restriction of ['read', 'write']) {
    const restricted = await browser.newContext({ colorScheme: 'dark' });
    try {
      await restricted.addInitScript(restriction => {
        const fail = () => { throw new DOMException('Storage blocked', 'SecurityError'); };
        if (restriction === 'read') Object.defineProperty(window, 'localStorage', { get: fail });
        else {
          Storage.prototype.setItem = fail;
          Storage.prototype.removeItem = fail;
        }
      }, restriction);
      const page = await restricted.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(base);
      await expectTheme(page, 'dark', `Blocked storage ${restriction} follows the device`);
      await page.getByLabel('Color theme').selectOption('light');
      await expectTheme(page, 'light', `Blocked storage ${restriction} still permits a page choice`);
      await page.getByLabel('Color theme').selectOption('system');
      await expectTheme(page, 'dark', `Blocked storage ${restriction} still permits system mode`);
      check(errors.length === 0, `Blocked storage ${restriction} causes no uncaught errors`);
    } finally { await restricted.close(); }
  }

  const early = await browser.newContext({ colorScheme: 'light' });
  let releaseStylesheet;
  const held = new Promise(resolve => { releaseStylesheet = resolve; });
  try {
    await early.addInitScript(key => localStorage.setItem(key, 'dark'), key);
    const page = await early.newPage();
    await page.route('**/assets/site.css', async route => { await held; await route.continue(); });
    await page.goto(base, { waitUntil: 'commit' });
    await page.waitForFunction(() => document.documentElement.dataset.theme === 'dark');
    check(await page.evaluate(() => document.styleSheets.length) === 0, 'Saved theme is applied while the stylesheet is still blocked, before first paint');
    releaseStylesheet();
    await page.waitForLoadState();
    await expectTheme(page, 'dark', 'Early preference survives stylesheet loading');
  } finally {
    releaseStylesheet();
    await early.close();
  }
}
