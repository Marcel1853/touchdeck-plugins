#!/usr/bin/env python3
"""Erzeugt RimWorld.tdprofile: fertige TouchDeck-Seiten für das Plugin „RimWorld“.

Aufruf:  python3 tools/make_profile.py
Import:  TouchDeck › Seitenliste › „⋯“ › Profil importieren (oder „Fertige Seiten“ in der Plugin-Karte).
Format (touchdeck-profile, Version 1): touchdeck-rs/server/src/core/profiles.rs und store.rs.

Aufbau: Hauptseite „RimWorld“ mit Live-Anzeigen und vier Ordnern (Zeit, Kolonisten, Meldungen, Spiel),
angelegt wie „Ordner hier erstellen“ im Editor (createFolder in web/editor/js/views/pages.js): eigene Seite
„RimWorld › …“ mit gleichem Raster und Zurück-Button oben links, auf der Hauptseite ein 📁-Button.
Was das Spiel weiß (Pause, alle eingezogen, Gefahr), zeigen Live-Anzeigen mit „an“-Look statt Umschalter,
die mit dem Spiel auseinanderlaufen könnten.
"""
import json
import os
import zipfile

PLUGIN = "plugin:rimworld"
WINDOW = "rimworld"               # Fensterklasse unter Linux: „RimWorldLinux“ (Vergleich: enthält, ohne Groß/klein)
ROWS, COLS = 4, 6                 # Hauptseite und alle Ordner: gleiche Rasterform wie createFolder

PAGE_MAIN = "p_rimworld"
PAGES = {"zeit": "p_rimworld_zeit", "kolonisten": "p_rimworld_kolonisten",
         "meldungen": "p_rimworld_meldungen", "spiel": "p_rimworld_spiel"}
FLOW_SPEED = "f_rimworld_tempo"
FLOW_JUMP = "f_rimworld_kolonist"
FLOW_MESSAGE = "f_rimworld_nachricht"
NAMES = 8

COLOR = "#2b2f3a"
COLOR_GAME = "#4a3a28"     # RimWorld-Braun
COLOR_FOLDER = "#3a3f4b"   # wie createFolder
COLOR_LIVE = "#1f3a2f"
COLOR_DANGER = "#c0392b"
COLOR_COLONIST = "#2f3b4a"

_ids = {"n": 0}


def action(type_, **params):
    return {"id": "", "type": type_, "enabled": True, "params": params}


def comment(text):
    return action("comment", text=text)


def rw(aid, **params):
    """Aktion des Plugins: plugin:rimworld:<id>."""
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
        "id": f"b_rimworld_{_ids['n']}",
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
    # folder: Ordner in der Seitenliste (eigene Gruppe „RimWorld“); ratioW/ratioH wie createFolder
    return {"id": pid, "name": name, "rows": ROWS, "cols": COLS, "layout": "grid", "folder": "RimWorld",
            "background": "#16140f", "ratioW": 16, "ratioH": 10, "colSizes": [], "rowSizes": [],
            "buttons": buttons, "events": events or []}


def back():
    # genau wie createFolder: Zeile 0, Spalte 0, ⬅️, #3a3f4b, go_page __back
    return button(0, 0, "Zurück", [action("go_page", page="__back")], icon="⬅️", color=COLOR_FOLDER)


def folder(row, col, title, pid):
    # wie createFolder: 📁 mit dem Ordnernamen, Aktion go_page auf die Unterseite
    return button(row, col, title, [action("go_page", page=pid)], icon="📁", color=COLOR_FOLDER)


def page_opened(*actions):
    """Logik der Seite: „Seite geöffnet“ (page_view ohne Seitenwahl = diese Seite, events.rs)."""
    return [{"id": f"pe_rimworld_{_ids['n']}", "enabled": True,
             "trigger": {"type": "page_view", "params": {"page": "", "state": "open"}}, "actions": list(actions)}]


# ---------------------------------------------------------------- wiederkehrende Buttons

def pause_button(row, col):
    # Zustand aus dem Spiel ({RWPause} = an/aus) statt Umschalter: Pause per Leertaste im Spiel bleibt richtig
    return button(row, col, "Pause", [rw("pause", op="toggle")], icon="⏸️", icon_on="▶️", title_on="Pausiert",
                  live=value_live("RWPause"), color=COLOR_GAME, color_on="#9e6b2f")


