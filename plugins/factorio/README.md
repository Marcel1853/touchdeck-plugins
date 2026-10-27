# Factorio für TouchDeck · Factorio for TouchDeck

🇩🇪 Deutsch · [🇬🇧 English below](#english)

**Erweitertes TouchDeck-Plugin** für Factorio 2.1 (mit und ohne Space Age). Zeigt Forschung,
Geschwindigkeit, Evolution, Strom, Planet und mehr live auf deinen Buttons, Strom und Evolution
auch als Graph. Steuert das Spiel: Pause, Tempo, Speichern, Screenshot, Schnell-Chat,
Forschungs-Warteschlange.

Dazu gehört der Factorio-Mod **TouchDeck Bridge** (`touchdeck-bridge`, ab Version 0.6.0).

## So funktioniert es

```
Factorio + Mod ──schreibt──▶ ~/.factorio/script-output/touchdeck-bridge/state.json ──liest──▶ Plugin ──▶ Werte, Live-Anzeigen, Graphen, Auslöser
TouchDeck-Button ──Tastenkürzel Strg+Alt+Umschalt+…──▶ Factorio-Fenster ──▶ Mod führt aus, schreibt Antwort in state.json
```

- **Keine Startoption, kein RCON, kein Netzwerk.** Der Mod schreibt eine JSON-Datei, das Plugin
  achtet auf Änderungen (alle 250 ms).
- Jeder Befehl ist ein eigenes Tastenkürzel des Mods. TouchDeck drückt es mit seiner eingebauten
  Aktion „Tastenkürzel“ im Factorio-Fenster. In Factorio muss nichts eingestellt werden.
- Danach wartet das Plugin auf die Antwort des Spiels und zeigt sie als Meldung des Buttons
  (z. B. „Geschwindigkeit 2×“ oder „Nur für Admins“).
- TouchDeck tippt keinen Text ins Spiel: Mit der Eingabemethode IBus kommen erzeugte Tasten in
  Factorio-Textfeldern nicht an (im Spiel geprüft). Deshalb liegen die Schnell-Chat-Texte im Mod.

## Einrichtung in vier Schritten

1. **Mod installieren:** `touchdeck-bridge_0.6.0.zip` nach `~/.factorio/mods/` legen (oder den
   Ordner `touchdeck-bridge`); unter Windows (ganz frühe Alpha, ungetestet) nach
   `%APPDATA%\Factorio\mods\`. Factorio starten, der Mod ist automatisch an.
2. **Plugin laden:** In TouchDeck den erweiterten Modus einschalten (Plugins › Erweitert), dann
   Plugins › Marktplatz › **Factorio** installieren (oder Plugins › Entwickeln › diesen Ordner
   laden). Zweimal bestätigen, weil es ein erweitertes Plugin ist.
3. **Seite importieren:** In der Plugin-Karte oder unter „Fertige Seiten“ auf
   `Factorio.tdprofile` klicken (oder Seitenliste › „⋯“ › Profil importieren).
   Der Import fügt nur hinzu: Seiten einer älteren Version vorher löschen.
4. **Spiel laden** – fertig. `{FStatus}` auf der Seite zeigt „läuft“.

Voraussetzungen: TouchDeck 0.12 (Graphen mit mehreren Reihen, Button-Art „Anzeige“, Sicherheitsabfrage,
Bildschirmschoner; ältere Versionen ignorieren, was sie nicht kennen), Linux mit X11, Python 3.8 oder neuer.
Keine Pflicht-Einstellungen.

## Die fertige Seite

Hauptseite **Factorio** (4 × 6) mit Live-Anzeigen, großen Strom- und Evolutions-Graphen, einem
Button **UTLogistics** und sechs Ordnern (je eine
eigene Seite mit Zurück-Button oben links): **Zeit**, **Forschung**, **Chat**, **Spiel**,
**Produktion** und **Strom** (über den Strom-Graphen der Hauptseite). Kommt
Factorio in den Vordergrund, wechselt TouchDeck auf allen Geräten zur Seite „Factorio“.

| Button | Tippen | Doppeltippen | Halten | Loslassen |
| --- | --- | --- | --- | --- |
| Tempo (Hauptseite) | 1× | 2× | 4× | wieder 1× |
| Pause | Pause an/aus (leuchtet rot bei Pause, aus `{FPause}`) | – | – | – |
| Halten = 4× (Zeit) | – | – | 4× | wieder 1× |
| Langsamer / Schneller (Zeit) | halbe / doppelte Geschwindigkeit | – | – | – |
| Abbrechen (Forschung) | Forschung abbrechen – erst beim **zweiten** Druck (Sicherheitsabfrage) | – | – | – |
| #1 / #2 / #3 (Forschung) | günstigste verfügbare Forschung einreihen, Name steht auf dem Button | – | – | – |
| Chat-Buttons | Schnell-Chat 1–6 | – | – | – |
| Strom (Hauptseite) | öffnet den Ordner Spiel; Erzeugung nach Quelle gestapelt (Dampf, Solar, Akkus …), letzte 2 Minuten | – | – | – |
| Evolution (Hauptseite) | Anzeige; Flächen-Graph der letzten Stunde (0–100 %) | – | – | – |

Buttons, die nur etwas anzeigen (Status, Planet, Spielzeit, Tempo-Anzeige, Erzeugung, Verbrauch …),
sind von der Art „Anzeige“: kein Antippen, keine Drück-Animation.

Der Pause-Zustand kommt aus dem Spiel (Wert `{FPause}`), nicht aus einem frei laufenden Umschalter.
Er stimmt also auch, wenn du am Rechner pausierst.

**UTLogistics-Button (Startseite):** Er ist anfangs **versteckt** und erscheint erst, wenn das Spiel
UTLogistics meldet (Events „UTLogistics aktiv → Button zeigen“ / „… nicht aktiv → Button verstecken“, Aktion
„Button zeigen/verstecken“, TouchDeck 0.11). Ist UTLogistics im Spiel aktiv (Wert `FUtlAktiv` = ja), öffnet
er die Seite „UTLogistics“ aus dem eigenen Profil `UTLogistics.tdprofile` (gesucht über den Namen,
weil der Import Seiten neue IDs gibt; die Seite erscheint dann auf allen Geräten). Sonst öffnet er die
Mod-Seite im Portal. Wer UTL nicht nutzt, löscht den Button einfach.

**Strom:** Erzeugung nach Quelle (Dampf, Turbinen, Solar, Akkus …) und Verbrauch nach Gebäude
(die sechs größten Verbraucher, Rest „Sonstige“) als große gestapelte Graphen der letzten
10 Minuten, dazu Erzeugung, Verbrauch und Auslastung als Zahl.

**Produktion – du wählst, was du siehst:** 8 Plätze, jeder mit Graph (Produktion und Verbrauch pro
Minute, letzte 10 Minuten). Am Platz selbst:

| Geste | Wirkung |
| --- | --- |
| Antippen | nächstes Item (alphabetisch) |
| Halten | voriges Item |
| Doppeltippen | wieder automatisch |

Automatische Plätze zeigen die meistproduzierten Items, die kein anderer Platz zeigt. Von Hand
gewählte Plätze leuchten. „Alle automatisch“ setzt alles zurück. Die Auswahl merkt sich TouchDeck in
den Werten `FItemWahl1`–`FItemWahl8`, sie bleibt nach einem Neustart erhalten. Zur Wahl stehen alle
Items und Flüssigkeiten, die auf deiner Fläche gerade hergestellt oder verbraucht werden.

**Schnell-Chat:** Hilfe!, Bin gleich da!, Brauche Eisen!, Angriff an der Basis!, Bin kurz weg.,
Danke!. Die Texte sind übersetzt, jeder Mitspieler liest sie in seiner Sprache. Eigene Texte
setzt du in Factorio unter Einstellungen › Mod-Einstellungen › Spieler › Schnell-Chat 1–6 (dann
auch die Beschriftung des Buttons ändern).

**Bildschirmschoner (TouchDeck 0.12):** Unter der Uhr erscheint eine Karte „Factorio“ mit Status,
Forschung, Strom, Planet, Tempo und Evolution. Sie verschwindet, wenn Factorio beendet ist.

**Events:** Factorio im Vordergrund (nur beim ersten Mal) → Seite Factorio · Forschung fertig und „Ich bin gestorben“ →
Meldung auf dem Deck (Wert `{FMeldung}`, unten rechts auf der Hauptseite). Keine Popups am PC –
im Spiel siehst du es ja ohnehin.

## UTLogistics (optional, eigenes Profil)

Hast du den Mod **UTLogistics** aktiv, liest touchdeck-bridge dessen Daten – nur lesend und so, wie
es das UTL-Wiki („Für Mod-Autoren“, Seite „Leistung“) empfiehlt: billige Zähler bei jeder
Aktualisierung, Listen und Statistik nur selten, alles andere aus UTLs Ereignissen. Es ist **kein
UTL-Add-on** (keine eigenen Rollen, Fahrten oder Fenster). Ohne UTLogistics passiert nichts, die
Seite zeigt „UTLogistics nicht aktiv“.

**Als UTL-Add-on (nur Fenster, ab UTLogistics 0.0.20):** Im **Stationsfenster** jeder UTL-Station gibt
es den Abschnitt **„TouchDeck“**: Häkchen „Auf dem TouchDeck zeigen“ und einen Platz 1–8 wählen.
Gespeichert wird das als UTL-Stationsdaten – es reist mit Blaupausen und beim Einstellungen-Kopieren
mit. Im **UTL-Manager** zeigt der Reiter **„TouchDeck“** alle angehefteten Stationen mit „Lösen“.

Dafür gibt es ein **eigenes Profil** `UTLogistics.tdprofile` mit vier Seiten im Ordner „Factorio“:
**UTLogistics** (Übersicht) und die Unterseiten **Stationen**, **Netze** und **Warnungen**.

- **Stationen:** die 8 im Spiel angehefteten Stationen – Züge da und unterwegs (Graph), Angebot (+)
  und Bedarf (−).
- **Netze:** 8 Plätze für die Netze des gezeigten Planeten (freie Züge, Lieferungen, Stationen, Graph).
  Am Platz: antippen = nächstes Netz, halten = voriges, doppelt = automatisch (meiste Stationen).
- **Warnungen:** die letzten 5 Warnungen im Volltext und bis zu 5 Anfragen ohne Zug.

Übersicht:

- **Planet** (Button oben links): Mit Space Age zählt alles **je Planet**. Zuerst steht er auf
  **automatisch** und zeigt den Planeten, auf dem du gerade bist. Auf einer Raumplattform (dort gibt
  es keine Schienen) bleibt der zuletzt gezeigte Planet stehen. **Antippen** = nächster Planet,
  **halten** = alle Planeten zusammen, **doppelt tippen** = wieder automatisch. Die Wahl bleibt nach
  einem Neustart erhalten (`FUtlFlaecheWahl`).

- Züge frei/unterwegs (Graph), Stationen, Netze, Auslastung
- gelieferte Waren pro Stunde (gestapelter Graph) und Lieferungen pro Minute der letzten Stunde (Balken)
- **letzte Warnung mit vollem Text** in deiner Sprache, z. B. „UTL: Zug 5 steckt seit 3 Minuten fest …“
  (ab UTLogistics 0.0.20; ältere Versionen: kurzer Text je Art)
- **Anfragen ohne Zug**: Anzahl und die älteste, z. B. „Kupferplatte · Eisen · seit 7 min“ (ab 0.0.20)
- Buttons „Manager öffnen“ (Strg+Alt+Umschalt+G) und „Warnungen“ (Manager im Reiter Warnungen,
  Strg+Alt+Umschalt+A); die Anfrage-Anzeige öffnet ebenfalls den Manager

Keine Popups am PC. Wer doch reagieren will: Auslöser „UTLogistics: neue Warnung“ (`{Event.Warnung}`)
und „UTLogistics: Anfrage wartet ohne Zug“ (`{Event.Anzahl}`, `{Event.Text}`) in eigenen Events.

Werte: `FUtlStation1`–`8`, `FUtlStationInfo1`–`8`, `FUtlNetz1`–`8` (gewählt in `FUtlNetzWahl1`–`8`),
`FUtlWarnung1`–`5`, `FUtlOhneZug1`–`5`, `FUtlStatus`, `FUtlFlaeche` (angezeigter Planet), `FUtlZuegeFrei`, `FUtlUnterwegs`, `FUtlStationen`, `FUtlNetze`,
`FUtlLieferungen` (seit touchdeck-bridge mitzählt), `FUtlLieferungenStunde`, `FUtlAuslastung`,
`FUtlWarnungen`, `FUtlWarnung`, `FUtlOhneZug`, `FUtlOhneZugText`, `FUtlWare1`–`3`.
Alles gilt für dein Team und den gewählten Planeten; nur die Auslastung der Züge gibt UTL lediglich
für alle Planeten zusammen her. Aktion „UTLogistics: Planet wählen“ (nächster, voriger, automatisch, alle).

## Aktionen

| Aktion | Was sie macht |
| --- | --- |
| Auf Antwort des Spiels warten | nach einem Tastenkürzel: wartet bis zu 3 s auf die Bestätigung des Mods |
| UTLogistics: Seite öffnen | öffnet die Seite „UTLogistics“ (über den Namen); fehlt sie, kommt der Hinweis, das Profil zu importieren |
| UTLogistics: Planet wählen | nächster, voriger, automatisch, alle |
| UTLogistics: Netz-Platz wählen | Platz 1–8: nächstes, voriges, automatisch, alle automatisch |
| Produktions-Platz: Item wählen | Platz 1–8: nächstes, voriges, automatisch, nach Name (Spielsprache oder intern, z. B. „Eisenplatte“) oder alle automatisch |

## Eigene Buttons

Zwei Aktionen hintereinander:

1. **Tastenkürzel** (eingebaute Aktion): z. B. `ctrl+alt+shift+p`, Fenster `factorio`.
2. **Factorio › Auf Antwort des Spiels warten**: Befehl `Pause` (oder leer = jede Antwort).
   Wartet bis zu 3 s und zeigt die Antwort. Ohne Antwort sagt sie, warum: Spiel aus, Esc-Menü offen
   oder Fenster nicht erreichbar.

| Strg+Alt+Umschalt+… | Befehl |
| --- | --- |
| P | Pause umschalten |
| 1 / 2 / 3 / 4 | Geschwindigkeit 0,5× / 1× / 2× / 4× |
| N / M | langsamer (½) / schneller (×2) |
| S | Speichern (`_autosave-touchdeck`) |
| K | Screenshot nach `script-output/touchdeck-bridge/screenshots/` |
| Q / W / E | Forschungsvorschlag 1 / 2 / 3 einreihen |
| X | Forschung abbrechen |
| 5 6 7 8 9 0 | Schnell-Chat 1–6 |
| H | Zurück zum Spieler (Fernansicht verlassen) |
| U | Daten neu schreiben |
| G / A | UTL-Manager / UTL-Manager Warnungen (nur mit UTLogistics) |

## Auslöser (für Events)

| Auslöser | Daten |
| --- | --- |
| Forschung abgeschlossen | `{Event.Name}` (Spielsprache), `{Event.Intern}` |
| Forschung gestartet | `{Event.Name}`, `{Event.Intern}` |
| Rakete gestartet | `{Event.Anzahl}` |
| Spieler gestorben | `{Event.Spieler}`, `{Event.Ich}` (ja/nein) |
| Evolution hat 10-%-Stufe überschritten | `{Event.Prozent}`, `{Event.Flaeche}` |
| Befehl vom Spiel beantwortet | `{Event.Befehl}`, `{Event.Ok}` (ja/nein), `{Event.Meldung}` |
| Spiel verbunden / getrennt | – |

## Werte

| Wert | Inhalt |
| --- | --- |
| `FStatus` | läuft · pausiert · keine Daten (Menü, Ladebildschirm) · Factorio aus |
| `FVerbunden` | ja/nein |
| `FSpielzeit`, `FTick` | gespielte Zeit (h:mm:ss), aktueller Tick |
| `FGeschwindigkeit`, `FPause` | z. B. `1`, `0.5` · an/aus |
| `FForschung`, `FForschungProzent`, `FWarteschlange` | aktuelle Forschung in Spielsprache, 0–100, Länge der Warteschlange |
| `FVorschlag1` … `FVorschlag3` | günstigste verfügbare Forschungen |
| `FStromErzeugung`, `FStromVerbrauch` | Strom des Netzes, in dem du stehst, z. B. `35,2 MW` (kein Netz in der Nähe: „–“) |
| `FEvolution` | Evolution auf deiner Fläche in Prozent (auf Plattformen „–“) |
| `FRaketen`, `FSpieler`, `FPlanet` | Raketen der Force, Spieler online, Planet oder Raumplattform |
| `FItem1` … `FItem8` | Produktions-Plätze, z. B. `Eisenplatte: 600/min` |
| `FItemWahl1` … `FItemWahl8` | gewähltes Item je Platz (`item.iron-plate`), leer = automatisch; bleibt erhalten |
| `FMeldung` | letzte Antwort des Spiels |

## Live-Anzeigen (mit Graph)

Im Editor unter Live-Anzeige › Plugin. Alle liefern eine echte Zahl (`number`) für Graphen;
„Strom-Erzeugung“ zusätzlich mehrere Reihen (`series`) – mit „Fläche gestapelt“ ergibt die obere
Kante die Gesamterzeugung. Akkus zählen nur beim Entladen (Laden ist Verbrauch).

| Live-Anzeige | Text | Balken (0–100) | Zahl für Graph | „an“ |
| --- | --- | --- | --- | --- |
| Forschung mit Fortschritt | Name und % | Fortschritt | Fortschritt | Forschung läuft |
| Verbindung und Pause | Zustand | – | – | verbunden |
| Spielgeschwindigkeit | z. B. `2×` | – | Geschwindigkeit | nicht 1× |
| Evolution | z. B. `12,3 %` | Evolution | Evolution in % | ab 50 % |
| Strom-Erzeugung | z. B. `35,2 MW` | Auslastung (Verbrauch ÷ Erzeugung) | MW, dazu `series` je Quelle: Dampf, Turbinen, Solar, Akkus, Brennstoff, Fusion, Blitze, Schnittstelle, Sonstige | Netz erzeugt |
| Strom-Verbrauch | z. B. `17,6 MW` | Auslastung | MW, dazu `series` je Gebäude (sechs größte + Sonstige) | Netz verbraucht |
| Produktion Platz 1–8 | z. B. `Eisenplatte 600/min` | – | Produktion/min, dazu `series` Produktion und Verbrauch | von Hand gewählt |

## Einstellungen (alle optional)

| Einstellung | Standard |
| --- | --- |
| Ordner der Mod-Dateien | leer = `~/.factorio/script-output/touchdeck-bridge` oder die Flatpak-Steam-Variante; unter Windows `%APPDATA%\Factorio\script-output\touchdeck-bridge` |
| Dateien prüfen alle … ms | 250 (solange Factorio läuft oder vor Kurzem Daten kamen) |
| Ohne Factorio nur alle … ms prüfen | 3000 (`/proc` dann nur alle 5 s) |
| Keine Daten seit … Sekunden = nicht verbunden | 5 |

## Datenschutz

Alles bleibt auf deinem Rechner. Das Plugin liest nur die Dateien des Mods (`state.json`,
`names.txt`, `items.json`, `labels.txt`, `utl.json`, `utl-alerts.txt`) und
`/proc/*/comm` (um zu sehen, ob Factorio läuft). Es öffnet keine Netzwerkverbindung und schreibt
nichts auf die Platte; die Auswahl der Plätze liegt in TouchDeck-Werten.

## Grenzen (ehrlich)

- **Esc-Menü im Einzelspieler:** Das Spiel steht dann komplett, nimmt keine Tasten an und schreibt
  nichts. TouchDeck zeigt „keine Daten“, Befehle melden „Ist das Esc-Menü offen?“.
- **Pause per Button** (`game.tick_paused`): In diesem Zustand laufen keine Takt-Handler (im Spiel
  geprüft). Der Mod schreibt den Zustand beim Pausieren sofort, TouchDeck zeigt „pausiert“. Weiter
  geht es über dasselbe Tastenkürzel. Gehst du pausiert ins Hauptmenü, steht „pausiert“, bis
  Factorio beendet ist.
- **Strom** gilt für das Netz, in dem du stehst (ein Mast im Umkreis von 32 Feldern). Mehrere
  getrennte Netze werden nicht zusammengezählt.
- **Kein freier Text:** Chat nur mit den sechs Schnell-Chat-Texten, Forschung nur über die drei
  Vorschläge. Mehr gibt es im Spiel mit `/touchdeck …` oder dem Befehlsfeld (Strg+Alt+Umschalt+B,
  von Hand tippen).
- **Produktion** gilt für die Fläche, auf der du stehst (Planet oder Plattform). Neue Zahlen kommen
  alle 5 Sekunden. Ob Items höherer Qualität (Space Age) mitgezählt werden, ist noch nicht geprüft.
- Tastenkürzel brauchen ein erreichbares Factorio-Fenster unter X11.
- Am Spielanfang gibt es nur „Auslöser-Forschungen“ (herstellen, abbauen …). Die kann man nicht
  einreihen, deshalb sind die Vorschläge dann leer.
- Mehrspieler: Jeder Spieler bekommt seine Dateien nur auf dem eigenen Rechner. Pause, Tempo und
  Speichern nur für Admins.

## Entwickeln und Testen

- `python3 tools/make_profile.py` erzeugt `Factorio.tdprofile` neu.
- `python3 tests/check_profile.py [touchdeck-rs/server/catalog]` prüft die Seite gegen die Regeln
  von TouchDeck (Überlappung, Aktionen, Werte, Verweise, Graphen).
- `python3 tests/test_plugin.py [state.json]` testet das Plugin gegen einen nachgebauten Mod
  (Verbinden, Werte, Strom, Graph-Zahlen, Ereignisse, Antworten, Zeitüberschreitung, kaputte
  Dateien, Herzschlag-Ausfall, Pause, neuer Spielstand) und optional gegen eine echte Datei des Mods.

Lizenz: MIT.

---

<a id="english"></a>

## English

**Advanced TouchDeck plugin** for Factorio 2.1 (with or without Space Age). Shows research,
speed, evolution, power, planet and more live on your buttons, power and evolution also as graphs,
and controls the game: pause, speed, save, screenshot, quick chat, research queue. Needs the
Factorio mod **TouchDeck Bridge** (`touchdeck-bridge`, 0.6.0 or newer).

- No launch option, no RCON, no network: the mod writes
  `~/.factorio/script-output/touchdeck-bridge/state.json`, the plugin watches it.
- Every command is its own key binding of the mod (Ctrl+Alt+Shift+…, table above). TouchDeck presses
  it with its built-in “Hotkey” action; the plugin waits for the game's answer and shows it on the
  button. TouchDeck never types text into the game (with IBus, generated keys do not reach Factorio
  text fields).

**Setup:** 1. put the mod into `~/.factorio/mods/` (Windows, very early alpha: `%APPDATA%\Factorio\mods\`) · 2. enable advanced mode in TouchDeck and install
**Factorio** from Plugins › Marketplace (or load this folder under Plugins › Develop) · 3. import `Factorio.tdprofile` (remove pages of an older version first) · 4. load a game.

**Action:** *Wait for the game's answer* (after a Hotkey action). **Triggers:** research
finished/started, rocket launched, player died, evolution 10 % step, command answered, connected,
disconnected. **Live displays** with a real number for graphs: research, status, speed, evolution,
power production (MW, plus `series` by source for stacked graphs) and consumption (MW, plus
`series` by building), and 8 production slots (per minute, production and consumption as two series).
On the production page you pick each slot's item right on the button: tap = next, hold = previous,
double tap = automatic (most produced); the choice is kept in TouchDeck values. **Values:** see the German table (`FStatus`, `FForschung`,
`FStromErzeugung`, `FGeschwindigkeit`, `FPause`, `FEvolution`, `FPlanet` …).

**Privacy:** everything stays on your computer. The plugin reads two files of the mod and
`/proc/*/comm`; it opens no network connection and writes nothing to disk.

**Limits:** nothing works while the Esc menu of a single player game is open; tick-paused games
run no timed handlers (the mod writes the state when pausing); power is the grid you stand in;
no free text (six quick chat texts, three research suggestions); key bindings need an X11 window.

License: MIT.
