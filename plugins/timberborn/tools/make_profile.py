#!/usr/bin/env python3
"""Erzeugt die fertigen TouchDeck-Seiten für das Plugin „Timberborn“ auf Englisch und Deutsch:
„Timberborn (English).tdprofile“ und „Timberborn (Deutsch).tdprofile“ (gleicher Aufbau, nur die Texte unterscheiden sich).

Aufruf:  python3 tools/make_profile.py
Import:  TouchDeck › Seitenliste › „⋯“ › Profil importieren (oder „Fertige Seiten“ in der Plugin-Karte).
Format (touchdeck-profile, Version 1): touchdeck-rs/server/src/core/profiles.rs und store.rs.

Aufbau: Hauptseite „Timberborn“ mit Live-Anzeigen und sieben Ordnern (Zeit, Wetter, Biber, Vorräte, Meldungen,
Warnungen, Spiel), angelegt wie „Ordner hier erstellen“ im Editor (createFolder in web/editor/js/views/pages.js):
eigene Seite „Timberborn › …“ mit gleichem Raster und Zurück-Button oben links, auf der Hauptseite ein 📁-Button.
Was das Spiel weiß (Pause, Gefahr, Obdachlose …), zeigen Live-Anzeigen mit „an“-Look statt Umschalter,
die mit dem Spiel auseinanderlaufen könnten.
"""
import json
import os
import zipfile

PLUGIN = "plugin:timberborn"
# Fensterklasse: unter Proton „steam_app_1062090“, unter Windows das Programm „Timberborn“ (Vergleich: enthält, ohne Groß/klein)
WINDOWS = {"proton": "steam_app_1062090", "native": "timberborn"}
ROWS, COLS = 4, 6                 # Hauptseite und alle Ordner: gleiche Rasterform wie createFolder

PAGE_MAIN = "p_timberborn"
PAGES = {"zeit": "p_timberborn_zeit", "wetter": "p_timberborn_wetter", "biber": "p_timberborn_biber",
         "vorraete": "p_timberborn_vorraete", "meldungen": "p_timberborn_meldungen",
         "warnungen": "p_timberborn_warnungen", "spiel": "p_timberborn_spiel"}
FLOW_SPEED = "f_timberborn_tempo"
HISTORY = 8
ALERTS = 8
# Waren mit eigener Live-Anzeige (wie GOOD_LIVES in plugin.py): Id, Symbol, Deutsch, Englisch
GOODS = [("Log", "🪵", "Rohholz", "Logs"), ("Plank", "🪚", "Bretter", "Planks"), ("Gear", "⚙️", "Zahnräder", "Gears"),
         ("TreatedPlank", "🟫", "Behandelte Bretter", "Treated planks"), ("MetalBlock", "🔩", "Metallblöcke", "Metal blocks"),
         ("ScrapMetal", "🧲", "Schrott", "Scrap metal"), ("Biofuel", "🛢️", "Biokraftstoff", "Biofuel"),
         ("Dirt", "🟤", "Erde", "Dirt"), ("Explosives", "🧨", "Sprengstoff", "Explosives"), ("Paper", "📄", "Papier", "Paper"),
         ("Book", "📚", "Bücher", "Books"), ("PunchCard", "🎫", "Lochkarten", "Punch cards")]

COLOR = "#2b2f3a"
COLOR_GAME = "#5a4128"     # Holzbraun
COLOR_FOLDER = "#3a3f4b"   # wie createFolder
COLOR_LIVE = "#1f3a2f"
COLOR_ON = "#2f6f4f"
COLOR_DANGER = "#c0392b"
COLOR_WATER = "#1f4560"
COLOR_BEAVER = "#4a3a2a"

_ids = {"n": 0}
_lang = {"de": True}


def L(de, en):
    """Sichtbarer Text in der Sprache des gerade erzeugten Profils."""
    return de if _lang["de"] else en


def inp(name):
    """Platzhalter für eine Eingabe der Vorlage: {Eingabe.X} bzw. {Input.X} (actions.rs kennt beide)."""
    return "{" + L("Eingabe", "Input") + "." + name + "}"


def action(type_, **params):
    return {"id": "", "type": type_, "enabled": True, "params": params}


def comment(text):
    return action("comment", text=text)


def tb(aid, **params):
    """Aktion des Plugins: plugin:timberborn:<id>."""
    return action(f"{PLUGIN}:{aid}", **params)


