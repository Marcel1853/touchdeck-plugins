# TouchDeck Bridge (RimWorld-Mod)

[English](README.md) · **Deutsch**

Verbindet RimWorld mit [TouchDeck](https://github.com/Marcel1853/touchdeck-plugins) (Handy oder Tablet
als Bedienfeld). Der Mod öffnet einen kleinen TCP-Server; das TouchDeck-Plugin `rimworld` verbindet
sich damit, zeigt den Zustand der Kolonie live und schickt Befehle.

- **Version:** 0.2.0 · **Spiel:** RimWorld 1.6 (gebaut und geprüft gegen 1.6.4871 rev598)
- **Braucht:** Harmony (`brrainz.harmony`), vor diesem Mod laden
- **packageId:** `Marcel171297.TouchDeckBridge` · **Autor:** Marcel171297 · **Lizenz:** MIT

## Funktionen

- **Zustand** (höchstens alle 500 ms, nur bei Änderung, sonst alle 5 s ein Herzschlag): Datum und
  Stunde, Tick, Tempo und Pause, freie Kolonisten und Gefangene der aktuellen Karte, niedrigste und
  mittlere Stimmung, eingezogene Kolonisten, Namen in der Reihenfolge der Kolonistenleiste, Silber,
  Stahl, Komponenten, Medizin, Nahrung, Wetter und Außentemperatur, Kolonie, Karte, Spielstand,
  aktuelle Forschung mit Prozent, Gefahrenstufe (wie für die Musik des Spiels: ruhig/Gefahr/groß),
  letzter Brief, die letzten 8 Briefe aus Verlauf › Nachrichten (Titel, Typ, Bedrohung, Alter).
  Im Hauptmenü nur `inGame: false`.
- **Befehle:** Pause (umschalten/an/aus), Tempo 1–4 und schneller/langsamer (4 nur im
  Entwicklermodus, wie im Spiel), Speichern (Name oder Schnellspeicher; im Permadeath-Modus immer
  der eigene Spielstand), Screenshot (Pfad in der Antwort), alle einziehen/freigeben, Kamera zu
  Kolonist Nr. N, nächster/voriger Kolonist, Kamera zum letzten Brief oder zu einem Brief aus dem Verlauf, Brief öffnen, Nachricht
  oben links einblenden, Hauptreiter öffnen/schließen, Forschung nach Name wählen.
- **Ereignisse:** jeder Brief (Titel, Typ, Text gekürzt, Bedrohung), Tod eines Kolonisten,
  Nervenzusammenbruch (Name, Art), fertige Forschung. Gleiche Ereignisse derselben Ursache innerhalb
  von 4 s werden nur einmal gemeldet.

## Einrichtung

1. Harmony im Workshop abonnieren.
2. Diesen Ordner `TouchDeckBridge` nach `…/steamapps/common/RimWorld/Mods/` kopieren.
3. Im Spiel unter **Mods** aktivieren (nach Harmony), neu starten.
4. Optional: **Optionen › Mod-Einstellungen › TouchDeck Bridge** – Server an/aus, Adresse, Port,
   Geheimwort, Sendeintervall. Änderungen gelten sofort, der Server startet selbst neu.

Danach das TouchDeck-Plugin `rimworld` einrichten (siehe [README des Plugins](../../README.de.md)).

## Bauen

```
./build.sh            # baut 1.6/Assemblies/TouchDeckBridge.dll und führt die Protokoll-Tests aus
./build.sh install    # zusätzlich nach RimWorld/Mods/TouchDeckBridge kopieren
```

Braucht das .NET-SDK (getestet mit 8.0) und Mono (für die net472-Referenzen unter
`/usr/lib/mono/4.7.2-api` und zum Ausführen der Tests). Gebaut wird gegen die DLLs der eigenen
RimWorld-Installation und Harmony aus dem Workshop – so passen die Namen genau zur gespielten
Version, und nichts muss heruntergeladen werden. Andere Pfade: `RIMWORLD_DIR=… HARMONY_DIR=… ./build.sh`.
Wer lieber ohne installiertes Spiel baut, kann die Referenzen in `TouchDeckBridge.csproj` durch das
NuGet-Paket `Krafs.Rimworld.Ref` (1.6.*) und `Lib.Harmony` (`ExcludeAssets=runtime`) ersetzen.

