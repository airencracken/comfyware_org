# comfyware_org

The website for **comfyware.org**: a home for Imvault, Witmoot, Songstead, and the Comfyware
approach to software for friends, family, and small communities.

Plain HTML and CSS, with local screenshots, system fonts, and a small optional
script for the light/dark theme preference. The public files live in `site/`;
there is no frontend build step or runtime dependency.

## Preview

```sh
make preview
```

Open <http://127.0.0.1:8765>. Use `make preview PORT=9000` for another port;
Ctrl-C stops the server. Previewing requires only Make and Python 3.

Run `make help` (or just `make`) for all targets. For development checks, install
Node.js 20 or later and Caddy, then run:

```sh
make setup
make check
make screenshots
```

If Chromium is already installed, use `make deps` followed by
`make check CHROMIUM=/usr/bin/chromium` instead. See the
[website guide](scripts/site/README.md) for more options, asset provenance,
and the production Caddy configuration.

## Deploy

On the web server, run `git pull`, then `make deploy`. It checks the content and
publishes `site/` to `/var/www/comfyware` (set `DEPLOY_DIR` to change it), removing
anything no longer in `site/`. Use `DRY_RUN=1 make deploy` to preview.

## Repository layout

- `site/`: the complete public website; serve only this directory.
- `scripts/site/`: content, HTTP, and browser checks, plus hosting documentation.
- `.github/workflows/website.yml`: website CI checks.

The Gentoo overlay is maintained separately in
[airencracken/comfyware](https://github.com/airencracken/comfyware).

Licensed under AGPL-3.0-or-later. See [LICENSE](LICENSE).
