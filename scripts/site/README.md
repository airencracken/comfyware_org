# Comfyware website

The public website lives in `site/`: plain HTML, one stylesheet, and local assets.
There is no frontend framework, JavaScript, build step, remote font, or analytics.
The Node dependencies in this directory are only for browser and accessibility tests.

## Preview

From the repository root:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory site
```

Open <http://127.0.0.1:8765>. This preview server is for local use. It uses its own
default error response; production Caddy serves our `404.html` with a 404 status.

## Check

```sh
python3 scripts/site/test_content.py
python3 scripts/site/test_http.py  # requires Caddy
npm ci --prefix scripts/site
cd scripts/site
npx playwright install chromium
npm test
```

To use a system Chromium instead, set `CHROMIUM=/usr/bin/chromium`. Optionally set
`SCREENSHOT_DIR=/tmp/comfyware-screenshots` to save desktop and mobile screenshots.
`SITE_URL=http://127.0.0.1:8765` tests a server already running. Without `SITE_URL`,
the test starts and stops its own temporary server on an available port.

The checks validate every route, local link and fragment, image dimensions,
canonical metadata, sitemap, asset boundaries, and markup structure. Ten deliberate
page mutations check that broken links, traversal references, injected code, wrong
metadata, and external assets fail validation. Browser checks cover four widths,
WCAG A/AA automated accessibility checks, and keyboard/navigation/FAQ use without
JavaScript. The HTTP tests start a temporary Caddy instance using the shipping
site block, and check status codes, redirects, content types, caching, headers,
read-only methods, and attempts to read paths outside the public site.
There is no application API or mutable state to test.

## Host

Serve **only the contents of `site/`**, at the root of comfyware.org. Any static web
server can do this; the canonical URLs and sitemap assume that domain and root.
Directory URLs such as `/imvault/` must serve their `index.html` files. Configure
unknown routes to return `404.html` with HTTP status **404**, not a success status.

`Caddyfile` is a ready-to-adapt site block. By default it serves `/srv/comfyware`
at `comfyware.org`, with automatic HTTPS. Copy the public files into that document
root and import the site block into your Caddy configuration. The Caddy service
account needs read access. Set DNS to the host and allow HTTPS before launch.
`COMFYWARE_ROOT` and `COMFYWARE_DOMAIN` can override those defaults for testing.
The repository and these scripts must stay outside the public document root.

Validate the configuration before reloading an existing server:

```sh
caddy validate --config scripts/site/Caddyfile --adapter caddyfile
```

This repository does not automatically deploy the site. Publishing is a separate
step once the hosting destination is chosen. Install dependencies and run checks
in CI or locally; the production host needs only the files in `site/`.

## Content and assets

Project links use the installation guides and latest-release redirects, avoiding
hardcoded versions that become stale. Keep feature descriptions aligned with the
project READMEs. The Arise description deliberately calls out its experimental
status. Application accounts live on their individual installations.

Screenshots are copied, unmodified, from the projects' demo/test screenshots:

- `assets/imvault-gallery.png`: `imvault/docs/images/recent.png` at
  `ff69d6af87e87204117c106cbdf2bb803ba31cde`.
- `assets/witmoot-board.png`: `witmoot/docs/images/board.png` at
  `7a2cba7c05d3704fafcd72058e17ba69c99ceddb`.

They contain sample media and conversations, not a live community. The house mark
is an SVG drawn for this site. Website code and these project assets use the
repository's AGPL-3.0-or-later license; see the root `LICENSE`.
