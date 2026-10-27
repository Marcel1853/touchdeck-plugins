# Zwischenablage-Slots für TouchDeck · Clipboard Slots

🇩🇪 Deutsch · [🇬🇧 English below](#english)

**Erweitertes TouchDeck-Plugin.** Macht aus Buttons einen Zwischenablage-Manager: Texte in Slots
ablegen, per Fingertipp zurückholen, Verlauf der letzten Kopien, Zwischenablage in einen Wert
schreiben und zurück, kurze Text-Bereinigung. Es nutzt nur die offiziellen Plugin-Nachrichten von
TouchDeck (Aktionen, Trigger, Werte, Log) und baut nichts nach, was TouchDeck selbst schon kann.

## Voraussetzungen

- TouchDeck 0.9 (Linux, X11), **erweiterter Modus** eingeschaltet (Plugins › Erweitert)
- Python 3.8 oder neuer (unter Linux Mint bereits dabei)
- Ein Zwischenablage-Programm: `xclip` (empfohlen), `xsel` oder `wl-clipboard`

```
sudo apt install xclip
```

**Windows (ganz frühe Alpha, ungetestet):** Python 3.8+ von python.org genügt, ein
Zwischenablage-Programm ist nicht nötig. Die Slots liegen dort unter
`%APPDATA%\touchdeck-clipboard-slots`.

## Einrichten

1. Plugins › Marktplatz › „Zwischenablage-Slots“ › **Prüfen** › installieren (zweimal bestätigen, weil es
   ein erweitertes Plugin ist). Ohne Marktplatz geht auch die Adresse
   `Marcel1853/touchdeck-plugins/plugins/clipboard-slots`.
2. **Fertige Seite importieren:** in der Plugin-Karte (oder unter „Fertige Seiten“ in der Seitenliste) auf
   „📄 Zwischenablage Seite importieren“ klicken. Es entsteht eine Seite mit 12 Slot-Buttons und
   6 Werkzeug-Buttons. Einzeln Buttons anlegen ist nicht nötig.
3. Fertig. Es gibt keine Pflicht-Einstellungen, die Vorgaben passen für den Alltag.

### So bedienst du die Seite

- **Slot-Button kurz tippen:** legt den Slot in die Zwischenablage und fügt ihn ein. Das Einfügen
  steckt in der Vorlage „Einfügen“ (`Strg+V`). Für Terminals dort einmal auf `Strg+Umschalt+V`
  ändern, alle Buttons folgen.
- **Slot-Button halten (ca. 0,5 s):** speichert den aktuellen Inhalt der Zwischenablage in diesen Slot.
- Die Beschriftung zeigt eine Vorschau des Slots (`{Slot1}` …).
- Werkzeug-Reihe: vorletzte Kopie einfügen, die davor, als eine Zeile einfügen, Link ohne Tracking
  einfügen, Verlauf leeren, Auto-Speichern ein/aus.

### Auto-Speichern (Ringpuffer)

Mit dem Button „Auto-Speichern“ landet **jede neue Kopie (`Strg+C`) automatisch im nächsten Slot**:
Slot 1, 2, 3 … und nach dem letzten wieder bei 1. Dabei gilt:

- Texte, die schon in einem Slot liegen, werden nicht doppelt gespeichert.
- Der Modus bleibt nach einem Neustart erhalten. `{AutoSave}` zeigt an/aus, `{NextSlot}` den nächsten Slot.
- Auto-Speichern überschreibt Slots. Wer feste Slots behalten will, setzt in den Einstellungen
  „Auto-Speichern nutzt die Slots 1 bis …“, zum Beispiel 10, und nutzt die übrigen von Hand.
- „Alle Slots leeren“ setzt den Zähler auf 1 zurück.
- Mehr oder weniger Slots: `python3 tools/make_profile.py 20` erzeugt eine neue Datei, und die Anzahl
  in den Plugin-Einstellungen passend setzen. Slot-Felder nehmen auch Platzhalter wie `{Eingabe.Nummer}`.

## Aktionen

| Aktion | Was sie macht |
| --- | --- |
| Zwischenablage in Slot speichern | Kopiert den aktuellen Text in Slot 1–50 |
| Slot in Zwischenablage legen | Holt den Text aus dem Slot zurück |
| Verlaufseintrag in Zwischenablage legen | 1 = zuletzt kopiert, 2 = davor, … |
| Zwischenablage in Wert schreiben | Schreibt den Text in einen TouchDeck-Wert |
| Wert in Zwischenablage kopieren | Kopiert einen TouchDeck-Wert (z. B. aus einer HTTP-Antwort) |
| Text in Zwischenablage umwandeln | Ränder kürzen, eine Zeile, GROSS, klein, Tracking aus Link entfernen |
| Auto-Speichern in Slots | Jede neue Kopie in den nächsten Slot (Ringpuffer), ein/aus/umschalten |
| Leeren | Verlauf, Zwischenablage, einen Slot oder alle Slots |

**Eigene Buttons:** Die fertige Seite nutzt das schon. Wer selbst baut: Aktion „Slot in Zwischenablage legen“, danach die normale TouchDeck-Aktion
„Tastenkürzel“ mit `Strg+V` (im Terminal `Strg+Umschalt+V`). Der Slot liegt dann garantiert schon
in der Zwischenablage, wenn das Tastenkürzel ausgelöst wird.

## Trigger

- **Text in der Zwischenablage hat sich geändert**: im Ereignis stehen `{Event.Text}` und
  `{Event.Length}` zur Verfügung. Eigene Änderungen durch das Plugin lösen ihn nicht aus.

## Werte für Live-Anzeigen

| Wert | Inhalt |
| --- | --- |
| `Clip` | Vorschau der Zwischenablage (eine Zeile, 60 Zeichen) |
| `ClipLength` | Länge in Zeichen |
| `ClipCount` | Einträge im Verlauf |
| `Slot1` … `SlotN` | Vorschau des jeweiligen Slots (40 Zeichen), leer wenn leer |
| `AutoSave` / `NextSlot` | Auto-Speichern „an“ oder „aus“ / nächster Slot |

In Button-Beschriftungen mit `{Slot1}` anzeigen, oder als Live-Anzeige „Wert einer Variablen“.

## Einstellungen

Alle optional: Anzahl Slots (12), Slots nach Neustart behalten (an), Verlauf mitschreiben (an),
Länge des Verlaufs (20), Texte ignorieren über … Zeichen (10000), Prüfintervall (1000 ms).

## Datenschutz, was gespeichert wird

- **Verlauf:** nur im Arbeitsspeicher, wird nie auf die Platte geschrieben und endet mit dem Plugin.
  Wer Passwörter kopiert, kann den Verlauf in den Einstellungen ausschalten oder per Aktion leeren.
- **Slots:** nur wenn „Slots nach Neustart behalten“ an ist, in
  `~/.config/touchdeck-clipboard-slots/slots.json` (Rechte 600, nur du; dort steht auch der Auto-Modus). Dort nichts ablegen, was
  geheim bleiben muss, oder die Einstellung ausschalten.
- Das Plugin sendet nichts ins Netz und lädt keinen Code nach.

## Grenzen

- Werte in TouchDeck sind auf 1000 Zeichen begrenzt: „Zwischenablage in Wert schreiben“ kürzt längere Texte.
- Nur Text. Bilder und Dateien in der Zwischenablage werden ignoriert.
- Die Zwischenablage wird per Abfrage geprüft (Standard jede Sekunde), nicht per Ereignis.

---

## English

**Advanced TouchDeck plugin** that turns buttons into a clipboard manager: save texts into slots,
bring them back with one tap, history of recent copies, clipboard to value and back, quick text
clean-ups. It only uses TouchDeck's documented plugin messages and does not rebuild anything
TouchDeck already does.

**Requirements:** TouchDeck 0.9 (Linux, X11) with advanced mode on, Python 3.8+, and `xclip`, `xsel`
or `wl-clipboard` (`sudo apt install xclip`). **Windows** (very early alpha, untested): Python 3.8+
from python.org is enough, no clipboard tool needed; slots are stored in
`%APPDATA%\touchdeck-clipboard-slots`.

**Setup:** Plugins › Marketplace › “Clipboard Slots” › Check › install (or enter
`Marcel1853/touchdeck-plugins/plugins/clipboard-slots`). Then click “📄 Zwischenablage Seite import” on the
plugin card (or under “Ready-made pages” in the page list): a ready-made page,
tap a slot to paste it, hold a slot (~0.5 s) to save the clipboard into it. No required settings.

**Actions:** save clipboard to slot · put slot into clipboard · put history entry into clipboard ·
clipboard to value · value to clipboard · clean up clipboard text (trim, single line, upper/lower
case, strip tracking from a link) · auto-save into slots (ring buffer: every new copy goes into the next slot) · clear (history, clipboard, one slot, all slots).
To paste with a button, add TouchDeck's own “Keyboard shortcut” `Ctrl+V` after “Put slot into
clipboard”.

**Trigger:** clipboard text changed (`{Event.Text}`, `{Event.Length}`).
**Values:** `Clip`, `ClipLength`, `ClipCount`, `Slot1` … `SlotN`.

**Privacy:** the history lives in memory only. Slots are saved to
`~/.config/touchdeck-clipboard-slots/slots.json` (mode 600) unless you turn that off. Nothing is
sent over the network, nothing is downloaded.

License: MIT
