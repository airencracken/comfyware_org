# comfyware_org

The website for **comfyware.org**: a home for Imvault, Witmoot, and the Comfyware
approach to software for friends, family, and small communities.

Plain HTML and CSS, with local screenshots and system fonts. The public files
live in `site/`; there is no frontend build step or JavaScript dependency.

## Preview

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory site
```

Open <http://127.0.0.1:8765>. See the [website guide](scripts/site/README.md) for
tests, screenshots, asset provenance, and the production Caddy configuration.

## Repository layout

- `site/`: the complete public website; serve only this directory.
- `scripts/site/`: content, HTTP, and browser checks, plus hosting documentation.
- `.github/workflows/website.yml`: website CI checks.

The Gentoo overlay is maintained separately in
[airencracken/comfyware](https://github.com/airencracken/comfyware).

Licensed under AGPL-3.0-or-later. See [LICENSE](LICENSE).
