#!/usr/bin/env python3
"""Erzeugt Zwischenablage-Seite.tdprofile: eine fertige TouchDeck-Seite für das Plugin.

Aufruf:  python3 tools/make_profile.py [Anzahl Slots, Standard 12]
Import:  TouchDeck › Seitenliste › „⋯“ › Profil importieren.
Das Format (touchdeck-profile, Version 1) ist in touchdeck-rs/server/src/core/profiles.rs beschrieben.
"""
import json
import sys
import zipfile

PLUGIN = "plugin:clipboard-slots"
COLS = 6
FLOW_PASTE = "f_einfuegen"
FLOW_SLOT = "f_slot_einfuegen"


def action(kind, **params):
    return {"id": "", "type": kind, "enabled": True, "params": params}


def paste():
    # Das Einfügen steckt in der Vorlage „Einfügen“: dort einmal ändern (im Terminal ctrl+shift+v),
    # und alle Buttons folgen.
    return action("run_flow", flow=FLOW_PASTE)


def flows():
    return [
        {"id": FLOW_PASTE, "name": "Einfügen", "inputs": [],
         "actions": [action("hotkey", keys="ctrl+v")]},
        {"id": FLOW_SLOT, "name": "Slot einfügen", "inputs": [{"name": "Nummer", "default": "1"}],
         "actions": [action(f"{PLUGIN}:load-slot", slot="{Eingabe.Nummer}"), paste()]},
    ]


def button(row, col, title, actions, hold=None, color="#2b2f3a"):
    return {
        "id": f"b_{row}_{col}",
        "row": row, "col": col, "rowSpan": 1, "colSpan": 1,
        "title": title,
        "icon": {"type": "emoji", "value": ""},
        "color": color,
        "titlePos": "center",
        "fontSize": 13,
        "actions": actions,
        "holdActions": hold or [],
    }


def build(slots):
    buttons = []
    for n in range(1, slots + 1):
        row, col = divmod(n - 1, COLS)
        buttons.append(button(
            row, col, f"{n} · {{Slot{n}}}",
            actions=[action("run_flow", flow=FLOW_SLOT, **{"in:Nummer": str(n)})],
            hold=[action(f"{PLUGIN}:save-slot", slot=n)],
        ))
    row = (slots + COLS - 1) // COLS
    tools = [
        ("Davor\neinfügen", [action(f"{PLUGIN}:copy-history", entry=2), paste()], None),
        ("Davor-davor\neinfügen", [action(f"{PLUGIN}:copy-history", entry=3), paste()], None),
        ("Als eine Zeile\neinfügen", [action(f"{PLUGIN}:transform", mode="oneline"), paste()], None),
        ("Link säubern\nund einfügen", [action(f"{PLUGIN}:transform", mode="clean-url"), paste()], None),
        ("Verlauf\nleeren", [action(f"{PLUGIN}:clear", what="history")], None),
        ("Auto-Speichern\n{AutoSave}", [action(f"{PLUGIN}:auto-mode", mode="toggle")], None),
    ]
    for col, (title, acts, hold) in enumerate(tools):
        buttons.append(button(row, col, title, acts, hold, color="#3a3550"))
    page = {
        "id": "p_zwischenablage",
        "name": "Zwischenablage",
        "rows": row + 1, "cols": COLS,
        "layout": "grid",
        "buttons": buttons,
        "events": [],
    }
    values = {f"Slot{n}": {"default": "", "description": f"Vorschau Slot {n} (Plugin Zwischenablage-Slots)",
                           "folder": "Zwischenablage", "resetOnStart": False}
              for n in range(1, slots + 1)}
    values["AutoSave"] = {"default": "aus", "description": "Auto-Speichern an oder aus (Plugin Zwischenablage-Slots)",
                          "folder": "Zwischenablage", "resetOnStart": False}
    values["NextSlot"] = {"default": "1", "description": "Nächster Slot beim Auto-Speichern",
                          "folder": "Zwischenablage", "resetOnStart": False}
    return {
        "format": "touchdeck-profile", "formatVersion": 1, "app": "0.9.0",
        "name": "Zwischenablage", "pages": [page], "flows": flows(), "events": [],
        "values": values, "images": {},
    }


if __name__ == "__main__":
    n = max(1, min(50, int(sys.argv[1]))) if len(sys.argv) > 1 else 12
    with zipfile.ZipFile("Zwischenablage-Seite.tdprofile", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("profile.json", json.dumps(build(n), ensure_ascii=False, indent=2))
    print(f"Zwischenablage-Seite.tdprofile mit {n} Slots geschrieben")
