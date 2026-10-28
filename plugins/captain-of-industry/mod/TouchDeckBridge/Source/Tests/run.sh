#!/usr/bin/env bash
# Übersetzt die spielunabhängigen Teile des Mods mit den Tests und startet sie mit mono
# (Mono, wie im Spiel). Kein Download, kein Test-Framework nötig.
set -euo pipefail
cd "$(dirname "$0")"
dotnet build -nologo -v q Tests.csproj
mono bin/Tests.exe
