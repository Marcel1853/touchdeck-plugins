#!/usr/bin/env python3
"""Prüft „Timberborn (English).tdprofile“ und „Timberborn (Deutsch).tdprofile“ gegen die Regeln von TouchDeck (store.rs, profiles.rs, Katalog, createFolder).

Aufruf:  python3 tests/check_profile.py [Pfad zu touchdeck-rs/server/catalog]
Ohne Katalogpfad werden nur Aufbau, Überlappung, Werte, Ordner und Verweise geprüft.
"""
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERRORS = []
TOP_PAGE = "p_timberborn"
FILES = {"Timberborn (English).tdprofile": "Back", "Timberborn (Deutsch).tdprofile": "Zurück"}   # Datei → Titel des Zurück-Buttons
BACK = {"icon": {"type": "emoji", "value": "⬅️"}, "color": "#3a3f4b",
        "actions": [{"id": "", "type": "go_page", "enabled": True, "params": {"page": "__back"}}]}


def err(msg):
    ERRORS.append(msg)


def valid_value_name(name):           # store.rs: valid_variable_name
    return 1 <= len(name) <= 40 and all(c.isalpha() or c.isdigit() or c in " _.-" for c in name)


def main():
    catalog = sys.argv[1] if len(sys.argv) > 1 else None
    for file, back_title in FILES.items():
        print(f"— {file}")
        before = len(ERRORS)
        check_file(file, back_title, catalog)
        for e in ERRORS[before:]:
            print("FEHLER", e)
    sys.exit(1 if ERRORS else 0)


