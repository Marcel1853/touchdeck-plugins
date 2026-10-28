#!/usr/bin/env bash
# Baut TouchDeckBridge.dll, führt die Protokoll-Tests aus und packt die ZIP für Spieler und TouchDeck.
#   ./build.sh            bauen, testen, ZIP packen
#   ./build.sh install    zusätzlich in den Mods-Ordner von Captain of Industry kopieren
# Pfade: COI_ROOT (Spielordner), COI_MODS (Mods-Ordner). Standard: Steam unter ~/.local/share,
# Mods-Ordner im Proton-Präfix (Captain of Industry läuft unter Linux über Proton).
set -euo pipefail
cd "$(dirname "$0")"
STEAM="$HOME/.local/share/Steam/steamapps"
COI_ROOT="${COI_ROOT:-$STEAM/common/Captain of Industry}"
COI_MODS="${COI_MODS:-$STEAM/compatdata/1594320/pfx/drive_c/users/steamuser/AppData/Roaming/Captain of Industry/Mods}"
VERSION=$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' manifest.json)

if [ ! -f "$COI_ROOT/Captain of Industry_Data/Managed/Mafi.Core.dll" ]; then
  echo "Captain of Industry nicht gefunden in $COI_ROOT (COI_ROOT setzen)" >&2
  exit 1
fi
# Bei laufendem Factorio hängt der PC beim Bauen.
if pgrep -x factorio >/dev/null 2>&1; then
  echo "Factorio läuft – bitte erst beenden, dann bauen." >&2
  exit 1
fi

dotnet build -nologo -v q -c Release Source/TouchDeckBridge/TouchDeckBridge.csproj -p:CoiRoot="$COI_ROOT"
rm -rf Source/TouchDeckBridge/obj
Source/Tests/run.sh
rm -rf Source/Tests/obj Source/Tests/bin

# ZIP mit dem Mod-Ordner als Wurzel (so wie im Mods-Ordner nötig); nur, was das Spiel braucht, plus Anleitung.
FILES=(TouchDeckBridge.dll manifest.json README.md README.de.md CHANGELOG.md LICENSE)
tmp=$(mktemp -d)
mkdir "$tmp/TouchDeckBridge"
cp "${FILES[@]}" "$tmp/TouchDeckBridge/"
rm -f ../../TouchDeckBridge_*.zip
(cd "$tmp" && TZ=UTC touch -t 202601010000 TouchDeckBridge TouchDeckBridge/* && zip -q -X -r - TouchDeckBridge) > "../../TouchDeckBridge_$VERSION.zip"
rm -rf "$tmp"
echo "ZIP: $(cd ../.. && pwd)/TouchDeckBridge_$VERSION.zip"

if [ "${1:-}" = "install" ]; then
  target="$COI_MODS/TouchDeckBridge"
  mkdir -p "$target"
  # settings.json bleibt erhalten.
  cp "${FILES[@]}" "$target/"
  echo "Installiert nach $target"
fi
