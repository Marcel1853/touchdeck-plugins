#!/usr/bin/env bash
# Baut Code.dll und führt die Protokoll-Tests aus.
#   ./build.sh            bauen und testen
#   ./build.sh install    zusätzlich in den Mods-Ordner von Timberborn kopieren
# Pfade: TIMBERBORN_DIR (Spielordner), TIMBERBORN_MODS (Mods-Ordner). Standard: Steam unter ~/.local/share,
# Mods-Ordner im Proton-Präfix (Windows-Version über Proton), sonst ~/Documents/Timberborn/Mods.
set -euo pipefail
cd "$(dirname "$0")"
STEAM="$HOME/.local/share/Steam/steamapps"
TIMBERBORN_DIR="${TIMBERBORN_DIR:-$STEAM/common/Timberborn}"
if [ -z "${TIMBERBORN_MODS:-}" ]; then
  proton="$STEAM/compatdata/1062090/pfx/drive_c/users/steamuser/Documents/Timberborn/Mods"
  if [ -d "$proton" ]; then TIMBERBORN_MODS="$proton"; else TIMBERBORN_MODS="$HOME/Documents/Timberborn/Mods"; fi
fi

if [ ! -f "$TIMBERBORN_DIR/Timberborn_Data/Managed/Timberborn.TimeSystem.dll" ]; then
  echo "Timberborn nicht gefunden in $TIMBERBORN_DIR (TIMBERBORN_DIR setzen)" >&2
  exit 1
fi

dotnet build -nologo -v q -c Release Source/TouchDeckBridge/TouchDeckBridge.csproj -p:TimberbornDir="$TIMBERBORN_DIR"
rm -rf Source/TouchDeckBridge/obj
Source/Tests/run.sh
rm -rf Source/Tests/obj Source/Tests/bin

if [ "${1:-}" = "install" ]; then
  target="$TIMBERBORN_MODS/TouchDeckBridge"
  mkdir -p "$target"
  # Nur, was das Spiel braucht, plus Anleitung; den Quellcode gibt es im Repo. settings.json bleibt erhalten.
  cp Code.dll manifest.json thumbnail.png README.md README.de.md CHANGELOG.md LICENSE "$target/"
  echo "Installiert nach $target"
fi
