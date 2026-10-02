# SPDX-License-Identifier: AGPL-3.0-or-later
.DEFAULT_GOAL := help

HOST ?= 127.0.0.1
PORT ?= 8765
# Where `make deploy` publishes site/ (the example host's document root).
DEPLOY_DIR ?= /var/www/comfyware
SCREENSHOT_DIR ?= $(CURDIR)/.artifacts/screenshots
PLAYWRIGHT_INSTALL_ARGS ?=

# Pass command-line overrides through to the browser test runner.
export CHROMIUM SITE_URL

.PHONY: help preview serve setup deps browser-install check test test-content test-http test-browser test-deploy screenshots check-config deploy

help:
	@printf '%s\n' \
	  'Comfyware website' \
	  '' \
	  '  make preview         Serve locally at http://127.0.0.1:8765 (Ctrl-C to stop)' \
	  '  make setup           Install test packages and Chromium' \
	  '  make check           Run all content, HTTP, browser, and config checks' \
	  '  make test-content    Validate pages, links, metadata, and assets' \
	  '  make test-http       Test the production Caddy site block' \
	  '  make test-browser    Check layouts, accessibility, and navigation' \
	  '  make screenshots     Run browser checks and save desktop/mobile screenshots' \
	  '  make check-config    Validate the production Caddy configuration' \
	  '  make deploy          Check the content, then publish site/ to DEPLOY_DIR' \
	  '  make test-deploy     Test the deploy script against throwaway directories' \
	  '  make deps            Install just the test packages from the lockfile' \
	  '  make browser-install Install Chromium (test packages must be installed)' \
	  '' \
	  'Aliases: make serve = make preview; make test = make check.' \
	  'Options: HOST=127.0.0.1 PORT=8765 CHROMIUM=/path/to/chromium' \
	  '         SITE_URL=http://127.0.0.1:8765 SCREENSHOT_DIR=/path/to/screenshots' \
	  '         PLAYWRIGHT_INSTALL_ARGS=--with-deps (for browser system packages)' \
	  '         DEPLOY_DIR=/var/www/comfyware DRY_RUN=1 (preview a deploy)'

preview:
	python3 -m http.server "$(PORT)" --bind "$(HOST)" --directory site

serve: preview

# Keep package installation ahead of browser installation, including under -j.
setup: deps
	$(MAKE) browser-install

deps:
	npm ci --prefix scripts/site

browser-install:
	cd scripts/site && npm exec -- playwright install $(PLAYWRIGHT_INSTALL_ARGS) chromium

check: test-content test-http test-deploy test-browser check-config

test: check

test-content:
	python3 scripts/site/test_content.py

test-http:
	python3 scripts/site/test_http.py

test-deploy:
	python3 scripts/site/test_deploy.py

# rsync --delete makes DEPLOY_DIR an exact copy of site/, so removed pages stop
# being served. Run with DRY_RUN=1 to see what would change first.
deploy: test-content
	sh scripts/site/deploy.sh "$(DEPLOY_DIR)"

test-browser:
	npm test --prefix scripts/site

screenshots:
	SCREENSHOT_DIR="$(SCREENSHOT_DIR)" $(MAKE) test-browser

check-config:
	caddy validate --config scripts/site/Caddyfile --adapter caddyfile
