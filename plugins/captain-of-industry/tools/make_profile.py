#!/usr/bin/env python3
"""Erzeugt die fertigen TouchDeck-Seiten für das Plugin „Captain of Industry“ auf Englisch und Deutsch:
„Captain of Industry (English).tdprofile“ und „Captain of Industry (Deutsch).tdprofile“ (gleicher Aufbau,
nur die Texte unterscheiden sich).

Aufruf:  python3 tools/make_profile.py
Import:  TouchDeck › Seitenliste › „⋯“ › Profil importieren (oder „Fertige Seiten“ in der Plugin-Karte).
Format (touchdeck-profile, Version 1): touchdeck-rs/server/src/core/profiles.rs und store.rs.

Aufbau: Hauptseite „Captain of Industry“ mit Live-Anzeigen und sechs Ordnern (Meldungen, Verlauf, Strom,
Bevölkerung, Waren, Spiel), angelegt wie „Ordner hier erstellen“ im Editor (createFolder in
web/editor/js/views/pages.js): eigene Seite „Captain of Industry › …“ mit gleichem Raster und Zurück-Button oben
links, auf der Hauptseite ein 📁-Button. Was das Spiel weiß (Pause, Strommangel, fehlende Arbeiter …), zeigen
Live-Anzeigen mit „an“-Look (rot) statt Umschalter, die mit dem Spiel auseinanderlaufen könnten.
Keine Benachrichtigungen auf dem PC: was wichtig ist, zeigen die Buttons rot an.
"""
import json
import os
import zipfile

PLUGIN = "plugin:captain-of-industry"
NAME = "Captain of Industry"
# Fensterklasse: unter Proton „steam_app_1594320“, unter Windows das Programm (Vergleich: enthält, ohne Groß/klein)
WINDOWS = {"proton": "steam_app_1594320", "native": "captain of industry"}
ROWS, COLS = 4, 6                 # Hauptseite und alle Ordner: gleiche Rasterform wie createFolder

PAGE_MAIN = "p_coi"
PAGES = {"meldungen": "p_coi_meldungen", "verlauf": "p_coi_verlauf", "strom": "p_coi_strom",
         "leute": "p_coi_bevoelkerung", "waren": "p_coi_waren", "spiel": "p_coi_spiel"}
FLOW_SPEED = "f_coi_tempo"
HISTORY = 8
ALERTS = 8
GOODS = 8

COLOR = "#2b2f3a"
COLOR_GAME = "#4a4f2a"     # Olivgrün wie die Oberfläche des Spiels
COLOR_FOLDER = "#3a3f4b"   # wie createFolder
COLOR_LIVE = "#1f3340"
COLOR_ON = "#2f6f4f"
COLOR_DANGER = "#c0392b"
COLOR_POWER = "#3d3a1f"
COLOR_PEOPLE = "#3a2f40"
COLOR_NEW = "#7a5a1f"

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


def coi(aid, **params):
    """Aktion des Plugins: plugin:captain-of-industry:<id>."""
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
        "id": f"b_coi_{_ids['n']}",
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
    # folder: Ordner in der Seitenliste (eigene Gruppe „Captain of Industry“); ratioW/ratioH wie createFolder
    return {"id": pid, "name": name, "rows": ROWS, "cols": COLS, "layout": "grid", "folder": NAME,
            "background": "#11161a", "ratioW": 16, "ratioH": 10, "colSizes": [], "rowSizes": [],
            "buttons": buttons, "events": events or []}


def sub(de, en):
    return L(f"{NAME} › {de}", f"{NAME} › {en}")


def back():
    # genau wie createFolder: Zeile 0, Spalte 0, ⬅️, #3a3f4b, go_page __back
    return button(0, 0, L("Zurück", "Back"), [action("go_page", page="__back")], icon="⬅️", color=COLOR_FOLDER)


