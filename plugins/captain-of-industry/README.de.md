# Captain of Industry für TouchDeck

[English](README.md) · **Deutsch**

**Erweitertes TouchDeck-Plugin** für Captain of Industry 0.8. Zeigt live auf deinen Buttons, was man
im Spiel leicht übersieht: ob der Strom reicht, ob Arbeiter fehlen, wie viele Monate die Nahrung noch
reicht, ob Einheit verloren geht, ob die Forschung stillsteht, welche Waren voll oder knapp werden,
alle aktiven Meldungen (kein Treibstoff, Lager voll …) und einen Verlauf der letzten Meldungen und
Nachrichten – auch der, die im Spiel schon wieder verschwunden sind. Und es steuert das Spiel: Pause,
Tempo, Speichern, Kamera zu Meldungen. Meldungen, Nachrichten, Strommangel, Hunger, Krankheit,
fertige Forschung und das neue Jahr lösen TouchDeck-Events aus.

Dazu gehört der Mod **TouchDeck Bridge** (Ordner `mod/TouchDeckBridge`). Er braucht keine anderen
Mods und fügt dem Spiel keine Inhalte hinzu.

## So funktioniert es

```
Captain of Industry + Mod (TCP-Server 127.0.0.1:34202) ◀── JSON-Zeilen ──▶ Plugin (Client) ──▶ Werte, Live-Anzeigen, Auslöser
TouchDeck-Button ──▶ Plugin-Aktion ──▶ Befehl an den Mod ──▶ Antwort („Spiel pausiert“) als Meldung des Buttons
```

- Captain of Industry lädt Mods erst mit einem Spielstand. Der Mod startet seinen TCP-Server beim
  ersten Laden und lässt ihn bis zum Beenden des Spiels laufen (im Hauptmenü meldet er „kein Spiel
  geladen“). Standardmäßig ist er nur auf diesem PC erreichbar (`127.0.0.1`).
- Den Zustand liest der Mod im Sync-Schritt des Spiels – dort, wo auch die Anzeigen des Spiels lesen.
  Befehle gehen als ganz normale Eingaben ins Spiel, wie die Knöpfe der Oberfläche.
- Alle Zahlen stammen aus dem Spiel selbst: Strom und Rechenleistung, Einheit, Arbeiter, Siedlungen,
  Nahrung in Monaten, Krankheit, Forschung, Warenstatistik (Herstellung minus Verbrauch im letzten
  Monat), Meldungsfeld rechts.

## Einrichtung in vier Schritten

1. **Plugin laden:** In TouchDeck den erweiterten Modus einschalten (Plugins › Erweitert), dann
   Plugins › Marktplatz › **Captain of Industry** installieren (oder Plugins › Entwickeln › diesen
   Ordner laden). Zweimal bestätigen, weil es ein erweitertes Plugin ist.
