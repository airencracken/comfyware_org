# comfyware_org

The website for **comfyware.org**, home of Imvault, Witmoot, Songstead,
Folkweave, Tidings, Comfylib and the Comfyware principles.

It is plain HTML and CSS in `site/`, with local images, system fonts and a small
optional theme script. There is no build step.

## Preview

```sh
make preview
```

Open <http://127.0.0.1:8765>. `make preview PORT=9000` picks another port. You
need only Make and Python 3.

## Check

With Node.js 20 or later and Caddy installed:

```sh
make setup    # or: make deps, then add CHROMIUM=/usr/bin/chromium below
make check
```

`make help` lists every target. The [website guide](scripts/site/README.md)
covers the checks, asset sources and the Caddy configuration.

## Deploy

On the web server, run `git pull`, then `make deploy`. It runs the content
checks and copies `site/` to `/var/www/comfyware` (set `DEPLOY_DIR` to change
it), removing anything no longer in `site/`. `DRY_RUN=1 make deploy` shows what
would change.

## Layout

- `site/`: the public website. Serve only this directory.
- `scripts/site/`: checks and hosting notes.
- `docs/`: mascot notes.

The Gentoo overlay lives in
[airencracken/comfyware](https://github.com/airencracken/comfyware).

Licensed under AGPL-3.0-or-later. See [LICENSE](LICENSE).
