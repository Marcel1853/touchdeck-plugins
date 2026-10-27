#!/usr/bin/env python3
"""Tests für plugin.py gegen den Fake-Mod (tests/fake_mod.py). Nur Standardbibliothek.

Aufruf:  python3 tests/test_plugin.py
Startet plugin.py wie TouchDeck (JSON-Zeilen über stdin/stdout) und prüft, was ankommt:
Hallo, Zustand, Werte, Live-Anzeigen, Wetter-Countdown, Vorräte, Nachrichtenverlauf, Warnungen,
Ereignisse, Befehle mit Antwort, Timeout, Abbruch mit Neuverbindung, kaputte Zeilen, falsches
Geheimwort und ungültige Einstellungen.
"""
import json
import os
import queue
import subprocess
import sys
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from fake_mod import FakeMod  # noqa: E402


class PluginProcess:
    """plugin.py als Kindprozess, so wie TouchDeck ihn startet."""

    def __init__(self, settings, env_extra=None):
        env = dict(os.environ, LANG="de_DE.UTF-8", LC_ALL="", LC_MESSAGES="", TIMBERBORN_DEAD_AFTER="3")
        env.update(env_extra or {})
        self.p = subprocess.Popen([sys.executable, os.path.join(ROOT, "plugin.py")], cwd=ROOT, env=env,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, encoding="utf-8", bufsize=1)
        self.out = queue.Queue()
        self.values = {}
        self.lives = {}
        self.fired = []
        self.logs = []
        self.results = {}
        self.stderr = []
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._read_err, daemon=True).start()
        self.send({"type": "start", "plugin": {"id": "timberborn"}, "settings": settings, "touchdeck": "0.12.0"})

    def _read(self):
        for line in self.p.stdout:
            msg = json.loads(line)   # jede Zeile muss gültiges JSON sein
            kind = msg.get("type")
            if kind == "setValue":
                self.values[msg["name"]] = msg["value"]
            elif kind == "call" and msg.get("op") == "live.set":
                self.lives[msg["args"]["id"]] = msg["args"]["value"]
            elif kind == "fire":
                self.fired.append((msg["trigger"], msg["data"]))
            elif kind == "log":
                self.logs.append((msg["level"], msg["message"]))
            elif kind == "result":
                self.results[msg["requestId"]] = msg
            self.out.put(msg)

    def _read_err(self):
        for line in self.p.stderr:
            self.stderr.append(line)

    def send(self, msg):
        self.p.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self.p.stdin.flush()

    def wait(self, cond, timeout=6.0, what=""):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if cond():
                return True
            time.sleep(0.02)
        raise AssertionError(f"Zeitüberschreitung: {what}\nWerte: {self.values}\nLogs: {self.logs[-8:]}")

    def action(self, aid, params=None, timeout=8.0):
        rid = f"r_{aid}_{time.monotonic_ns()}"
        self.send({"type": "action", "requestId": rid, "id": aid, "params": params or {}, "info": {}})
        self.wait(lambda: rid in self.results, timeout, f"Ergebnis für {aid}")
        return self.results[rid]

    def stop(self):
        try:
            self.send({"type": "stop"})
            self.p.wait(3)
        except Exception:
            self.p.kill()
            self.p.wait(3)
        for pipe in (self.p.stdin, self.p.stdout, self.p.stderr):
            try:
                pipe.close()
            except (OSError, ValueError):
                pass
        assert not self.stderr, "".join(self.stderr)


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.mod = FakeMod()
        self.pl = PluginProcess({"host": "127.0.0.1", "port": self.mod.port, "secret": "", "timeout": 2})

    def tearDown(self):
        self.pl.stop()
        self.mod.close()

    def connected(self):
        self.pl.wait(lambda: self.pl.values.get("TBVerbunden") == "ja", what="verbunden")
        self.pl.wait(lambda: self.pl.values.get("TBImSpiel") == "ja", what="im Spiel")

    def test_hello_state_values_and_lives(self):
        self.connected()
        hello = self.mod.hellos[0]
        self.assertEqual(hello["type"], "hello")
        self.assertEqual(hello["proto"], 1)
        self.assertTrue(hello["client"].startswith("touchdeck-timberborn/"))
        self.assertIn(("connected", {}), self.pl.fired)
        v = self.pl.values
        self.assertEqual(v["TBZyklus"], "4")
        self.assertEqual(v["TBTag"], "3")
        self.assertEqual(v["TBUhrzeit"], "14:30")
        self.assertEqual(v["TBDatum"], "Zyklus 4 · Tag 3")
        self.assertEqual(v["TBTempo"], "1")
        self.assertEqual(v["TBPause"], "aus")
        self.assertEqual(v["TBBiber"], "23")
        self.assertEqual(v["TBBevoelkerung"], "25")
        self.assertEqual(v["TBObdachlos"], "2")
        self.assertEqual(v["TBArbeitslos"], "3")
        self.assertEqual(v["TBVerseucht"], "0")
        self.assertEqual(v["TBZufriedenheit"], "7")
        self.assertEqual(v["TBWissenschaft"], "1234")
        self.assertEqual(v["TBWasser"], "160")
        self.assertEqual(v["TBWasserTage"], "2,4")
        self.assertEqual(v["TBNahrungTage"], "9,5")
        self.assertEqual(v["TBFraktion"], "Folktails")
        self.assertEqual(v["TBSiedlung"], "Biberbach")
        # Live-Anzeigen in der Form, die TouchDeck erwartet: text, value (0–100 oder None), on
        L = self.pl.lives
        self.assertEqual(L["date"], {"text": "Zyklus 4 · Tag 3\n14:30", "value": None, "on": False})
        self.assertEqual(L["speed"], {"text": "Tempo 1 (×1)", "value": None, "on": True})
        self.assertEqual(L["population"]["text"], "23 Biber\n18 erw. · 5 Kinder · 2 Bots")
        self.assertEqual(L["homeless"], {"text": "2 obdachlos\n0 Betten frei", "value": None, "on": True})
        self.assertEqual(L["unemployed"], {"text": "3 arbeitslos\n0 Stellen frei", "value": None, "on": True})
        self.assertFalse(L["contaminated"]["on"])
        self.assertEqual(L["science"]["text"], "1.234 Wissenschaft")
        self.assertEqual(L["water"], {"text": "160 · 2,4 Tage", "value": None, "on": True}, "Wasser knapp → rot")
        self.assertEqual(L["food"], {"text": "412 · 9,5 Tage", "value": None, "on": False})
        self.assertTrue(L["status"]["on"])
        for name, value in v.items():
            self.assertTrue(all(c.isalnum() or c in " _.-" for c in name), name)
            self.assertLessEqual(len(value), 1000)

    def test_weather_countdown(self):
        self.connected()
        L = self.pl.lives
        # Art noch geheim (wie im Spiel), Balken = Rest der ruhigen Zeit
        self.assertEqual(L["weather"], {"text": "Gefahr in 5,5 Tagen", "value": 42, "on": False})
        self.assertEqual(self.pl.values["TBGefahrArt"], "?")
        self.assertEqual(self.pl.values["TBGefahrIn"], "5,5")
        self.mod.state.update(hazardIn=1.0, hazardNext="drought", hazardNextName="Dürre")
        self.mod.push_state()
        self.pl.wait(lambda: self.pl.lives["weather"]["text"] == "Dürre in 1 Tag", what="angekündigt")
        self.assertTrue(self.pl.lives["weather"]["on"])
        self.assertEqual(self.pl.values["TBGefahrArt"], "Dürre")
        self.mod.state.update(weather="drought", weatherName="Dürre", hazardIn=-1, hazardLeft=3.0)
        self.mod.push_state()
        self.pl.wait(lambda: self.pl.lives["weather"]["text"] == "Dürre: noch 3 Tage", what="läuft")
        self.assertEqual(self.pl.lives["weather"]["value"], 75)
        self.assertEqual(self.pl.values["TBGefahrRest"], "3")
        self.assertEqual(self.pl.values["TBWetter"], "Dürre")
        self.mod.state.update(hazardIn=-1, hazardLeft=-1, hazardDays=0)
        self.mod.push_state()
        self.pl.wait(lambda: self.pl.lives["weather"]["text"] == "Keine Gefahr in diesem Zyklus", what="keine Gefahr")

    def test_goods(self):
        self.connected()
        v, L = self.pl.values, self.pl.lives
        self.assertEqual(v["TBWare_Log"], "230")
        self.assertEqual(v["TBWare_Berries"], "412")
        self.assertEqual(L["good_Log"], {"text": "Rohholz\n230/300 · +12,5/Tag", "value": 77, "on": False})
        self.assertEqual(L["good_Plank"], {"text": "Brett\n90/90", "value": 100, "on": True}, "Lager voll → an")
        self.assertEqual(L["good_Gear"]["text"], "Zahnrad\n0/40 · -1,5/Tag")
        self.assertEqual(L["good_Dirt"]["text"], "–", "nicht vorhandene Ware")
        # Ware verschwindet aus dem Zustand → Wert 0
        self.mod.state["goods"] = [g for g in self.mod.state["goods"] if g["id"] != "Log"]
        self.mod.push_state()
        self.pl.wait(lambda: self.pl.values.get("TBWare_Log") == "0", what="Rohholz weg")
        self.assertEqual(self.pl.lives["good_Log"]["text"], "–")

    def test_history_and_alerts(self):
        self.connected()
        v, L = self.pl.values, self.pl.lives
        self.assertEqual(v["TBMeldung1"], "Der Biber „Kalle“ ist gestorben. (Z4 T3)")
        self.assertEqual(v["TBMeldung4"], "–")
        self.assertEqual(L["note1"], {"text": "Der Biber „Kalle“ ist gestorben.\nZyklus 4 · Tag 3", "value": None, "on": True})
        self.assertFalse(L["note2"]["on"], "nicht von heute")
        self.assertEqual(L["note8"]["text"], "–")
        self.assertEqual(v["TBWarnungen"], "2")
        self.assertEqual(v["TBWarnung1"], "Arbeitslos (3)")
        self.assertEqual(L["alerts"], {"text": "2 Warnungen\nArbeitslos (3)", "value": None, "on": True})
        self.assertEqual(L["alert2"], {"text": "Obdachlos\n2×", "value": None, "on": True})
        self.assertEqual(L["alert3"]["text"], "–")
        r = self.pl.action("notification", {"n": 1})
        self.assertEqual(r["message"], "Kamera bei „Der Biber „Kalle“ ist gestorben.“")
        r = self.pl.action("notification", {"n": "3"})
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "„Wassertank ist leer“ gibt es nicht mehr")
        r = self.pl.action("notification", {"n": 5})
        self.assertEqual(r["error"], "Meldung 5 gibt es noch nicht")
        r = self.pl.action("alert", {"n": 2})
        self.assertEqual(r["message"], "Kamera bei „Obdachlos“")
        r = self.pl.action("alert", {"n": 7})
        self.assertEqual(r["error"], "Warnung 7 gibt es gerade nicht")
        self.mod.state["alerts"] = []
        self.mod.push_state()
        self.pl.wait(lambda: self.pl.lives["alerts"]["text"] == "Keine Warnungen", what="keine Warnungen")
        self.assertFalse(self.pl.lives["alerts"]["on"])

    def test_main_menu_resets_values(self):
        self.connected()
        self.mod.state = {"inGame": False}
        self.mod.push_state()
        self.pl.wait(lambda: self.pl.values.get("TBImSpiel") == "nein", what="Hauptmenü")
        self.assertEqual(self.pl.values["TBBiber"], "–")
        self.assertEqual(self.pl.values["TBWare_Log"], "–")
        self.assertEqual(self.pl.values["TBVerbunden"], "ja")
        self.assertEqual(self.pl.lives["weather"]["value"], None)
        self.assertEqual(self.pl.values["TBStatus"], "Hauptmenü (kein Spiel geladen)")
        r = self.pl.action("pause")
        self.assertFalse(r["ok"])
        self.assertIn("Kein Spiel geladen", r["error"])

    def test_events_become_triggers(self):
        self.connected()
        self.mod.event("notification", {"text": "Ein neuer Biber wurde geboren.", "cycle": 4, "day": 3})
        self.mod.event("hazard_approaching", {"kind": "badtide", "name": "Faulwasserflut", "days": 5, "cycle": 4})
        self.mod.event("hazard_started", {"kind": "drought", "name": "Dürre", "days": 4, "cycle": 4})
        self.mod.event("hazard_ended", {"kind": "drought", "name": "Dürre", "days": 0, "cycle": 4})
        self.mod.event("cycle_started", {"cycle": 5})
        self.mod.event("beaver_born", {})
        self.mod.event("character_died", {"name": "Kalle", "age": 31})
        self.mod.event("alert", {"text": "Arbeitslos"})
        self.mod.event("game_over", {})
        self.pl.wait(lambda: any(f[0] == "game_over" for f in self.pl.fired), what="Spiel vorbei")
        fired = {}
        for trig, data in self.pl.fired:
            fired.setdefault(trig, []).append(data)
        self.assertEqual(fired["notification"][0], {"Text": "Ein neuer Biber wurde geboren.", "Zyklus": "4", "Cycle": "4",
                                                    "Tag": "3", "Day": "3"})
        self.assertEqual(fired["hazard_approaching"][0]["Art"], "badtide")
        self.assertEqual(fired["hazard_started"][0]["Name"], "Dürre")
        self.assertEqual(fired["hazard_started"][0]["Tage"], "4")
        self.assertEqual(fired["hazard_ended"][0]["Kind"], "drought")
        self.assertEqual(fired["cycle_started"][0], {"Zyklus": "5", "Cycle": "5"})
        self.assertEqual(fired["beaver_born"], [{}])
        self.assertEqual(fired["character_died"][0], {"Name": "Kalle", "Alter": "31", "Age": "31"})
        self.assertEqual(fired["alert"][0], {"Text": "Arbeitslos"})

    def test_commands_with_ack(self):
        self.connected()
        r = self.pl.action("pause")
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["message"], "Spiel pausiert")
        self.pl.wait(lambda: self.pl.values.get("TBPause") == "an", what="Pause sichtbar")
        self.assertEqual(self.pl.lives["speed"], {"text": "Pause", "value": None, "on": False})
        self.assertEqual(self.pl.values["TBTempo"], "0")
        r = self.pl.action("pause", {"op": "off"})
        self.assertEqual(r["message"], "Spiel läuft weiter")
        r = self.pl.action("speed", {"op": "set", "value": "3"})
        self.assertEqual(r["message"], "Tempo 3 (×7)")
        self.pl.wait(lambda: self.pl.lives["speed"]["text"] == "Tempo 3 (×7)", what="Tempo 3")
        r = self.pl.action("speed", {"op": "down"})
        self.assertEqual(r["message"], "Tempo 2 (×3)")
        sent = [m for m in self.mod.received if m.get("cmd") == "speed"][0]
        self.assertEqual(sent["args"], {"op": "set", "value": 3})
        r = self.pl.action("speed", {"op": "set", "value": 9})
        sent = [m for m in self.mod.received if m.get("cmd") == "speed"][-1]
        self.assertEqual(sent["args"]["value"], 3, "Tempo auf 1–3 begrenzt")
        r = self.pl.action("save", {"name": ""})
        self.assertEqual(r["message"], "Gespeichert als TouchDeck-Quicksave")
        r = self.pl.action("message", {"text": "Hallo „Biber“", "kind": "warning"})
        self.assertTrue(r["ok"])
        sent = [m for m in self.mod.received if m.get("cmd") == "message"][-1]
        self.assertEqual(sent["args"], {"text": "Hallo „Biber“", "kind": "warning"})
        r = self.pl.action("message", {"text": ""})
        self.assertEqual(r["error"], "Kein Text angegeben")
        r = self.pl.action("refresh")
        self.assertEqual(r["message"], "Zustand neu angefordert")
        r = self.pl.action("gibtsnicht")
        self.assertFalse(r["ok"])
        ids = [m["id"] for m in self.mod.received if m.get("type") == "cmd"]
        self.assertEqual(len(ids), len(set(ids)), "jede Anfrage hat eine eigene id")

    def test_parallel_commands(self):
        self.connected()
        rids = []
        for i in range(6):
            rid = f"p{i}"
            rids.append(rid)
            self.pl.send({"type": "action", "requestId": rid, "id": "alert", "params": {"n": i % 2 + 1}, "info": {}})
        self.pl.wait(lambda: all(r in self.pl.results for r in rids), what="sechs Antworten")
        names = ["Arbeitslos", "Obdachlos"]
        for i, rid in enumerate(rids):
            self.assertEqual(self.pl.results[rid]["message"], f"Kamera bei „{names[i % 2]}“", "Antwort passt zur Anfrage")

    def test_timeout(self):
        self.connected()
        self.mod.answer = False
        t0 = time.monotonic()
        r = self.pl.action("pause")
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "Keine Antwort von Timberborn innerhalb von 2 s")
        self.assertLess(time.monotonic() - t0, 4)

    def test_broken_lines_are_ignored(self):
        self.connected()
        self.mod.send_raw(b"kaputt {\n")
        self.mod.send_raw(b"[1,2,3]\n")
        self.mod.send_raw(b"\xff\xfe\n")
        self.mod.send_raw(b'{"type":"state","state":"kein Objekt"}\n')
        self.mod.send_raw(b"x" * (70 * 1024) + b"\n")
        self.mod.state = dict(self.mod.state, science=999, goods="kaputt", notifications=[1, None, "x"], alerts={})
        self.mod.push_state()
        self.pl.wait(lambda: self.pl.values.get("TBWissenschaft") == "999", what="Zustand nach kaputten Zeilen")
        self.assertTrue(any("verworfen" in m for _, m in self.pl.logs))
        self.assertEqual(self.pl.values["TBMeldung1"], "–")
        self.assertEqual(self.pl.p.poll(), None, "Plugin läuft noch")

    def test_reconnect_after_drop(self):
        self.connected()
        self.mod.drop_clients()
        self.pl.wait(lambda: self.pl.values.get("TBVerbunden") == "nein", what="getrennt")
        self.assertIn(("disconnected", {}), self.pl.fired)
        self.assertEqual(self.pl.values["TBBiber"], "–")
        r = self.pl.action("pause")
        self.assertFalse(r["ok"])
        self.assertIn("Timberborn nicht erreichbar", r["error"])
        self.pl.wait(lambda: self.pl.values.get("TBVerbunden") == "ja", timeout=8, what="wieder verbunden")
        self.pl.wait(lambda: self.pl.values.get("TBBiber") == "23", what="Zustand nach Neuverbindung")
        self.assertEqual(len(self.mod.hellos), 2)

    def test_dead_mod_without_heartbeat(self):
        self.connected()
        self.mod.heartbeat = False
        self.pl.wait(lambda: self.pl.values.get("TBVerbunden") == "nein", timeout=6, what="ohne Herzschlag getrennt")
        self.mod.heartbeat = True
        self.pl.wait(lambda: self.pl.values.get("TBVerbunden") == "ja", timeout=8, what="wieder verbunden")


