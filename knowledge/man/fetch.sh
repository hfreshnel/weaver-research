#!/usr/bin/env bash
# Fetch official man pages for the commands of the simulated machine, without installing
# anything: download the Ubuntu packages, extract only usr/share/man, render to plain text.
# Output: knowledge/man/data/<command>.txt  (gitignored)
set -eu
here=$(cd "$(dirname "$0")" && pwd)
pkgs="cups-client cups-bsd sane-utils pulseaudio-utils wireplumber network-manager flatpak timeshift snapper
      bluez poppler-utils qpdf imagemagick-6.q16 libreoffice-common apt procps psmisc coreutils libglib2.0-bin
      xdg-utils iputils-ping iproute2 file"
dl=$(mktemp -d); ex=$(mktemp -d)
(cd "$dl" && apt-get download $pkgs >/dev/null)
ls "$dl" > "$here/packages.txt"
for deb in "$dl"/*.deb; do dpkg-deb --fsys-tarfile "$deb" | tar -x -C "$ex" --wildcards './usr/share/man/man1/*' './usr/share/man/man8/*' 2>/dev/null || true; done
mkdir -p "$here/data"
for f in "$ex"/usr/share/man/man[18]/*; do
  [ -f "$f" ] || continue
  name=$(basename "$f" | sed -E 's/\.(1|8)[a-z0-9]*(\.gz)?$//')
  if [[ "$f" == *.gz ]]; then zcat "$f"; else cat "$f"; fi | groff -man -Tutf8 -P -c 2>/dev/null | col -bx > "$here/data/$name.txt" || true
done
rm -rf "$dl" "$ex"
echo "$(ls "$here/data" | wc -l) pages, $(du -sh "$here/data" | cut -f1)"
