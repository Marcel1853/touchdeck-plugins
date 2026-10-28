# Timberborn für TouchDeck

[English](README.md) · **Deutsch**

**Erweitertes TouchDeck-Plugin** für Timberborn 1.1. Zeigt live auf deinen Buttons, was man im Spiel
leicht übersieht: wann die nächste Dürre oder Faulwasserflut kommt, wie viele Tage Wasser und Nahrung
noch reichen, Obdachlose, Arbeitslose, Verseuchte, volle Lager, den Nachrichtenverlauf und alle
aktiven Warnungen. Und es steuert das Spiel: Pause, Tempo 1–3, Speichern, Kamera zu Meldungen und
Warnungen, Nachrichten im Spiel. Gefahren, neue Meldungen, Geburten und Todesfälle lösen
TouchDeck-Events aus.

Dazu gehört der Timberborn-Mod **TouchDeck Bridge** (Ordner `mod/TouchDeckBridge`). Er braucht kein
Harmony und keine anderen Mods.

## So funktioniert es

```
Timberborn + Mod (TCP-Server 127.0.0.1:34201) ◀──── JSON-Zeilen ────▶ Plugin (Client) ──▶ Werte, Live-Anzeigen, Auslöser
TouchDeck-Button ──▶ Plugin-Aktion ──▶ Befehl an den Mod ──▶ Antwort („Spiel pausiert“) als Meldung des Buttons
```

- Der Mod öffnet beim Spielstart einen kleinen TCP-Server, standardmäßig nur auf diesem PC
  (`127.0.0.1`). Das Plugin verbindet sich, baut die Verbindung bei Abbruch selbst wieder auf und
  bekommt den Zustand, sobald sich etwas ändert (mindestens alle 5 s ein Herzschlag).
- Befehle laufen im Spiel im Hauptthread – auch bei Pause und im Hauptmenü (dort antworten sie
  „Kein Spiel geladen“).
- Alle Zahlen stammen aus dem Spiel selbst: Wetter aus dem Wetterdienst, Bevölkerung aus der
  Bevölkerungsstatistik, „reicht noch … Tage“ aus der Warenstatistik (Durchschnitt der letzten drei
  Tage), Warnungen aus dem Warnfeld oben rechts.
- Die Art der nächsten Gefahr verrät das Plugin erst, wenn auch das Spiel sie ankündigt (3 Tage
  vorher). Bis dahin steht dort „?“.

## Einrichtung in vier Schritten

1. **Mod installieren:** Den Ordner `mod/TouchDeckBridge` (oder `TouchDeckBridge_0.1.0.zip` entpackt)
   in den Mod-Ordner von Timberborn legen: `Dokumente/Timberborn/Mods/`. Unter Linux mit Proton
   (Steam) ist das
   `~/.local/share/Steam/steamapps/compatdata/1062090/pfx/drive_c/users/steamuser/Documents/Timberborn/Mods/`.
   Timberborn starten und im Mod-Manager „TouchDeck Bridge“ einschalten.
   **Einfacher:** erst Schritt 2, dann in der Plugin-Karte auf „🧩 Mod installieren“ klicken –
   TouchDeck findet den Mod-Ordner selbst (Linux, Windows und Proton).
2. **Plugin laden:** In TouchDeck den erweiterten Modus einschalten (Plugins › Erweitert), dann
   Plugins › Marktplatz › **Timberborn** installieren (oder Plugins › Entwickeln › diesen Ordner
   laden). Zweimal bestätigen, weil es ein erweitertes Plugin ist.
3. **Seiten importieren:** In der Plugin-Karte oder unter „Fertige Seiten“ auf
   **Timberborn (Deutsch)** oder **Timberborn (English)** klicken – gleiche Seiten, nur die Texte
   unterscheiden sich. Nur eine davon importieren: Der Import fügt nur hinzu, er überschreibt nichts.
4. **Spielstand laden** – fertig. Der Status-Button oben links zeigt „läuft“.

Voraussetzungen: Timberborn 1.1, TouchDeck 0.12, Python 3.8 oder neuer (Linux; Windows ist eine ganz
frühe Alpha und ungetestet). Keine Pflicht-Einstellungen: Adresse `127.0.0.1`, Port `34201` und leeres
Geheimwort passen zu den Vorgaben des Mods.

## Zwei PCs: Streaming-PC und Spiele-PC

Läuft TouchDeck auf einem anderen Rechner als das Spiel (zum Beispiel auf dem Streaming-PC),
geht das so:

1. **Auf dem Spiele-PC** in `settings.json` im Mod-Ordner (`…/Mods/TouchDeckBridge/settings.json`,
   legt der Mod beim ersten Start an) eintragen:
   ```json
   {
     "enabled": true,
     "address": "0.0.0.0",
     "port": 34201,
     "secret": "ein-langes-geheimwort",
     "intervalMs": 500
   }
   ```
   `0.0.0.0` heißt: auf allen Netzwerkkarten. Statt `0.0.0.0` geht auch die IP einer bestimmten
   Netzwerkkarte. Ohne Geheimwort mit mindestens 12 Zeichen startet der Server dann nicht.
   Gespeicherte Änderungen übernimmt der Mod nach höchstens 2 Sekunden, auch während des Spiels.
