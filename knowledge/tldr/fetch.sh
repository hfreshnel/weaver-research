#!/usr/bin/env bash
# Fetch tldr-pages (English + French) from the official release. Output: knowledge/tldr/data/{en,fr}/<command>.md
set -eu
here=$(cd "$(dirname "$0")" && pwd)
ver=v2.3
tmp=$(mktemp -d)
for lang in en fr; do
  curl -sL -o "$tmp/$lang.zip" "https://github.com/tldr-pages/tldr/releases/download/$ver/tldr-pages.$lang.zip"
  sha256sum "$tmp/$lang.zip" | sed "s|$tmp/||"
  rm -rf "$here/data/$lang"; mkdir -p "$here/data/$lang"
  python3 -I -c "
import zipfile,sys,pathlib
z=zipfile.ZipFile(sys.argv[1]); out=pathlib.Path(sys.argv[2])
# Keep only the platforms of the target OS; linux pages override common ones of the same name.
for plat in ('common', 'linux'):
    for n in z.namelist():
        parts = pathlib.PurePosixPath(n).parts
        if n.endswith('.md') and '..' not in parts and len(parts) >= 2 and parts[-2] == plat:
            (out/parts[-1]).write_bytes(z.read(n))
" "$tmp/$lang.zip" "$here/data/$lang"
done
rm -rf "$tmp"
echo "en: $(ls "$here/data/en" | wc -l) pages, fr: $(ls "$here/data/fr" | wc -l) pages, $(du -sh "$here/data" | cut -f1)"
