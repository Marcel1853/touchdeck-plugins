# Changelog / Änderungsprotokoll

## 0.1.2 – 2026-10-28

- Fix: the mod found the game's input service only under its interface and then stopped completely –
  no values, no commands. Now it also searches the game's objects, looks again for missing services on
  the first game tick, and keeps running if one is missing (only the affected command reports it).
- Fehler behoben: Der Mod fand den Eingabedienst des Spiels nur unter seiner Schnittstelle und brach
  dann ganz ab – keine Werte, keine Befehle. Jetzt sucht er auch unter den Objekten des Spiels, sucht
  fehlende Dienste beim ersten Spieltakt noch einmal und läuft weiter, wenn einer fehlt (nur der
  betroffene Befehl meldet das).
- Fix: saving failed with the mod („Failed to create generic serializer for 'GameLink'“). The mod
  subscribed to the calendar in a way the game writes into the save. Now it checks the date on every
  game tick instead; nothing of the mod ends up in the save.
- Fehler behoben: Mit dem Mod schlug das Speichern fehl („Failed to create generic serializer for
  'GameLink'“). Der Mod hatte sich beim Kalender so angemeldet, dass das Spiel es in den Spielstand
  schreibt. Jetzt prüft er das Datum in jedem Spieltakt; vom Mod landet nichts im Spielstand.

## 0.1.1 – 2026-10-28

- Preview image (TouchDeck icon) in the game's mod manager; verified for game version 0.8.7d.
- Vorschaubild (TouchDeck-Icon) in der Mod-Verwaltung des Spiels; für Spielversion 0.8.7d verifiziert.

## 0.1.0 – 2026-10-28

- First version for Captain of Industry 0.8: TCP server (default 127.0.0.1:34202, settings in
  `settings.json`, applied without restart), state with date, speed, power, computing, unity,
  workers, population, homeless, food in months, disease, research, products with trend (pinned
  first), active alerts and a history of new alerts and messages. Commands: pause, speed, save,
  camera to an alert or history entry.
- Erste Version für Captain of Industry 0.8: TCP-Server (Standard 127.0.0.1:34202, Einstellungen in
  `settings.json`, gelten ohne Neustart), Zustand mit Datum, Tempo, Strom, Rechenleistung, Einheit,
  Arbeitern, Einwohnern, Obdachlosen, Nahrung in Monaten, Krankheit, Forschung, Waren mit Trend
  (angeheftete zuerst), aktiven Meldungen und einem Verlauf neuer Meldungen und Nachrichten. Befehle:
  Pause, Tempo, Speichern, Kamera zu Meldung oder Verlaufseintrag.