def flow(fid, **inputs):
    """Vorlage ausführen; Eingaben als „in:<Name>“ (actions.rs, run_flow)."""
    return action("run_flow", flow=fid, times=1, **{f"in:{k}": str(v) for k, v in inputs.items()})


def button(row, col, title, actions=None, *, icon="", color=COLOR, span=1, rows=1, live=None, color_on=None,
           hold=None, hold_repeat=0, release=None, double=None, font=13, pos="bottom", title_on=None, icon_on=None,
           events=None, confirm=False):
    _ids["n"] += 1
    mode = "press"
    if not (actions or hold or release or double):
        mode = "display"   # reine Anzeige: kein Antippen, keine Drück-Animation
    b = {
        "id": f"b_timberborn_{_ids['n']}",
        "row": row, "col": col, "rowSpan": rows, "colSpan": span,
        "title": title,
        "icon": {"type": "emoji", "value": icon},
        "color": color,
        "titlePos": pos,
        "fontSize": font,
        "mode": mode,
        "actions": actions or [],
        "holdActions": hold or [],
        "releaseActions": release or [],
        "doubleActions": double or [],
        "holdRepeat": hold_repeat,
        "events": events or [],
    }
    if color_on:
        b["colorOn"] = color_on
    if title_on:
        b["titleOn"] = title_on
    if icon_on:
        b["iconOn"] = {"type": "emoji", "value": icon_on}
    if confirm:
        b["confirm"] = True
    if live:
        b["live"] = live
    return b


def plugin_live(lid, bar=False):
    return {"source": f"{PLUGIN}:{lid}", "command": "", "variable": "", "bar": bar}


def value_live(name):
    return {"source": "variable", "command": "", "variable": name, "bar": False}


def page(pid, name, buttons, events=None):
    # folder: Ordner in der Seitenliste (eigene Gruppe „Timberborn“); ratioW/ratioH wie createFolder
    return {"id": pid, "name": name, "rows": ROWS, "cols": COLS, "layout": "grid", "folder": "Timberborn",
            "background": "#141a12", "ratioW": 16, "ratioH": 10, "colSizes": [], "rowSizes": [],
            "buttons": buttons, "events": events or []}


def sub(de, en):
    return L(f"Timberborn › {de}", f"Timberborn › {en}")


def back():
    # genau wie createFolder: Zeile 0, Spalte 0, ⬅️, #3a3f4b, go_page __back
    return button(0, 0, L("Zurück", "Back"), [action("go_page", page="__back")], icon="⬅️", color=COLOR_FOLDER)


def folder(row, col, title, pid):
    # wie createFolder: 📁 mit dem Ordnernamen, Aktion go_page auf die Unterseite
    return button(row, col, title, [action("go_page", page=pid)], icon="📁", color=COLOR_FOLDER)


def page_opened(*actions):
    """Logik der Seite: „Seite geöffnet“ (page_view ohne Seitenwahl = diese Seite, events.rs)."""
    return [{"id": f"pe_timberborn_{_ids['n']}", "enabled": True,
             "trigger": {"type": "page_view", "params": {"page": "", "state": "open"}}, "actions": list(actions)}]


def refresh_on_open():
    return page_opened(comment(L("Beim Öffnen den aktuellen Stand aus dem Spiel holen.",
                                 "When opened, fetch the current state from the game.")), tb("refresh"))


# ---------------------------------------------------------------- wiederkehrende Buttons

def status_button(row, col, span=1):
    return button(row, col, "", [tb("refresh")], icon="🦫", span=span, live=plugin_live("status"), color=COLOR_LIVE,
                  color_on=COLOR_ON, font=11)


def date_button(row, col, span=2):
    # „an“ = Nacht (Biber schlafen)
    return button(row, col, "", [], icon="📅", icon_on="🌙", span=span, live=plugin_live("date"), font=12,
                  color=COLOR_LIVE, color_on="#22304f")


def pause_button(row, col):
    # Zustand aus dem Spiel ({TBPause} = an/aus) statt Umschalter: Pause per Leertaste im Spiel bleibt richtig
    return button(row, col, "Pause", [tb("pause", op="toggle")], icon="⏸️", icon_on="▶️", title_on=L("Pausiert", "Paused"),
                  live=value_live("TBPause"), color=COLOR_GAME, color_on="#9e6b2f")


