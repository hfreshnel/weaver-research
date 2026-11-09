#!/usr/bin/env bash
# Fetch the offline Arch Wiki (official arch-wiki-docs package, GFDL 1.3+) and convert the
# en + fr pages to plain text. Nothing is installed; the package is read in a temp dir.
# Output: knowledge/archwiki/data/{en,fr}/<Page__Sub>.txt  (gitignored)
set -eu
here=$(cd "$(dirname "$0")" && pwd)
ver=20261003-1
sha=1824753d4dfe5429d16a3fab97f21685116bf5bcf14ab69f18777e2e33f7d76e
tmp=$(mktemp -d)
curl -sSL --fail -o "$tmp/awd.pkg.tar.zst" "https://geo.mirror.pkgbuild.com/extra/os/x86_64/arch-wiki-docs-$ver-any.pkg.tar.zst"
echo "$sha  $tmp/awd.pkg.tar.zst" | sha256sum -c --quiet
rm -rf "$here/data"
python3 -I "$here/extract.py" "$tmp/awd.pkg.tar.zst" "$here/data"
rm -rf "$tmp"
du -sh "$here/data" | cut -f1