def check_file(file, back_title, catalog):
    errors_before = len(ERRORS)
    with zipfile.ZipFile(os.path.join(ROOT, file)) as z:
        names = z.namelist()
        prof = json.loads(z.read("profile.json"))
    plugin = json.load(open(os.path.join(ROOT, "plugin.json"), encoding="utf-8"))

    if names != ["profile.json"]:
        err(f"unerwartete Dateien im ZIP: {names}")
    if prof.get("format") != "touchdeck-profile" or prof.get("formatVersion") != 1:
        err("format/formatVersion falsch")

    actions, triggers, lives = {}, {}, set()
    if catalog:
        actions = {a["type"]: {f["key"] for f in a.get("fields", [])} for a in json.load(open(os.path.join(catalog, "actions.json")))}
        triggers = {a["type"]: {f["key"] for f in a.get("fields", [])} for a in json.load(open(os.path.join(catalog, "triggers.json")))}
        lives = {s["value"] for s in json.load(open(os.path.join(catalog, "live.json")))["liveSources"]}
    for a in plugin["actions"]:
        actions[f"plugin:timberborn:{a['id']}"] = {f["key"] for f in a["fields"]}
    for tr in plugin["triggers"]:
        triggers[f"plugin:timberborn:{tr['id']}"] = {f["key"] for f in tr["fields"]}
    plugin_lives = {f"plugin:timberborn:{x['id']}" for x in plugin["lives"]}
    select_values = {f"plugin:timberborn:{a['id']}": {f["key"]: {o["value"] for o in f["options"]}
                                                     for f in a["fields"] if f["type"] == "select"}
                     for a in plugin["actions"]}

    pages = {p["id"]: p for p in prof["pages"]}
    flow_ids = {f["id"] for f in prof["flows"]}
    flow_inputs = {f["id"]: {i["name"] for i in f["inputs"]} for f in prof["flows"]}
    values = set(prof["values"])
    used_flows = set()
    opened_pages = set()

    def check_refs(where, text):
        for ref in re.findall(r"\{([A-Za-z][A-Za-z0-9_]*)\}", str(text)):
            if ref.startswith("TB") and ref not in values:
                err(f"{where}: Wert {{{ref}}} nicht angelegt")

    def check_actions(where, lst, flow=None):
        for a in lst:
            kind = a.get("type")
            if catalog or kind.startswith("plugin:"):
                if kind not in actions:
                    err(f"{where}: unbekannter Aktionstyp {kind}")
                    continue
                for k, v in a["params"].items():
                    if k.startswith("in:"):
                        if k[3:] not in flow_inputs.get(a["params"].get("flow"), set()):
                            err(f"{where}: Vorlage hat keine Eingabe {k[3:]}")
                    elif k not in actions[kind]:
                        err(f"{where}: Aktion {kind} kennt kein Feld {k}")
                    elif k in select_values.get(kind, {}) and "{" not in str(v) and v not in select_values[kind][k]:
                        err(f"{where}: {kind}.{k} = {v!r} ist keine Auswahl in plugin.json")
            if kind in ("go_page", "deck_show_page"):
                target = a["params"].get("page")
                if target not in pages and target not in ("__back", "__next", "__prev"):
                    err(f"{where}: Seite {target} fehlt")
                opened_pages.add(target)
            if kind == "run_flow":
                if a["params"].get("flow") not in flow_ids:
                    err(f"{where}: Vorlage {a['params'].get('flow')} fehlt")
                used_flows.add(a["params"].get("flow"))
            for v in a["params"].values():
                check_refs(where, v)
                for ref in re.findall(r"\{(?:Eingabe|Input)\.([^}]+)\}", str(v)):
                    if flow is None or ref not in flow_inputs[flow]:
                        err(f"{where}: {{Eingabe.{ref}}} ohne passende Eingabe der Vorlage")

    for p in prof["pages"]:
        rows, cols = p["rows"], p["cols"]
        if not (1 <= rows <= 12 and 1 <= cols <= 16):
            err(f"{p['name']}: Raster {rows}×{cols} außerhalb 12×16")
        if rows * cols < 12:
            err(f"{p['name']}: Raster {rows}×{cols} zu klein")
        if not p["id"].startswith("p_"):
            err(f"{p['name']}: Seiten-ID ohne Präfix p_")
        taken = {}
        for b in p["buttons"]:
            where = f"{p['name']} / {b['title']!r}"
            r, c, rs, cs = b["row"], b["col"], b["rowSpan"], b["colSpan"]
            if not (0 <= r < rows and 0 <= c < cols) or r + rs > rows or c + cs > cols:
                err(f"{where}: liegt außerhalb der Seite")
            for cell in [(rr, cc) for rr in range(r, r + rs) for cc in range(c, c + cs)]:
                if cell in taken:
                    err(f"{where}: überlappt {taken[cell]!r}")
                taken[cell] = b["title"]
            if len(b["title"]) > 200:
                err(f"{where}: Titel zu lang")
            check_refs(where, b["title"])
            live = b.get("live")
            if live:
                src = live["source"]
                if src.startswith("plugin:"):
                    if src not in plugin_lives:
                        err(f"{where}: Live-Anzeige {src} nicht in plugin.json")
                elif catalog and src not in lives:
                    err(f"{where}: Live-Quelle {src} unbekannt")
                if src == "variable" and live["variable"] not in values:
                    err(f"{where}: Live-Wert {live['variable']} nicht angelegt")
            if b.get("mode") == "display" and any(b.get(k) for k in ("actions", "holdActions", "releaseActions", "doubleActions")):
                err(f"{where}: Anzeige-Button mit Aktionen")
            if b.get("mode") not in ("press", "display"):
                err(f"{where}: unerwarteter Modus {b.get('mode')}")
            if b.get("releaseActions") and not b.get("holdActions"):
                err(f"{where}: Loslassen ohne Halten")
            if b.get("holdRepeat") and not b.get("holdActions"):
                err(f"{where}: Wiederholung ohne Halten")
            for key in ("actions", "holdActions", "releaseActions", "doubleActions"):
                check_actions(f"{where} [{key}]", b.get(key, []))
        for e in p.get("events", []):
            if e["trigger"]["type"] != "page_view":
                err(f"{p['name']}: Seiten-Event mit {e['trigger']['type']}")
            check_actions(f"{p['name']} [Seiten-Logik]", e["actions"])

    # Ordner wie createFolder: Unterseite „<Eltern> › <Name>“, gleiches Raster, Zurück oben links,
    # auf der Elternseite ein 📁-Button mit dem Ordnernamen
    main_page = pages.get(TOP_PAGE)
    if not main_page:
        err("Hauptseite fehlt")
    else:
        for pid, p in pages.items():
            if pid == TOP_PAGE:
                continue
            parent, _, name = p["name"].partition(" › ")
            if parent != main_page["name"] or not name:
                err(f"{p['name']}: Name nicht „{main_page['name']} › …“")
            if (p["rows"], p["cols"]) != (main_page["rows"], main_page["cols"]):
                err(f"{p['name']}: anderes Raster als die Elternseite")
            first = [b for b in p["buttons"] if b["row"] == 0 and b["col"] == 0]
            if not first or first[0]["title"] != back_title or any(first[0].get(k) != v for k, v in BACK.items()):
                err(f"{p['name']}: Zurück-Button oben links nicht wie createFolder")
            openers = [b for b in main_page["buttons"]
                       if b["actions"] == [{"id": "", "type": "go_page", "enabled": True, "params": {"page": pid}}]]
            if not openers or openers[0]["title"] != name or openers[0]["icon"]["value"] != "📁":
                err(f"{p['name']}: 📁-Button „{name}“ auf der Hauptseite fehlt")
    for pid in pages:
        if pid != TOP_PAGE and pid not in opened_pages:
            err(f"Seite {pid} ist von nirgends erreichbar")

    for f in prof["flows"]:
        check_actions(f"Vorlage {f['name']}", f["actions"], flow=f["id"])
        if f["id"] not in used_flows:
            err(f"Vorlage {f['name']} wird nirgends benutzt")
    for e in prof["events"]:
        kind = e["trigger"]["type"]
        if (catalog or kind.startswith("plugin:")) and kind not in triggers:
            err(f"Event {e['name']}: unbekannter Auslöser {kind}")
        elif kind in triggers:
            for k in e["trigger"]["params"]:
                if k not in triggers[kind]:
                    err(f"Event {e['name']}: Auslöser {kind} kennt kein Feld {k}")
        check_actions(f"Event {e['name']}", e["actions"])
    for name in values:
        if not valid_value_name(name):
            err(f"Wertname ungültig: {name}")

    # Alle Werte, die das Plugin setzt, sind im Profil angelegt
    src = open(os.path.join(ROOT, "plugin.py"), encoding="utf-8").read()
    for name in set(re.findall(r'"(TB[A-Za-z]+\d*)"', src)) | {f"TBMeldung{i}" for i in range(1, 9)} | {f"TBWarnung{i}" for i in range(1, 9)}:
        if name not in values:
            err(f"Plugin setzt {name}, im Profil nicht angelegt")

    n_buttons = sum(len(p["buttons"]) for p in prof["pages"])
    print(f"{len(prof['pages'])} Seiten, {n_buttons} Buttons, {len(prof['flows'])} Vorlagen, "
          f"{len(prof['events'])} Events, {len(values)} Werte – {len(ERRORS) - errors_before} Fehler"
          + ("" if catalog else " (ohne Katalog geprüft)"))


if __name__ == "__main__":
    main()