def speed_button(row, col, span=1):
    # Tippen = schneller, doppelt = langsamer, halten = zurück auf 1× (normal)
    return button(row, col, "Tempo", [rw("speed", op="up")], icon="⏩", span=span, live=plugin_live("speed"),
                  color=COLOR_GAME, color_on="#2f6f4f", double=[rw("speed", op="down")],
                  hold=[flow(FLOW_SPEED, Stufe=1)])


def save_button(row, col):
    # Tippen = Schnellspeicher, halten = eigener Spielstand mit Datum im Namen
    return button(row, col, "Speichern", [rw("save", name="")], icon="💾", color=COLOR_GAME,
                  hold=[rw("save", name="TouchDeck {RWDatum} {RWUhrzeit}")])


def draft_button(row, col, span=1):
    # „an“ nur, wenn wirklich alle eingezogen sind (Zustand aus dem Spiel, kein Umschalter)
    return button(row, col, "Einziehen", [rw("draft", op="toggle")], icon="🪖", span=span,
                  live=plugin_live("draft"), color=COLOR_COLONIST, color_on=COLOR_DANGER,
                  double=[rw("draft", op="off")], hold=[rw("draft", op="on")])


def next_colonist(row, col):
    # Tippen = nächster, doppelt = voriger, halten = alle 0,8 s weiter (Kolonisten durchsehen)
    return button(row, col, "Nächster", [rw("cycle", op="next")], icon="🔁", color=COLOR_COLONIST,
                  double=[rw("cycle", op="prev")], hold=[rw("cycle", op="next")], hold_repeat=800)


def danger_button(row, col):
    # rot, solange das Spiel Gefahr meldet; Tippen = Kamera zum letzten Brief
    return button(row, col, "Bedrohung", [rw("letter", op="jump")], icon="🛡️", icon_on="⚔️",
                  live=plugin_live("danger"), color=COLOR, color_on=COLOR_DANGER, double=[rw("letter", op="open")])


def letter_button(row, col, span=1):
    return button(row, col, "{RWBrief}", [rw("letter", op="jump")], icon="✉️", span=span, font=11,
                  double=[rw("letter", op="open")])


def tab_button(row, col, title, name, icon):
    return button(row, col, title, [rw("tab", name=name)], icon=icon, color=COLOR_FOLDER)


# ---------------------------------------------------------------- Seiten

def main_page():
    return page(PAGE_MAIN, "RimWorld", [
        button(0, 0, "", [], icon="🌍", live=plugin_live("status"), color=COLOR_LIVE, color_on="#2f6f4f", font=11),
        button(0, 1, "", [], icon="📅", span=2, live=plugin_live("date"), font=12),
        speed_button(0, 3),
        pause_button(0, 4),
        save_button(0, 5),
        button(1, 0, "Stimmung", [], icon="🙂", span=2, live=plugin_live("mood", bar=True),
               color=COLOR_LIVE, color_on=COLOR_DANGER),
        button(1, 2, "Forschung", [rw("tab", name="Research")], icon="🔬", span=2,
               live=plugin_live("research", bar=True), color=COLOR_LIVE, color_on="#2f5f8e"),
        button(1, 4, "Silber", [], icon="🪙", live=plugin_live("silver"), color=COLOR_LIVE),
        danger_button(1, 5),
        folder(2, 0, "Zeit", PAGES["zeit"]),
        folder(2, 1, "Kolonisten", PAGES["kolonisten"]),
        folder(2, 2, "Meldungen", PAGES["meldungen"]),
        folder(2, 3, "Spiel", PAGES["spiel"]),
        draft_button(2, 4),
        next_colonist(2, 5),
        button(3, 0, "{RWKolonisten} Kolonisten\n{RWGefangene} Gefangene", [], icon="👥", font=10),
        button(3, 1, "{RWWetter}\n{RWTemperatur}", [], icon="🌦️", font=11),
        button(3, 2, "Stahl {RWStahl} · Komp. {RWKomponenten}\nMedizin {RWMedizin} · Nahrung {RWNahrung}", [],
               icon="📦", span=2, font=10),
        letter_button(3, 4, span=2),
    ])


