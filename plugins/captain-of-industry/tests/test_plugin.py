#!/usr/bin/env python3
"""Tests für plugin.py gegen den Fake-Mod (tests/fake_mod.py). Nur Standardbibliothek.

Aufruf:  python3 tests/test_plugin.py
Startet plugin.py wie TouchDeck (JSON-Zeilen über stdin/stdout) und prüft, was ankommt:
Hallo, Zustand, Werte, Live-Anzeigen, Strom, Einheit, Arbeiter, Nahrung, Forschung, Waren, Meldungen,
Verlauf, Ereignisse, Befehle mit Antwort, Timeout, Abbruch mit Neuverbindung, kaputte Zeilen, falsches
Geheimwort, ungültige Einstellungen – und dass das Plugin nie eine Desktop-Benachrichtigung schickt.
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
        env = dict(os.environ, LANG="de_DE.UTF-8", LC_ALL="", LC_MESSAGES="", COI_DEAD_AFTER="3")
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
        self.notified = []
        self.stderr = []
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._read_err, daemon=True).start()
        self.send({"type": "start", "plugin": {"id": "captain-of-industry"}, "settings": settings, "touchdeck": "0.12.0"})

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
            elif kind == "notify":
                self.notified.append(msg)
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
        assert not self.notified, f"keine Desktop-Benachrichtigungen: {self.notified}"


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.mod = FakeMod()
        self.pl = PluginProcess({"host": "127.0.0.1", "port": self.mod.port, "secret": "", "timeout": 2})

    def tearDown(self):
        self.pl.stop()
        self.mod.close()

    def connected(self):
        self.pl.wait(lambda: self.pl.values.get("COIVerbunden") == "ja", what="verbunden")
        self.pl.wait(lambda: self.pl.values.get("COIImSpiel") == "ja", what="im Spiel")

    def test_hello_state_values_and_lives(self):
        self.connected()
        hello = self.mod.hellos[0]
        self.assertEqual(hello["type"], "hello")
        self.assertEqual(hello["proto"], 1)
        self.assertTrue(hello["client"].startswith("touchdeck-coi/"))
        self.assertIn(("connected", {}), self.pl.fired)
        v = self.pl.values
        self.assertEqual(v["COIJahr"], "3")
        self.assertEqual(v["COIMonat"], "7")
        self.assertEqual(v["COIDatum"], "Jahr 3 · Juli")
        self.assertEqual(v["COITempo"], "1")
        self.assertEqual(v["COIPause"], "aus")
        self.assertEqual(v["COIStrom"], "9400")
        self.assertEqual(v["COIStromKapazitaet"], "12000")
        self.assertEqual(v["COIRechnen"], "52")
        self.assertEqual(v["COIEinheit"], "152")
        self.assertEqual(v["COIEinheitMonat"], "-2,5")
        self.assertEqual(v["COIArbeiterFrei"], "-6")
        self.assertEqual(v["COIEinwohner"], "1240")
        self.assertEqual(v["COIObdachlos"], "0")
        self.assertEqual(v["COINahrungMonate"], "2")
        self.assertEqual(v["COIHunger"], "nein")
        self.assertEqual(v["COIKrankheit"], "–")
        self.assertEqual(v["COIForschung"], "Dampfturbine")
        self.assertEqual(v["COIForschungProzent"], "64")
        self.assertEqual(v["COIUngelesen"], "1")
        # Live-Anzeigen in der Form, die TouchDeck erwartet: text, value (0–100 oder None), on
        L = self.pl.lives
        self.assertEqual(L["date"], {"text": "Jahr 3 · Juli", "value": None, "on": False})
        self.assertEqual(L["speed"], {"text": "Tempo 1 (×1)", "value": 25, "on": True})
        self.assertEqual(L["power"], {"text": "Strom 9,4 MW / 12 MW\n2,6 MW frei", "value": 78, "on": False,
                                       "number": 9400, "series": {"Bedarf": 9400, "Kapazität": 12000}})
        self.assertEqual(L["computing"], {"text": "Rechnen 52 TF / 48 TF", "value": 100, "on": True,
                                           "number": 52, "series": {"Bedarf": 52, "Kapazität": 48}}, "Rechenleistung reicht nicht → rot")
        self.assertEqual(L["unity"], {"text": "Einheit 152\n−2,5/Monat", "value": 38, "on": True, "number": 152}, "Einheit nimmt ab → rot")
        self.assertEqual(L["workers"], {"text": "6 Arbeiter fehlen", "value": None, "on": True})
        self.assertEqual(L["population"], {"text": "1.240 Einwohner (+12)\n35 Wohnplätze frei", "value": None, "on": False})
        self.assertEqual(L["food"], {"text": "Nahrung für 2 Monate", "value": 17, "on": True}, "Nahrung knapp → rot")
        self.assertEqual(L["health"], {"text": "Keine Krankheit", "value": None, "on": False})
        self.assertEqual(L["research"], {"text": "Dampfturbine · 64 %", "value": 64, "on": True})
        self.assertTrue(L["status"]["on"])
        for name, value in v.items():
            self.assertTrue(all(c.isalnum() or c in " _.-" for c in name), name)
            self.assertLessEqual(len(name), 40, name)
            self.assertLessEqual(len(value), 1000)

    def test_power_short_and_people(self):
        self.connected()
        self.mod.state.update(powerDemand=15000, powerUsed=12000, workersFree=4, homeless=7, foodMonths=0, starving=True,
                              disease="Grippe", diseaseMonths=3, research="", researchLab=True)
        self.mod.push_state()
        L = self.pl.lives
        self.pl.wait(lambda: L["power"]["text"] == "Strom 12 MW / 12 MW\nStrom fehlt: 3 MW", what="Strom fehlt")
        self.assertEqual(L["power"]["value"], 100)
        self.assertTrue(L["power"]["on"])
        self.assertEqual(L["workers"], {"text": "4 Arbeiter frei", "value": None, "on": False})
        self.assertEqual(L["population"]["text"], "1.240 Einwohner (+12)\n7 obdachlos")
        self.assertTrue(L["population"]["on"])
        self.assertEqual(L["food"], {"text": "Hunger! Nahrung fehlt", "value": 0, "on": True})
        self.assertEqual(L["health"], {"text": "Grippe: noch 3 Monate", "value": None, "on": True})
        self.assertEqual(L["research"], {"text": "Keine Forschung aktiv", "value": None, "on": True}, "Labor ohne Arbeit → rot")
        self.assertEqual(self.pl.values["COIHunger"], "ja")
        self.mod.state.update(researchLab=False)
        self.mod.push_state()
        self.pl.wait(lambda: L["research"]["text"] == "Kein Forschungslabor aktiv", what="kein Labor")
        self.assertFalse(L["research"]["on"])

    def test_goods(self):
        self.connected()
        v, L = self.pl.values, self.pl.lives
        self.assertEqual(v["COIWare_IronOre"], "1800")
        self.assertNotIn("COIWare_Food-Bread", v, "ungültige Kennung wird übergangen")
        self.assertEqual(L["good1"], {"text": "📌 Diesel\n90/600 · −120/Monat", "value": 15, "on": True,
                                       "number": 90, "series": {"Diesel": 90}}, "wird knapp → an")
        self.assertEqual(L["good2"], {"text": "📌 Bauteile\n400/400", "value": 100, "on": True,
                                       "number": 400, "series": {"Bauteile": 400}}, "Lager voll → an")
        self.assertEqual(L["good3"], {"text": "Eisenerz\n1.800/2.400 · +340/Monat", "value": 75, "on": False,
                                       "number": 1800, "series": {"Eisenerz": 1800}})
        self.assertEqual(L["good4"]["text"], "–")
        self.mod.state["goods"] = [g for g in self.mod.state["goods"] if g["id"] != "IronOre"]
        self.mod.push_state()
        self.pl.wait(lambda: self.pl.values.get("COIWare_IronOre") == "0", what="Eisenerz weg")

    def test_alerts_and_history(self):
        self.connected()
        v, L = self.pl.values, self.pl.lives
        self.assertEqual(v["COIWarnungen"], "3")
        self.assertEqual(v["COIWarnung1"], "Kein Treibstoff (4)")
        self.assertEqual(L["alerts"], {"text": "3 Meldungen\nKein Treibstoff (4)", "value": None, "on": True})
        self.assertEqual(L["alert2"], {"text": "Lager voll\n2×", "value": None, "on": True})
        self.assertFalse(L["alert3"]["on"], "Erfolgsmeldung leuchtet nicht")
        self.assertEqual(L["alert4"]["text"], "–")
        self.assertEqual(v["COIVerlauf1"], "Kein Treibstoff (3×) (Jahr 3)")
        self.assertEqual(v["COIVerlauf2"], "Forschung fertig: Dampfkessel (Jahr 3)")
        self.assertEqual(v["COIVerlauf3"], "18 Flüchtlinge aufgenommen (Jahr 3)")
        self.assertEqual(v["COIVerlauf4"], "–")
        self.assertEqual(L["note1"], {"text": "Kein Treibstoff (3×)\nJahr 3 · Monat 7", "value": None, "on": True})
        self.assertFalse(L["note2"]["on"], "nicht aus diesem Monat")
        r = self.pl.action("alert", {"n": 1})
        self.assertEqual(r["message"], "Kamera bei „Kein Treibstoff“")
        r = self.pl.action("alert", {"n": 7})
        self.assertEqual(r["error"], "Meldung 7 gibt es gerade nicht")
        r = self.pl.action("history", {"n": "1"})
        self.assertEqual(r["message"], "Kamera bei „Kein Treibstoff“")
        r = self.pl.action("history", {"n": 2})
        self.assertEqual(r["error"], "„Dampfkessel“ hat keinen Ort (mehr)")
        r = self.pl.action("history", {"n": 6})
        self.assertEqual(r["error"], "Eintrag 6 gibt es im Verlauf noch nicht")
        self.mod.state["alerts"] = []
        self.mod.push_state()
        self.pl.wait(lambda: self.pl.lives["alerts"]["text"] == "Keine Meldungen", what="keine Meldungen")
        self.assertFalse(self.pl.lives["alerts"]["on"])

    def test_main_menu_resets_values(self):
        self.connected()
        self.mod.state = {"inGame": False}
        self.mod.push_state()
        self.pl.wait(lambda: self.pl.values.get("COIImSpiel") == "nein", what="Hauptmenü")
        self.assertEqual(self.pl.values["COIEinwohner"], "–")
        self.assertEqual(self.pl.values["COIWare_IronOre"], "–")
        self.assertEqual(self.pl.values["COIVerbunden"], "ja")
        self.assertEqual(self.pl.lives["power"]["value"], None)
        self.assertEqual(self.pl.values["COIStatus"], "Hauptmenü (kein Spiel geladen)")
        r = self.pl.action("pause")
        self.assertFalse(r["ok"])
        self.assertIn("Kein Spiel geladen", r["error"])

    def test_events_become_triggers(self):
        self.connected()
        self.mod.event("notification", {"text": "Kein Treibstoff", "style": "critical"})
        self.mod.event("message", {"text": "Dampfkessel", "kind": "research"})
        self.mod.event("research_finished", {"name": "Dampfkessel"})
        self.mod.event("new_year", {"year": 4})
        self.mod.event("power_short", {"capacity": 100, "demand": 120})
        self.mod.event("food_low", {"months": 2})
        self.mod.event("starving", {"months": 0})
        self.mod.event("disease", {"name": "Grippe"})
        self.mod.event("game_over", {"text": "Alle verhungert"})
        self.pl.wait(lambda: any(f[0] == "game_over" for f in self.pl.fired), what="Spiel vorbei")
        fired = {}
        for trig, data in self.pl.fired:
            fired.setdefault(trig, []).append(data)
        self.assertEqual(fired["notification"][0], {"Text": "Kein Treibstoff", "Art": "critical", "Kind": "critical"})
        self.assertEqual(fired["message"][0], {"Text": "Forschung fertig: Dampfkessel", "Art": "research", "Kind": "research"})
        self.assertEqual(fired["research_finished"][0], {"Name": "Dampfkessel"})
        self.assertEqual(fired["new_year"][0], {"Jahr": "4", "Year": "4"})
        self.assertEqual(fired["power_short"][0]["Bedarf"], "120")
        self.assertEqual(fired["food_low"][0], {"Monate": "2", "Months": "2"})
        self.assertEqual(fired["starving"][0]["Monate"], "0")
        self.assertEqual(fired["disease"][0], {"Name": "Grippe"})
        self.assertEqual(fired["game_over"][0], {"Text": "Alle verhungert"})

    def test_commands_with_ack(self):
        self.connected()
        r = self.pl.action("pause")
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["message"], "Spiel pausiert")
        self.pl.wait(lambda: self.pl.values.get("COIPause") == "an", what="Pause sichtbar")
        self.assertEqual(self.pl.lives["speed"], {"text": "Pause", "value": None, "on": False})
        self.assertEqual(self.pl.values["COITempo"], "0")
        r = self.pl.action("pause", {"op": "off"})
        self.assertEqual(r["message"], "Spiel läuft weiter")
        r = self.pl.action("speed", {"op": "set", "value": "4"})
        self.assertEqual(r["message"], "Tempo 4 (×5)")
        self.pl.wait(lambda: self.pl.lives["speed"]["text"] == "Tempo 4 (×5)", what="Tempo 4")
        self.assertEqual(self.pl.lives["speed"]["value"], 100)
        r = self.pl.action("speed", {"op": "down"})
        self.assertEqual(r["message"], "Tempo 3 (×3)")
        sent = [m for m in self.mod.received if m.get("cmd") == "speed"][0]
        self.assertEqual(sent["args"], {"op": "set", "value": 4})
        r = self.pl.action("speed", {"op": "set", "value": 9})
        self.assertEqual(r["error"], "Tempo 9 gibt es nicht (1–4)")
        r = self.pl.action("save", {"name": ""})
        self.assertEqual(r["message"], "Speichern als „TouchDeck-Quicksave“ angestoßen")
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
        names = ["Kein Treibstoff", "Lager voll"]
        for i, rid in enumerate(rids):
            self.assertEqual(self.pl.results[rid]["message"], f"Kamera bei „{names[i % 2]}“", "Antwort passt zur Anfrage")

    def test_timeout(self):
        self.connected()
        self.mod.answer = False
        t0 = time.monotonic()
        r = self.pl.action("pause")
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "Keine Antwort vom Spiel innerhalb von 2 s")
        self.assertLess(time.monotonic() - t0, 4)

    def test_broken_lines_are_ignored(self):
        self.connected()
        self.mod.send_raw(b"kaputt {\n")
        self.mod.send_raw(b"[1,2,3]\n")
        self.mod.send_raw(b"\xff\xfe\n")
        self.mod.send_raw(b'{"type":"state","state":"kein Objekt"}\n')
        self.mod.send_raw(b"x" * (70 * 1024) + b"\n")
        self.mod.state = dict(self.mod.state, population=999, goods="kaputt", goodSlots=[None], history=[1, None, "x"],
                              alerts={}, speeds="x")
        self.mod.push_state()
        self.pl.wait(lambda: self.pl.values.get("COIEinwohner") == "999", what="Zustand nach kaputten Zeilen")
        self.assertTrue(any("verworfen" in m for _, m in self.pl.logs))
        self.assertEqual(self.pl.values["COIVerlauf1"], "–")
        self.assertEqual(self.pl.p.poll(), None, "Plugin läuft noch")

    def test_reconnect_after_drop(self):
        self.connected()
        self.mod.drop_clients()
        self.pl.wait(lambda: self.pl.values.get("COIVerbunden") == "nein", what="getrennt")
        self.assertIn(("disconnected", {}), self.pl.fired)
        self.assertEqual(self.pl.values["COIEinwohner"], "–")
        r = self.pl.action("pause")
        self.assertFalse(r["ok"])
        self.assertIn("Captain of Industry nicht erreichbar", r["error"])
        self.pl.wait(lambda: self.pl.values.get("COIVerbunden") == "ja", timeout=8, what="wieder verbunden")
        self.pl.wait(lambda: self.pl.values.get("COIEinwohner") == "1240", what="Zustand nach Neuverbindung")
        self.assertEqual(len(self.mod.hellos), 2)

    def test_dead_mod_without_heartbeat(self):
        self.connected()
        self.mod.heartbeat = False
        self.pl.wait(lambda: self.pl.values.get("COIVerbunden") == "nein", timeout=6, what="ohne Herzschlag getrennt")
        self.mod.heartbeat = True
        self.pl.wait(lambda: self.pl.values.get("COIVerbunden") == "ja", timeout=8, what="wieder verbunden")


class SettingsTests(unittest.TestCase):
    def test_wrong_secret(self):
        mod = FakeMod(secret="richtiges-geheimwort")
        pl = PluginProcess({"host": "127.0.0.1", "port": mod.port, "secret": "falsch"})
        try:
            pl.wait(lambda: pl.values.get("COIStatus") == "Geheimwort falsch", what="Ablehnung")
            self.assertEqual(pl.values["COIVerbunden"], "nein")
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
            pl.wait(lambda: pl.values.get("COIVerbunden") == "ja", what="verbunden mit Geheimwort")
        finally:
            pl.stop()
            mod.close()

    def test_remote_needs_secret(self):
        """Streaming-PC → Spiele-PC: ohne langes Geheimwort startet das Plugin gar nicht erst."""
        pl = PluginProcess({"host": "192.168.178.20", "port": 34202, "secret": "kurz"})
        try:
            pl.wait(lambda: pl.values.get("COIStatus") == "Einstellungen ungültig (siehe Log)", what="Einstellungen")
            self.assertTrue(any(lvl == "error" and "Geheimwort" in m for lvl, m in pl.logs))
            r = pl.action("pause")
            self.assertIn("Captain of Industry nicht erreichbar", r["error"])
        finally:
            pl.stop()

    def test_host_name_with_secret(self):
        """Rechnername statt IP (z. B. „gaming-pc.local“) ist erlaubt, braucht aber ein Geheimwort."""
        pl = PluginProcess({"host": "gaming-pc.invalid", "port": 34202, "secret": "ein-langes-geheimwort"})
        try:
            pl.wait(lambda: pl.values.get("COIStatus") == "Captain of Industry nicht erreichbar", timeout=10, what="versucht")
            self.assertFalse(any("host:" in m for _, m in pl.logs), "Rechnername gilt als gültig")
        finally:
            pl.stop()

    def test_bad_port_falls_back(self):
        pl = PluginProcess({"host": "127.0.0.1", "port": 80})
        try:
            pl.wait(lambda: any("34202" in m for _, m in pl.logs), what="Hinweis Port")
        finally:
            pl.stop()

    def test_nothing_running(self):
        pl = PluginProcess({"host": "127.0.0.1", "port": 1})   # ungültig → 34202; dort läuft (hoffentlich) nichts
        try:
            pl.wait(lambda: pl.values.get("COIStatus") == "Captain of Industry nicht erreichbar", what="nicht erreichbar")
            self.assertEqual(pl.lives["status"], {"text": "Captain of Industry nicht erreichbar", "value": None, "on": False})
        finally:
            pl.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
