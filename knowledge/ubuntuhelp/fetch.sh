#!/usr/bin/env bash
# Fetch the Ubuntu 24.04 desktop help (GNOME help + Ubuntu's own pages), en + fr, without
# installing anything: download the packages, extract only usr/share/help/{C,fr}, convert the
# Mallard pages to text. ubuntu-docs pages override gnome-user-docs pages of the same name,
# as on a real Ubuntu desktop.
# Output: knowledge/ubuntuhelp/data/{en,fr}/<page>.txt  (gitignored)
set -eu
here=$(cd "$(dirname "$0")" && pwd)
dl=$(mktemp -d); ex=$(mktemp -d)
(cd "$dl" && apt-get download gnome-user-docs gnome-user-docs-fr ubuntu-docs >/dev/null)
(cd "$dl" && sha256sum *.deb) > "$here/packages.txt"
for deb in "$dl"/gnome-user-docs*.deb "$dl"/ubuntu-docs*.deb; do
  dpkg-deb --fsys-tarfile "$deb" | tar -x -C "$ex" --wildcards './usr/share/help/C/*.page' './usr/share/help/fr/*.page' 2>/dev/null || true
done
rm -rf "$here/data"
python3 -I "$here/extract.py" "$ex/usr/share/help" "$here/data"
rm -rf "$dl" "$ex"
echo "$(ls "$here/data/en" | wc -l) en + $(ls "$here/data/fr" | wc -l) fr pages, $(du -sh "$here/data" | cut -f1)"
