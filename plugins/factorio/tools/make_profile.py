#!/usr/bin/env python3
"""Erzeugt Factorio.tdprofile und UTLogistics.tdprofile: fertige TouchDeck-Seiten für das Plugin „Factorio“.

Aufruf:  python3 tools/make_profile.py
Import:  TouchDeck › Seitenliste › „⋯“ › Profil importieren (oder „Fertige Seiten“ in der Plugin-Karte).
Format (touchdeck-profile, Version 1): touchdeck-rs/server/src/core/profiles.rs und store.rs.

Aufbau: Hauptseite „Factorio“ mit Live-Anzeigen und Graphen und sechs Ordnern (Zeit, Forschung, Chat,
Spiel, Strom, Produktion), angelegt wie „Ordner hier erstellen“ im Editor: eigene Seite „Factorio › …“ mit Zurück-Button
oben links. Jeder Befehl drückt ein Tastenkürzel des Mods im Factorio-Fenster und wartet auf die
Antwort des Spiels. Text wird nie getippt: Mit IBus kommt er in Factorio-Textfeldern nicht an
(im Spiel geprüft).
"""
import json
import os
import zipfile

PLUGIN = "plugin:factorio"
WINDOW = "factorio"              # Fensterklasse (WM_CLASS) des Spiels: „factorio“, „com.factorio.Factorio“
ROWS, COLS = 3, 5

# Tastenkürzel des Mods (prototypes/inputs.lua) → Befehl, auf dessen Antwort gewartet wird
KEYS = {
    "pause": ("p", "pause"),
    "speed05": ("1", "speed"), "speed1": ("2", "speed"), "speed2": ("3", "speed"), "speed4": ("4", "speed"),
    "slower": ("n", "speed"), "faster": ("m", "speed"),
    "save": ("s", "save"),
    "screenshot": ("k", "screenshot"),
    "cancel": ("x", "cancel"),
    "research1": ("q", "research"), "research2": ("w", "research"), "research3": ("e", "research"),
    "chat1": ("5", "quickchat"), "chat2": ("6", "quickchat"), "chat3": ("7", "quickchat"),
    "chat4": ("8", "quickchat"), "chat5": ("9", "quickchat"), "chat6": ("0", "quickchat"),
    "center": ("h", "center"),
    "refresh": ("u", "refresh"),
    "utl": ("g", "utl"), "utl_alerts": ("a", "utl"),
}
CHAT = [("Hilfe!", "🆘"), ("Bin gleich da!", "🏃"), ("Brauche Eisen!", "⛏️"),
        ("Angriff an der Basis!", "⚔️"), ("Bin kurz weg.", "☕"), ("Danke!", "👍")]

PAGE_MAIN = "p_factorio"
PAGES = {"zeit": "p_factorio_zeit", "forschung": "p_factorio_forschung",
         "chat": "p_factorio_chat", "spiel": "p_factorio_spiel",
         "strom": "p_factorio_strom", "produktion": "p_factorio_produktion"}
ITEM_SLOTS = 8

COLOR = "#2b2f3a"
COLOR_GAME = "#4a3b22"     # Factorio-Braun
COLOR_FOLDER = "#3a3f4b"
COLOR_LIVE = "#1f3a2f"
COLOR_POWER = "#f1c40f"

_ids = {"n": 0}


def action(kind, **params):
    return {"id": "", "type": kind, "enabled": True, "params": params}


def comment(text):
    return action("comment", text=text)


def press(name):
    """Nur das Tastenkürzel drücken (für Halten/Loslassen, ohne Warten)."""
    return action("hotkey", keys=f"ctrl+alt+shift+{KEYS[name][0]}", window=WINDOW, back=True)


def key(name):
    """Tastenkürzel im Factorio-Fenster drücken und auf die Antwort des Spiels warten."""
    return [press(name), action(f"{PLUGIN}:await", cmd=KEYS[name][1], seconds=3)]