def time_page():
    buttons = [
        back(),
        pause_button(0, 1),
        speed_button(0, 2),
        button(0, 3, "{RWDatum}\n{RWUhrzeit}", [], icon="📅", span=2, font=12),
        save_button(0, 5),
    ]
    for i, (icon, label) in enumerate([("▶️", "1× normal"), ("⏩", "2× schnell"), ("⏭️", "3× superschnell"),
                                       ("🚀", "4× ultra\n(Entwicklermodus)")]):
        buttons.append(button(1, i, label, [flow(FLOW_SPEED, Stufe=i + 1)], icon=icon, color=COLOR_GAME,
                              font=12 if i < 3 else 10))
    buttons += [
        button(1, 4, "Langsamer", [rw("speed", op="down")], icon="🐢", color=COLOR_GAME),
        # halten = schrittweise schneller (alle 0,6 s eine Stufe)
        button(1, 5, "Schneller", [rw("speed", op="up")], icon="🐇", color=COLOR_GAME,
               hold=[rw("speed", op="up")], hold_repeat=600),
        button(2, 0, "Pause an", [rw("pause", op="on")], icon="⏸️", color=COLOR_GAME),
        button(2, 1, "Weiter", [rw("pause", op="off")], icon="▶️", color=COLOR_GAME),
        # „Kurz anhalten“: solange gedrückt Pause, beim Loslassen geht es weiter
        button(2, 2, "Halten =\nkurz Pause", [], icon="✋", color=COLOR_GAME, font=11,
               hold=[rw("pause", op="on")], release=[rw("pause", op="off")]),
        button(2, 3, "", [], icon="⏩", span=3, live=plugin_live("speed"), color=COLOR_LIVE, color_on="#2f6f4f"),
    ]
    return page(PAGES["zeit"], "RimWorld › Zeit", buttons)


def colonists_page():
    buttons = [
        back(),
        draft_button(0, 1),
        button(0, 2, "Alle\neinziehen", [rw("draft", op="on")], icon="⚔️", color=COLOR_COLONIST, font=12),
        button(0, 3, "Alle\nfreigeben", [rw("draft", op="off")], icon="🏳️", color=COLOR_COLONIST, font=12),
        next_colonist(0, 4),
        danger_button(0, 5),
    ]
    # Kolonist 1–8 in der Reihenfolge der Kolonistenleiste; Name aus {RWKolonistN}
    for i in range(NAMES):
        n = i + 1
        buttons.append(button(1 + i // 4, i % 4, f"{{RWKolonist{n}}}", [flow(FLOW_JUMP, Nr=n)], icon="🧑",
                              color=COLOR_COLONIST, font=12))
    buttons += [
        button(1, 4, "Stimmung", [], icon="🙂", span=2, live=plugin_live("mood", bar=True),
               color=COLOR_LIVE, color_on=COLOR_DANGER),
        button(2, 4, "{RWKolonisten} Kolonisten\n{RWEingezogen} eingezogen", [], icon="👥", span=2, font=11),
        button(3, 0, "Voriger", [rw("cycle", op="prev")], icon="◀️", color=COLOR_COLONIST),
        button(3, 1, "Arbeit", [rw("tab", name="Work")], icon="🛠️", color=COLOR_FOLDER),
        button(3, 2, "Zeitplan", [rw("tab", name="Schedule")], icon="🗓️", color=COLOR_FOLDER),
        button(3, 3, "Zuweisen", [rw("tab", name="Assign")], icon="📋", color=COLOR_FOLDER),
        button(3, 4, "Stimmung Ø {RWStimmungSchnitt} %\nniedrigste {RWStimmungMin} %", [], icon="📊", span=2, font=10),
    ]
    # Beim Öffnen einmal den Zustand holen, damit Namen und Zahlen sofort stimmen
    return page(PAGES["kolonisten"], "RimWorld › Kolonisten", buttons,
                events=page_opened(comment("Beim Öffnen den aktuellen Stand aus dem Spiel holen."), rw("refresh")))


QUICK = [
    ("Alle in Deckung!", "🛡️", "threat"),
    ("Essenszeit!", "🍲", "neutral"),
    ("Gut gemacht, Leute!", "👍", "positive"),
    ("Feierabend – ab ins Bett!", "🛏️", "neutral"),
    ("Überfall kommt!", "⚔️", "threat"),
    ("Kolonie: {RWKolonisten} Leute, Stimmung ab {RWStimmungMin} %", "📊", "neutral"),
]