Aufbau des Quellcodes:

| Ordner | Inhalt |
| --- | --- |
| `Source/TouchDeckBridge/Protocol/` | JSON, Protokoll, Befehlswarteschlange, TCP-Server – ohne RimWorld-Typen |
| `Source/TouchDeckBridge/Game/` | dünne Adapter: Mod-Einstellungen, Hauptthread-Takt, Zustand, Befehle, Harmony-Patches |
| `Source/Tests/` | Tests der Protokoll-Teile (laufen unter Mono, ohne Spiel) |

## Wie der Mod mit dem Spiel umgeht

- **Hauptthread:** Der Netzwerk-Thread fasst den Spielzustand nie an. Befehle landen in einer
  Warteschlange; ein unsichtbares Unity-Objekt arbeitet sie in jedem Bild im Hauptthread ab
  (höchstens 8 pro Bild) und sammelt dort auch den Zustand ein. Das läuft auch bei Pause und im
  Hauptmenü – anders als eine `GameComponent`, die es im Hauptmenü nicht gibt (dann käme auf Befehle
  keine Antwort).
- **Keine Last pro Tick:** Zustand höchstens alle 250–5000 ms (Einstellung), nur aus vorhandenen
  Listen und Zählern (`FreeColonists`, `resourceCounter`, Kolonistenleiste). Ohne verbundenes Plugin
  wird nichts eingesammelt.
- **Harmony nur für Ereignisse:** `LetterStack.ReceiveLetter`, `Pawn.Kill`,
  `MentalStateHandler.TryStartMentalState`, `ResearchManager.FinishProject` und für den Namen des
  Spielstands `GameDataSaveLoader.SaveGame`/`LoadGame`. Jeder Patch wird einzeln angelegt; fehlt eine
  Methode in einer anderen Version, fällt nur dieses Ereignis weg (Warnung im Log).
- **Fehler** werden abgefangen und ins Log geschrieben, sie bringen das Spiel nicht zum Absturz.

## Sicherheit

- Standard ist `127.0.0.1`: nur Programme auf diesem PC erreichen den Server. **Auch das ist jedes
  Programm auf diesem PC** – wer das nicht will, setzt ein Geheimwort (Mod und Plugin gleich).
- Jede andere Adresse (z. B. `0.0.0.0` für alle Netzwerkkarten) verlangt ein Geheimwort mit
  mindestens 12 Zeichen; ohne startet der Server nicht und das Einstellungsfenster zeigt eine Warnung.
  Das Geheimwort steht im Hallo des Plugins und wird in konstanter Zeit verglichen.
- **Unverschlüsselt.** Nur im eigenen Netz nutzen, nie ins offene Internet stellen.
- Höchstens 4 Verbindungen, Zeilen über 64 KB werden verworfen, höchstens 64 wartende Befehle.

## Mehrspieler

Ein Mehrspieler-Betrieb (z. B. mit dem Mod „Multiplayer“) ist nicht Ziel. Befehle ändern das Spiel
direkt im eigenen Spiel und laufen nicht über die Synchronisation eines Mehrspieler-Mods: Pause,
Tempo, Einziehen und Forschung würden die Spiele auseinanderlaufen lassen (Desync). Nur Anzeigen,
Kamera, Screenshot und Nachrichten wären unkritisch – das ist nicht getestet.

## Bekannte Grenzen

- Tempo 4 (ultraschnell) gibt es in RimWorld nur im Entwicklermodus; sonst antwortet der Befehl mit
  einem Hinweis.
- „Speichern“ meldet „gespeichert“, sobald die Speicher-Aktion des Spiels fertig ist. Scheitert das
  Speichern im Spiel selbst (z. B. Platte voll), zeigt RimWorld seinen eigenen Fehler.
- Der Screenshot wird erst am Ende des Bildes geschrieben; der Pfad in der Antwort stimmt trotzdem.
- „Spielstand“ kennt der Mod erst, nachdem in dieser Sitzung gespeichert oder geladen wurde.
- Kolonist Nr. N folgt der Kolonistenleiste (alle Karten, auch Karawanen); Kolonisten und Stimmung
  im Zustand zählen nur die aktuelle Karte.