def button(row, col, title, actions=None, *, icon="", color=COLOR, span=1, rows=1, live=None, mode="press",
           color_on=None, hold=None, release=None, double=None, font=13, pos="bottom"):
    _ids["n"] += 1
    if mode == "press" and not (actions or hold or release or double):
        mode = "display"   # reine Anzeige: kein Antippen, keine Drück-Animation (TouchDeck 0.10)
    b = {
        "id": f"b_factorio_{_ids['n']}",
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
    }
    if color_on:
        b["colorOn"] = color_on
    if live:
        b["live"] = live
    return b


def plugin_live(lid, bar=False, graph=None):
    live = {"source": f"{PLUGIN}:{lid}", "command": "", "variable": "", "bar": bar}
    if graph:
        live.update(graph)
    return live


def value_live(name):
    return {"source": "variable", "command": "", "variable": name, "bar": False}


# Graphen (store.rs, Live: graph, graphPoints, graphInterval, graphMin/Max, graphColor, graphAlign)
GRAPH_POWER = {"graph": "line", "graphPoints": 60, "graphInterval": 2, "graphMin": 0,
               "graphColor": COLOR_POWER, "graphAlign": "left"}          # letzte 2 Minuten
# Erzeugung nach Quelle (Dampf, Solar, Akkus …) übereinander: oberste Kante = Gesamterzeugung
GRAPH_SOURCES = dict(GRAPH_POWER, graph="stack")
# Strom-Seite: längerer Verlauf (10 Minuten), Verbrauch nach Verbraucher gestapelt
GRAPH_SOURCES_LONG = dict(GRAPH_SOURCES, graphPoints=120, graphInterval=5)
GRAPH_CONSUMERS_LONG = dict(GRAPH_SOURCES_LONG, graphColor="#e67e22")
# Produktions-Plätze: Produktion und Verbrauch pro Minute als zwei Linien, letzte 10 Minuten
GRAPH_ITEM = {"graph": "line", "graphPoints": 60, "graphInterval": 10, "graphMin": 0, "graphAlign": "left"}
GRAPH_EVOLUTION = {"graph": "area", "graphPoints": 120, "graphInterval": 30, "graphMin": 0,
                   "graphMax": 100, "graphColor": "#c0392b", "graphAlign": "left"}   # letzte Stunde


def page(pid, name, buttons, rows=ROWS):
    # Ordner in der Seitenliste (TouchDeck 0.10); ältere Versionen ignorieren das Feld
    return {"id": pid, "name": name, "rows": rows, "cols": COLS, "layout": "grid", "folder": "Factorio",
            "background": "#14161b", "buttons": buttons, "events": []}


def back():
    return button(0, 0, "Zurück", [action("go_page", page="__back")], icon="⬅️", color=COLOR_FOLDER)


def folder(row, col, title, icon, pid):
    return button(row, col, title, [action("go_page", page=pid)], icon=icon, color=COLOR_FOLDER)


def pause_button(row, col):
    # Zustand kommt aus dem Spiel ({FPause}), kein frei laufender Umschalter
    return button(row, col, "Pause", key("pause"), icon="⏸️", live=value_live("FPause"), color=COLOR_GAME,
                  color_on="#c0392b")


