# Comfyware website

The public website lives in `site/`: plain HTML, one stylesheet, a small theme
script, and local assets. There is no frontend framework, build step, remote font,
or analytics. The site follows the device's light/dark preference by default.
The header's System/Light/Dark control saves an explicit choice in localStorage
and synchronizes it across tabs. If storage is blocked, the choice works for the
current page. Without JavaScript, the site still follows the device preference
and all content and navigation work; the theme control stays hidden.
The Node dependencies in this directory are only for browser and accessibility tests.

## Preview

From the repository root:

```sh
make preview
# Choose another port if needed:
make preview PORT=9000
```

Open <http://127.0.0.1:8765>. This preview server is for local use. It uses its own
default error response; production Caddy serves our `404.html` with a 404 status.
Ctrl-C stops the server. `make serve` is an alias. Previewing needs only Make and
Python 3; it does not need the browser-test packages. The default binding is
`127.0.0.1`; `HOST` and `PORT` can be overridden explicitly.

## Check

```sh
make setup        # install test packages and Chromium
make check        # all checks, including the Caddy configuration
make screenshots  # checks plus desktop/mobile screenshots in .artifacts/screenshots/
```

The checks need Python 3.9 or later, Node.js 20 or later, and Caddy on `PATH`.
`make setup` installs the packages in `scripts/site/` from the lockfile, then
downloads Chromium. If browser system libraries are missing, run
`make browser-install PLAYWRIGHT_INSTALL_ARGS=--with-deps` after installing the
test packages; installing those system packages may require administrator access.

To use an existing Chromium installation instead of downloading one:

```sh
make deps
make check CHROMIUM=/usr/bin/chromium
make screenshots CHROMIUM=/usr/bin/chromium SCREENSHOT_DIR=/tmp/comfyware-screenshots
```

Run individual suites with `make test-content`, `make test-http`, or
`make test-browser`. `make test` is an alias for `make check`.
`make test-browser SITE_URL=http://127.0.0.1:8765` tests a server already running.
Without `SITE_URL`, the browser suite starts and stops its own temporary server
on an available port. `make help` lists all targets and overrides.

The checks validate every route, local link and fragment, image dimensions,
canonical metadata, sitemap, asset boundaries, and markup structure. Deliberate
page mutations check that broken links, traversal references, injected code, wrong
metadata, and external assets fail validation. Browser checks cover both palettes
at four widths, WCAG A/AA automated accessibility checks, theme persistence,
system changes, cross-tab synchronization, invalid or blocked storage, and applying
the saved theme before the stylesheet loads. They also check keyboard/navigation/FAQ
use without JavaScript. Screenshots include both palettes in their filenames.
The HTTP tests start a temporary Caddy instance using the shipping
site block, and check status codes, redirects, content types, caching, headers,
read-only methods, and attempts to read paths outside the public site.
There is no application API or server-side mutable state to test.

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
make check-config
```

Publish from a checkout on the web server:

```sh
git pull
DRY_RUN=1 make deploy   # list what would change
make deploy
```

`make deploy` runs the content checks, then copies `site/` to `DEPLOY_DIR`
(default `/var/www/comfyware`) with rsync. The document root becomes an exact
copy: pages and assets removed from `site/` stop being served, and files are
published world-readable (directories 0755, files 0644). It needs Python 3 and
rsync, nothing from the browser or Caddy checks. It refuses a destination that
is missing, relative, `/`, inside this repository, or that contains it. Set
`DEPLOY_DIR=/srv/comfyware` to match the Caddyfile's default root. CI does not
deploy; run the full `make check` there or locally before publishing.

## Content and assets

The homepage's approach section summarizes our own
[Comfyware principles page](../../site/principles/index.html):
local sovereignty, accountable hosts, respect for attention, bounded communities,
exit and ownership, and community-defined house rules. These guide product choices;
they are not a claim that every planned portability feature already exists.

Project links use the installation guides and latest-release redirects, avoiding
hardcoded versions that become stale. Keep feature descriptions aligned with the
project READMEs. The Arise description deliberately calls out its experimental
status. Application accounts live on their individual installations.

Screenshots are copied, unmodified, from the projects' demo/test screenshots:

- `assets/imvault-gallery.png`: `imvault/docs/images/recent.png` at
  `ff69d6af87e87204117c106cbdf2bb803ba31cde`.
- `assets/witmoot-board.png`: `witmoot/docs/images/board.png` at
  `8f20e2f26bf594394526ee7f6a558f013fd3c47b` (0.7.2).

- `assets/songstead-recent.png`: captured from Songstead 0.6.0 at
  `285014a`, with four fictional music
  recommendations, local sample artwork and three disposable demo accounts.
  It shows the optional tile layout; List remains the application default. To reproduce it after
  `make deps`, run `SONGSTEAD_BINARY=/path/to/songstead CHROMIUM=/usr/bin/chromium node scripts/site/capture-songstead.mjs`.
  The script creates a temporary database, uses local HTTP only, blocks external
  browser requests, and deletes its demo data when it finishes.

They contain sample media and conversations, not a live community. The house mark
is an SVG drawn for this site. `assets/comfy-robot.png` is the site's comfy robot
mascot's social preview; the homepage uses its smaller WebP derivative. Both
are 680 × 680 with transparency, with download budgets checked in CI. Separate
small PNGs supply the favicon and Apple touch icon. The original generated
artwork is preserved outside the public site; see the
[mascot prompt, provenance, and compression commands](../../docs/mascot.md).
Earlier concepts are kept under `design/mascot-options/`.
Website code and these project assets use the repository's AGPL-3.0-or-later
license; see the root `LICENSE`.
