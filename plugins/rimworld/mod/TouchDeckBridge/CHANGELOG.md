# Changelog

## 0.2.0 – 2026-10-26

- Zustand enthält die letzten 8 Briefe aus „Verlauf › Nachrichten“ (auch weggeklickte):
  ID, Titel, Typ, Bedrohung und Alter in der Sprache des Spiels.
- Befehl `letter` mit `id`: Kamera zu einem Brief aus dem Verlauf oder ihn öffnen.
- Plugin 0.2.0: Seite „Meldungen“ zeigt diese Ereignisse (rot bei Bedrohung und Tod) statt der
  Schnellnachrichten; Vorlage „Nachricht senden“ entfernt (die Aktion „Nachricht im Spiel zeigen“
  gibt es weiterhin).

## 0.1.0 – 2026-10-25

- JSON-Serialisierer und -Parser ohne fremdes Paket (Strings, Zahlen, Booleans, Objekte, Listen),
  mit Tests für Anführungszeichen, Umlaute, Zeilenumbrüche, Steuerzeichen und kaputte Eingaben.
- Protokoll Version 1: Hallo mit Geheimwort, Willkommen/Ablehnung, Zustand nur bei Änderung,
  Herzschlag alle 5 s, Ereignisse sofort, Befehle mit `id` und Antwort `ack` (`ok`, `code`, `args`).
- TCP-Server in eigenen Threads: höchstens 4 Verbindungen, Zeilen bis 64 KB, Befehlswarteschlange
  mit 64 Plätzen; Fernzugriff nur mit Geheimwort (mindestens 12 Zeichen).
- Mod-Einstellungen: Server an/aus, Adresse, Port, Geheimwort, Sendeintervall; Server startet bei
  Änderung selbst neu, ungültige Eingaben fallen auf den Standard zurück (Meldung im Log).
- Hauptthread-Takt über ein unsichtbares Unity-Objekt: Befehle und Zustand auch bei Pause und im
  Hauptmenü („Kein Spiel geladen“).
- Zustand: Datum, Stunde, Tempo, Pause, Kolonisten, Gefangene, Stimmung (niedrigste, Schnitt),
  Eingezogene, Namen der Kolonistenleiste, Silber, Stahl, Komponenten, Medizin, Nahrung, Wetter,
  Temperatur, Kolonie, Karte, Spielstand, Forschung mit Prozent, Gefahrenstufe, letzter Brief.
- Befehle: Pause, Tempo (setzen, schneller, langsamer), Speichern, Screenshot, Einziehen,
  Kamera zu Kolonist Nr., nächster/voriger Kolonist, letzter Brief (Kamera/öffnen), Nachricht,
  Hauptreiter, Forschung wählen.
- Ereignisse über einzeln abgesicherte Harmony-Patches: Brief, Tod eines Kolonisten,
  Nervenzusammenbruch, Forschung fertig; doppelte Meldungen innerhalb von 4 s unterdrückt.
- Übersetzungen Deutsch und Englisch für das Einstellungsfenster.
