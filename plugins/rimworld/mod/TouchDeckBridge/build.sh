#!/usr/bin/env bash
# Baut TouchDeckBridge.dll nach 1.6/Assemblies/ und führt die Protokoll-Tests aus.
#   ./build.sh            bauen und testen
#   ./build.sh install    zusätzlich in den Mods-Ordner von RimWorld kopieren
# Pfade: RIMWORLD_DIR (Spielordner), HARMONY_DIR (Harmony aus dem Workshop) – Standard: Steam unter ~/.local/share.
set -euo pipefail
cd "$(dirname "$0")"
RIMWORLD_DIR="${RIMWORLD_DIR:-$HOME/.local/share/Steam/steamapps/common/RimWorld}"
HARMONY_DIR="${HARMONY_DIR:-$HOME/.local/share/Steam/steamapps/workshop/content/294100/2009463077}"

if [ ! -f "$RIMWORLD_DIR/RimWorldLinux_Data/Managed/Assembly-CSharp.dll" ]; then
  echo "RimWorld nicht gefunden in $RIMWORLD_DIR (RIMWORLD_DIR setzen)" >&2
  exit 1
fi
if [ ! -f "$HARMONY_DIR/1.6/Assemblies/0Harmony.dll" ]; then
  echo "Harmony nicht gefunden in $HARMONY_DIR (Harmony im Workshop abonnieren oder HARMONY_DIR setzen)" >&2
  exit 1
fi

dotnet build -nologo -v q -c Release Source/TouchDeckBridge/TouchDeckBridge.csproj \
  -p:RimWorldDir="$RIMWORLD_DIR" -p:HarmonyDir="$HARMONY_DIR"
rm -rf Source/TouchDeckBridge/obj
Source/Tests/run.sh
rm -rf Source/Tests/obj Source/Tests/bin

if [ "${1:-}" = "install" ]; then
  target="$RIMWORLD_DIR/Mods/TouchDeckBridge"
  mkdir -p "$target"
  # Nur, was das Spiel braucht, plus Anleitung; den Quellcode gibt es im Repo
  rm -rf "$target/About" "$target/1.6" "$target/Languages"
  cp -r About 1.6 Languages README.md README.de.md CHANGELOG.md LICENSE "$target/"
  echo "Installiert nach $target"
fi
