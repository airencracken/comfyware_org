// SPDX-License-Identifier: AGPL-3.0-or-later
// Apply a saved choice before the stylesheet loads to avoid a theme flash.
(() => {
  const key = 'comfyware-theme';
  const root = document.documentElement;
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  const normalize = value => value === 'light' || value === 'dark' ? value : 'system';
  let choice = 'system';
  let picker;

  try { choice = normalize(localStorage.getItem(key)); } catch { /* Storage is optional. */ }

  function apply() {
    if (choice === 'system') root.removeAttribute('data-theme');
    else root.dataset.theme = choice;
    const dark = choice === 'dark' || (choice === 'system' && system.matches);
    document.querySelectorAll('meta[name="theme-color"]').forEach(meta => {
      meta.content = dark ? '#18221e' : '#f7f5ed';
    });
    if (picker) picker.value = choice;
  }

  apply();
  system.addEventListener('change', apply);
  window.addEventListener('storage', event => {
    if (event.key !== key && event.key !== null) return;
    choice = normalize(event.newValue);
    apply();
  });
  document.addEventListener('DOMContentLoaded', () => {
    picker = document.getElementById('theme');
    if (!picker) return;
    picker.value = choice;
    picker.addEventListener('change', () => {
      choice = normalize(picker.value);
      apply();
      try {
        if (choice === 'system') localStorage.removeItem(key);
        else localStorage.setItem(key, choice);
      } catch { /* The choice still works for this page when storage is blocked. */ }
    });
    picker.closest('.theme-picker').hidden = false;
  });
})();
