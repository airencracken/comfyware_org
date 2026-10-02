#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-or-later
# Publish site/ to a web server's document root.
#
#   sh scripts/site/deploy.sh /var/www/comfyware
#   DRY_RUN=1 sh scripts/site/deploy.sh /var/www/comfyware
#
# rsync --delete makes the document root an exact copy, so a page or asset
# removed from site/ stops being served. That makes the destination worth
# guarding: it must be an existing absolute directory, and never / or a path
# inside this repository.

fail() {
	printf 'deploy: %s\n' "$*" >&2
	exit 1
}

[ $# -eq 1 ] || fail 'usage: deploy.sh DOCUMENT_ROOT'
target=$1

root=$(cd "$(dirname "$0")/../.." && pwd -P) || fail 'cannot find the repository'
[ -f "$root/site/index.html" ] || fail "no site/index.html in $root"
command -v rsync >/dev/null 2>&1 || fail 'rsync is not installed'

case $target in
'') fail 'the document root is empty' ;;
/*) ;;
*) fail "the document root must be an absolute path: $target" ;;
esac
[ -d "$target" ] || fail "the document root does not exist: $target"
resolved=$(cd "$target" && pwd -P) || fail "cannot enter $target"
[ "$resolved" != / ] || fail 'refusing to publish to /'
case $resolved/ in
"$root"/*) fail "the document root is inside the repository: $resolved" ;;
esac
case $root/ in
"$resolved"/*) fail "the repository is inside the document root: $resolved" ;;
esac

set -- -a --delete --delay-updates --chmod=D755,F644
if [ -n "${DRY_RUN:-}" ]; then
	set -- "$@" --dry-run --itemize-changes
fi
rsync "$@" "$root/site/" "$resolved/" || fail "rsync to $resolved failed"
if [ -n "${DRY_RUN:-}" ]; then
	printf 'deploy: dry run only; nothing in %s changed\n' "$resolved"
else
	printf 'deploy: published site/ to %s\n' "$resolved"
fi
