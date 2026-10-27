# RimWorld für TouchDeck

[English](README.md) · **Deutsch**

**Erweitertes TouchDeck-Plugin** für RimWorld 1.6. Zeigt Datum, Tempo, Stimmung, Silber, Forschung,
Bedrohung und mehr live auf deinen Buttons und steuert das Spiel: Pause, Tempo 1–4, Speichern,
Screenshot, alle einziehen, Kamera zu Kolonisten oder zum letzten Brief, Nachrichten im Spiel,
Hauptreiter und Forschung. Briefe, Überfälle, Todesfälle, Nervenzusammenbrüche und fertige Forschung
lösen TouchDeck-Events aus.

Dazu gehört der RimWorld-Mod **TouchDeck Bridge** (Ordner `mod/TouchDeckBridge`, braucht Harmony).

## So funktioniert es

```
RimWorld + Mod (TCP-Server 127.0.0.1:34200) ◀──── JSON-Zeilen ────▶ Plugin (Client) ──▶ Werte, Live-Anzeigen, Auslöser
TouchDeck-Button ──▶ Plugin-Aktion ──▶ Befehl an den Mod ──▶ Antwort („Spiel pausiert“) als Meldung des Buttons
```

- Der Mod öffnet beim Spielstart einen kleinen TCP-Server, standardmäßig nur auf diesem PC
  (`127.0.0.1`). Das Plugin verbindet sich, baut die Verbindung bei Abbruch selbst wieder auf und
  bekommt den Zustand, sobald sich etwas ändert (mindestens alle 5 s ein Herzschlag).
- Befehle laufen im Spiel im Hauptthread – auch bei Pause und im Hauptmenü (dort antworten sie
  „Kein Spiel geladen“).
- Kein Tastendruck, keine Startoption, keine Einstellung in RimWorld nötig.

## Einrichtung in vier Schritten

1. **Mod installieren und aktivieren:** Harmony aus dem Steam-Workshop abonnieren. Den Ordner
   `mod/TouchDeckBridge` (oder `TouchDeckBridge_0.2.0.zip` entpackt) nach
   `…/steamapps/common/RimWorld/Mods/` legen. In RimWorld unter **Mods** „TouchDeck Bridge“ nach
   Harmony aktivieren und neu starten.
2. **Plugin laden:** In TouchDeck den erweiterten Modus einschalten (Plugins › Erweitert), dann
   Plugins › Marktplatz › **RimWorld** installieren (oder Plugins › Entwickeln › diesen Ordner
   laden). Zweimal bestätigen, weil es ein erweitertes Plugin ist.
3. **Seiten importieren:** In der Plugin-Karte oder unter „Fertige Seiten“ auf
   **RimWorld (Deutsch)** oder **RimWorld (English)** klicken – gleiche Seiten, nur die Texte
   unterscheiden sich. Nur eine davon importieren: Der Import fügt nur hinzu, er überschreibt nichts.
4. **Spiel starten** und eine Kolonie laden – fertig. Der Status-Button oben links zeigt „läuft“.

Voraussetzungen: RimWorld 1.6 mit Harmony, TouchDeck 0.12, Python 3.8 oder neuer (Linux; Windows ist eine ganz frühe Alpha und ungetestet). Keine
Pflicht-Einstellungen: Adresse `127.0.0.1`, Port `34200` und leeres Geheimwort passen zu den
Vorgaben des Mods.

## Die fertigen Seiten

Hauptseite **RimWorld** (4 × 6) mit Live-Anzeigen und vier Ordnern, angelegt wie „Ordner hier
erstellen“ im Editor (eigene Seite „RimWorld › …“ mit Zurück oben links): **Zeit**, **Kolonisten**,
**Meldungen**, **Spiel**. Kommt RimWorld in den Vordergrund, wechselt TouchDeck einmal pro
Spielstart auf die Seite „RimWorld“ (Event „RimWorld im Vordergrund“; „nur beim ersten Mal“
ausschalten, wenn es jedes Mal springen soll). Bei einem Überfall oder Tod eines Kolonisten kommt
eine Benachrichtigung auf dem PC.

### Was jeder Button kann

