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

The three app cards and product pages show matching version labels and links to
the exact release notes. The workshop section also shows Arise's release while
retaining its experimental status. `releases.json` records the currently published stable
versions; update it with those labels and links during each release. Content
checks reject missing, duplicate, stale or mismatched release links. Each app card and product page also links directly to the maintained Docker
Compose guide. Documentation landing pages link to the matching GHCR package
and explain architecture selection, version pins, and persistent storage. Deploy
these links and update the release catalog only after the images support anonymous
pulls. Installation
guides and the footer's Latest release redirects remain available. Product pages
describe the purpose, experience, boundaries, installation, and backup approach
in no more than 650 words. Keep release-specific prose and UI walkthroughs in
the app's documentation and release notes. The Arise description deliberately calls out its experimental
status. Application accounts live on their individual installations.

Each app has a documentation landing page at `/<app>/docs/`, linked from its
home card, product page and footer. The five topics are installation,
configuration, backups/recovery, upgrades, and help. These pages link to the
guides maintained alongside each app rather than copying commands into this
repository. When a guide moves, update its link here. Content and HTTP checks
cover the docs routes, topic anchors, canonical URLs, sitemap and guide links;
browser checks exercise them without JavaScript. Tests also reject release
prose and oversized product copy before deployment. A failed content gate leaves
the existing deployed files untouched.

The footer names Marcus and links to the public GitHub profile. The homepage
links to website issues for questions and suggestions. Do not add a personal
address or location without the maintainer choosing to publish it.

Screenshots show isolated demo/test instances. Browser images use lossless WebP;
PNG versions of Imvault and Witmoot remain available for social preview cards
(the Imvault social image is scaled to 800 pixels wide):

- `assets/imvault-gallery.webp`: captured from Imvault at
  `8e695909352fbbfbd3ebcfedcd963c763a329a06`. Its disposable demo uses the
  animation in `design/screenshots/animation.gif`, which has a visible first
  frame. The fixture generator requires Pillow only when regenerating it.
  Run Imvault's `make demo` in a disposable checkout, then from this repository
  run `CHROMIUM=/usr/bin/chromium node scripts/site/capture-imvault.mjs http://127.0.0.1:8080 /tmp/imvault-gallery.png`.
  This replaces only the demo member's sample GIF and captures the real Recent
  page. The script refuses remote URLs and blocks external requests. Convert
  the result using the lossless command below.
- `assets/witmoot-board.webp`: losslessly converted from `witmoot/docs/images/board.png` at
  `8f20e2f26bf594394526ee7f6a558f013fd3c47b` (0.7.2).

- `assets/songstead-recent.webp`: captured from Songstead 0.9.0 at
  `c9e5bbd`, with four fictional music
  recommendations, local sample artwork and three disposable demo accounts.
  It shows the optional tile layout; List remains the application default. To reproduce it after
  `make deps`, run `SONGSTEAD_BINARY=/path/to/songstead CHROMIUM=/usr/bin/chromium node scripts/site/capture-songstead.mjs`.
  The script creates a temporary database, uses local HTTP only, blocks external
  browser requests, and deletes its demo data when it finishes. It writes
  `/tmp/songstead-recent.png` by default; `SCREENSHOT_OUTPUT` overrides that
  destination. Convert it to WebP after capturing.

For example, with Pillow installed for asset maintenance:

```sh
python3 - <<'PY'
from PIL import Image
Image.open('/tmp/imvault-gallery.png').save(
    'site/assets/imvault-gallery.webp', format='WEBP', lossless=True, method=6)
PY
```

Keep screenshots of real application pages, with fictional content and demo
accounts. The homepage links each preview to its full image. A public interactive
demo would need a dedicated sample instance; private community instances are
not demo targets.

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
