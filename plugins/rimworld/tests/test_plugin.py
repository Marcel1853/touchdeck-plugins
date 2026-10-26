#!/usr/bin/env python3
"""Tests für plugin.py gegen den Fake-Mod (tests/fake_mod.py). Nur Standardbibliothek.

Aufruf:  python3 tests/test_plugin.py
Startet plugin.py wie TouchDeck (JSON-Zeilen über stdin/stdout) und prüft, was ankommt:
Hallo, Zustand, Werte, Live-Anzeigen, Ereignisse, Befehle mit Antwort, Timeout, Abbruch mit
Neuverbindung, kaputte Zeilen, falsches Geheimwort und ungültige Einstellungen.
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
        env = dict(os.environ, LANG="de_DE.UTF-8", LC_ALL="", LC_MESSAGES="", RIMWORLD_DEAD_AFTER="3")
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
        self.send({"type": "start", "plugin": {"id": "rimworld"}, "settings": settings, "touchdeck": "0.12.0"})

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
        self.pl.wait(lambda: self.pl.values.get("RWVerbunden") == "ja", what="verbunden")

    def test_hello_state_values_and_lives(self):
        self.connected()
        hello = self.mod.hellos[0]
        self.assertEqual(hello["type"], "hello")
        self.assertEqual(hello["proto"], 1)
        self.assertIn("secret", hello)
        self.assertIn(("connected", {}), self.pl.fired)
        self.pl.wait(lambda: self.pl.values.get("RWImSpiel") == "ja", what="im Spiel")
        v = self.pl.values
        self.assertEqual(v["RWDatum"], "5. Aprimay 5501")
        self.assertEqual(v["RWUhrzeit"], "14:00")
        self.assertEqual(v["RWTempo"], "1")
        self.assertEqual(v["RWPause"], "aus")
        self.assertEqual(v["RWKolonisten"], "3")
        self.assertEqual(v["RWStimmungMin"], "31")
        self.assertEqual(v["RWSilber"], "1234")
        self.assertEqual(v["RWForschung"], "Elektrizität")
        self.assertEqual(v["RWForschungProzent"], "42")
        self.assertEqual(v["RWWetter"], "Klar")
        self.assertEqual(v["RWKarte"], "Neu-Hoffnung")
        self.assertEqual(v["RWKolonist3"], 'Ölaf "der Große"')
        self.assertEqual(v["RWKolonist4"], "–")
        self.assertEqual(v["RWEingezogen"], "0/3")
        # Live-Anzeigen in der Form, die TouchDeck erwartet: text, value (0–100 oder None), on
        L = self.pl.lives
        self.assertEqual(L["mood"], {"text": "31 % (Engie)", "value": 31, "on": False})
        self.assertEqual(L["research"], {"text": "Elektrizität · 42 %", "value": 42, "on": True})
        self.assertEqual(L["speed"], {"text": "1× normal", "value": None, "on": True})
        self.assertEqual(L["silver"]["text"], "1.234")
        self.assertFalse(L["danger"]["on"])
        self.assertFalse(L["draft"]["on"])
        self.assertTrue(L["status"]["on"])
        for name, value in v.items():
            self.assertTrue(all(c.isalnum() or c in " _.-" for c in name), name)
            self.assertLessEqual(len(value), 1000)

    def test_main_menu_resets_values(self):
        self.connected()
        self.pl.wait(lambda: self.pl.values.get("RWSilber") == "1234", what="Silber")
        self.mod.state = {"inGame": False}
        self.mod.push_state()
        self.pl.wait(lambda: self.pl.values.get("RWImSpiel") == "nein", what="Hauptmenü")
        self.assertEqual(self.pl.values["RWSilber"], "–")
        self.assertEqual(self.pl.values["RWVerbunden"], "ja")
        self.assertEqual(self.pl.lives["mood"]["value"], None)
        r = self.pl.action("pause")
        self.assertFalse(r["ok"])
        self.assertIn("Kein Spiel geladen", r["error"])

    def test_events_become_triggers(self):
        self.connected()
        self.mod.event("letter", {"title": "Überfall", "kind": "ThreatBig", "text": "Piraten\n„kommen“", "threat": "big"})
        self.mod.event("letter", {"title": "Händler", "kind": "NeutralEvent", "text": "", "threat": ""})
        self.mod.event("colonist_died", {"name": "Tom"})
        self.mod.event("mental_break", {"name": "Engie", "kind": "Fressattacke", "defName": "Binging_Food"})
        self.mod.event("research_finished", {"name": "Elektrizität", "defName": "Electricity"})
        self.pl.wait(lambda: any(f[0] == "research_finished" for f in self.pl.fired), what="Forschung fertig")
        fired = dict()
        for trig, data in self.pl.fired:
            fired.setdefault(trig, []).append(data)
        self.assertEqual(len(fired["letter"]), 2)
        self.assertEqual(fired["letter"][0]["Titel"], "Überfall")
        self.assertEqual(fired["letter"][0]["Bedrohung"], "big")
        self.assertEqual(fired["letter"][0]["Text"], "Piraten\n„kommen“")
        self.assertEqual(len(fired["raid"]), 1, "nur der Brief mit großer Bedrohung ist ein Überfall")
        self.assertEqual(fired["colonist_died"][0]["Name"], "Tom")
        self.assertEqual(fired["mental_break"][0], {"Name": "Engie", "Art": "Fressattacke", "Kind": "Fressattacke",
                                                    "Intern": "Binging_Food"})
        self.assertEqual(fired["research_finished"][0]["Intern"], "Electricity")

    def test_commands_with_ack(self):
        self.connected()
        r = self.pl.action("pause")
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["message"], "Spiel pausiert")
        self.pl.wait(lambda: self.pl.values.get("RWPause") == "an", what="Pause sichtbar")
        self.assertEqual(self.pl.lives["speed"], {"text": "pausiert", "value": None, "on": False})
        r = self.pl.action("speed", {"op": "set", "value": "3"})
        self.assertEqual(r["message"], "Tempo 3× superschnell")
        r = self.pl.action("speed", {"op": "set", "value": 4})
        self.assertFalse(r["ok"])
        self.assertIn("Entwicklermodus", r["error"])
        r = self.pl.action("save", {"name": ""})
        self.assertEqual(r["message"], "Gespeichert als TouchDeck-Quicksave")
        r = self.pl.action("screenshot")
        self.assertIn("TouchDeck_test.png", r["message"])
        r = self.pl.action("draft", {"op": "toggle"})
        self.assertEqual(r["message"], "3 Kolonisten eingezogen")
        self.pl.wait(lambda: self.pl.lives.get("draft", {}).get("on"), what="alle eingezogen")
        r = self.pl.action("jump", {"n": "2"})
        self.assertEqual(r["message"], "Kamera bei Tom")
        r = self.pl.action("jump", {"n": 9})
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "Kolonist 9 gibt es nicht (es gibt 3)")
        r = self.pl.action("message", {"text": "Hallo „Kolonie“\nzweite Zeile", "kind": "positive"})
        self.assertTrue(r["ok"])
        sent = [m for m in self.mod.received if m.get("cmd") == "message"][-1]
        self.assertEqual(sent["args"], {"text": "Hallo „Kolonie“\nzweite Zeile", "kind": "positive"})
        r = self.pl.action("research", {"name": "Elektrizität"})
        self.assertEqual(r["message"], "Forschung: Elektrizität")
        r = self.pl.action("letter", {"op": "open"})
        self.assertEqual(r["message"], "Brief „Händler“ geöffnet")
        r = self.pl.action("gibtsnicht")
        self.assertFalse(r["ok"])
        ids = [m["id"] for m in self.mod.received if m.get("type") == "cmd"]
        self.assertEqual(len(ids), len(set(ids)), "jede Anfrage hat eine eigene id")

    def test_event_history(self):
        self.connected()
        self.pl.wait(lambda: self.pl.values.get("RWEreignis1") == "Händler (2 Std.)", what="Ereignis 1")
        v, L = self.pl.values, self.pl.lives
        self.assertEqual(v["RWEreignis2"], "Überfall (1 Tag)")
        self.assertEqual(v["RWEreignis4"], "–")
        self.assertEqual(L["event1"], {"text": "Händler\n2 Std.", "value": None, "on": False})
        self.assertTrue(L["event2"]["on"], "Überfall rot")
        self.assertTrue(L["event3"]["on"], "Tod rot")
        self.assertEqual(L["event8"]["text"], "–")
        r = self.pl.action("letter", {"op": "jump", "n": 2})
        self.assertEqual(r["message"], "Kamera beim Brief „Überfall“")
        sent = [m for m in self.mod.received if m.get("cmd") == "letter"][-1]
        self.assertEqual(sent["args"], {"op": "jump", "id": 40}, "Nummer wird zur Brief-ID")
        r = self.pl.action("letter", {"op": "open", "n": "3"})
        self.assertEqual(r["message"], "Brief „Tod: Tom“ geöffnet")
        r = self.pl.action("letter", {"op": "jump", "n": 5})
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "Ereignis 5 gibt es noch nicht")
        r = self.pl.action("letter", {"op": "jump"})
        self.assertEqual(r["message"], "Kamera beim Brief „Händler“", "ohne Nummer = letzter Brief")
        # Brief inzwischen aus dem Verlauf gefallen
        self.mod.state["events"][0]["id"] = 99
        r = self.pl.action("letter", {"op": "jump", "n": 1})
        self.assertEqual(r["error"], "Dieser Brief ist nicht mehr im Verlauf")

    def test_parallel_commands(self):
        self.connected()
        rids = []
        for i in range(6):
            rid = f"p{i}"
            rids.append(rid)
            self.pl.send({"type": "action", "requestId": rid, "id": "jump", "params": {"n": i % 3 + 1}, "info": {}})
        self.pl.wait(lambda: all(r in self.pl.results for r in rids), what="sechs Antworten")
        names = ["Engie", "Tom", 'Ölaf "der Große"']
        for i, rid in enumerate(rids):
            self.assertEqual(self.pl.results[rid]["message"], f"Kamera bei {names[i % 3]}", "Antwort passt zur Anfrage")

    def test_timeout(self):
        self.connected()
        self.mod.answer = False
        t0 = time.monotonic()
        r = self.pl.action("pause")
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "Keine Antwort von RimWorld innerhalb von 2 s")
        self.assertLess(time.monotonic() - t0, 4)

    def test_broken_lines_are_ignored(self):
        self.connected()
        self.mod.send_raw(b"kaputt {\n")
        self.mod.send_raw(b"[1,2,3]\n")
        self.mod.send_raw(b"\xff\xfe\n")
        self.mod.send_raw(b'{"type":"state","state":"kein Objekt"}\n')
        self.mod.send_raw(b"x" * (70 * 1024) + b"\n")
        self.mod.state["silver"] = 999
        self.mod.push_state()
        self.pl.wait(lambda: self.pl.values.get("RWSilber") == "999", what="Zustand nach kaputten Zeilen")
        self.assertTrue(any("verworfen" in m for _, m in self.pl.logs))
        self.assertEqual(self.pl.p.poll(), None, "Plugin läuft noch")

    def test_reconnect_after_drop(self):
        self.connected()
        self.mod.drop_clients()
        self.pl.wait(lambda: self.pl.values.get("RWVerbunden") == "nein", what="getrennt")
        self.assertIn(("disconnected", {}), self.pl.fired)
        self.assertEqual(self.pl.values["RWSilber"], "–")
        r = self.pl.action("pause")
        self.assertFalse(r["ok"])
        self.assertIn("RimWorld nicht erreichbar", r["error"])
        self.pl.wait(lambda: self.pl.values.get("RWVerbunden") == "ja", timeout=8, what="wieder verbunden")
        self.pl.wait(lambda: self.pl.values.get("RWSilber") == "1234", what="Zustand nach Neuverbindung")
        self.assertEqual(len(self.mod.hellos), 2)

    def test_dead_mod_without_heartbeat(self):
        self.connected()
        self.mod.heartbeat = False
        self.pl.wait(lambda: self.pl.values.get("RWVerbunden") == "nein", timeout=6, what="ohne Herzschlag getrennt")
        self.mod.heartbeat = True
        self.pl.wait(lambda: self.pl.values.get("RWVerbunden") == "ja", timeout=8, what="wieder verbunden")


class SettingsTests(unittest.TestCase):
    def test_wrong_secret(self):
        mod = FakeMod(secret="richtiges-geheimwort")
        pl = PluginProcess({"host": "127.0.0.1", "port": mod.port, "secret": "falsch"})
        try:
            pl.wait(lambda: pl.values.get("RWStatus") == "Geheimwort falsch", what="Ablehnung")
            self.assertEqual(pl.values["RWVerbunden"], "nein")
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
            pl.wait(lambda: pl.values.get("RWVerbunden") == "ja", what="verbunden mit Geheimwort")
        finally:
            pl.stop()
            mod.close()

    def test_remote_needs_secret(self):
        pl = PluginProcess({"host": "192.168.178.20", "port": 34200, "secret": "kurz"})
        try:
            pl.wait(lambda: pl.values.get("RWStatus") == "Einstellungen ungültig (siehe Log)", what="Einstellungen")
            self.assertTrue(any(lvl == "error" and "Geheimwort" in m for lvl, m in pl.logs))
            r = pl.action("pause")
            self.assertIn("RimWorld nicht erreichbar", r["error"])
        finally:
            pl.stop()

    def test_bad_port_falls_back(self):
        pl = PluginProcess({"host": "127.0.0.1", "port": 80})
        try:
            pl.wait(lambda: any("34200" in m for _, m in pl.logs), what="Hinweis Port")
        finally:
            pl.stop()

    def test_nothing_running(self):
        pl = PluginProcess({"host": "127.0.0.1", "port": 1})   # ungültig → 34200; dort läuft (hoffentlich) nichts
        try:
            pl.wait(lambda: pl.values.get("RWStatus") == "RimWorld nicht erreichbar", what="nicht erreichbar")
            self.assertEqual(pl.lives["status"], {"text": "RimWorld nicht erreichbar", "value": None, "on": False})
        finally:
            pl.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