def speed_button(row, col, span=1):
    # Tippen = schneller, doppelt = langsamer, halten = zurück auf Tempo 1
    return button(row, col, L("Tempo", "Speed"), [tb("speed", op="up")], icon="⏩", span=span, live=plugin_live("speed"),
                  color=COLOR_GAME, color_on=COLOR_ON, double=[tb("speed", op="down")],
                  hold=[flow(FLOW_SPEED, **{L("Stufe", "Speed"): 1})])


def save_button(row, col):
    # Tippen = Schnellspeicher, halten = eigener Spielstand mit Zyklus und Tag im Namen
    return button(row, col, L("Speichern", "Save"), [tb("save", name="")], icon="💾", color=COLOR_GAME,
                  hold=[tb("save", name=L("TouchDeck Zyklus {TBZyklus} Tag {TBTag}", "TouchDeck cycle {TBZyklus} day {TBTag}"))])


def weather_button(row, col, span=2):
    # Balken = Rest der ruhigen Zeit bzw. der Gefahr; rot, sobald die Gefahr angekündigt ist oder läuft
    return button(row, col, "", [], icon="🌤️", icon_on="☀️", span=span, live=plugin_live("weather", bar=True),
                  color=COLOR_LIVE, color_on=COLOR_DANGER, font=12)


def water_button(row, col, span=1):
    return button(row, col, L("Wasser", "Water"), [], icon="💧", span=span, live=plugin_live("water"), color=COLOR_WATER,
                  color_on=COLOR_DANGER, font=12)


def food_button(row, col, span=1):
    return button(row, col, L("Nahrung", "Food"), [], icon="🫐", span=span, live=plugin_live("food"), color=COLOR_LIVE,
                  color_on=COLOR_DANGER, font=12)


def alerts_button(row, col, span=2):
    # Tippen = Kamera zur größten Warnung (jedes Tippen der nächste Betroffene)
    return button(row, col, "", [tb("alert", n=1)], icon="✅", icon_on="⚠️", span=span, live=plugin_live("alerts"),
                  color=COLOR_LIVE, color_on=COLOR_DANGER, font=11)


def note_button(row, col, n, span=2):
    # Tippen = Kamera zu dem, was die Meldung betrifft; „an“ = von heute
    return button(row, col, "", [tb("notification", n=n)], icon="📜", span=span, live=plugin_live(f"note{n}"),
                  color=COLOR, color_on="#7a5a1f", font=10)


def alert_button(row, col, n, span=2):
    return button(row, col, "", [tb("alert", n=n)], icon="⚠️", span=span, live=plugin_live(f"alert{n}"),
                  color=COLOR, color_on=COLOR_DANGER, font=11)


def beaver_live(row, col, lid, icon, span=2):
    return button(row, col, "", [], icon=icon, span=span, live=plugin_live(lid), color=COLOR_BEAVER,
                  color_on=COLOR_DANGER, font=12)


def hint(row, col, text, span=2):
    return button(row, col, text, [], span=span, font=10, color=COLOR_FOLDER)


# ---------------------------------------------------------------- Seiten

def main_page():
    return page(PAGE_MAIN, "Timberborn", [
        status_button(0, 0),
        date_button(0, 1),
        speed_button(0, 3),
        pause_button(0, 4),
        save_button(0, 5),
        weather_button(1, 0),
        water_button(1, 2),
        food_button(1, 3),
        alerts_button(1, 4),
        folder(2, 0, L("Zeit", "Time"), PAGES["zeit"]),
        folder(2, 1, L("Wetter", "Weather"), PAGES["wetter"]),
        folder(2, 2, L("Biber", "Beavers"), PAGES["biber"]),
        folder(2, 3, L("Vorräte", "Supplies"), PAGES["vorraete"]),
        folder(2, 4, L("Meldungen", "Notifications"), PAGES["meldungen"]),
        folder(2, 5, L("Warnungen", "Alerts"), PAGES["warnungen"]),
        beaver_live(3, 0, "population", "🦫"),
        beaver_live(3, 2, "homeless", "🏚️", span=1),
        beaver_live(3, 3, "unemployed", "🛠️", span=1),
        note_button(3, 4, 1, span=1),
        folder(3, 5, L("Spiel", "Game"), PAGES["spiel"]),
    ])