class SettingsTests(unittest.TestCase):
    def test_wrong_secret(self):
        mod = FakeMod(secret="richtiges-geheimwort")
        pl = PluginProcess({"host": "127.0.0.1", "port": mod.port, "secret": "falsch"})
        try:
            pl.wait(lambda: pl.values.get("TBStatus") == "Geheimwort falsch", what="Ablehnung")
            self.assertEqual(pl.values["TBVerbunden"], "nein")
            self.assertTrue(any(lvl == "error" and "secret" in m for lvl, m in pl.logs))
            time.sleep(1.5)
            self.assertEqual(len(mod.hellos), 1, "nach Ablehnung nicht sofort erneut versuchen")
        finally:
            pl.stop()
            mod.close()

    def test_right_secret(self):
        mod = FakeMod(secret="richtiges-geheimwort")
        pl = PluginProcess({"host": "127.0.0.1", "port": str(mod.port), "secret": " richtiges-geheimwort "})
        try:
            pl.wait(lambda: pl.values.get("TBVerbunden") == "ja", what="verbunden mit Geheimwort")
        finally:
            pl.stop()
            mod.close()

    def test_remote_needs_secret(self):
        """Streaming-PC → Spiele-PC: ohne langes Geheimwort startet das Plugin gar nicht erst."""
        pl = PluginProcess({"host": "192.168.178.20", "port": 34201, "secret": "kurz"})
        try:
            pl.wait(lambda: pl.values.get("TBStatus") == "Einstellungen ungültig (siehe Log)", what="Einstellungen")
            self.assertTrue(any(lvl == "error" and "Geheimwort" in m for lvl, m in pl.logs))
            r = pl.action("pause")
            self.assertIn("Timberborn nicht erreichbar", r["error"])
        finally:
            pl.stop()

    def test_host_name_with_secret(self):
        """Rechnername statt IP (z. B. „gaming-pc.local“) ist erlaubt, braucht aber ein Geheimwort."""
        pl = PluginProcess({"host": "gaming-pc.invalid", "port": 34201, "secret": "ein-langes-geheimwort"})
        try:
            pl.wait(lambda: pl.values.get("TBStatus") == "Timberborn nicht erreichbar", timeout=10, what="versucht")
            self.assertFalse(any("host:" in m for _, m in pl.logs), "Rechnername gilt als gültig")
        finally:
            pl.stop()

    def test_bad_port_falls_back(self):
        pl = PluginProcess({"host": "127.0.0.1", "port": 80})
        try:
            pl.wait(lambda: any("34201" in m for _, m in pl.logs), what="Hinweis Port")
        finally:
            pl.stop()

    def test_nothing_running(self):
        pl = PluginProcess({"host": "127.0.0.1", "port": 1})   # ungültig → 34201; dort läuft (hoffentlich) nichts
        try:
            pl.wait(lambda: pl.values.get("TBStatus") == "Timberborn nicht erreichbar", what="nicht erreichbar")
            self.assertEqual(pl.lives["status"], {"text": "Timberborn nicht erreichbar", "value": None, "on": False})
        finally:
            pl.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
