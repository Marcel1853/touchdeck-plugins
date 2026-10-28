# TouchDeck Bridge (Mod für Captain of Industry)

[English](README.md) · **Deutsch**

Verbindet Captain of Industry mit [TouchDeck](https://github.com/Marcel1853/touchdeck-plugins) –
Makro-Buttons auf Handy oder Tablet. Der Mod öffnet einen kleinen TCP-Server und liefert dem
TouchDeck-Plugin „Captain of Industry“ den Zustand des Spiels: Datum, Tempo, Strom, Rechenleistung,
Einheit, freie oder fehlende Arbeiter, Einwohner, Obdachlose, Nahrung in Monaten, Krankheit,
Forschung, Waren mit Trend, aktive Meldungen und einen Verlauf neuer Meldungen und Nachrichten.
Befehle vom Plugin (Pause, Tempo, Speichern, Kamera zu Meldungen) führt er im Hauptthread des
Spiels aus.

- Braucht keine anderen Mods, fügt dem Spiel keine Inhalte hinzu – lässt sich zu bestehenden
  Spielständen hinzufügen und wieder entfernen.
- Nichts geht ins Internet. Standard: nur `127.0.0.1:34202` (dieser PC).

## Installation

Am einfachsten aus TouchDeck: Plugin-Karte „Captain of Industry“ › „🧩 Mod installieren“.

Von Hand: den Ordner `TouchDeckBridge` (aus `TouchDeckBridge_0.1.3.zip`) in den Mod-Ordner legen:

- Windows: `%APPDATA%\Captain of Industry\Mods\TouchDeckBridge`
- Linux (Steam mit Proton):
  `~/.local/share/Steam/steamapps/compatdata/1594320/pfx/drive_c/users/steamuser/AppData/Roaming/Captain of Industry/Mods/TouchDeckBridge`

Dann beim Laden oder Anlegen eines Spielstands unter „Mods“ „TouchDeck Bridge“ einschalten.

## Einstellungen

Beim ersten Laden eines Spielstands legt der Mod `settings.json` in seinem Ordner an:

| Schlüssel | Standard | Bedeutung |
| --- | --- | --- |
| `enabled` | `true` | Server an/aus |
| `address` | `127.0.0.1` | `127.0.0.1` = nur dieser PC; `0.0.0.0` = alle Netzwerkkarten (TouchDeck auf einem anderen PC) |
| `port` | `34202` | 1024–65535, im Plugin denselben eintragen |
| `secret` | leer | Geheimwort; Pflicht (mindestens 12 Zeichen), wenn `address` nicht `127.0.0.1` ist |
| `intervalMs` | `500` | wie oft der Zustand höchstens geschickt wird (200–5000) |

Änderungen gelten nach höchstens 2 Sekunden, ohne Neustart. Die Verbindung ist nicht verschlüsselt:
nur im eigenen Netz nutzen. Meldungen des Mods stehen im Log des Spiels
(`…/Captain of Industry/Logs/`, Zeilen mit „[TouchDeck Bridge]“).

## Bauen

`./build.sh` übersetzt `TouchDeckBridge.dll` gegen die DLLs der eigenen Installation von Captain of
Industry (Pfad über `COI_ROOT`), führt die Protokoll-Tests aus und packt
`../../TouchDeckBridge_<Version>.zip`. `./build.sh install` kopiert den Mod zusätzlich in den
Mod-Ordner (`COI_MODS`). Braucht `dotnet` und `mono`, lädt nichts herunter.

Lizenz: MIT.