def time_page():
    buttons = [
        back(),
        pause_button(0, 1),
        speed_button(0, 2),
        date_button(0, 3),
        save_button(0, 5),
    ]
    for i, (icon, label) in enumerate([("▶️", L("Tempo 1\n×1", "Speed 1\n×1")), ("⏩", L("Tempo 2\n×3", "Speed 2\n×3")),
                                       ("⏭️", L("Tempo 3\n×7", "Speed 3\n×7"))]):
        buttons.append(button(1, i, label, [flow(FLOW_SPEED, **{L("Stufe", "Speed"): i + 1})], icon=icon,
                              color=COLOR_GAME, font=12))
    buttons += [
        button(1, 3, L("Langsamer", "Slower"), [tb("speed", op="down")], icon="🐢", color=COLOR_GAME),
        # halten = schrittweise schneller (alle 0,6 s eine Stufe)
        button(1, 4, L("Schneller", "Faster"), [tb("speed", op="up")], icon="🐇", color=COLOR_GAME,
               hold=[tb("speed", op="up")], hold_repeat=600),
        button(1, 5, L("Pause an", "Pause"), [tb("pause", op="on")], icon="⏸️", color=COLOR_GAME),
        button(2, 0, L("Weiter", "Resume"), [tb("pause", op="off")], icon="▶️", color=COLOR_GAME),
        # „Kurz anhalten“: solange gedrückt Pause, beim Loslassen geht es weiter
        button(2, 1, L("Halten =\nkurz Pause", "Hold =\nshort pause"), [], icon="✋", color=COLOR_GAME, font=11,
               hold=[tb("pause", op="on")], release=[tb("pause", op="off")]),
        button(2, 2, "", [], icon="⏩", span=4, live=plugin_live("speed"), color=COLOR_LIVE, color_on=COLOR_ON),
        weather_button(3, 0, span=3),
        water_button(3, 3),
        food_button(3, 4),
        button(3, 5, "{TBDatum}\n{TBUhrzeit}", [], icon="🕒", font=10),
    ]
    return page(PAGES["zeit"], sub("Zeit", "Time"), buttons)


def weather_page():
    """Wann kommt die nächste Dürre oder Faulwasserflut, wie lange dauert sie? Die Art verrät das Plugin – wie das
    Spiel – erst, wenn sie angekündigt ist (3 Tage vorher)."""
    return page(PAGES["wetter"], sub("Wetter", "Weather"), [
        back(),
        weather_button(0, 1, span=3),
        button(0, 4, "{TBWetter}", [], icon="🌦️", span=2, font=12),
        button(1, 0, L("Gefahr in\n{TBGefahrIn} Tagen", "Hazard in\n{TBGefahrIn} days"), [], icon="⏳", span=2, font=12),
        button(1, 2, L("Nächste Gefahr\n{TBGefahrArt}", "Next hazard\n{TBGefahrArt}"), [], icon="❓", span=2, font=12),
        button(1, 4, L("Dauer\n{TBGefahrDauer} Tage", "Duration\n{TBGefahrDauer} days"), [], icon="📏", span=2, font=12),
        water_button(2, 0, span=2),
        food_button(2, 2, span=2),
        button(2, 4, L("Gefahr noch\n{TBGefahrRest} Tage", "Hazard left\n{TBGefahrRest} days"), [], icon="⌛", span=2, font=12),
        date_button(3, 0, span=3),
        speed_button(3, 3),
        pause_button(3, 4),
        button(3, 5, L("Abfragen", "Refresh"), [tb("refresh")], icon="🔄", color=COLOR_FOLDER),
    ], events=refresh_on_open())


def beavers_page():
    return page(PAGES["biber"], sub("Biber", "Beavers"), [
        back(),
        beaver_live(0, 1, "population", "🦫", span=3),
        beaver_live(0, 4, "wellbeing", "😊"),
        beaver_live(1, 0, "homeless", "🏚️"),
        beaver_live(1, 2, "unemployed", "🛠️"),
        beaver_live(1, 4, "contaminated", "☣️"),
        button(2, 0, L("{TBErwachsene}\nErwachsene", "{TBErwachsene}\nadults"), [], icon="🦫", font=11),
        button(2, 1, L("{TBKinder}\nKinder", "{TBKinder}\nkids"), [], icon="🍼", font=11),
        button(2, 2, L("{TBBots}\nBots", "{TBBots}\nbots"), [], icon="🤖", font=11),
        button(2, 3, L("{TBBettenFrei}\nBetten frei", "{TBBettenFrei}\nbeds free"), [], icon="🛏️", font=11),
        button(2, 4, L("{TBStellenFrei}\nStellen frei", "{TBStellenFrei}\njobs free"), [], icon="🏭", font=11),
        button(2, 5, "", [], icon="🔬", live=plugin_live("science"), color=COLOR_LIVE, font=11),
        alert_button(3, 0, 1, span=3),
        alert_button(3, 3, 2, span=3),
    ], events=refresh_on_open())