def main_page():
    return page(PAGE_MAIN, "Factorio", [
        button(0, 0, "{FStatus}", [], icon="🏭", live=plugin_live("status"), color=COLOR_LIVE,
               color_on="#2f9e6b", font=11),
        button(0, 1, "Forschung", [action("go_page", page=PAGES["forschung"])], icon="🔬",
               span=2, live=plugin_live("research", bar=True), color=COLOR_LIVE, color_on="#2f6f9e"),
        button(0, 3, "Tempo", key("speed1"), icon="⏩", live=plugin_live("speed"), color=COLOR_GAME,
               color_on="#9e6b2f", double=key("speed2"), hold=[press("speed4")], release=[press("speed1")]),
        pause_button(0, 4),
        folder(1, 0, "Zeit", "⏱️", PAGES["zeit"]),
        folder(1, 1, "Forschung", "🧪", PAGES["forschung"]),
        folder(1, 2, "Chat", "💬", PAGES["chat"]),
        folder(1, 3, "Spiel", "🎮", PAGES["spiel"]),
        folder(1, 4, "Produktion", "📦", PAGES["produktion"]),
        button(2, 0, "Strom", [action("go_page", page=PAGES["strom"])], span=2,
               live=plugin_live("power", graph=GRAPH_SOURCES), color=COLOR_LIVE, color_on="#3b3a1f"),
        button(2, 2, "Evolution", [], live=plugin_live("evolution", graph=GRAPH_EVOLUTION), color_on="#3a1f1f"),
        button(2, 3, "{FPlanet}", [], icon="🪐", font=12),
        button(2, 4, "{FMeldung}", [], icon="💬", font=10),
    ])


def time_page():
    return page(PAGES["zeit"], "Factorio › Zeit", [
        back(),
        pause_button(0, 1),
        button(0, 2, "Speichern", key("save"), icon="💾", color=COLOR_GAME),
        button(0, 3, "Tempo\n{FGeschwindigkeit}×", [], icon="⏩", live=plugin_live("speed"), color_on="#9e6b2f"),
        button(0, 4, "Spielzeit\n{FSpielzeit}", [], icon="🕒", font=12),
        button(1, 0, "0,5×", key("speed05"), icon="🐢", color=COLOR_GAME),
        button(1, 1, "1×", key("speed1"), icon="▶️", color=COLOR_GAME),
        button(1, 2, "2×", key("speed2"), icon="⏩", color=COLOR_GAME),
        button(1, 3, "4×", key("speed4"), icon="⏭️", color=COLOR_GAME),
        button(1, 4, "Halten\n= 4×", [], icon="🔥", color=COLOR_GAME, hold=[press("speed4")],
               release=key("speed1")),
        button(2, 0, "Langsamer\n(½)", key("slower"), icon="🐌", color=COLOR_GAME),
        button(2, 1, "Schneller\n(×2)", key("faster"), icon="🚀", color=COLOR_GAME),
    ])


def research_page():
    buttons = [
        back(),
        button(0, 1, "Aktuell", [], icon="🔬", span=2, live=plugin_live("research", bar=True),
               color=COLOR_LIVE, color_on="#2f6f9e"),
        button(0, 3, "Warteschlange\n{FWarteschlange}", [], icon="📋", font=12),
        button(0, 4, "Abbrechen\n(halten)", [], icon="✖️", color="#5a2b2b", hold=key("cancel")),
    ]
    for i in range(3):
        buttons.append(button(1, i, f"#{i + 1}\n{{FVorschlag{i + 1}}}", key(f"research{i + 1}"),
                              icon="➕", color=COLOR_GAME, font=11))
    buttons.append(button(1, 3, "Liste neu\nschreiben", key("refresh"), icon="🔄"))
    return page(PAGES["forschung"], "Factorio › Forschung", buttons)


def chat_page():
    buttons = [back()]
    for i, (text, icon) in enumerate(CHAT):
        row, col = divmod(i + 1, COLS)
        buttons.append(button(row, col, text, key(f"chat{i + 1}"), icon=icon, font=11))
    buttons.append(button(2, 4, "Letzte\nMeldung\n{FMeldung}", [], icon="💬", font=10))
    return page(PAGES["chat"], "Factorio › Chat", buttons)