2. **Mod installieren:** In der Plugin-Karte auf **„🧩 Mod installieren“** klicken – TouchDeck findet
   den Mod-Ordner selbst (Windows und Linux mit Proton). Von Hand: `TouchDeckBridge_0.1.3.zip` in den
   Ordner `Mods` von Captain of Industry entpacken:
   - Windows: `%APPDATA%\Captain of Industry\Mods\`
   - Linux (Steam mit Proton):
     `~/.local/share/Steam/steamapps/compatdata/1594320/pfx/drive_c/users/steamuser/AppData/Roaming/Captain of Industry/Mods/`

   Danach liegt dort ein Ordner `TouchDeckBridge` mit `manifest.json` und `TouchDeckBridge.dll`.
   Quellcode und Anleitung des Mods:
   [github.com/Marcel1853/touchdeck-plugins › plugins/captain-of-industry/mod](https://github.com/Marcel1853/touchdeck-plugins/tree/main/plugins/captain-of-industry/mod/TouchDeckBridge)
3. **Seiten importieren:** In der Plugin-Karte oder unter „Fertige Seiten“ auf
   **Captain of Industry (Deutsch)** oder **Captain of Industry (English)** klicken – gleiche Seiten,
   nur die Texte unterscheiden sich. Nur eine davon importieren: Der Import fügt nur hinzu.
4. **Spielstand laden** und dabei unter „Mods“ **TouchDeck Bridge** einschalten (geht auch bei
   bestehenden Spielständen). Der Status-Button oben links zeigt dann „läuft“.

Voraussetzungen: Captain of Industry 0.8 (getestet mit 0.8.7), TouchDeck 0.12, Python 3.8 oder
neuer (Linux; Windows ist eine ganz frühe Alpha und ungetestet). Keine Pflicht-Einstellungen:
Adresse `127.0.0.1`, Port `34202` und leeres Geheimwort passen zu den Vorgaben des Mods.

## Zwei PCs: Streaming-PC und Spiele-PC

Läuft TouchDeck auf einem anderen Rechner als das Spiel (zum Beispiel auf dem Streaming-PC),
geht das so:

1. **Auf dem Spiele-PC** in `settings.json` im Mod-Ordner (`…/Mods/TouchDeckBridge/settings.json`,
   legt der Mod beim ersten Laden eines Spielstands an) eintragen:
   ```json
   {
     "enabled": true,
     "address": "0.0.0.0",
     "port": 34202,
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
3. Falls eine Firewall auf dem Spiele-PC läuft: den Port (TCP 34202) im eigenen Netz freigeben.

Die Verbindung ist **nicht verschlüsselt**: nur im eigenen Netz nutzen, nie ins offene Internet
stellen (keine Portfreigabe im Router).

## Die fertigen Seiten

Hauptseite **Captain of Industry** (4 × 6) mit den wichtigsten Live-Anzeigen und sechs Ordnern,
angelegt wie „Ordner hier erstellen“ im Editor (eigene Seite „Captain of Industry › …“ mit Zurück
oben links): **Meldungen**, **Verlauf**, **Strom**, **Bevölkerung**, **Waren**, **Spiel**. Kommt das
Spiel in den Vordergrund, wechselt TouchDeck einmal pro Spielstart auf die Hauptseite (zwei Events:
Linux mit Proton und Windows). Benachrichtigungen auf dem PC gibt es bewusst keine: Was wichtig ist,
zeigen die Buttons **rot** an.

| Seite | Was drauf ist |
| --- | --- |
| Hauptseite | Status, Jahr und Monat, Tempo, Pause, Speichern, Strom mit Auslastungsbalken, Arbeiter, Nahrung, Meldungen, Einheit, Forschung, neuester Verlaufseintrag |
| Meldungen | bis zu 8 aktive Meldungen, kritische zuerst, mit Anzahl der Betroffenen |
| Verlauf | die letzten 8 neuen Meldungen und Nachrichten (Forschung fertig, Flüchtlinge …), neueste zuerst |
| Strom | Strom und Rechenleistung als Graph (Bedarf und Kapazität als zwei Linien, letzte 10 Minuten), Einheit als Graph (letzte Stunde) mit Änderung pro Monat, Bedarf, Forschung |
| Bevölkerung | Einwohner, Obdachlose, freie Wohnplätze, Arbeiter, Nahrung, Hunger, Krankheit, die zwei wichtigsten Meldungen |
| Waren | 8 Waren mit Verlauf des Bestands als Graph (letzte halbe Stunde) und Trend pro Monat: zuerst die im Spiel angehefteten (📌), dann die mit dem größten Bestand |
| Spiel | Verbindung, Tempo 1–3, langsamer/schneller, Pause an/weiter, „Halten = kurz Pause“, Schnellspeichern, Speichern mit Jahr und Monat |

### Was rot wird

| Anzeige | Rot, wenn … |
| --- | --- |
| Strom | der Bedarf größer ist als die Erzeugung |
| Rechenleistung | der Bedarf größer ist als die Kapazität |
| Einheit | sie im letzten Monat abgenommen hat |
| Arbeiter | Arbeiter fehlen |
| Bevölkerung | jemand obdachlos ist |
| Nahrung | sie für weniger als 3 Monate reicht oder Leute hungern |
| Krankheit | eine Krankheit umgeht |
| Meldungen | es aktive Warnungen oder kritische Meldungen gibt (grüne Erfolgsmeldungen nicht) |
| Ware 1–8 | das Lager voll ist oder die Ware beim jetzigen Verbrauch in weniger als 2 Monaten leer ist |
| Verlauf 1–8 | (hervorgehoben) der Eintrag aus diesem Monat stammt |
| Forschung | (blau) Forschung läuft; „Keine Forschung aktiv“ heißt: Labor steht still |

### Was die Buttons können

| Button | Tippen | Doppeltippen | Halten |
| --- | --- | --- | --- |
| Status | Zustand neu holen | – | – |
| Tempo | eine Stufe schneller | eine Stufe langsamer | zurück auf Tempo 1 |
| Pause | Pause an/aus (`{COIPause}` zeigt den echten Zustand) | – | – |
| Speichern | Schnellspeicher „TouchDeck-Quicksave“ | – | Spielstand „TouchDeck Jahr ‹J› Monat ‹M›“ |
| Meldungen | Kamera zur wichtigsten Meldung | – | – |
| Meldung 1–8 | Kamera zum nächsten Betroffenen (jedes Tippen der nächste) | – | – |
| Verlauf 1–8 | Kamera dorthin, wenn die Meldung einen Ort hat | – | – |
| Schneller (Spiel) | eine Stufe | – | alle 0,6 s eine Stufe |
| Halten = kurz Pause (Spiel) | – | – | Pause, beim **Loslassen** weiter |

Meldungen, Verlauf, Strom, Bevölkerung und Waren holen beim Öffnen einmal den Zustand.

## Aktionen, Auslöser, Werte

**Aktionen** (`plugin:captain-of-industry:…`): `pause` (umschalten/an/aus), `speed` (Stufe setzen,
schneller, langsamer – Stufen wie die Tempo-Knöpfe im Spiel), `save` (Name, leer =
„TouchDeck-Quicksave“), `alert` (Kamera zu Meldung Nr. 1–8, jedes Mal der nächste Betroffene),
`history` (Kamera zu Verlauf Nr. 1–8), `refresh`.

**Auslöser**: `notification` (Text, Art: `critical`/`warning`/`success`), `message` (Text, Art:
`message`, `research`, `refugees`, `explored`, `battle`), `research_finished` (Name), `power_short`
(Kapazitaet, Bedarf), `food_low` (Monate), `starving` (Monate), `disease` (Name), `new_year` (Jahr),
`game_over` (Text), `connected`, `disconnected`. Daten im Event als `{Event.Text}`, `{Event.Name}`
usw. (englische Schlüssel wie `{Event.Year}` gehen auch).

**Werte** (Namen in beiden Sprachen gleich): `COIJahr`, `COIMonat`, `COIDatum`, `COITempo`,
`COIPause`, `COIStrom`, `COIStromBedarf`, `COIStromKapazitaet` (kW), `COIRechnen`,
`COIRechnenKapazitaet` (TFLOPS), `COIEinheit`, `COIEinheitMonat`, `COIArbeiterFrei` (negativ = so
viele fehlen), `COIEinwohner`, `COIObdachlos`, `COIWohnraumFrei`, `COINahrungMonate`, `COIHunger`,
`COIKrankheit`, `COIForschung`, `COIForschungProzent`, `COIWarnungen`, `COIUngelesen`,
`COIWarnung1`–`COIWarnung8`, `COIVerlauf1`–`COIVerlauf8`, `COIStatus`, `COIVerbunden`, `COIImSpiel`
und für jede Ware im Lager `COIWare_<Id>` (z. B. `COIWare_IronOre`, `COIWare_Diesel`).

**Live-Anzeigen**: `status`, `date`, `speed` (Balken), `power` (Balken), `computing` (Balken),
`unity` (Balken), `workers`, `population`, `food` (Balken), `health`, `research` (Balken), `alerts`,
`good1`–`good8` (Balken), `note1`–`note8`, `alert1`–`alert8`.

## Einstellungen

| Plugin | Mod (`settings.json` im Mod-Ordner) |
| --- | --- |
| Adresse (Standard `127.0.0.1`, auch Rechnername) | `address` (Standard `127.0.0.1`, `0.0.0.0` = alle Netzwerkkarten) |
| Port (Standard `34202`) | `port` (1024–65535) |
| Geheimwort | `secret` |
| Wartezeit auf Antwort (5 s) | `enabled` (Server an/aus), `intervalMs` (Sendeintervall, 500 ms) |

Warum eine eigene Datei und nicht die Mod-Einstellungen im Spiel? Die speichert Captain of Industry
im Spielstand – Adresse und Port gehören aber zum PC, nicht zum Spielstand.

## Datenschutz und Sicherheit

- Alles bleibt auf deinem PC bzw. in deinem Netz. Nichts geht ins Internet, es gibt keine Telemetrie.
- Auch mit `127.0.0.1` kann jedes Programm auf diesem PC Befehle an den Mod schicken. Wer das nicht
  möchte, trägt in Mod und Plugin dasselbe Geheimwort ein.
- Fernzugriff nur mit Geheimwort (mindestens 12 Zeichen) und nur im eigenen Netz – siehe oben.

## Tests

```
python3 tests/test_plugin.py         # Plugin gegen einen Fake-Mod (Zustand, Strom, Waren, Meldungen, Verlauf, Befehle, Timeout …)
python3 tests/test_real_server.py    # Plugin gegen den echten C#-Server des Mods (braucht dotnet + mono)
python3 tests/check_profile.py ../../../touchdeck-rs/server/catalog   # Seiten gegen die Regeln von TouchDeck
python3 tools/make_profile.py        # erzeugt beide Seiten-Dateien (Englisch und Deutsch)
mod/TouchDeckBridge/build.sh         # Mod bauen + Protokoll-Tests + ZIP
python3 tests/fake_mod.py            # Fake-Mod zum Ausprobieren der Seiten ohne Spiel
```

Lizenz: MIT.
