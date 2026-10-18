#!/usr/bin/env python3
"""Prüft Factorio.tdprofile gegen die Regeln von TouchDeck (store.rs, profiles.rs, Katalog).

Aufruf:  python3 tests/check_profile.py [Pfad zu touchdeck-rs/server/catalog]
Ohne Katalogpfad werden nur Aufbau, Überlappung, Werte und Verweise geprüft.
"""
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERRORS = []


def err(msg):
    ERRORS.append(msg)


def valid_value_name(name):           # store.rs: valid_variable_name
    return 1 <= len(name) <= 40 and all(c.isalpha() or c.isdigit() or c in " _.-" for c in name)


TOP_PAGES = {"p_factorio", "p_factorio_utl"}   # Hauptseiten ohne Zurück-Button


def main():
    catalog = sys.argv[1] if len(sys.argv) > 1 else None
    for name in ("Factorio.tdprofile", "UTLogistics.tdprofile"):
        print(f"— {name}")
        check_file(name, catalog)
    for e in ERRORS:
        print("FEHLER", e)
    sys.exit(1 if ERRORS else 0)


def check_file(file, catalog):
    with zipfile.ZipFile(os.path.join(ROOT, file)) as z:
        names = z.namelist()
        prof = json.loads(z.read("profile.json"))
    plugin = json.load(open(os.path.join(ROOT, "plugin.json"), encoding="utf-8"))

    if names != ["profile.json"]:
        err(f"unerwartete Dateien im ZIP: {names}")
    if prof.get("format") != "touchdeck-profile" or prof.get("formatVersion") != 1:
        err("format/formatVersion falsch")

    actions = {}
    triggers = {}
    lives = set()
    if catalog:
        actions = {a["type"]: {f["key"] for f in a.get("fields", [])} for a in json.load(open(os.path.join(catalog, "actions.json")))}
        triggers = {a["type"]: {f["key"] for f in a.get("fields", [])} for a in json.load(open(os.path.join(catalog, "triggers.json")))}
        lives = {s["value"] for s in json.load(open(os.path.join(catalog, "live.json")))["liveSources"]}
    for a in plugin["actions"]:
        actions[f"plugin:factorio:{a['id']}"] = {f["key"] for f in a["fields"]}
    for tr in plugin["triggers"]:
        triggers[f"plugin:factorio:{tr['id']}"] = {f["key"] for f in tr["fields"]}
    plugin_lives = {f"plugin:factorio:{x['id']}" for x in plugin["lives"]}

    page_ids = {p["id"] for p in prof["pages"]}
    flow_ids = {f["id"] for f in prof["flows"]}
    flow_inputs = {f["id"]: {i["name"] for i in f["inputs"]} for f in prof["flows"]}
    values = set(prof["values"])

    def check_actions(where, lst):
        for a in lst:
            kind = a.get("type")
            if catalog or kind.startswith("plugin:"):
                if kind not in actions:
                    err(f"{where}: unbekannter Aktionstyp {kind}")
                    continue
                for k in a["params"]:
                    if k.startswith("in:"):
                        if k[3:] not in flow_inputs.get(a["params"].get("flow"), set()):
                            err(f"{where}: Vorlage hat keine Eingabe {k[3:]}")
                    elif k not in actions[kind]:
                        err(f"{where}: Aktion {kind} kennt kein Feld {k}")
            if kind in ("go_page", "deck_show_page"):
                target = a["params"].get("page")
                if target not in page_ids and target not in ("__back", "__next", "__prev"):
                    err(f"{where}: Seite {target} fehlt")
            if kind == "run_flow" and a["params"].get("flow") not in flow_ids:
                err(f"{where}: Vorlage {a['params'].get('flow')} fehlt")
            for v in a["params"].values():
                for ref in re.findall(r"\{([A-Za-z][A-Za-z0-9_]*)\}", str(v)):
                    if ref.startswith("F") and ref not in values:
                        err(f"{where}: Wert {{{ref}}} nicht angelegt")

    for p in prof["pages"]:
        rows, cols = p["rows"], p["cols"]
        if not (1 <= rows <= 12 and 1 <= cols <= 16):
            err(f"{p['name']}: Raster {rows}×{cols} außerhalb 12×16")
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
            for ref in re.findall(r"\{([A-Za-z][A-Za-z0-9_]*)\}", b["title"]):
                if ref not in values:
                    err(f"{where}: Wert {{{ref}}} nicht angelegt")
            live = b.get("live")
            if live:
                src = live["source"]
                if src.startswith("plugin:"):
                    if src not in plugin_lives:
                        err(f"{where}: Live-Anzeige {src} nicht in plugin.json")
                elif catalog and src not in lives:
                    err(f"{where}: Live-Quelle {src} unbekannt")
                if live.get("graph", "") not in ("", "line", "area", "stack", "bars"):
                    err(f"{where}: Graph-Art {live['graph']} unbekannt")
                if live.get("graph") and not (10 <= live.get("graphPoints", 60) <= 300 and 1 <= live.get("graphInterval", 2) <= 3600):
                    err(f"{where}: Graph-Punkte/-Abstand außerhalb der Grenzen")
                if src == "variable" and live["variable"] not in values:
                    err(f"{where}: Live-Wert {live['variable']} nicht angelegt")
            if b.get("mode") == "display" and any(b.get(k) for k in ("actions", "holdActions", "releaseActions", "doubleActions")):
                err(f"{where}: Anzeige-Button mit Aktionen")
            for key in ("actions", "holdActions", "releaseActions", "doubleActions"):
                check_actions(f"{where} [{key}]", b.get(key, []))
        if p["id"] not in TOP_PAGES and not any(b["row"] == 0 and b["col"] == 0 and
                                              b["actions"] == [{"id": "", "type": "go_page", "enabled": True,
                                                                "params": {"page": "__back"}}]
                                              for b in p["buttons"]):
            err(f"{p['name']}: Zurück-Button oben links fehlt")
    for f in prof["flows"]:
        check_actions(f"Vorlage {f['name']}", f["actions"])
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

    n_buttons = sum(len(p["buttons"]) for p in prof["pages"])
    print(f"{len(prof['pages'])} Seiten, {n_buttons} Buttons, {len(prof['flows'])} Vorlage(n), "
          f"{len(prof['events'])} Events, {len(values)} Werte – {len(ERRORS)} Fehler"
          + ("" if catalog else " (ohne Katalog geprüft)"))


if __name__ == "__main__":
    main()
