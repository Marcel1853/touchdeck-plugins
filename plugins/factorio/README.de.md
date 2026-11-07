# Factorio für TouchDeck

[English](README.md) · **Deutsch**

**Erweitertes TouchDeck-Plugin** für Factorio 2.1 (mit und ohne Space Age). Zeigt Forschung,
Geschwindigkeit, Evolution, Strom, Produktion, Planet und – mit UTLogistics – deine Züge live auf
deinen Buttons, vieles davon auch als Graph. Buttons pausieren, ändern das Tempo, speichern, machen
Screenshots und reihen Forschung ein.

Dazu gehört der Factorio-Mod **[TouchDeck Bridge](https://mods.factorio.com/mod/touchdeck-bridge)**
aus dem Mod-Portal.

- **Arbeitet mit [UTLogistics](https://mods.factorio.com/mod/UTLogistics) zusammen**, wenn es in Factorio
  installiert ist (optional, siehe unten).
- **Linux: getestet. Windows: noch nicht getestet** – Rückmeldungen sind willkommen.
- Sprachen: Deutsch und Englisch; Französisch, Spanisch, Polnisch, brasilianisches Portugiesisch,
  Russisch und Chinesisch sind KI-Übersetzungen (Korrekturen willkommen). Die fertigen Seiten sind
  auf Deutsch beschriftet.
- Die Funktionen sind **Beispiele** dafür, was ein Spiel und TouchDeck zusammen können. Lizenz MIT:
  Baue gern dein eigenes Plugin oder deinen eigenen Mod daraus. **Vorschläge sind willkommen.**

## Einrichtung

1. **TouchDeck installieren** (kostenlos):
   [github.com/Marcel1853/touchdeck/releases](https://github.com/Marcel1853/touchdeck/releases),
   dazu die Android-App fürs Handy oder Tablet.
2. **Plugin installieren:** In TouchDeck den erweiterten Modus einschalten (*Plugins › Erweitert*),
   dann *Plugins › Marktplatz › **Factorio** › Installieren*. TouchDeck fragt zweimal nach, weil es
   ein erweitertes Plugin ist.
3. **Mod installieren:** In Factorio im Hauptmenü unter *Mods* nach **„TouchDeck Bridge“** suchen und
   installieren. Oder in TouchDeck in der Plugin-Karte auf **„🧩 Mod installieren“** klicken – das
   Plugin bringt den Mod mit, TouchDeck legt ihn in deinen Factorio-Mod-Ordner. Danach Factorio
   (neu) starten, der Mod ist automatisch an.
4. **Seiten importieren:** In der Plugin-Karte bei „Fertige Seiten“ auf **Factorio** klicken (mit
   UTLogistics zusätzlich auf **UTLogistics**). Der Import fügt nur hinzu: Hast du schon Seiten
   einer älteren Version, lösche sie vorher.
5. **Spiel laden** – fertig. Oben links auf der Seite „Factorio“ steht dann „läuft“.

Voraussetzungen: TouchDeck 0.12 oder neuer, Python 3.8 oder neuer (unter Linux meist schon dabei),
unter Linux eine X11-Sitzung. In Factorio musst du nichts einstellen: keine Startoption, kein
Netzwerk, kein RCON.

## So funktioniert es

- Der Mod schreibt kleine Dateien in den Factorio-Benutzerordner (`script-output/touchdeck-bridge/`),
  das Plugin achtet auf Änderungen. Es geht nichts ins Netz.
- Jeder Befehl ist ein eigenes Tastenkürzel des Mods (`Strg+Alt+Umschalt+…`). TouchDeck drückt es im
  Factorio-Fenster, das Plugin wartet auf die Antwort des Spiels und zeigt sie am Button
  (z. B. „Geschwindigkeit 2×“ oder „Nur für Admins“).

## Die fertigen Seiten

Hauptseite **Factorio** mit Status, Forschung, Tempo, Pause, Speichern und großen Graphen für Strom
und Evolution, dazu Ordner zu **Zeit**, **Forschung**, **Strom**, **Spiel** und **Produktion**. Kommt
Factorio in den Vordergrund, wechselt TouchDeck zur Seite „Factorio“.

| Button | Tippen | Doppeltippen | Halten | Loslassen |
| --- | --- | --- | --- | --- |
| Tempo (Hauptseite) | 1× | 2× | 4× | wieder 1× |
| Pause | Pause an/aus (leuchtet rot bei Pause) | – | – | – |
| Halten = 4× (Zeit) | – | – | 4× | wieder 1× |
| Langsamer / Schneller (Zeit) | halbe / doppelte Geschwindigkeit | – | – | – |
| Abbrechen (Forschung) | Forschung abbrechen – erst beim **zweiten** Druck | – | – | – |
| #1 / #2 / #3 (Forschung) | günstigste verfügbare Forschung einreihen | – | – | – |
| Strom (Hauptseite) | öffnet die Seite Strom | – | – | – |

- **Strom:** Erzeugung nach Quelle (Dampf, Turbinen, Solar, Akkus …) und Verbrauch nach Gebäude als
  gestapelte Graphen der letzten 10 Minuten, dazu Erzeugung, Verbrauch und Auslastung.
- **Produktion – du wählst, was du siehst:** 8 Plätze, jeder mit Graph (Produktion und Verbrauch pro
  Minute). Am Platz: **antippen** = nächstes Item, **halten** = voriges, **doppelt tippen** = wieder
  automatisch (meistproduzierte Items). Die Auswahl bleibt erhalten.
- **Bildschirmschoner:** Unter der Uhr erscheint eine Karte mit Status, Forschung, Strom, Planet,
  Tempo und Evolution.
- **Meldungen:** „Forschung fertig“ und „Du bist gestorben“ erscheinen unten rechts auf der
  Hauptseite – keine Popups am PC.
- Den Button **UTLogistics** zeigt die Hauptseite nur, wenn UTLogistics im Spiel aktiv ist.

## UTLogistics (optional)

Mit dem Mod [UTLogistics](https://mods.factorio.com/mod/UTLogistics) liest TouchDeck Bridge dessen
Daten – je Planet: freie und fahrende Züge, Lieferungen, Stationen, Netze, Warnungen im Volltext und
Anfragen ohne Zug. Dafür gibt es die fertigen Seiten **UTLogistics** (Übersicht), **Stationen**,
**Netze** und **Warnungen**.

- **Planet** (Button oben): zeigt automatisch den Planeten, auf dem du bist. **Antippen** = nächster
  Planet, **halten** = alle Planeten, **doppelt tippen** = wieder automatisch.
- **Stationen:** Im UTL-Stationsfenster gibt es den Abschnitt **„TouchDeck“**: „Auf dem TouchDeck
  zeigen“ anhaken und einen Platz 1–8 wählen. Die Station erscheint dann mit Zügen (da und
  unterwegs), Angebot und Bedarf. Die Wahl reist mit Blaupausen mit. Der UTL-Manager hat einen
  Reiter **„TouchDeck“** mit allen angehefteten Stationen.
- **Netze:** 8 Plätze für die Netze des Planeten. Am Platz: **antippen** = nächstes Netz,
  **halten** = voriges, **doppelt tippen** = automatisch.
- Buttons öffnen den UTL-Manager (auch direkt im Reiter Warnungen).

Ohne UTLogistics passiert nichts – die Seiten zeigen dann „UTLogistics nicht aktiv“.

## Eigene Buttons

Zwei Aktionen hintereinander:

1. **Tastenkürzel** (eingebaute Aktion): z. B. `ctrl+alt+shift+p`, Fenster `factorio`.
2. **Factorio › Auf Antwort des Spiels warten**: wartet bis zu 3 s und zeigt die Antwort. Ohne
   Antwort sagt sie, warum: Spiel aus, Esc-Menü offen oder Fenster nicht erreichbar.

| Strg+Alt+Umschalt+… | Befehl |
| --- | --- |
| P | Pause umschalten |
| 1 / 2 / 3 / 4 | Geschwindigkeit 0,5× / 1× / 2× / 4× |
| N / M | langsamer (½) / schneller (×2) |
| S | Speichern (`_autosave-touchdeck`) |
| K | Screenshot |
| Q / W / E | Forschungsvorschlag 1 / 2 / 3 einreihen |
| X | Forschung abbrechen |
| H | Zurück zum Spieler (Fernansicht verlassen) |
| U | Daten neu schreiben |
| G / A | UTL-Manager / UTL-Manager Warnungen (nur mit UTLogistics) |

Weitere Aktionen: *Produktions-Platz: Item wählen* (auch nach Name, z. B. „Eisenplatte“),
*UTLogistics: Planet wählen*, *UTLogistics: Netz-Platz wählen*, *UTLogistics: Seite öffnen*.

## Auslöser (für Events)

| Auslöser | Daten |
| --- | --- |
| Forschung abgeschlossen / gestartet | `{Event.Name}` (Spielsprache), `{Event.Intern}` |
| Rakete gestartet | `{Event.Anzahl}` |
| Spieler gestorben | `{Event.Spieler}`, `{Event.Ich}` (ja/nein) |
| Evolution hat 10-%-Stufe überschritten | `{Event.Prozent}`, `{Event.Flaeche}` |
| Befehl vom Spiel beantwortet | `{Event.Befehl}`, `{Event.Ok}` (ja/nein), `{Event.Meldung}` |
| Spiel verbunden / getrennt | – |
| UTLogistics: neue Warnung | `{Event.Warnung}` |
| UTLogistics: Anfrage wartet ohne Zug | `{Event.Anzahl}`, `{Event.Text}` |

## Werte

| Wert | Inhalt |
| --- | --- |
| `FStatus` | läuft · pausiert · angehalten · Factorio aus |
| `FSpielzeit`, `FTick` | gespielte Zeit (h:mm:ss), aktueller Tick |
| `FGeschwindigkeit`, `FPause` | z. B. `1`, `0.5` · an/aus |
| `FForschung`, `FForschungProzent`, `FWarteschlange` | aktuelle Forschung, 0–100, Länge der Warteschlange |
| `FVorschlag1` … `FVorschlag3` | günstigste verfügbare Forschungen |
| `FStromErzeugung`, `FStromVerbrauch` | Strom des Netzes, in dem du stehst, z. B. `35,2 MW` |
| `FEvolution`, `FRaketen`, `FSpieler`, `FPlanet` | Evolution in %, Raketen, Spieler online, Planet oder Raumplattform |
| `FItem1` … `FItem8` | Produktions-Plätze, z. B. `Eisenplatte: 600/min` |
| `FMeldung` | letzte Antwort oder Meldung des Spiels |
| `FUtl…` | Werte für UTLogistics (Züge, Stationen, Netze, Warnungen …), siehe Werte-Liste in TouchDeck |

Im Editor gibt es unter *Live-Anzeige › Plugin* außerdem Anzeigen mit Graph: Forschung, Tempo,
Evolution, Strom-Erzeugung (gestapelt nach Quelle), Strom-Verbrauch (nach Gebäude), die 8
Produktions-Plätze und für UTLogistics Züge, Waren, Lieferungen, Stationen und Netze.

## Einstellungen (alle optional)

| Einstellung | Standard |
| --- | --- |
| Ordner der Mod-Dateien | leer = automatisch suchen |
| Dateien prüfen alle … ms | 250 (solange Factorio läuft) |
| Ohne Factorio nur alle … ms prüfen | 3000 |
| Keine Daten seit … Sekunden = nicht verbunden | 5 |

## Datenschutz

Alles bleibt auf deinem Rechner. Das Plugin liest nur die Dateien des Mods und schaut nach, ob
Factorio läuft. Es öffnet keine Netzwerkverbindung und schreibt nichts auf die Platte.

## Grenzen

- **Einzelspieler – Pause, Esc-Menü und Forschung (Technologiebaum):** Das Spiel steht dann komplett,
  nimmt keine Tasten an und schreibt nichts. TouchDeck behält die letzten Werte und zeigt
  „angehalten“. Eine Lösung dafür kenne ich noch nicht – Ideen sind willkommen. Im Mehrspieler läuft
  das Spiel in diesen Fenstern weiter.
- **Strom** gilt für das Netz, in dem du stehst. Getrennte Netze werden nicht zusammengezählt.
- **Produktion** gilt für den Planeten oder die Plattform, auf der du stehst.
- **Kein freier Text:** Forschung nur über die drei Vorschläge. Mehr geht im Spiel mit
  `/touchdeck …` oder dem Befehlsfeld (Strg+Alt+Umschalt+B).
- Am Spielanfang gibt es nur „Auslöser-Forschungen“ (herstellen, abbauen …), die sich nicht
  einreihen lassen – dann gibt es noch keine Vorschläge.
- Mehrspieler: Jeder Spieler bekommt die Daten nur auf seinem eigenen Rechner. Pause, Tempo und
  Speichern nur für Admins.

## Für eigene Plugins und Mods

Den Quelltext findest du auf GitHub:
[Marcel1853/touchdeck-plugins › plugins/factorio](https://github.com/Marcel1853/touchdeck-plugins/tree/main/plugins/factorio)
(den Mod im Zip daneben). Eine eigene Kopie lädst du in TouchDeck unter *Plugins › Entwickeln*.

- `python3 tools/make_profile.py` erzeugt die fertigen Seiten neu.
- `python3 tests/test_plugin.py` testet das Plugin gegen einen nachgebauten Mod.
- `python3 tests/check_profile.py <touchdeck>/touchdeck-rs/server/catalog` prüft die Seiten gegen die
  Regeln aus dem [TouchDeck-Quelltext](https://github.com/Marcel1853/touchdeck).

Lizenz: MIT.