def messages_page():
    buttons = [
        back(),
        letter_button(0, 1, span=3),
        danger_button(0, 4),
        button(0, 5, "Aufträge", [rw("tab", name="Quests")], icon="📜", color=COLOR_FOLDER),
    ]
    for i, (text, icon, kind) in enumerate(QUICK):
        buttons.append(button(1 + i // 3, (i % 3) * 2, text, [flow(FLOW_MESSAGE, Text=text, Art=kind)], icon=icon,
                              span=2, font=11, color=COLOR_GAME))
    buttons += [
        button(3, 0, "Hinweis: Eigene Texte als Kopie eines Buttons, nur den Text der Vorlage-Eingabe ändern.",
               [], span=4, font=9, color=COLOR_FOLDER),
        button(3, 4, "Verlauf", [rw("tab", name="History")], icon="📖", color=COLOR_FOLDER),
        button(3, 5, "Fraktionen", [rw("tab", name="Factions")], icon="🏳️", color=COLOR_FOLDER),
    ]
    return page(PAGES["meldungen"], "RimWorld › Meldungen", buttons)


def game_page():
    return page(PAGES["spiel"], "RimWorld › Spiel", [
        back(),
        button(0, 1, "Verbunden: {RWVerbunden}", [rw("refresh")], icon="🔌", span=2, live=plugin_live("status"),
               color=COLOR_LIVE, color_on="#2f6f4f", font=11),
        button(0, 3, "{RWKolonie}\n{RWKarte}", [], icon="🏠", span=2, font=11),
        button(0, 5, "Spielstand\n{RWSpielstand}", [], icon="📁", font=10),
        button(1, 0, "Schnell-\nspeichern", [rw("save", name="")], icon="💾", color=COLOR_GAME, font=12),
        button(1, 1, "Speichern\nmit Datum", [rw("save", name="TouchDeck {RWDatum} {RWUhrzeit}")], icon="🗂️",
               color=COLOR_GAME, font=12),
        button(1, 2, "Screenshot", [rw("screenshot")], icon="📸", color=COLOR_GAME),
        button(1, 3, "Zustand\nabfragen", [rw("refresh")], icon="🔄", color=COLOR_FOLDER, font=12),
        pause_button(1, 4),
        speed_button(1, 5),
        tab_button(2, 0, "Arbeit", "Work", "🛠️"),
        tab_button(2, 1, "Zeitplan", "Schedule", "🗓️"),
        tab_button(2, 2, "Zuweisen", "Assign", "📋"),
        tab_button(2, 3, "Tiere", "Animals", "🐄"),
        tab_button(2, 4, "Forschung", "Research", "🔬"),
        tab_button(2, 5, "Welt", "World", "🗺️"),
        button(3, 0, "Forschung", [rw("tab", name="Research")], icon="🔬", span=3,
               live=plugin_live("research", bar=True), color=COLOR_LIVE, color_on="#2f5f8e"),
        tab_button(3, 3, "Architekt", "Architect", "🏗️"),
        tab_button(3, 4, "Menü", "Menu", "☰"),
        letter_button(3, 5),
    ])


# ---------------------------------------------------------------- Vorlagen, Events, Werte

def flows():
    return [
        {"id": FLOW_SPEED, "name": "RimWorld: Tempo setzen", "folder": "RimWorld",
         "inputs": [{"name": "Stufe", "default": "1"}],
         "actions": [comment("Tempo 1–4 setzen (4 nur im Entwicklermodus). Hebt die Pause auf, wie im Spiel."),
                     rw("speed", op="set", value="{Eingabe.Stufe}")]},
        {"id": FLOW_JUMP, "name": "RimWorld: Kolonist springen", "folder": "RimWorld",
         "inputs": [{"name": "Nr", "default": "1"}],
         "actions": [comment("Kamera zu Kolonist Nr. (Reihenfolge der Kolonistenleiste) und auswählen."),
                     rw("jump", n="{Eingabe.Nr}")]},
        {"id": FLOW_MESSAGE, "name": "RimWorld: Nachricht senden", "folder": "RimWorld",
         "inputs": [{"name": "Text", "default": "Hallo aus TouchDeck!"}, {"name": "Art", "default": "neutral"}],
         "actions": [comment("Text oben links im Spiel einblenden. Art: neutral, positive, negative oder threat. "
                             "Platzhalter wie {RWKolonisten} werden vorher ersetzt."),
                     rw("message", text="{Eingabe.Text}", kind="{Eingabe.Art}")]},
    ]