- Nur IPv4.

## Im Spiel prüfen (Testliste)

Was nur im Spiel läuft, ist nicht automatisch getestet. So prüfst du es (Plugin verbunden, Seite
„RimWorld“ offen):

| Schritt | Erwartet |
| --- | --- |
| Spiel starten, im **Hauptmenü** bleiben | Log: „[TouchDeck Bridge] listening on 127.0.0.1:34200“. Status-Button „Hauptmenü (kein Spiel geladen)“, Werte „–“. Pause drücken → Meldung „Kein Spiel geladen“. |
| Mod-Einstellungen öffnen | „Server läuft auf 127.0.0.1:34200, verbunden: 1“. |
| Kolonie laden | Status „läuft“, Datum, Silber, Stimmung, Forschung erscheinen innerhalb ~1 s. |
| **Leertaste im Spiel** (Pause) | Pause-Button wird braun mit ▶️, Tempo-Anzeige „pausiert“. |
| Pause-Button am Deck | Spiel pausiert/läuft weiter, Meldung am Button. |
| Tempo antippen / doppelt / halten | schneller / langsamer / 1×; bei Pause hebt Tempo die Pause auf. |
| Tempo 4× ohne Entwicklermodus | Meldung „Tempo 4 gibt es … nur im Entwicklermodus“, Tempo bleibt. |
| **Spiel pausiert**, dann Einziehen, Kolonist 1, Nachricht | Alles klappt auch bei Pause (Befehle laufen pro Bild, nicht pro Tick). |
| Einziehen antippen | Alle einziehbaren Kolonisten eingezogen, Button rot „3/3 eingezogen“; nochmal → alle frei. |
| Einen Kolonisten im Spiel von Hand freigeben | Einziehen-Button wird wieder dunkel („2/3“). |
| Kolonist 1–8 | Kamera springt und wählt aus; Namen stimmen mit der Leiste oben überein. |
| Nachricht-Button | Text erscheint oben links; „Bedrohung“ mit Warnton. |
| Speichern antippen | Ladebildschirm „Speichern“, danach „Gespeichert als TouchDeck-Quicksave“; Spielstand im Laden-Menü. |
| Screenshot | Meldung mit Pfad, Datei liegt in `~/.config/unity3d/Ludeon Studios/RimWorld by Ludeon Studios/Screenshots/`. |
| Forschung-Button | Forschungsfenster öffnet/schließt. |
| Dev-Modus › Überfall auslösen | Brief kommt; Event „raid“ → PC-Benachrichtigung; Bedrohung wird rot; Brief-Button zeigt den Titel; „Bedrohung“ antippen → Kamera zum Ort. |
| Dev-Modus › Kolonist töten | Benachrichtigung „… ist gestorben“, Kolonistenzahl sinkt. |
| Dev-Modus › Nervenzusammenbruch | Auslöser `mental_break` (z. B. im Event-Protokoll von TouchDeck). |
| Dev-Modus › Forschung abschließen | Auslöser `research_finished`, Forschungsanzeige wechselt. |
| **Spiel laden, während verbunden** | Kurz „Hauptmenü“, danach Werte des neuen Spielstands; „Spielstand“ zeigt dessen Namen; keine Fehler im Log. |
| Zurück ins Hauptmenü | Werte „–“, Verbindung bleibt („Verbunden: ja“). |
| Mod-Einstellungen: Port ändern, schließen | Log: Server neu gestartet auf dem neuen Port; Plugin verliert die Verbindung, bis dort derselbe Port steht. |
| Adresse `0.0.0.0` ohne Geheimwort | Rote Warnung im Fenster, Server läuft nicht. Mit 12+ Zeichen: läuft, gelber Hinweis. |
| Spiel beenden | Plugin: „RimWorld nicht erreichbar“, Auslöser `disconnected`. |
| Log (`Player.log`) nach allem | keine roten Fehler mit „TouchDeck Bridge“; bei Warnung „event … disabled“ fehlt nur dieses Ereignis. |