| Button | Tippen | Doppeltippen | Halten | Anzeige |
| --- | --- | --- | --- | --- |
| Status (Hauptseite) | – | – | – | Verbindung und Zustand, grün im Spiel |
| Datum (Hauptseite) | – | – | – | Datum und Stunde im Spiel |
| Tempo | eine Stufe schneller | eine Stufe langsamer | zurück auf 1× | Tempo, an = läuft |
| Pause | Pause an/aus | – | – | `{RWPause}`: an = pausiert (▶️, braun) |
| Speichern | Schnellspeicher „TouchDeck-Quicksave“ | – | Spielstand „TouchDeck ‹Datum› ‹Stunde›“ | – |
| Stimmung | – | – | – | niedrigste Stimmung als Balken, rot unter 25 % |
| Forschung | Forschungsfenster auf/zu | – | – | Forschung mit Balken |
| Silber | – | – | – | Silber im Lager |
| Bedrohung | Kamera zum letzten Brief | Brief öffnen | – | rot ⚔️, solange das Spiel Gefahr meldet |
| Einziehen | alle rein, wenn nicht alle drin sind, sonst alle raus | alle freigeben | alle einziehen | „2/5 eingezogen“, rot = alle eingezogen |
| Nächster | nächster Kolonist (Kamera + Auswahl) | voriger | alle 0,8 s weiter | – |
| Brief `{RWBrief}` | Kamera zum letzten Brief | Brief öffnen | – | Titel des letzten Briefs |
| Tempo 1× bis 4× (Zeit) | Tempo setzen (Vorlage „Tempo setzen“), 4× nur im Entwicklermodus | – | – | – |
| Langsamer / Schneller (Zeit) | eine Stufe | – | Schneller: alle 0,6 s eine Stufe | – |
| Pause an / Weiter (Zeit) | anhalten / weiterlaufen | – | – | – |
| Halten = kurz Pause (Zeit) | – | – | Pause, beim **Loslassen** weiter | – |
| Kolonist 1–8 (Kolonisten) | Kamera zu Kolonist Nr. (Vorlage „Kolonist springen“) | – | – | Name aus der Kolonistenleiste |
| Alle einziehen / freigeben (Kolonisten) | wie beschriftet | – | – | – |
| Arbeit, Zeitplan, Zuweisen, Tiere, Forschung, Welt, Architekt, Menü, Aufträge, Verlauf, Fraktionen | Hauptreiter auf/zu | – | – | – |
| Ereignis 1–8 (Meldungen) | Kamera dorthin, wo es passiert ist | Brief öffnen | – | die letzten 8 Briefe aus Verlauf › Nachrichten (auch weggeklickte), neueste zuerst: Titel und Alter, rot bei Bedrohung und Tod |
| Ältere: Verlauf öffnen (Meldungen) | Fenster „Verlauf“ öffnen | – | – | – |
| Schnellspeichern / Speichern mit Datum / Screenshot (Spiel) | wie beschriftet, Pfad des Screenshots als Meldung | – | – | – |
| Zustand abfragen, Verbunden (Spiel) | Zustand sofort neu holen | – | – | Verbindung |

Die Seite **Kolonisten** holt beim Öffnen einmal den Zustand (Seiten-Logik „Seite geöffnet“).

**Warum keine Umschalter?** Ein Umschalter merkt sich seinen Zustand in TouchDeck. Pausiert man
mit der Leertaste im Spiel oder zieht Kolonisten dort ein, wäre er falsch. Pause, Einziehen und
Bedrohung zeigen deshalb den echten Zustand des Spiels über Live-Anzeigen mit „an“-Look.

**Warum kein Regler fürs Tempo?** Regler in TouchDeck steuern nur Lautstärke, Mikrofon, OBS oder
einen Befehl (`store.rs`, `live.json`), keine Plugin-Werte. RimWorld hat ohnehin nur vier Stufen:
Plus/Minus und Stufen-Buttons sind genauer.

**`deck.setLook`** nutzt das Plugin nicht: Beim Import bekommen Buttons neue IDs, das Plugin könnte
sie nicht sicher finden. Die Färbung bei Gefahr kommt aus der Live-Anzeige „Bedrohung“ (an = rot).

## Aktionen, Auslöser, Werte

**Aktionen** (`plugin:rimworld:…`): `pause` (umschalten/an/aus), `speed` (setzen 1–4, schneller,
langsamer), `save` (Name, leer = Schnellspeicher; im Permadeath-Modus immer der eigene Spielstand),
`screenshot`, `draft` (umschalten/alle/keiner), `jump` (Kolonist Nr.), `cycle` (nächster/voriger),
`letter` (Kamera zum letzten Brief oder zu Ereignis Nr. 1–8 / öffnen), `message` (Text mit Platzhaltern, Art), `tab`
(Hauptreiter), `research` (Forschung nach Name wählen), `refresh`.

