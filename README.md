# TouchDeck-Plugins

Plugins erweitern [TouchDeck](https://github.com/Marcel1853) – die Makro-Fernbedienung
für Linux – um neue **Aktionen** und **Auslöser**. Dieses Repo enthält:

| Inhalt | |
|---|---|
| [`plugins.json`](plugins.json) | Die Liste für den **Marktplatz** in TouchDeck (Plugins › Marktplatz) |
| [`beispiele/`](beispiele/) | Beispiel-Plugins zum Abschauen und Kopieren |
| [Wiki](../../wiki) | Die Anleitung: Plugins schreiben, testen und veröffentlichen |

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
| [`beispiele/beispiel`](beispiele/beispiel) | normal (JavaScript) | Aktionen, Auslöser, Zeitgeber, Werte, Internet, Einstellungen |
| [`beispiele/beispiel-erweitert`](beispiele/beispiel-erweitert) | erweitert (Python) | Systemwerte lesen, Befehle ausführen, Auslöser |
| [`beispiele/beispiel-node`](beispiele/beispiel-node) | erweitert (Node.js) | Zählen, Werte, Auslöser |

Zum Ausprobieren einen Ordner kopieren und in TouchDeck unter **Plugins › Entwickeln**
laden.

## Eigenes Plugin in den Marktplatz bringen

1. Plugin als **öffentliches** GitHub-Repo veröffentlichen (`plugin.json` im Hauptordner),
   am besten mit einem Release wie `v1.0.0`.
2. Pull Request an dieses Repo mit einem neuen Eintrag in `plugins.json`:

   ```json
   { "repo": "dein-name/touchdeck-mein-plugin", "name": "Mein Plugin",
     "description": "Was es macht", "author": "Dein Name" }
   ```

Einträge werden vor der Aufnahme angesehen. Trotzdem gilt: TouchDeck zeigt vor jeder
Installation Quelle und Berechtigungen – installiere nur, was du nachvollziehen kannst.

## Lizenz

Beispiele und Anleitung stehen unter der [MIT-Lizenz](LICENSE) – kopieren und
verändern ausdrücklich erwünscht.