2. **Auf dem Streaming-PC** in den Plugin-Einstellungen: **Adresse** = IP oder Rechnername des
   Spiele-PCs (z. B. `192.168.178.20` oder `gaming-pc.local`), **Port** = derselbe wie im Mod,
   **Geheimwort** = dasselbe.
3. Falls eine Firewall auf dem Spiele-PC läuft: den Port (TCP 34201) im eigenen Netz freigeben.

Die Verbindung ist **nicht verschlüsselt**: nur im eigenen Netz nutzen, nie ins offene Internet
stellen (keine Portfreigabe im Router).

## Die fertigen Seiten

Hauptseite **Timberborn** (4 × 6) mit den wichtigsten Live-Anzeigen und sieben Ordnern, angelegt wie
„Ordner hier erstellen“ im Editor (eigene Seite „Timberborn › …“ mit Zurück oben links): **Zeit**,
**Wetter**, **Biber**, **Vorräte**, **Meldungen**, **Warnungen**, **Spiel**. Kommt Timberborn in den
Vordergrund, wechselt TouchDeck einmal pro Spielstart auf die Seite „Timberborn“ (zwei Events: Linux
mit Proton und Windows; „nur beim ersten Mal“ ausschalten, wenn es jedes Mal springen soll). Benachrichtigungen
auf dem PC gibt es bewusst keine: Was wichtig ist, zeigen die Buttons rot an.

| Seite | Was drauf ist |
| --- | --- |
| Hauptseite | Status, Zyklus/Tag/Uhrzeit (an = Nacht), Tempo, Pause, Speichern, Wetter-Countdown mit Balken, Wasser und Nahrung mit „reicht … Tage“, Warnungen, Biber, Obdachlose, Arbeitslose, neueste Meldung |
| Zeit | Tempo 1–3, langsamer/schneller, Pause an/weiter, „Halten = kurz Pause“ |
| Wetter | Countdown bis zur Gefahr, Art (sobald angekündigt), Dauer, Resttage, Wasser, Nahrung |
| Biber | Bevölkerung, Zufriedenheit, Obdachlose/freie Betten, Arbeitslose/freie Stellen, Verseuchte, Kinder, Bots, Wissenschaft, die zwei größten Warnungen |
| Vorräte | Wasser, Nahrung, Wissenschaft und zwölf Waren mit Füllbalken und Trend pro Tag (an = Lager voll) |
| Meldungen | Nachrichtenverlauf: die letzten 8 Meldungen, neueste zuerst, von heute hervorgehoben |
| Warnungen | bis zu 8 aktive Warnungen mit Anzahl der Betroffenen |
| Spiel | Verbindung, Siedlung und Fraktion, Schnellspeichern, Speichern mit Zyklus und Tag, Gruß ins Spiel |

### Was die Buttons können

| Button | Tippen | Doppeltippen | Halten | Anzeige |
| --- | --- | --- | --- | --- |
| Status | Zustand neu holen | – | – | Verbindung und Zustand, grün im Spiel |
| Tempo | eine Stufe schneller | eine Stufe langsamer | zurück auf Tempo 1 | Tempo, an = läuft |
| Pause | Pause an/aus | – | – | `{TBPause}`: an = pausiert (▶️, braun) |
| Speichern | Schnellspeicher „TouchDeck-Quicksave“ | – | Spielstand „TouchDeck Zyklus ‹Z› Tag ‹T›“ | – |
| Wetter | – | – | – | „Gefahr in 5,5 Tagen“ bzw. „Dürre: noch 3 Tage“, rot ab 3 Tagen vorher |
| Wasser / Nahrung | – | – | – | Bestand und wie viele Tage er reicht, rot unter 3 Tagen |
| Warnungen | Kamera zur größten Warnung | – | – | Anzahl und größte Warnung, rot, wenn es welche gibt |
| Meldung 1–8 | Kamera zu dem Biber oder Gebäude, um das es geht | – | – | Text, Zyklus und Tag; hervorgehoben, wenn von heute |
| Warnung 1–8 | Kamera zum nächsten Betroffenen (jedes Tippen der nächste) | – | – | Text und Anzahl |
| Tempo 1–3 (Zeit) | Tempo setzen (Vorlage „Tempo setzen“) | – | – | – |
| Schneller (Zeit) | eine Stufe | – | alle 0,6 s eine Stufe | – |
| Halten = kurz Pause (Zeit) | – | – | Pause, beim **Loslassen** weiter | – |

Wetter, Biber, Vorräte, Meldungen und Warnungen holen beim Öffnen einmal den Zustand (Seiten-Logik
„Seite geöffnet“).