def events():
    return [
        {"id": "ev_rimworld_fokus", "name": "RimWorld im Vordergrund → Seite RimWorld", "folder": "RimWorld",
         "enabled": True, "trigger": {"type": "app_focus", "params": {"app": WINDOW, "once": True}}, "cooldown": 0,
         "actions": [action("deck_show_page", page=PAGE_MAIN)]},
        {"id": "ev_rimworld_ueberfall", "name": "RimWorld: Überfall → Benachrichtigung", "folder": "RimWorld",
         "enabled": True, "trigger": {"type": f"{PLUGIN}:raid", "params": {}}, "cooldown": 5,
         "actions": [action("notify", title="⚔️ RimWorld: {Event.Titel}", body="{Event.Text}", target="pc")]},
        {"id": "ev_rimworld_tod", "name": "RimWorld: Kolonist gestorben → Benachrichtigung", "folder": "RimWorld",
         "enabled": True, "trigger": {"type": f"{PLUGIN}:colonist_died", "params": {}}, "cooldown": 0,
         "actions": [action("notify", title="🪦 RimWorld", body="{Event.Name} ist gestorben.", target="pc")]},
    ]


VALUES = {
    "RWStatus": "Zustand: läuft, pausiert, Hauptmenü, nicht erreichbar",
    "RWVerbunden": "ja/nein: Verbindung zum Mod steht",
    "RWImSpiel": "ja/nein: ein Spiel ist geladen (nicht Hauptmenü)",
    "RWDatum": "Datum im Spiel (Sprache des Spiels)",
    "RWUhrzeit": "Uhrzeit im Spiel (volle Stunde)",
    "RWTempo": "Tempo 0–4 (1 = normal)",
    "RWPause": "an/aus",
    "RWKolonisten": "Freie Kolonisten auf der aktuellen Karte",
    "RWGefangene": "Gefangene auf der aktuellen Karte",
    "RWStimmungMin": "Niedrigste Stimmung in Prozent",
    "RWStimmungSchnitt": "Durchschnittliche Stimmung in Prozent",
    "RWEingezogen": "Eingezogen/einziehbar, z. B. 2/5",
    "RWSilber": "Silber im Lager",
    "RWStahl": "Stahl im Lager",
    "RWKomponenten": "Komponenten im Lager",
    "RWMedizin": "Medizin im Lager (alle Sorten)",
    "RWNahrung": "Nährwert essbarer Vorräte",
    "RWForschung": "Aktuelle Forschung",
    "RWForschungProzent": "Fortschritt der Forschung (0–100)",
    "RWWetter": "Wetter auf der Karte",
    "RWTemperatur": "Außentemperatur der Karte (Einheit wie im Spiel)",
    "RWKarte": "Name der aktuellen Karte",
    "RWKolonie": "Name der Kolonie (Fraktion)",
    "RWSpielstand": "Zuletzt gespeicherter oder geladener Spielstand",
    "RWBedrohung": "ruhig, Gefahr, große Gefahr",
    "RWBrief": "Titel des letzten Briefs",
}
for _i in range(1, NAMES + 1):
    VALUES[f"RWKolonist{_i}"] = f"Kolonist {_i} der Kolonistenleiste"


def build():
    pages = [main_page(), time_page(), colonists_page(), messages_page(), game_page()]
    values = {name: {"default": "nein" if name in ("RWVerbunden", "RWImSpiel") else "–",
                     "description": f"{desc} (Plugin RimWorld)", "folder": "RimWorld", "resetOnStart": True}
              for name, desc in VALUES.items()}
    return {
        "format": "touchdeck-profile", "formatVersion": 1, "app": "0.12.0",
        "name": "RimWorld", "pages": pages, "flows": flows(), "events": events(),
        "values": values, "images": {},
    }


def write(path, profile):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("profile.json", json.dumps(profile, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "RimWorld.tdprofile")
    write(path, build())
    print(f"{path} geschrieben")