def game_page():
    return page(PAGES["spiel"], "Factorio › Spiel", [
        back(),
        button(0, 1, "Zum Spieler", key("center"), icon="🧍", color=COLOR_GAME),
        button(0, 2, "Screenshot", key("screenshot"), icon="📸", color=COLOR_GAME),
        button(0, 3, "Daten neu", key("refresh"), icon="🔄"),
        button(0, 4, "{FStatus}", [], icon="🏭", live=plugin_live("status"), color_on="#2f9e6b", font=11),
        button(1, 0, "Spieler\n{FSpieler}", [], icon="👥", font=12),
        button(1, 1, "{FPlanet}", [], icon="🪐", font=12),
        button(1, 2, "Tick\n{FTick}", [], icon="⏲️", font=11),
        button(1, 3, "Raketen\n{FRaketen}", [], icon="🚀", font=12),
        button(1, 4, "Evolution\n{FEvolution} %", [], icon="👾", font=12),
        button(2, 0, "Erzeugung", [], span=2, live=plugin_live("power", bar=True, graph=GRAPH_SOURCES),
               color=COLOR_LIVE, color_on="#3b3a1f"),
        button(2, 2, "Verbrauch", [], span=2,
               live=plugin_live("consumption", graph=dict(GRAPH_POWER, graphColor="#e67e22")),
               color=COLOR_LIVE, color_on="#3b2a1f"),
    ])


def power_page():
    return page(PAGES["strom"], "Factorio › Strom", [
        back(),
        button(0, 1, "Erzeugung\n{FStromErzeugung}", [], icon="⚡", font=12),
        button(0, 2, "Verbrauch\n{FStromVerbrauch}", [], icon="🔌", font=12),
        button(0, 3, "Auslastung", [], live=plugin_live("power", bar=True), color=COLOR_LIVE, color_on="#3b3a1f"),
        button(0, 4, "{FStatus}", [], icon="🏭", live=plugin_live("status"), color_on="#2f9e6b", font=11),
        button(1, 0, "Erzeugung nach Quelle", [], span=3, rows=2,
               live=plugin_live("power", graph=GRAPH_SOURCES_LONG), color=COLOR_LIVE, color_on="#3b3a1f"),
        button(1, 3, "Verbrauch nach Gebäude", [], span=2, rows=2,
               live=plugin_live("consumption", graph=GRAPH_CONSUMERS_LONG), color=COLOR_LIVE, color_on="#3b2a1f"),
    ])


def production_page():
    def slot_action(op, n):
        return [action(f"{PLUGIN}:item", slot=n, op=op)]
    buttons = [
        back(),
        button(0, 1, "Platz antippen = nächstes Item · halten = voriges · doppelt = automatisch", [],
               span=2, font=10, color=COLOR_FOLDER),
        button(0, 3, "Alle\nautomatisch", [action(f"{PLUGIN}:item", slot=1, op="all_auto")], icon="🔁"),
        button(0, 4, "Daten neu", key("refresh"), icon="🔄"),
    ]
    for i in range(ITEM_SLOTS):
        n = i + 1
        row, col = 1 + i // 4, i % 4
        buttons.append(button(row, col, "", slot_action("next", n), live=plugin_live(f"item{n}", graph=GRAPH_ITEM),
                              color=COLOR_LIVE, color_on="#2f4f6f", font=11, pos="bottom",
                              hold=slot_action("prev", n), double=slot_action("auto", n)))
    buttons.append(button(1, 4, "{FPlanet}", [], icon="🪐", font=11))
    buttons.append(button(2, 4, "{FMeldung}", [], icon="💬", font=10))
    return page(PAGES["produktion"], "Factorio › Produktion", buttons)


def events():
    return [
        {"id": "ev_factorio_fokus", "name": "Factorio im Vordergrund → Seite Factorio", "enabled": True,
         "trigger": {"type": "app_focus", "params": {"app": WINDOW}}, "cooldown": 0,
         "actions": [action("deck_show_page", page=PAGE_MAIN)]},
        {"id": "ev_factorio_forschung", "name": "Factorio: Forschung fertig → Meldung auf dem Deck", "enabled": True,
         "trigger": {"type": f"{PLUGIN}:research_finished", "params": {}}, "cooldown": 0,
         "actions": [action("var_set", name="FMeldung", value="🔬 Forschung fertig: {Event.Name}")]},
        {"id": "ev_factorio_tod", "name": "Factorio: ich bin gestorben → Meldung auf dem Deck", "enabled": True,
         "trigger": {"type": f"{PLUGIN}:player_died", "params": {"Ich": "ja"}}, "cooldown": 0,
         "actions": [action("var_set", name="FMeldung", value="💀 Du bist gestorben")]},
    ]