**Warum keine Umschalter?** Ein Umschalter merkt sich seinen Zustand in TouchDeck. Pausiert man mit
der Leertaste im Spiel, wäre er falsch. Pause, Gefahr und Warnungen zeigen deshalb den echten
Zustand des Spiels über Live-Anzeigen mit „an“-Look.

## Aktionen, Auslöser, Werte

**Aktionen** (`plugin:timberborn:…`): `pause` (umschalten/an/aus), `speed` (setzen 1–3, schneller,
langsamer), `save` (Name, leer = „TouchDeck-Quicksave“), `notification` (Kamera zu Meldung Nr. 1–8),
`alert` (Kamera zu Warnung Nr. 1–8, jedes Mal der nächste Betroffene), `message` (Text mit
Platzhaltern, normal oder Warnung), `refresh`.

**Auslöser**: `notification` (Text, Zyklus, Tag), `hazard_approaching` (Art, Name, Tage),
`hazard_started` (Art, Name, Tage), `hazard_ended`, `cycle_started` (Zyklus), `beaver_born`,
`character_died` (Name, Alter), `alert` (Text – genau wie im Warnfeld), `game_over`, `connected`,
`disconnected`. Daten im Event als `{Event.Name}`, `{Event.Tage}` usw. (englische Schlüssel wie
`{Event.Days}` gehen auch). Die Art ist `drought` oder `badtide`.

**Werte** (Namen in beiden Sprachen gleich): `TBZyklus`, `TBTag`, `TBUhrzeit`, `TBDatum`, `TBTempo`
(0–3), `TBPause` (an/aus), `TBWetter`, `TBGefahrIn`, `TBGefahrArt`, `TBGefahrRest`, `TBGefahrDauer`,
`TBBiber`, `TBErwachsene`, `TBKinder`, `TBBots`, `TBBevoelkerung`, `TBObdachlos`, `TBBettenFrei`,
`TBArbeitslos`, `TBStellenFrei`, `TBVerseucht`, `TBZufriedenheit`, `TBWissenschaft`, `TBWasser`,
`TBWasserTage`, `TBNahrung`, `TBNahrungTage`, `TBWarnungen`, `TBFraktion`, `TBSiedlung`,
`TBMeldung1`–`TBMeldung8`, `TBWarnung1`–`TBWarnung8`, `TBStatus`, `TBVerbunden`, `TBImSpiel` und für
jede Ware im Lager `TBWare_<Id>` (z. B. `TBWare_Log`, `TBWare_Berries` – die IDs stehen in den
Blueprints des Spiels).

**Live-Anzeigen**: `status`, `date`, `speed`, `weather` (Balken), `population`, `homeless`,
`unemployed`, `contaminated`, `wellbeing`, `science`, `water`, `food`, `alerts`, `good_<Id>` für
Log, Plank, Gear, TreatedPlank, MetalBlock, ScrapMetal, Biofuel, Dirt, Explosives, Paper, Book,
PunchCard (Balken), `note1`–`note8`, `alert1`–`alert8`.

## Einstellungen

| Plugin | Mod (`settings.json` im Mod-Ordner) |
| --- | --- |
| Adresse (Standard `127.0.0.1`, auch Rechnername) | `address` (Standard `127.0.0.1`, `0.0.0.0` = alle Netzwerkkarten) |
| Port (Standard `34201`) | `port` (1024–65535) |
| Geheimwort | `secret` |
| Wartezeit auf Antwort (5 s) | `enabled` (Server an/aus), `intervalMs` (Sendeintervall, 500 ms) |

## Datenschutz und Sicherheit

- Alles bleibt auf deinem PC bzw. in deinem Netz. Nichts geht ins Internet, es gibt keine Telemetrie.
- Auch mit `127.0.0.1` kann jedes Programm auf diesem PC Befehle an den Mod schicken. Wer das nicht
  möchte, trägt in Mod und Plugin dasselbe Geheimwort ein.
- Fernzugriff nur mit Geheimwort (mindestens 12 Zeichen) und nur im eigenen Netz – siehe oben.

## Tests

```
python3 tests/test_plugin.py         # Plugin gegen einen Fake-Mod (Zustand, Wetter, Vorräte, Verlauf, Befehle, Timeout …)
python3 tests/test_real_server.py    # Plugin gegen den echten C#-Server des Mods (braucht dotnet + mono)
python3 tests/check_profile.py ../../../touchdeck-rs/server/catalog   # Seiten gegen die Regeln von TouchDeck
python3 tools/make_profile.py        # erzeugt beide Seiten-Dateien (Englisch und Deutsch)
mod/TouchDeckBridge/build.sh         # Mod bauen + Protokoll-Tests (JSON, Warteschlange, TCP-Server)
python3 tests/fake_mod.py            # Fake-Mod zum Ausprobieren der Seiten ohne Spiel
```

Lizenz: MIT.