**Auslöser**: `letter` (Titel, Typ, Text, Bedrohung), `raid` (Brief mit großer Bedrohung),
`colonist_died` (Name), `mental_break` (Name, Art), `research_finished` (Name, Intern),
`connected`, `disconnected`. Daten im Event als `{Event.Titel}`, `{Event.Name}` usw. (englische
Schlüssel wie `{Event.Title}` gehen auch). Gleiche Ereignisse derselben Ursache innerhalb von 4 s
meldet der Mod nur einmal.

**Werte** (Namen in beiden Sprachen gleich, das Plugin setzt genau diese): `RWDatum`, `RWUhrzeit`,
`RWTempo` (0–4), `RWPause` (an/aus), `RWKolonisten`, `RWGefangene`, `RWStimmungMin`,
`RWStimmungSchnitt`, `RWEingezogen`, `RWSilber`, `RWStahl`, `RWKomponenten`, `RWMedizin`,
`RWNahrung`, `RWForschung`, `RWForschungProzent`, `RWWetter`, `RWTemperatur`, `RWKarte`,
`RWKolonie`, `RWSpielstand`, `RWBedrohung`, `RWBrief`, `RWKolonist1`–`RWKolonist8`, `RWEreignis1`–`RWEreignis8` (Ereignisse aus dem Verlauf), `RWStatus`,
`RWVerbunden` (ja/nein), `RWImSpiel` (ja/nein). Ihre Texte (z. B. „pausiert“, „ja“) folgen der
Systemsprache.

**Live-Anzeigen**: `status`, `date`, `speed`, `mood` (Balken), `research` (Balken), `silver`,
`danger`, `draft`, `event1`–`event8` (Ereignisse aus dem Verlauf; an = Bedrohung oder Tod).

## Einstellungen

| Plugin | Mod (Optionen › Mod-Einstellungen › TouchDeck Bridge) |
| --- | --- |
| Adresse (Standard `127.0.0.1`) | Adresse (Standard `127.0.0.1`, `0.0.0.0` = alle Netzwerkkarten) |
| Port (Standard `34200`) | Port (1024–65535) |
| Geheimwort | Geheimwort |
| Wartezeit auf Antwort (5 s) | Server an/aus, Sendeintervall (500 ms) |

Geänderte Mod-Einstellungen gelten sofort (der Server startet neu), ein Neustart des Spiels ist
nicht nötig.

## Datenschutz und Sicherheit

- Alles bleibt auf deinem PC: Plugin und Mod reden über `127.0.0.1`. Nichts geht ins Internet,
  es gibt keine Telemetrie.
- Auch mit `127.0.0.1` kann jedes Programm auf diesem PC Befehle an den Mod schicken. Wer das
  nicht möchte, trägt in Mod und Plugin dasselbe Geheimwort ein.
- **Fernzugriff** (Mod auf einem anderen Rechner): Adresse im Mod auf `0.0.0.0` oder die IP der
  Netzwerkkarte, im Plugin die IP des Spiele-PCs. Dann ist ein Geheimwort mit mindestens
  12 Zeichen Pflicht, sonst startet der Server nicht. Die Verbindung ist **nicht verschlüsselt**:
  nur im eigenen Netz nutzen, nie ins offene Internet stellen (keine Portfreigabe im Router).

## Tests

```
python3 tests/test_plugin.py         # Plugin gegen einen Fake-Mod (Hallo, Zustand, Befehle, Timeout, Abbruch …)
python3 tests/test_real_server.py    # Plugin gegen den echten C#-Server des Mods (braucht dotnet + mono)
python3 tests/check_profile.py ../../../touchdeck-rs/server/catalog   # Seiten gegen die Regeln von TouchDeck
python3 tools/make_profile.py        # erzeugt beide Seiten-Dateien (Englisch und Deutsch)
mod/TouchDeckBridge/build.sh         # Mod bauen + Protokoll-Tests (JSON, Warteschlange, TCP-Server)
python3 tests/fake_mod.py            # Fake-Mod zum Ausprobieren der Seiten ohne Spiel
```

Lizenz: MIT.