VALUES = {
    "FStatus": "Zustand: läuft, pausiert, keine Daten, Factorio aus",
    "FVerbunden": "ja/nein: Daten vom Mod kommen an",
    "FSpielzeit": "Gespielte Zeit (h:mm:ss)",
    "FTick": "Aktueller Tick",
    "FGeschwindigkeit": "Spielgeschwindigkeit (1 = normal)",
    "FPause": "an/aus",
    "FForschung": "Aktuelle Forschung (in Spielsprache)",
    "FForschungProzent": "Fortschritt der Forschung (0–100)",
    "FWarteschlange": "Einträge in der Forschungs-Warteschlange",
    "FEvolution": "Evolution der Gegner auf deiner Fläche in Prozent",
    "FRaketen": "Gestartete Raketen deiner Force",
    "FSpieler": "Spieler online",
    "FPlanet": "Planet oder Raumplattform, auf der du bist",
    "FVorschlag1": "Günstigste verfügbare Forschung",
    "FVorschlag2": "Zweitgünstigste verfügbare Forschung",
    "FVorschlag3": "Drittgünstigste verfügbare Forschung",
    "FStromErzeugung": "Strom-Erzeugung des Netzes, in dem du stehst",
    "FStromVerbrauch": "Strom-Verbrauch des Netzes, in dem du stehst",
    "FMeldung": "Letzte Antwort des Spiels auf einen Befehl",
}
for _i in range(1, ITEM_SLOTS + 1):
    VALUES[f"FItem{_i}"] = f"Produktions-Platz {_i}: Item und Menge pro Minute"
# Gemerkte Auswahl der Plätze: bleibt nach einem Neustart erhalten (nicht zurücksetzen)
KEEP = {f"FItemWahl{_i}": f"Gewähltes Item für Platz {_i} (leer = automatisch)" for _i in range(1, ITEM_SLOTS + 1)}


def build():
    pages = [main_page(), time_page(), research_page(), chat_page(), game_page(), power_page(), production_page()]
    values = {name: {"default": "–", "description": f"{desc} (Plugin Factorio)", "folder": "Factorio",
                     "resetOnStart": True}
              for name, desc in VALUES.items()}
    values.update({name: {"default": "", "description": f"{desc} (Plugin Factorio)", "folder": "Factorio",
                          "resetOnStart": False}
                   for name, desc in KEEP.items()})
    return {
        "format": "touchdeck-profile", "formatVersion": 1, "app": "0.9.0",
        "name": "Factorio", "pages": pages, "flows": [], "events": events(),
        "values": values, "images": {},
    }


# ---------------------------------------------------------------- UTLogistics (eigenes Profil)

PAGE_UTL = "p_factorio_utl"
COLOR_UTL = "#1f2f3a"

UTL_VALUES = {
    "FUtlStatus": "UTLogistics: Version oder „nicht aktiv“",
    "FUtlZuegeFrei": "UTLogistics: freie Züge im Depot (dein Team)",
    "FUtlUnterwegs": "UTLogistics: laufende Lieferungen",
    "FUtlStationen": "UTLogistics: Stationen (dein Team)",
    "FUtlNetze": "UTLogistics: Netze auf deiner Fläche",
    "FUtlLieferungen": "UTLogistics: abgeschlossene Lieferungen, seit touchdeck-bridge mitzählt",
    "FUtlLieferungenStunde": "UTLogistics: abgeschlossene Lieferungen der letzten Stunde",
    "FUtlOhneZug": "UTLogistics: Anfragen, die ohne Zug warten",
    "FUtlOhneZugText": "UTLogistics: älteste Anfrage ohne Zug (Ware, Netz, Wartezeit)",
    "FUtlAuslastung": "UTLogistics: mittlere Auslastung der Züge",
    "FUtlWarnungen": "UTLogistics: Warnungen der letzten 10 Minuten",
    "FUtlWarnung": "UTLogistics: letzte Warnung (voller Text in Spielsprache)",
    "FUtlWare1": "UTLogistics: meistgelieferte Ware pro Stunde",
    "FUtlWare2": "UTLogistics: zweitmeist gelieferte Ware pro Stunde",
    "FUtlWare3": "UTLogistics: drittmeist gelieferte Ware pro Stunde",
}
GRAPH_UTL_TRAINS = {"graph": "line", "graphPoints": 90, "graphInterval": 10, "graphMin": 0, "graphAlign": "left"}
GRAPH_UTL_GOODS = {"graph": "stack", "graphPoints": 60, "graphInterval": 60, "graphMin": 0, "graphAlign": "left"}