def folder(row, col, title, pid):
    # wie createFolder: 📁 mit dem Ordnernamen, Aktion go_page auf die Unterseite
    return button(row, col, title, [action("go_page", page=pid)], icon="📁", color=COLOR_FOLDER)


def page_opened(*actions):
    """Logik der Seite: „Seite geöffnet“ (page_view ohne Seitenwahl = diese Seite, events.rs)."""
    return [{"id": f"pe_coi_{_ids['n']}", "enabled": True,
             "trigger": {"type": "page_view", "params": {"page": "", "state": "open"}}, "actions": list(actions)}]


def refresh_on_open():
    return page_opened(comment(L("Beim Öffnen den aktuellen Stand aus dem Spiel holen.",
                                 "When opened, fetch the current state from the game.")), coi("refresh"))


def refresh_button(row, col):
    return button(row, col, L("Abfragen", "Refresh"), [coi("refresh")], icon="🔄", color=COLOR_FOLDER)


# ---------------------------------------------------------------- wiederkehrende Buttons

def status_button(row, col, span=1):
    return button(row, col, "", [coi("refresh")], icon="🏭", span=span, live=plugin_live("status"), color=COLOR_LIVE,
                  color_on=COLOR_ON, font=11)


def date_button(row, col, span=2):
    return button(row, col, "", [], icon="📅", span=span, live=plugin_live("date"), font=12, color=COLOR_LIVE)


def pause_button(row, col):
    # Zustand aus dem Spiel ({COIPause} = an/aus) statt Umschalter: Pause per Leertaste im Spiel bleibt richtig
    return button(row, col, "Pause", [coi("pause", op="toggle")], icon="⏸️", icon_on="▶️",
                  title_on=L("Pausiert", "Paused"), live=value_live("COIPause"), color=COLOR_GAME, color_on="#9e6b2f")


def speed_button(row, col, span=1):
    # Tippen = schneller, doppelt = langsamer, halten = zurück auf Tempo 1
    return button(row, col, L("Tempo", "Speed"), [coi("speed", op="up")], icon="⏩", span=span,
                  live=plugin_live("speed"), color=COLOR_GAME, color_on=COLOR_ON, double=[coi("speed", op="down")],
                  hold=[flow(FLOW_SPEED, **{L("Stufe", "Speed"): 1})])


def save_name():
    return L("TouchDeck Jahr {COIJahr} Monat {COIMonat}", "TouchDeck year {COIJahr} month {COIMonat}")


def save_button(row, col):
    # Tippen = Schnellspeicher, halten = eigener Spielstand mit Jahr und Monat im Namen
    return button(row, col, L("Speichern", "Save"), [coi("save", name="")], icon="💾", color=COLOR_GAME,
                  hold=[coi("save", name=save_name())])


def live_button(row, col, lid, icon, *, span=2, color=COLOR_LIVE, bar=False, actions=None, font=12, icon_on=None):
    """Live-Anzeige, die rot wird, sobald etwas nicht stimmt („an“ im Plugin)."""
    return button(row, col, "", actions or [], icon=icon, icon_on=icon_on, span=span, live=plugin_live(lid, bar=bar),
                  color=color, color_on=COLOR_DANGER, font=font)


def power_button(row, col, span=2):
    return live_button(row, col, "power", "⚡", span=span, color=COLOR_POWER, bar=True, font=11)


def computing_button(row, col, span=2):
    return live_button(row, col, "computing", "🖥️", span=span, color=COLOR_POWER, bar=True, font=11)


def unity_button(row, col, span=2):
    return live_button(row, col, "unity", "🤝", span=span, color=COLOR_POWER, bar=True, font=11)


def workers_button(row, col, span=1):
    return live_button(row, col, "workers", "👷", span=span, color=COLOR_PEOPLE, font=11)


def food_button(row, col, span=1):
    return live_button(row, col, "food", "🥫", span=span, color=COLOR_PEOPLE, bar=True, font=11)


