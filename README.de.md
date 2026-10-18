# TouchDeck-Plugins

🇬🇧 [English version](README.md)

Plugins erweitern [TouchDeck](https://github.com/Marcel1853) – die Makro-Fernbedienung
für Linux – um neue **Aktionen** und **Auslöser**. Dieses Repo enthält:

| | |
|---|---|
| [`plugins.json`](plugins.json) | Die Liste für den **Marktplatz** in TouchDeck (Plugins › Marktplatz) |
| [`examples/`](examples/) | Beispiel-Plugins zum Abschauen und Kopieren |
| [Wiki](../../wiki) | Die Anleitung: Plugins schreiben, testen und veröffentlichen |

## Plugins in diesem Repo

| Ordner | Art | Was es macht |
|---|---|---|
| [`plugins/clipboard-slots`](plugins/clipboard-slots) | erweitert (Python) | Zwischenablage-Manager: Slots, Verlauf, Zwischenablage ↔ Wert, Bereinigung, fertige Seite (MIT) |
| [`plugins/factorio`](plugins/factorio) | erweitert (Python) | Factorio live auf den Buttons (Forschung, Strom mit Graphen, Evolution …) und Spielsteuerung; braucht den mitgelieferten Mod „TouchDeck Bridge“, fertige Seiten (MIT) |

Installiert werden sie über den Marktplatz in TouchDeck. Jedes Plugin hat seine eigene Lizenz (siehe sein Ordner).

## Zwei Arten von Plugins

- **Normale Plugins** – JavaScript, laufen abgeschottet in TouchDeck. Sie dürfen nur,
  was sie in `plugin.json` angeben (bestimmte Internetadressen, Werte,
  Benachrichtigungen). Der Standard und für die meisten Ideen genug.
- **Erweiterte Plugins** – eigene Programme (Python, Node.js, …) mit vollen Rechten.
  Laufen nur, wenn der Nutzer den erweiterten Modus bewusst und auf eigene Gefahr
  einschaltet.

## Beispiele

| Ordner | Art | Zeigt |
|---|---|---|
| [`examples/example`](examples/example) | normal (JavaScript) | Aktionen, Auslöser, Zeitgeber, Werte, Internet, Einstellungen |
| [`examples/example-python`](examples/example-python) | erweitert (Python) | Systemwerte lesen, Befehle ausführen, Auslöser |
| [`examples/example-node`](examples/example-node) | erweitert (Node.js) | Zählen, Werte, Auslöser |

Zum Ausprobieren einen Ordner kopieren und in TouchDeck unter **Plugins › Entwickeln**
laden.

## Eigenes Plugin in den Marktplatz bringen

1. Plugin als **öffentliches** GitHub-Repo veröffentlichen (`plugin.json` im Hauptordner),
   am besten mit einem Release wie `v1.0.0`.
2. Pull Request an dieses Repo mit einem neuen Eintrag in `plugins.json`:

   ```json
   {
     "repo": "dein-name/touchdeck-mein-plugin",
     "name": { "en": "My plugin", "de": "Mein Plugin" },
     "description": { "en": "What it does", "de": "Was es macht" },
     "author": "Dein Name",
     "license": "MIT"
   }
   ```

   `name` und `description` dürfen ein einfacher Text oder Übersetzungen wie oben sein. Liegt das
   Plugin in einem Unterordner eines Repos, kommt `"path": "ordner/des/plugins"` dazu.

Einträge werden vor der Aufnahme angesehen. Trotzdem gilt: TouchDeck zeigt vor jeder
Installation Quelle, Lizenz und Berechtigungen – installiere nur, was du nachvollziehen
kannst.

## Öffentlich heißt nicht frei

Plugins müssen **öffentlich** sein, damit jeder den Code vor dem Installieren lesen kann.
Das heißt aber **nicht**, dass jeder ihn kopieren oder weiterverwenden darf. Jedes
Plugin darf eine eigene Lizenz haben:

- Eine `LICENSE`-Datei ins Repo legen und den Namen der Lizenz in `plugin.json`
  (`"license": "MIT"`) und in den Marktplatz-Eintrag schreiben.
- **Ohne Lizenz bleiben alle Rechte beim Autor** – andere dürfen den Code lesen, aber
  nicht kopieren, verändern oder veröffentlichen.
- Wer Weiterverwendung erlauben möchte, nimmt eine freie Lizenz wie MIT, Apache-2.0
  oder GPL-3.0. Wer nicht, schreibt zum Beispiel `"license": "Alle Rechte vorbehalten"`.

## Lizenz dieses Repos

Die Beispiele und die Anleitung in diesem Repo stehen unter der
[MIT-Lizenz](LICENSE) – kopieren und verändern ausdrücklich erwünscht. Plugins in
`plugins.json` behalten ihre eigenen Lizenzen.