GRAPH_UTL_RATE = {"graph": "bars", "graphPoints": 60, "graphInterval": 60, "graphMin": 0,
                  "graphColor": "#2f9e6b", "graphAlign": "left"}   # letzte Stunde, ein Balken je Minute


def utl_page():
    return page(PAGE_UTL, "UTLogistics", [
        button(0, 0, "{FUtlStatus}", [], icon="🚂", font=11, color=COLOR_UTL),
        button(0, 1, "Züge", [], span=2, live=plugin_live("utl_trains", graph=GRAPH_UTL_TRAINS),
               color=COLOR_LIVE, color_on="#2f4f6f"),
        button(0, 3, "Warnungen", key("utl_alerts"), icon="⚠️", live=plugin_live("utl_alerts"),
               color=COLOR_UTL, color_on="#c0392b", font=10),
        button(0, 4, "Manager\nöffnen", key("utl"), icon="📋", color=COLOR_GAME),
        button(1, 0, "Frei im Depot\n{FUtlZuegeFrei}", [], icon="🅿️", font=12),
        button(1, 1, "Unterwegs\n{FUtlUnterwegs}", [], icon="🚆", font=12),
        button(1, 2, "Stationen\n{FUtlStationen}", [], icon="🚉", font=12),
        button(1, 3, "Netze\n{FUtlNetze}", [], icon="🕸️", font=12),
        button(1, 4, "Auslastung\n{FUtlAuslastung}", [], icon="📈", font=12),
        button(2, 0, "Gelieferte Waren pro Stunde", [], span=3,
               live=plugin_live("utl_goods", graph=GRAPH_UTL_GOODS), color=COLOR_LIVE, color_on="#2f4f6f"),
        button(2, 3, "Lieferungen", [], span=2, live=plugin_live("utl_rate", graph=GRAPH_UTL_RATE),
               color=COLOR_LIVE, color_on="#1f3a2f"),
        button(3, 0, "{FUtlWarnung}", [], icon="🔔", span=3, font=10, color=COLOR_UTL),
        button(3, 3, "{FUtlOhneZugText}", key("utl"), icon="⏳", span=2, font=10,
               live=plugin_live("utl_unserved"), color=COLOR_UTL, color_on="#9e6b2f"),
    ], rows=4)


def build_utl():
    # Keine PC-Benachrichtigung: Die letzte Warnung steht ohnehin auf der Seite ({FUtlWarnung}).
    events = []
    values = {name: {"default": "–", "description": f"{desc} (Plugin Factorio)", "folder": "Factorio › UTL",
                     "resetOnStart": True}
              for name, desc in UTL_VALUES.items()}
    return {
        "format": "touchdeck-profile", "formatVersion": 1, "app": "0.10.0",
        "name": "UTLogistics", "pages": [utl_page()], "flows": [], "events": events,
        "values": values, "images": {},
    }


def write(path, profile):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("profile.json", json.dumps(profile, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name, profile in (("Factorio.tdprofile", build()), ("UTLogistics.tdprofile", build_utl())):
        write(os.path.join(root, name), profile)
        print(f"{os.path.join(root, name)} geschrieben")