def research_button(row, col, span=2):
    # „an“ heißt hier beides: läuft (Fortschritt) oder Labor ohne Arbeit – der Text sagt, was los ist
    return button(row, col, "", [], icon="🔬", span=span, live=plugin_live("research", bar=True), color=COLOR_LIVE,
                  color_on="#2f4f6f", font=11)


def alerts_button(row, col, span=2, go_page=False):
    # Tippen = Kamera zur wichtigsten Meldung (jedes Tippen der nächste Betroffene)
    acts = [action("go_page", page=PAGES["meldungen"])] if go_page else [coi("alert", n=1)]
    return button(row, col, "", acts, icon="✅", icon_on="⚠️", span=span, live=plugin_live("alerts"),
                  color=COLOR_LIVE, color_on=COLOR_DANGER, font=11)


def note_button(row, col, n, span=2):
    # Tippen = Kamera zu dem, was die Meldung betrifft; „an“ = aus diesem Monat
    return button(row, col, "", [coi("history", n=n)], icon="📜", span=span, live=plugin_live(f"note{n}"),
                  color=COLOR, color_on=COLOR_NEW, font=10)


def alert_button(row, col, n, span=2):
    return button(row, col, "", [coi("alert", n=n)], icon="⚠️", span=span, live=plugin_live(f"alert{n}"),
                  color=COLOR, color_on=COLOR_DANGER, font=11)


def good_button(row, col, n):
    return button(row, col, "", [], icon="📦", live=plugin_live(f"good{n}", bar=True), color=COLOR_LIVE,
                  color_on=COLOR_NEW, font=10)


def hint(row, col, text, span=2):
    return button(row, col, text, [], span=span, font=10, color=COLOR_FOLDER)


# ---------------------------------------------------------------- Seiten

def main_page():
    return page(PAGE_MAIN, NAME, [
        status_button(0, 0),
        date_button(0, 1),
        speed_button(0, 3),
        pause_button(0, 4),
        save_button(0, 5),
        power_button(1, 0),
        workers_button(1, 2),
        food_button(1, 3),
        alerts_button(1, 4),
        folder(2, 0, L("Meldungen", "Alerts"), PAGES["meldungen"]),
        folder(2, 1, L("Verlauf", "History"), PAGES["verlauf"]),
        folder(2, 2, L("Strom", "Power"), PAGES["strom"]),
        folder(2, 3, L("Bevölkerung", "Population"), PAGES["leute"]),
        folder(2, 4, L("Waren", "Products"), PAGES["waren"]),
        folder(2, 5, L("Spiel", "Game"), PAGES["spiel"]),
        unity_button(3, 0),
        research_button(3, 2),
        note_button(3, 4, 1),
    ])


