// Open native disclosure controls using the same interaction as a reader.
export async function act(locator, method, ...args) {
  const page = locator.page();
  if (await locator.count() === 0) {
    const menu = page.locator('details.comfy-account:not([open]) > summary');
    if (await menu.count()) await menu.click();
  }
  if (await locator.count() && !await locator.locator('xpath=ancestor::details[contains(@class, \"comfy-menu\")]').count()) {
    const openMenu = page.locator('details.comfy-menu[open] > summary');
    for (let i = await openMenu.count()-1; i >= 0; i--) await openMenu.nth(i).click();
  }
  const ancestors = locator.locator('xpath=ancestor::details[not(@open)]');
  for (let i = await ancestors.count() - 1; i >= 0; i--) {
    await ancestors.nth(i).locator(':scope > summary').click();
  }
  return locator[method](...args);
}
