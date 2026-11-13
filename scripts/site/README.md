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

The five released app cards and product pages show matching version labels and links to
the exact release notes. The workshop section also shows Arise's release while
retaining its experimental status. `releases.json` records the currently published stable
versions; update it with those labels and links during each release.
`facts.json` records facts several pages repeat: the Go version, each app's
packaging formats and README demo heading. `test_facts.py` checks every page
against it, along with back links and lists that should name all five apps. Content
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

Each released app has a documentation landing page at `/<app>/docs/`, linked from its
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
- `assets/witmoot-board.webp`: lossless WebP of the 256-colour `assets/witmoot-board.png`,
  made with `magick assets/witmoot-board.png -strip -define webp:lossless=true -define webp:method=6`.
  It is smaller than the PNG; `test_demo_assets.py` checks that every WebP stays smaller than its PNG twin.

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

## Folkweave and Tidings

Folkweave and Tidings have initial 0.1.0 releases, homepage cards alongside the
other apps, product pages, and five-topic documentation landing pages. Like
the other apps, each links to current release notes, published container images,
Linux/Debian installation, service setup, and verified backup/recovery guidance.
Folkweave's lack of parental approval controls and original photo retention
remain explicit. Tidings' page now describes transactional JSON import and
verified online backups. Browser checks cover both apps and sponsorship links.

The existing project mascots are copied into this website as small transparent
derivatives; no new illustration was generated for these pages:

- `assets/folkweave-loom.webp` is the app's 256 × 256 asset at Folkweave commit
  `f26c0d6`. Its companion PNG is resized from that repository's preserved
  `design/mascot/loom-original.png`, with a 256-color palette. The generation
  prompt remains in Folkweave's `docs/mascot.md`.
- `assets/tidings-town-crier.webp` and `.png` are 256 × 270 derivatives of
  Tidings' `internal/reader/static/town-crier.png` at `9a6ab00`. The prompt remains
  in Tidings' `docs/town-crier-prompt.txt`. The PNG is also the README derivative
  in Tidings' `docs/images/town-crier.png`.

Derivatives use ImageMagick `-resize 256x -strip`, WebP quality 85 with
`-define webp:method=6`, or PNG `-colors 256 -define png:compression-level=9`.
Each website derivative is under 25,000 bytes; the normal image checks also
validate dimensions and local-only serving. Original artwork stays in its app
repository, outside the public website.

## App mascots

All five app cards and product headers display their app's existing mascot.
Cards use a consistent 100 by 106 pixel box with `object-fit: contain`;
product artwork is 220 pixels wide beside the copy on desktop, or 140 pixels
wide above the copy on mobile. Keep the `data-mascot` identifier on each image
so content and browser checks can catch missing or swapped artwork.

The three additional transparent WebP derivatives are:

- `assets/imvault-keeper.webp`: Imvault `internal/web/static/img/mascot.png` at `aeb503abfc9f1345653ca5be2939e6185296abc3`.
- `assets/witmoot-knight.webp`: Witmoot `internal/forum/static/moot-knight.png` at `d33a1e5cd90856bd693d23eb30aab16f80241163`.
- `assets/songstead-jukebox.webp`: the existing `assets/songstead-jukebox.png`
  already preserved in this website.

To reproduce these derivatives with Pillow, convert the source to RGBA, use
`thumbnail((256, 256), Image.Resampling.LANCZOS)`, and save as WebP with
`quality=90, method=6`. Each app mascot has a 25,000-byte download budget,
with intrinsic dimensions checked against the HTML. No new artwork is generated.

## Fictional demonstration media and refreshed captures

The Imvault and Songstead screenshots use the current applications, local demo
accounts and original fictional media. Imvault shows two natural photos rather
than synthetic gradient fixtures. Songstead uses an illustrated album sleeve and
two photographic covers, with one intentional missing-artwork fallback. Source
items and listening notes are fictional. The browser never contacts a provider.

Original generated PNGs, upload-sized derivatives and the prompts are preserved
outside the public site in `design/demo-assets/`. See
[provenance and generation prompts](../../design/demo-assets/provenance.json).
The images were generated with `image_gen.imagegen`; conventional ImageMagick
resizing, metadata removal and PNG/JPEG encoding produced the app input files.

To reproduce, start an isolated Imvault demo and run
`node scripts/site/capture-imvault.mjs http://127.0.0.1:8080 /tmp/imvault-gallery.png`.
This removes synthetic files in that disposable demo and uploads the fictional
photos. The script refuses a non-loopback destination. For Songstead, set
`SONGSTEAD_BINARY` to the built executable and `SCREENSHOT_OUTPUT` to a local PNG
path, then run `node scripts/site/capture-songstead.mjs`. It creates and removes
its own temporary database. It provisions a local owner before adding members.

Keep original captures under `design/screenshots/`. Public WebP derivatives use
ImageMagick `-strip -quality 84 -define webp:method=6`; the Imvault social PNG uses
`-strip -colors 128 -define png:compression-level=9`. All public screenshots stay
below the website's 200,000-byte image budget. Update the HTML dimensions and
screenshot contract tests together when a capture's height changes.

Folkweave, Tidings and Witmoot captures use their current offline demos too. Run
`node scripts/site/capture-local.mjs APP http://127.0.0.1:PORT /tmp/capture.png`
after starting a disposable demo. The capture tool supports those three app IDs,
refuses non-loopback URLs and blocks external browser requests. Folkweave adds
the two fictional photos through its ordinary posting form. Tidings keeps its
fictional feed stories and Witmoot keeps its fictional board conversations.
These captures preserve the existing 1280 by 1000 (Folkweave and Tidings) and
1280 by 1233 (Witmoot) viewport contracts.