def supplies_page():
    buttons = [
        back(),
        water_button(0, 1, span=2),
        food_button(0, 3, span=2),
        button(0, 5, "", [], icon="🔬", live=plugin_live("science"), color=COLOR_LIVE, font=11),
    ]
    # Zwölf Waren mit Balken (Bestand/Lagerplatz) und Trend pro Tag; „an“ = Lager voll
    for i, (gid, icon, de, en) in enumerate(GOODS):
        buttons.append(button(1 + i // 6, i % 6, "", [], icon=icon, live=plugin_live(f"good_{gid}", bar=True),
                              color=COLOR_LIVE, color_on="#7a5a1f", font=10))
    buttons += [
        hint(3, 0, L("Weitere Waren als Wert:\nTBWare_<Id>, z. B. TBWare_Berries",
                     "More goods as value:\nTBWare_<Id>, e.g. TBWare_Berries"), span=3),
        button(3, 3, L("Abfragen", "Refresh"), [tb("refresh")], icon="🔄", color=COLOR_FOLDER),
        pause_button(3, 4),
        speed_button(3, 5),
    ]
    return page(PAGES["vorraete"], sub("Vorräte", "Supplies"), buttons, events=refresh_on_open())


def notes_page():
    """Nachrichtenverlauf: die letzten 8 Meldungen des Spiels (auch weggeklickte), neueste zuerst; von heute hervorgehoben.
    Tippen = Kamera zu dem Biber oder Gebäude, um das es geht."""
    buttons = [
        back(),
        hint(0, 1, L("Nachrichtenverlauf – neueste zuerst · antippen: Kamera hin",
                     "Notification history – newest first · tap: camera there"), span=3),
        button(0, 4, L("Abfragen", "Refresh"), [tb("refresh")], icon="🔄", color=COLOR_FOLDER),
        pause_button(0, 5),
    ]
    for i in range(HISTORY):
        buttons.append(note_button(1 + i // 3, (i % 3) * 2, i + 1))
    # neunter Platz: Übersicht der Warnungen, führt zur Seite „Warnungen“
    buttons.append(button(3, 4, "", [action("go_page", page=PAGES["warnungen"])], icon="✅", icon_on="⚠️", span=2,
                          live=plugin_live("alerts"), color=COLOR_LIVE, color_on=COLOR_DANGER, font=11))
    return page(PAGES["meldungen"], sub("Meldungen", "Notifications"), buttons, events=refresh_on_open())


def alerts_page():
    """Aktive Warnungen wie im Warnfeld des Spiels (Arbeitslos, Hungrig, Kein Strom …), die meisten Betroffenen zuerst.
    Jedes Tippen springt zum nächsten Betroffenen dieser Warnung."""
    buttons = [
        back(),
        alerts_button(0, 1, span=3),
        hint(0, 4, L("Antippen: Kamera zum nächsten Betroffenen", "Tap: camera to the next one affected")),
    ]
    for i in range(ALERTS):
        buttons.append(alert_button(1 + i // 3, (i % 3) * 2, i + 1))
    buttons.append(button(3, 4, L("Meldungen", "Notifications"), [action("go_page", page=PAGES["meldungen"])],
                          icon="📜", span=2, color=COLOR_FOLDER))
    return page(PAGES["warnungen"], sub("Warnungen", "Alerts"), buttons, events=refresh_on_open())


def game_page():
    return page(PAGES["spiel"], sub("Spiel", "Game"), [
        back(),
        button(0, 1, L("Verbunden: {TBVerbunden}", "Connected: {TBVerbunden}"), [tb("refresh")], icon="🔌", span=2,
               live=plugin_live("status"), color=COLOR_LIVE, color_on=COLOR_ON, font=11),
        button(0, 3, "{TBSiedlung}\n{TBFraktion}", [], icon="🏡", span=2, font=11),
        save_button(0, 5),
        button(1, 0, L("Schnell-\nspeichern", "Quick\nsave"), [tb("save", name="")], icon="💾", color=COLOR_GAME, font=12),
        button(1, 1, L("Speichern mit\nZyklus und Tag", "Save with\ncycle and day"),
               [tb("save", name=L("TouchDeck Zyklus {TBZyklus} Tag {TBTag}", "TouchDeck cycle {TBZyklus} day {TBTag}"))],
               icon="🗂️", color=COLOR_GAME, font=11),
        button(1, 2, L("Zustand\nabfragen", "Fetch\nstate"), [tb("refresh")], icon="🔄", color=COLOR_FOLDER, font=12),
        pause_button(1, 3),
        speed_button(1, 4),
        button(1, 5, L("Gruß ins\nSpiel", "Greeting\nto game"),
               [tb("message", text=L("Grüße vom TouchDeck! {TBBiber} Biber, {TBWasserTage} Tage Wasser.",
                                     "Greetings from TouchDeck! {TBBiber} beavers, {TBWasserTage} days of water."),
                   kind="info")], icon="💬", color=COLOR_GAME, font=11),
        date_button(2, 0, span=3),
        weather_button(2, 3, span=3),
        hint(3, 0, L("Adresse, Port und Geheimwort des Mods: settings.json im Mod-Ordner (gilt ohne Neustart)",
                     "Mod address, port and secret: settings.json in the mod folder (applies without restart)"), span=4),
        button(3, 4, "", [tb("alert", n=1)], icon="✅", icon_on="⚠️", span=2, live=plugin_live("alerts"),
               color=COLOR_LIVE, color_on=COLOR_DANGER, font=11),
    ])


# ---------------------------------------------------------------- Vorlagen, Events, Werte

def flows():
    stufe = L("Stufe", "Speed")
    return [
        {"id": FLOW_SPEED, "name": L("Timberborn: Tempo setzen", "Timberborn: set speed"), "folder": "Timberborn",
         "inputs": [{"name": stufe, "default": "1"}],
         "actions": [comment(L("Tempo 1–3 setzen, wie die Knöpfe im Spiel (×1, ×3, ×7). Hebt die Pause auf.",
                               "Set speed 1–3, like the buttons in the game (×1, ×3, ×7). Unpauses.")),
                     tb("speed", op="set", value=inp(stufe))]},
    ]


def events():
    # Keine Benachrichtigungen auf dem PC: was wichtig ist, zeigen die Buttons rot an.
    return [
        {"id": f"ev_timberborn_fokus_{key}",
         "name": L(f"Timberborn im Vordergrund ({label}) → Seite Timberborn", f"Timberborn in front ({label}) → page Timberborn"),
         "folder": "Timberborn", "enabled": True, "trigger": {"type": "app_focus", "params": {"app": app, "once": True}},
         "cooldown": 0, "actions": [action("deck_show_page", page=PAGE_MAIN)]}
        for key, app, label in (("proton", WINDOWS["proton"], "Linux/Proton"), ("nativ", WINDOWS["native"], "Windows"))
    ]


# Wertnamen bleiben in beiden Sprachen gleich: das Plugin setzt genau diese Namen
VALUES = {
    "TBStatus": ("Zustand: läuft, pausiert, Hauptmenü, nicht erreichbar", "State: running, paused, main menu, not reachable"),
    "TBVerbunden": ("ja/nein: Verbindung zum Mod steht", "yes/no: connected to the mod"),
    "TBImSpiel": ("ja/nein: ein Spielstand ist geladen (nicht Hauptmenü)", "yes/no: a game is loaded (not the main menu)"),
    "TBZyklus": ("Zyklus", "Cycle"),
    "TBTag": ("Tag im Zyklus", "Day in the cycle"),
    "TBUhrzeit": ("Uhrzeit im Spiel (HH:MM)", "In-game time (HH:MM)"),
    "TBDatum": ("Zyklus und Tag als Text", "Cycle and day as text"),
    "TBTempo": ("Tempo 0–3 (0 = Pause; 1 = ×1, 2 = ×3, 3 = ×7)", "Speed 0–3 (0 = paused; 1 = ×1, 2 = ×3, 3 = ×7)"),
    "TBPause": ("an/aus", "on/off"),
    "TBWetter": ("Aktuelles Wetter (Sprache des Spiels)", "Current weather (in the game's language)"),
    "TBGefahrIn": ("Tage bis zur nächsten Gefahr (0 = läuft)", "Days until the next hazard (0 = running)"),
    "TBGefahrArt": ("Art der nächsten Gefahr, „?“ bis das Spiel sie ankündigt", "Kind of the next hazard, “?” until the game announces it"),
    "TBGefahrRest": ("Resttage der laufenden Gefahr", "Days left of the running hazard"),
    "TBGefahrDauer": ("Dauer der Gefahr in diesem Zyklus (Tage)", "Duration of this cycle's hazard (days)"),
    "TBBiber": ("Biber (Erwachsene und Kinder)", "Beavers (adults and kids)"),
    "TBErwachsene": ("Erwachsene Biber", "Adult beavers"),
    "TBKinder": ("Biberkinder", "Beaver kids"),
    "TBBots": ("Bots", "Bots"),
    "TBBevoelkerung": ("Alle zusammen (Biber und Bots)", "Everyone (beavers and bots)"),
    "TBObdachlos": ("Obdachlose Biber", "Homeless beavers"),
    "TBBettenFrei": ("Freie Betten", "Free beds"),
    "TBArbeitslos": ("Arbeitslose Biber", "Unemployed beavers"),
    "TBStellenFrei": ("Freie Arbeitsplätze", "Free jobs"),
    "TBVerseucht": ("Verseuchte Biber", "Contaminated beavers"),
    "TBZufriedenheit": ("Durchschnittliche Zufriedenheit", "Average well-being"),
    "TBWissenschaft": ("Wissenschaftspunkte", "Science points"),
    "TBWasser": ("Wasser im Lager", "Water in storage"),
    "TBWasserTage": ("So viele Tage reicht das Wasser beim jetzigen Verbrauch („–“ = wird nicht weniger)",
                     "Days the water lasts at the current use (“–” = not decreasing)"),
    "TBNahrung": ("Nahrung im Lager (alle Sorten)", "Food in storage (all kinds)"),
    "TBNahrungTage": ("So viele Tage reicht die Nahrung beim jetzigen Verbrauch („–“ = wird nicht weniger)",
                      "Days the food lasts at the current use (“–” = not decreasing)"),
    "TBWarnungen": ("Anzahl verschiedener aktiver Warnungen", "Number of different active alerts"),
    "TBFraktion": ("Fraktion (Sprache des Spiels)", "Faction (in the game's language)"),
    "TBSiedlung": ("Name der Siedlung", "Settlement name"),
}
for _i in range(1, HISTORY + 1):
    VALUES[f"TBMeldung{_i}"] = (f"Meldung {_i} aus dem Nachrichtenverlauf (neueste zuerst): Text (Zyklus, Tag)",
                                f"Notification {_i} from the history (newest first): text (cycle, day)")
for _i in range(1, ALERTS + 1):
    VALUES[f"TBWarnung{_i}"] = (f"Warnung {_i} (die meisten Betroffenen zuerst): Text (Anzahl)",
                                f"Alert {_i} (most affected first): text (count)")
for _gid, _icon, _de, _en in [("Water", "", "Wasser", "Water")] + GOODS:
    VALUES[f"TBWare_{_gid}"] = (f"{_de} im Lager", f"{_en} in storage")

PROFILES = {"en": "Timberborn (English).tdprofile", "de": "Timberborn (Deutsch).tdprofile"}


def build(lang):
    _lang["de"] = lang == "de"
    _ids["n"] = 0
    pages = [main_page(), time_page(), weather_page(), beavers_page(), supplies_page(), notes_page(), alerts_page(),
             game_page()]
    values = {name: {"default": L("nein", "no") if name in ("TBVerbunden", "TBImSpiel") else "–",
                     "description": f"{L(*desc)} (Plugin Timberborn)", "folder": "Timberborn", "resetOnStart": True}
              for name, desc in VALUES.items()}
    return {
        "format": "touchdeck-profile", "formatVersion": 1, "app": "0.12.0",
        "name": "Timberborn", "pages": pages, "flows": flows(), "events": events(),
        "values": values, "images": {},
    }


def write(path, profile):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("profile.json", json.dumps(profile, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for lang, file in PROFILES.items():
        path = os.path.join(root, file)
        write(path, build(lang))
        print(f"{path} geschrieben")