def alerts_page():
    """Aktive Meldungen wie im Meldungsfeld des Spiels (kein Treibstoff, Lager voll, keine Arbeiter …), kritische
    zuerst, gleiche zusammengefasst. Jedes Tippen springt zum nächsten Betroffenen dieser Meldung."""
    buttons = [
        back(),
        alerts_button(0, 1, span=3),
        hint(0, 4, L("Antippen: Kamera zum nächsten Betroffenen", "Tap: camera to the next one affected")),
    ]
    for i in range(ALERTS):
        buttons.append(alert_button(1 + i // 3, (i % 3) * 2, i + 1))
    buttons.append(button(3, 4, L("Verlauf", "History"), [action("go_page", page=PAGES["verlauf"])],
                          icon="📜", span=2, color=COLOR_FOLDER))
    return page(PAGES["meldungen"], sub("Meldungen", "Alerts"), buttons, events=refresh_on_open())


def history_page():
    """Verlauf: die letzten 8 neuen Meldungen und Nachrichten (Forschung fertig, Flüchtlinge …), neueste zuerst –
    auch die, die im Spiel schon wieder verschwunden sind. Tippen = Kamera dorthin, wenn es einen Ort gibt."""
    buttons = [
        back(),
        hint(0, 1, L("Verlauf – neueste zuerst · antippen: Kamera hin",
                     "History – newest first · tap: camera there"), span=3),
        refresh_button(0, 4),
        pause_button(0, 5),
    ]
    for i in range(HISTORY):
        buttons.append(note_button(1 + i // 3, (i % 3) * 2, i + 1))
    # neunter Platz: Übersicht der Meldungen, führt zur Seite „Meldungen“
    buttons.append(alerts_button(3, 4, go_page=True))
    return page(PAGES["verlauf"], sub("Verlauf", "History"), buttons, events=refresh_on_open())


def power_page():
    return page(PAGES["strom"], sub("Strom", "Power"), [
        back(),
        power_button(0, 1, span=3),
        button(0, 4, L("Bedarf\n{COIStromBedarf} kW", "Demand\n{COIStromBedarf} kW"), [], icon="🔌", span=2, font=12),
        computing_button(1, 0, span=3),
        unity_button(1, 3, span=3),
        research_button(2, 0, span=3),
        button(2, 3, L("Einheit pro Monat\n{COIEinheitMonat}", "Unity per month\n{COIEinheitMonat}"), [], icon="📈",
               span=3, font=12),
        date_button(3, 0, span=3),
        speed_button(3, 3),
        pause_button(3, 4),
        refresh_button(3, 5),
    ], events=refresh_on_open())


def people_page():
    return page(PAGES["leute"], sub("Bevölkerung", "Population"), [
        back(),
        live_button(0, 1, "population", "👥", span=3, color=COLOR_PEOPLE),
        workers_button(0, 4, span=2),
        food_button(1, 0, span=3),
        live_button(1, 3, "health", "🦠", span=3, color=COLOR_PEOPLE),
        button(2, 0, L("{COIObdachlos}\nobdachlos", "{COIObdachlos}\nhomeless"), [], icon="🏚️", font=11),
        button(2, 1, L("{COIWohnraumFrei}\nWohnplätze frei", "{COIWohnraumFrei}\nhomes free"), [], icon="🏠", font=11),
        button(2, 2, L("{COIArbeiterFrei}\nArbeiter frei", "{COIArbeiterFrei}\nworkers free"), [], icon="👷", font=11),
        button(2, 3, L("Hunger:\n{COIHunger}", "Starving:\n{COIHunger}"), [], icon="🍽️", font=11),
        unity_button(2, 4),
        alert_button(3, 0, 1, span=3),
        alert_button(3, 3, 2, span=3),
    ], events=refresh_on_open())


def goods_page():
    buttons = [
        back(),
        food_button(0, 1, span=2),
        hint(0, 3, L("📌 = im Spiel angeheftet; danach die Waren mit dem größten Bestand",
                     "📌 = pinned in the game; then the products with the largest stock"), span=3),
    ]
    # Acht Waren mit Balken (Bestand/Lagerplatz) und Trend pro Monat; „an“ = Lager voll oder wird knapp
    for i in range(GOODS):
        buttons.append(good_button(1 + i // 6, i % 6, i + 1))
    buttons += [
        hint(2, 2, L("Alle Waren als Wert:\nCOIWare_<Id>, z. B. COIWare_IronOre",
                     "All products as value:\nCOIWare_<Id>, e.g. COIWare_IronOre"), span=4),
        hint(3, 0, L("Was hier stehen soll, im Spiel anheften (Stecknadel bei der Ware)",
                     "Pin what should show here in the game (pin icon at the product)"), span=3),
        refresh_button(3, 3),
        pause_button(3, 4),
        speed_button(3, 5),
    ]
    return page(PAGES["waren"], sub("Waren", "Products"), buttons, events=refresh_on_open())


def game_page():
    buttons = [
        back(),
        button(0, 1, L("Verbunden: {COIVerbunden}", "Connected: {COIVerbunden}"), [coi("refresh")], icon="🔌", span=2,
               live=plugin_live("status"), color=COLOR_LIVE, color_on=COLOR_ON, font=11),
        date_button(0, 3, span=2),
        save_button(0, 5),
    ]
    for i, icon in enumerate(["▶️", "⏩", "⏭️"]):
        buttons.append(button(1, i, L(f"Tempo {i + 1}", f"Speed {i + 1}"), [flow(FLOW_SPEED, **{L("Stufe", "Speed"): i + 1})],
                              icon=icon, color=COLOR_GAME, font=12))
    buttons += [
        button(1, 3, L("Langsamer", "Slower"), [coi("speed", op="down")], icon="🐢", color=COLOR_GAME),
        # halten = schrittweise schneller (alle 0,6 s eine Stufe)
        button(1, 4, L("Schneller", "Faster"), [coi("speed", op="up")], icon="🐇", color=COLOR_GAME,
               hold=[coi("speed", op="up")], hold_repeat=600),
        button(1, 5, "", [], icon="⏩", live=plugin_live("speed", bar=True), color=COLOR_LIVE, color_on=COLOR_ON, font=11),
        button(2, 0, L("Pause an", "Pause"), [coi("pause", op="on")], icon="⏸️", color=COLOR_GAME),
        button(2, 1, L("Weiter", "Resume"), [coi("pause", op="off")], icon="▶️", color=COLOR_GAME),
        # „Kurz anhalten“: solange gedrückt Pause, beim Loslassen geht es weiter
        button(2, 2, L("Halten =\nkurz Pause", "Hold =\nshort pause"), [], icon="✋", color=COLOR_GAME, font=11,
               hold=[coi("pause", op="on")], release=[coi("pause", op="off")]),
        button(2, 3, L("Schnell-\nspeichern", "Quick\nsave"), [coi("save", name="")], icon="💾", color=COLOR_GAME, font=12),
        button(2, 4, L("Speichern mit\nJahr und Monat", "Save with\nyear and month"), [coi("save", name=save_name())],
               icon="🗂️", color=COLOR_GAME, font=11),
        refresh_button(2, 5),
        hint(3, 0, L("Adresse, Port und Geheimwort des Mods: settings.json im Mod-Ordner (gilt ohne Neustart)",
                     "Mod address, port and secret: settings.json in the mod folder (applies without restart)"), span=4),
        alerts_button(3, 4),
    ]
    return page(PAGES["spiel"], sub("Spiel", "Game"), buttons)


# ---------------------------------------------------------------- Vorlagen, Events, Werte

def flows():
    stufe = L("Stufe", "Speed")
    return [
        {"id": FLOW_SPEED, "name": L(f"{NAME}: Tempo setzen", f"{NAME}: set speed"), "folder": NAME,
         "inputs": [{"name": stufe, "default": "1"}],
         "actions": [comment(L("Tempo setzen, wie die Tempo-Knöpfe im Spiel (1 = normal). Hebt die Pause auf.",
                               "Set the speed, like the speed buttons in the game (1 = normal). Unpauses.")),
                     coi("speed", op="set", value=inp(stufe))]},
    ]


def events():
    # Keine Benachrichtigungen auf dem PC: was wichtig ist, zeigen die Buttons rot an.
    return [
        {"id": f"ev_coi_fokus_{key}",
         "name": L(f"{NAME} im Vordergrund ({label}) → Seite {NAME}", f"{NAME} in front ({label}) → page {NAME}"),
         "folder": NAME, "enabled": True, "trigger": {"type": "app_focus", "params": {"app": app, "once": True}},
         "cooldown": 0, "actions": [action("deck_show_page", page=PAGE_MAIN)]}
        for key, app, label in (("proton", WINDOWS["proton"], "Linux/Proton"), ("nativ", WINDOWS["native"], "Windows"))
    ]


# Wertnamen bleiben in beiden Sprachen gleich: das Plugin setzt genau diese Namen
VALUES = {
    "COIStatus": ("Zustand: läuft, pausiert, Hauptmenü, nicht erreichbar", "State: running, paused, main menu, not reachable"),
    "COIVerbunden": ("ja/nein: Verbindung zum Mod steht", "yes/no: connected to the mod"),
    "COIImSpiel": ("ja/nein: ein Spielstand ist geladen (nicht Hauptmenü)", "yes/no: a game is loaded (not the main menu)"),
    "COIJahr": ("Jahr im Spiel", "In-game year"),
    "COIMonat": ("Monat im Spiel (1–12)", "In-game month (1–12)"),
    "COIDatum": ("Jahr und Monat als Text", "Year and month as text"),
    "COITempo": ("Tempostufe (0 = Pause, 1 = normal)", "Speed level (0 = paused, 1 = normal)"),
    "COIPause": ("an/aus", "on/off"),
    "COIStrom": ("Stromverbrauch in kW", "Power use in kW"),
    "COIStromBedarf": ("Strombedarf in kW", "Power demand in kW"),
    "COIStromKapazitaet": ("Stromerzeugung (Kapazität) in kW", "Power generation (capacity) in kW"),
    "COIRechnen": ("Bedarf an Rechenleistung in TFLOPS", "Computing demand in TFLOPS"),
    "COIRechnenKapazitaet": ("Rechenleistung (Kapazität) in TFLOPS", "Computing capacity in TFLOPS"),
    "COIEinheit": ("Einheit", "Unity"),
    "COIEinheitMonat": ("Änderung der Einheit im letzten Monat", "Change of unity last month"),
    "COIArbeiterFrei": ("Freie Arbeiter (negativ = so viele fehlen)", "Free workers (negative = this many missing)"),
    "COIEinwohner": ("Einwohner", "Population"),
    "COIObdachlos": ("Obdachlose", "Homeless"),
    "COIWohnraumFrei": ("Freie Wohnplätze", "Free homes"),
    "COINahrungMonate": ("So viele Monate reicht die Nahrung", "Months the food lasts"),
    "COIHunger": ("ja/nein: Leute hungern", "yes/no: people are starving"),
    "COIKrankheit": ("Krankheit, die gerade umgeht („–“ = keine)", "Disease going around (“–” = none)"),
    "COIForschung": ("Laufende Forschung (Sprache des Spiels)", "Current research (in the game's language)"),
    "COIForschungProzent": ("Fortschritt der Forschung in Prozent", "Research progress in percent"),
    "COIWarnungen": ("Anzahl verschiedener aktiver Meldungen", "Number of different active alerts"),
    "COIUngelesen": ("Ungelesene Nachrichten des Spiels", "Unread messages in the game"),
}
for _i in range(1, HISTORY + 1):
    VALUES[f"COIVerlauf{_i}"] = (f"Eintrag {_i} im Verlauf (neueste zuerst): Text (Jahr)",
                                 f"History entry {_i} (newest first): text (year)")
for _i in range(1, ALERTS + 1):
    VALUES[f"COIWarnung{_i}"] = (f"Meldung {_i} (kritische zuerst): Text (Anzahl)",
                                 f"Alert {_i} (critical first): text (count)")

PROFILES = {"en": f"{NAME} (English).tdprofile", "de": f"{NAME} (Deutsch).tdprofile"}


def build(lang):
    _lang["de"] = lang == "de"
    _ids["n"] = 0
    pages = [main_page(), alerts_page(), history_page(), power_page(), people_page(), goods_page(), game_page()]
    values = {name: {"default": L("nein", "no") if name in ("COIVerbunden", "COIImSpiel") else "–",
                     "description": f"{L(*desc)} (Plugin {NAME})", "folder": NAME, "resetOnStart": True}
              for name, desc in VALUES.items()}
    return {
        "format": "touchdeck-profile", "formatVersion": 1, "app": "0.12.0",
        "name": NAME, "pages": pages, "flows": flows(), "events": events(),
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
