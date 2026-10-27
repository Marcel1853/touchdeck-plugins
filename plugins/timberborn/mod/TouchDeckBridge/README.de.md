# TouchDeck Bridge (Timberborn-Mod)

[English](README.md) · **Deutsch**

Verbindet Timberborn mit [TouchDeck](https://github.com/Marcel1853/touchdeck-plugins) – Makro-Buttons
auf Handy oder Tablet. Der Mod öffnet einen kleinen TCP-Server und liefert dem TouchDeck-Plugin
„Timberborn“ den Zustand des Spiels: Zyklus, Tag, Tempo, Wetter mit Countdown, Bevölkerung,
Obdachlose, Arbeitslose, Verseuchte, Vorräte mit „reicht noch … Tage“, Nachrichtenverlauf und aktive
Warnungen. Befehle vom Plugin (Pause, Tempo, Speichern, Kamera zu Meldungen und Warnungen,
Nachricht im Spiel) führt er im Hauptthread des Spiels aus.

- Braucht kein Harmony und keine anderen Mods.
- Nichts geht ins Internet. Standard: nur `127.0.0.1:34201` (dieser PC).

## Installation

Diesen Ordner nach `Dokumente/Timberborn/Mods/TouchDeckBridge` legen (unter Linux mit Proton:
`~/.local/share/Steam/steamapps/compatdata/1062090/pfx/drive_c/users/steamuser/Documents/Timberborn/Mods/`)
und im Mod-Manager des Spiels einschalten.

## Einstellungen

Beim ersten Start legt der Mod `settings.json` in seinem Ordner an:

| Schlüssel | Standard | Bedeutung |
| --- | --- | --- |
| `enabled` | `true` | Server an/aus |
| `address` | `127.0.0.1` | `127.0.0.1` = nur dieser PC; `0.0.0.0` = alle Netzwerkkarten (TouchDeck auf einem anderen PC) |
| `port` | `34201` | 1024–65535, im Plugin denselben eintragen |
| `secret` | leer | Geheimwort; Pflicht (mindestens 12 Zeichen), wenn `address` nicht `127.0.0.1` ist |
| `intervalMs` | `500` | wie oft der Zustand höchstens geschickt wird (200–5000) |

Änderungen gelten nach höchstens 2 Sekunden, ohne Neustart. Die Verbindung ist nicht verschlüsselt:
nur im eigenen Netz nutzen.

## Bauen

`./build.sh` übersetzt `Code.dll` gegen die DLLs der eigenen Timberborn-Installation (Pfad über
`TIMBERBORN_DIR`) und führt die Protokoll-Tests aus. `./build.sh install` kopiert den Mod zusätzlich in
den Mod-Ordner. Braucht `dotnet` und `mono`, lädt nichts herunter.

Lizenz: MIT.
