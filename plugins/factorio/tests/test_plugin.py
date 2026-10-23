#!/usr/bin/env python3
"""Test des Plugins gegen einen nachgebauten Mod (schreibt state.json/names.txt wie touchdeck-bridge).

Aufruf:  python3 tests/test_plugin.py [echte state.json aus einem Headless-Lauf]
Startet plugin.py wie TouchDeck (JSON-Zeilen über stdin/stdout) und prüft Werte, Auslöser und
Aktionsergebnisse. Nur Standardbibliothek.
"""
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = []


def check(name, cond, extra=""):
    RESULTS.append(cond)
    print(("PASS " if cond else "FAIL ") + name + (f"  ({extra})" if extra and not cond else ""))


class FakeMod:
    """Schreibt die Dateien so, wie der Mod es tut."""

    def __init__(self, folder, session="42-0"):
        self.folder = folder
        self.session = session
        self.seq = 0
        self.events = []
        self.state = {"v": 1, "mod": "0.1.0", "session": session, "tick": 600, "played": 3725 * 60,
                      "speed": 1, "paused": False, "multiplayer": False, "admin": True, "player": "Marcel",
                      "players": 1, "research": "automation", "progress": 0.42, "queue": 2, "rockets": 3,
                      "evolution": 0.1234, "surface": {"index": 1, "name": "nauvis", "kind": "planet",
                                                       "planet": "nauvis"},
                      "space_age": True, "suggest": ["logistics", "turrets"],
                      "power": {"network": 1, "production": 35.2e6, "consumption": 17.6e6,
                                "sources": {"steam": 20e6, "solar": 12e6, "accumulator": 3.2e6},
                                "consumers": {"assembling-machine-2": 10e6, "lab": 5e6, "other": 2.6e6}}}

    def push(self, **event):
        self.seq += 1
        event["seq"] = self.seq
        self.events = (self.events + [event])[-20:]

    def write(self, **changes):
        self.state.update(changes)
        data = dict(self.state, seq=self.seq, events=self.events or {})
        tmp = os.path.join(self.folder, "state.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def items(self, items, labels):
        with open(os.path.join(self.folder, "labels.txt"), "w", encoding="utf-8") as f:
            f.write(labels)
        with open(os.path.join(self.folder, "items.json"), "w", encoding="utf-8") as f:
            json.dump({"v": 1, "tick": 600, "surface": "nauvis", "items": items}, f)

    def utl_alerts(self, lines):
        with open(os.path.join(self.folder, "utl-alerts.txt"), "w", encoding="utf-8") as f:
            f.write("".join(f"{tick}\t{text}\n" for tick, text in lines))

    def utl(self, data):
        with open(os.path.join(self.folder, "utl.json"), "w", encoding="utf-8") as f:
            json.dump(dict(data, v=1), f)

    def names(self, text):
        with open(os.path.join(self.folder, "names.txt"), "w", encoding="utf-8") as f:
            f.write(text)


class PluginProcess:
    def __init__(self, settings, env_extra=None, td_values=None):
        env = dict(os.environ, LANG="de_DE.UTF-8", LC_ALL="de_DE.UTF-8")
        env.update(env_extra or {})
        self.p = subprocess.Popen([sys.executable, "-I", os.path.join(ROOT, "plugin.py")],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, env=env, cwd=ROOT)
        self.q = queue.Queue()
        self.values = {}
        self.td_values = dict(td_values or {})   # Wertespeicher von TouchDeck (für getValue)
        self.fired = []
        self.results = {}
        self.lives = {}
        self.errors = []
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._err, daemon=True).start()
        self.send({"type": "start", "plugin": {"id": "factorio"}, "settings": settings, "touchdeck": "0.9.0"})

    def _read(self):
        for line in self.p.stdout:
            try:
                msg = json.loads(line)
            except ValueError:
                self.errors.append(line)
                continue
            kind = msg.get("type")
            if kind == "setValue":
                self.values[msg["name"]] = msg["value"]
                self.td_values[msg["name"]] = msg["value"]
            elif kind == "getValue":
                self.send({"type": "value", "requestId": msg["requestId"], "value": self.td_values.get(msg["name"])})
            elif kind == "fire":
                self.fired.append((msg["trigger"], msg.get("data") or {}))
            elif kind == "result":
                self.results[msg["requestId"]] = msg
            elif kind == "call" and msg.get("op") == "live.set":
                self.lives[msg["args"]["id"]] = msg["args"]["value"]
            elif kind == "log" and msg.get("level") == "error":
                self.errors.append(msg["message"])

    def _err(self):
        for line in self.p.stderr:
            self.errors.append(line)

    def send(self, msg):
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()

    def wait(self, cond, timeout=4.0):
        end = time.time() + timeout
        while time.time() < end:
            if cond():
                return True
            time.sleep(0.05)
        return cond()

    def action(self, rid, action, params, timeout=8.0):
        self.send({"type": "action", "requestId": rid, "id": action, "params": params, "info": {}})
        self.wait(lambda: rid in self.results, timeout)
        return self.results.get(rid)

    def stop(self):
        try:
            self.send({"type": "stop"})
            self.p.wait(3)
        except Exception:
            self.p.kill()


def fake_factorio(tmp):
    """Ein Prozess namens „factorio“, damit das Plugin „Spiel läuft“ erkennt."""
    exe = os.path.join(tmp, "factorio")
    shutil.copy("/bin/sleep", exe)
    return subprocess.Popen([exe, "60"])


def main():
    real_state = sys.argv[1] if len(sys.argv) > 1 else None
    tmp = tempfile.mkdtemp(prefix="td-factorio-test-")
    folder = os.path.join(tmp, "script-output", "touchdeck-bridge")
    os.makedirs(folder)
    settings = {"folder": folder, "interval": 100, "timeout": 2}
    game = None
    try:
        # 1) Alte Datei aus einer früheren Sitzung: nicht verbunden, keine alten Ereignisse auslösen
        mod = FakeMod(folder, session="alt")
        mod.push(type="research_finished", name="old-tech")
        mod.write()
        old = time.time() - 600
        os.utime(os.path.join(folder, "state.json"), (old, old))
        plug = PluginProcess(settings)
        plug.wait(lambda: plug.values.get("FVerbunden") == "nein", 2)
        time.sleep(0.5)
        check("alte Datei: nicht verbunden", plug.values.get("FVerbunden") == "nein", plug.values)
        check("alte Datei: kein Auslöser", not plug.fired, plug.fired)

        # 2) Spiel schreibt: verbunden, Werte, Übersetzung aus names.txt
        mod = FakeMod(folder)
        mod.names("research=Automatisierung\nfinished=\nplace=Nauvis\ntech.automation=Automatisierung\n"
                  "tech.logistics=Logistik\ntech.turrets=Geschütztürme\n")
        mod.write()
        ok = plug.wait(lambda: plug.values.get("FVerbunden") == "ja")
        check("verbunden", ok, plug.values.get("FStatus"))
        check("Auslöser connected", any(f[0] == "connected" for f in plug.fired), plug.fired)
        plug.wait(lambda: plug.values.get("FForschung") == "Automatisierung")
        v = plug.values
        check("FForschung übersetzt", v.get("FForschung") == "Automatisierung", v.get("FForschung"))
        check("FForschungProzent", v.get("FForschungProzent") == "42", v.get("FForschungProzent"))
        check("FSpielzeit", v.get("FSpielzeit") == "1:02:05", v.get("FSpielzeit"))
        check("FEvolution", v.get("FEvolution") == "12.3", v.get("FEvolution"))
        check("FPlanet", v.get("FPlanet") == "Nauvis", v.get("FPlanet"))
        check("FVorschlag1/2", v.get("FVorschlag1") == "Logistik" and v.get("FVorschlag2") == "Geschütztürme",
              (v.get("FVorschlag1"), v.get("FVorschlag2")))
        check("FVorschlag3 leer", v.get("FVorschlag3") == "–", v.get("FVorschlag3"))
        check("FGeschwindigkeit", v.get("FGeschwindigkeit") == "1", v.get("FGeschwindigkeit"))
        r = plug.lives.get("research") or {}
        check("Live Forschung mit Balken", r.get("value") == 42 and r.get("on") is True, r)

        # 3) Ereignis: Forschung fertig
        mod.push(type="research_finished", name="automation")
        mod.names("research=\nfinished=Automatisierung\nplace=Nauvis\ntech.logistics=Logistik\n")
        time.sleep(0.15)
        mod.write(research="", progress=0)
        ok = plug.wait(lambda: any(f[0] == "research_finished" for f in plug.fired))
        data = next((f[1] for f in plug.fired if f[0] == "research_finished"), {})
        check("Auslöser research_finished", ok and data.get("Intern") == "automation", data)
        check("research_finished mit Übersetzung", data.get("Name") == "Automatisierung", data)
        n_before = len(plug.fired)
        mod.write(tick=700)
        time.sleep(0.4)
        check("Ereignis nicht doppelt", len([f for f in plug.fired[n_before:] if f[0] == "research_finished"]) == 0)

        # 4) Strom und Zahlen für Graphen
        v = plug.values
        check("FStromErzeugung", v.get("FStromErzeugung") == "35,2 MW", v.get("FStromErzeugung"))
        check("FStromVerbrauch", v.get("FStromVerbrauch") == "17,6 MW", v.get("FStromVerbrauch"))
        pw = plug.lives.get("power") or {}
        check("Live Strom: Zahl für Graph", pw.get("number") == 35.2 and pw.get("text") == "35,2 MW", pw)
        check("Live Strom: Balken = Auslastung", pw.get("value") == 50, pw)
        check("Live Strom: Reihen nach Quelle (übersetzt)",
              pw.get("series") == {"Dampf": 20.0, "Solar": 12.0, "Akkus": 3.2}, pw.get("series"))
        ev = plug.lives.get("evolution") or {}
        check("Live Evolution: Zahl für Graph", ev.get("number") == 12.34, ev)
        check("Live Tempo: Zahl", (plug.lives.get("speed") or {}).get("number") == 1, plug.lives.get("speed"))
        # Strom-Verbrauch nach Gebäude (Namen aus labels.txt, sobald da)
        mod.items([], "entity.assembling-machine-2=Montagemaschine 2\nentity.lab=Labor\n")
        mod.write(tick=650)
        ok = plug.wait(lambda: (plug.lives.get("consumption") or {}).get("series", {}).get("Montagemaschine 2") == 10.0)
        check("Verbrauch nach Gebäude (übersetzt)", ok and plug.lives["consumption"]["series"] ==
              {"Montagemaschine 2": 10.0, "Labor": 5.0, "Sonstige": 2.6}, (plug.lives.get("consumption") or {}).get("series"))

        # Produktions-Plätze
        ITEMS = [{"n": "iron-plate", "k": "item", "p": 600, "c": 450},
                 {"n": "copper-plate", "k": "item", "p": 300, "c": 280},
                 {"n": "water", "k": "fluid", "p": 1200, "c": 1200},
                 {"n": "electronic-circuit", "k": "item", "p": 4.5, "c": 3}]
        LABELS = ("item.iron-plate=Eisenplatte\nitem.copper-plate=Kupferplatte\nfluid.water=Wasser\n"
                  "item.electronic-circuit=Elektronischer Schaltkreis\nentity.lab=Labor\n")
        mod.items(ITEMS, LABELS)
        ok = plug.wait(lambda: plug.values.get("FItem1") == "Eisenplatte: 600/min")
        check("Platz 1 automatisch = meistproduziert", ok, plug.values.get("FItem1"))
        check("Platz 4 mit Kommazahl", plug.values.get("FItem4") == "Elektronischer Schaltkreis: 4,5/min",
              plug.values.get("FItem4"))
        check("Platz 5 leer", plug.values.get("FItem5") == "–", plug.values.get("FItem5"))
        it = plug.lives.get("item1") or {}
        check("Live Platz 1: Reihen Produktion/Verbrauch", it.get("series") == {"Produktion": 600, "Verbrauch": 450}
              and it.get("number") == 600 and it.get("on") is False, it)
        res = plug.action("i1", "item", {"slot": 1, "op": "next"})
        check("Platz 1 nächstes (alphabetisch nach Eisenplatte)", res and res["ok"]
              and plug.values.get("FItem1") == "Elektronischer Schaltkreis: 4,5/min", (res, plug.values.get("FItem1")))
        check("Auswahl gemerkt in FItemWahl1", plug.values.get("FItemWahl1") == "item.electronic-circuit",
              plug.values.get("FItemWahl1"))
        check("gewählter Platz leuchtet", (plug.lives.get("item1") or {}).get("on") is True)
        check("automatische Plätze rücken nach", plug.values.get("FItem2") == "Wasser: 1200/min"
              or plug.values.get("FItem2") == "Eisenplatte: 600/min", plug.values.get("FItem2"))
        res = plug.action("i2", "item", {"slot": 2, "op": "set", "value": "kupfer"})
        check("Platz 2 nach deutschem Namen", res and res["ok"] and plug.values.get("FItem2") == "Kupferplatte: 300/min",
              (res, plug.values.get("FItem2")))
        res = plug.action("i3", "item", {"slot": 3, "op": "set", "value": "platte"})
        check("mehrdeutiger Name → Fehler mit Treffern", res and not res["ok"] and "Eisenplatte" in res.get("error", ""), res)
        res = plug.action("i4", "item", {"slot": 9, "op": "next"})
        check("Platz 9 gibt es nicht", res and not res["ok"], res)
        res = plug.action("i5", "item", {"slot": 1, "op": "prev"})
        check("Platz 1 voriges", res and res["ok"] and plug.values.get("FItem1") == "Eisenplatte: 600/min",
              (res, plug.values.get("FItem1")))
        res = plug.action("i6", "item", {"slot": 1, "op": "all_auto"})
        check("alle automatisch", res and res["ok"] and plug.td_values.get("FItemWahl2") == ""
              and plug.values.get("FItem1") == "Eisenplatte: 600/min", (res, plug.values.get("FItem1")))
        plug.action("i7", "item", {"slot": 2, "op": "set", "value": "wasser"})
        saved = dict(plug.td_values)

        # UTLogistics (optional): erst nicht aktiv, dann mit Daten
        mod.utl({"active": False})
        ok = plug.wait(lambda: plug.values.get("FUtlStatus") == "UTLogistics nicht aktiv")
        check("UTL nicht aktiv", ok and plug.values.get("FUtlZuegeFrei") == "–", plug.values.get("FUtlStatus"))
        time.sleep(0.15)
        UTL = {"active": True, "version": "0.0.20", "api": 1, "idle": 4, "deliveries": 7, "stations": 23,
               "networks": 2, "total": 12345, "hour": 34, "utilization": 0.625, "alerts_recent": 2,
               "last_alert": {"icon": "no_train", "group": "no_train", "tick": 5000},
               "unserved": [{"k": "item", "n": "copper-plate", "network": "Eisen", "since": 0,
                             "reason": "no-free-train"}],
               "goods": [{"k": "item", "n": "iron-plate", "hour": 4000, "ten": 700},
                         {"k": "item", "n": "copper-plate", "hour": 2500, "ten": 400}]}
        n_before = len(plug.fired)
        mod.write(tick=7 * 3600 + 100)   # Spiel steht bei Tick 25.300 → Anfrage seit Tick 0 = 7 min
        plug.wait(lambda: plug.values.get("FTick") == str(7 * 3600 + 100))
        mod.utl(UTL)
        ok = plug.wait(lambda: plug.values.get("FUtlZuegeFrei") == "4")
        v = plug.values
        check("UTL Werte", ok and v.get("FUtlStatus") == "UTLogistics 0.0.20" and v.get("FUtlUnterwegs") == "7"
              and v.get("FUtlStationen") == "23" and v.get("FUtlLieferungen") == "12.345"
              and v.get("FUtlAuslastung") == "62 %", {k: v.get(k) for k in v if k.startswith("FUtl")})
        check("UTL letzte Warnung (Kurztext ohne utl-alerts.txt)", v.get("FUtlWarnung") == "Kein freier Zug",
              v.get("FUtlWarnung"))
        check("UTL Lieferungen pro Stunde", v.get("FUtlLieferungenStunde") == "34"
              and (plug.lives.get("utl_rate") or {}).get("number") == 34, v.get("FUtlLieferungenStunde"))
        check("UTL Anfrage ohne Zug", v.get("FUtlOhneZug") == "1"
              and v.get("FUtlOhneZugText") == "Kupferplatte · Eisen · seit 7 min", v.get("FUtlOhneZugText"))
        check("UTL Ware mit Spielname", v.get("FUtlWare1") == "Eisenplatte: 4.000/h", v.get("FUtlWare1"))
        tr = plug.lives.get("utl_trains") or {}
        check("UTL Live Züge mit Reihen", tr.get("series") == {"Frei": 4, "Unterwegs": 7} and tr.get("number") == 7, tr)
        gd = plug.lives.get("utl_goods") or {}
        check("UTL Live Waren nach Ware", gd.get("series") == {"Eisenplatte": 4000, "Kupferplatte": 2500}, gd)
        check("UTL alte Warnung löst nicht aus", not any(f[0] == "utl_alert" for f in plug.fired[n_before:]))
        time.sleep(0.15)
        mod.utl_alerts([(6000, "UTL: Zug 5 steckt seit 3 Minuten fest (Ziel: Eisenmine)")])
        mod.utl(dict(UTL, last_alert={"icon": "stuck", "group": "train", "tick": 6000},
                     unserved=UTL["unserved"] + [{"k": "item", "n": "iron-plate", "network": "Eisen", "since": 500}]))
        ok = plug.wait(lambda: any(f[0] == "utl_alert" for f in plug.fired[n_before:]))
        data = next((f[1] for f in plug.fired[n_before:] if f[0] == "utl_alert"), {})
        check("UTL neue Warnung löst aus, voller Text", ok and
              data.get("Warnung") == "UTL: Zug 5 steckt seit 3 Minuten fest (Ziel: Eisenmine)", data)
        check("UTL voller Text im Wert", plug.values.get("FUtlWarnung", "").startswith("UTL: Zug 5"),
              plug.values.get("FUtlWarnung"))
        check("UTL neue Anfrage ohne Zug löst aus", any(f[0] == "utl_unserved" and f[1].get("Anzahl") == 2
                                                       for f in plug.fired[n_before:]))

        mod.write(power={})
        check("kein Stromnetz → –", plug.wait(lambda: plug.values.get("FStromErzeugung") == "–"))
        check("Live Strom: kein Netz", (plug.lives.get("power") or {}).get("text") == "kein Netz", plug.lives.get("power"))
        mod.write(power={"network": 1, "production": 300000, "consumption": 300000})
        check("Strom unter 1 MW", plug.wait(lambda: plug.values.get("FStromErzeugung") == "0,30 MW"),
              plug.values.get("FStromErzeugung"))

        # 5) Auf Antwort warten: Antwort kommt nach 0,3 s
        def answer():
            time.sleep(0.3)
            mod.push(type="ack", cmd="speed", ok=True, code="speed", value=2)
            mod.write(speed=2)
        threading.Thread(target=answer).start()
        res = plug.action("r7", "await", {"cmd": "speed", "seconds": 3})
        check("await: Antwort des Spiels", res and res["ok"] and res.get("message") == "Geschwindigkeit 2×", res)
        check("Auslöser command_done", any(f[0] == "command_done" and f[1].get("Ok") == "ja" for f in plug.fired))
        check("FMeldung", plug.values.get("FMeldung") == "Geschwindigkeit 2×", plug.values.get("FMeldung"))

        # 6) Fehler-Antwort des Spiels wird zum Fehler der Aktion
        def answer_fail():
            time.sleep(0.2)
            mod.push(type="ack", cmd="pause", ok=False, code="not-admin")
            mod.write()
        threading.Thread(target=answer_fail).start()
        res = plug.action("r8", "await", {"cmd": "pause", "seconds": 3})
        check("await: Fehler vom Spiel", res and not res["ok"] and "Admins" in res.get("error", ""), res)

        # 7) Keine Antwort: Zeitüberschreitung mit Erklärung
        t0 = time.time()
        res = plug.action("r9", "await", {"cmd": "save", "seconds": 1})
        check("await: Zeitüberschreitung", res and not res["ok"] and time.time() - t0 < 3, res)

        # 8) Kaputte Datei: kein Absturz, weiter verbunden
        with open(os.path.join(folder, "state.json"), "w") as f:
            f.write('{"v": 1, "tick": 7')
        time.sleep(0.4)
        mod.write(tick=800)
        time.sleep(0.4)
        check("kaputte Datei überstanden", plug.p.poll() is None and plug.values.get("FVerbunden") == "ja")
        with open(os.path.join(folder, "state.json"), "w") as f:
            f.write('{"v": 99}')
        time.sleep(0.4)
        mod.write(tick=900)
        check("falsche Version ignoriert", plug.wait(lambda: plug.values.get("FTick") == "900"))

        # 9) Herzschlag fällt aus: getrennt, Werte zurückgesetzt
        ok = plug.wait(lambda: plug.values.get("FVerbunden") == "nein", 4)
        check("Herzschlag-Ausfall → getrennt", ok)
        check("Auslöser disconnected", any(f[0] == "disconnected" for f in plug.fired))
        check("Werte zurückgesetzt", plug.values.get("FForschungProzent") == "–", plug.values.get("FForschungProzent"))
        res = plug.action("r10", "await", {"cmd": "chat", "seconds": 1})
        check("await ohne Verbindung → verständlicher Fehler",
              res and not res["ok"] and ("läuft nicht" in res.get("error", "") or "Menü" in res.get("error", "")), res)

        # 10) Pause: Spiel schreibt nichts mehr, bleibt aber „pausiert“ (Prozess läuft)
        game = fake_factorio(tmp)
        mod.write(paused=True, tick=1000)
        ok = plug.wait(lambda: plug.values.get("FStatus") == "pausiert", 3)
        time.sleep(2.6)   # länger als die Zeitgrenze
        check("pausiert bleibt verbunden", ok and plug.values.get("FVerbunden") == "ja", plug.values.get("FStatus"))
        check("FPause an", plug.values.get("FPause") == "an")
        mod.write(paused=False, tick=1001)
        check("weiter → läuft", plug.wait(lambda: plug.values.get("FStatus") == "läuft"))
        ok = plug.wait(lambda: plug.values.get("FStatus", "").startswith("angehalten"), 4)
        check("Spiel läuft, aber keine Daten → angehalten", ok, plug.values.get("FStatus"))
        check("angehalten: bleibt verbunden", plug.values.get("FVerbunden") == "ja")
        check("angehalten: Werte bleiben stehen", plug.values.get("FTick") == "1001", plug.values.get("FTick"))
        res = plug.action("r11", "await", {"cmd": "pause", "seconds": 0.5})
        check("angehalten: Befehl erklärt Menü", res and not res["ok"] and "Esc-Menü" in res.get("error", ""), res)

        # 11) Anderer Spielstand: alte Ereignisse der neuen Sitzung nicht auslösen
        mod2 = FakeMod(folder, session="neu")
        for i in range(5):
            mod2.push(type="rocket_launched", count=i + 1)
        n_before = len(plug.fired)
        mod2.write()
        plug.wait(lambda: plug.values.get("FVerbunden") == "ja")
        time.sleep(0.3)
        check("neue Sitzung: keine alten Raketen", not any(f[0] == "rocket_launched" for f in plug.fired[n_before:]))
        mod2.push(type="rocket_launched", count=6)
        mod2.write(rockets=6)
        ok = plug.wait(lambda: any(f[0] == "rocket_launched" for f in plug.fired[n_before:]))
        data = next((f[1] for f in plug.fired[n_before:] if f[0] == "rocket_launched"), {})
        check("neue Rakete ausgelöst", ok and data.get("Anzahl") == 6, data)

        # 12) Echte Datei vom Mod (aus einem Headless-Lauf), falls angegeben
        if real_state:
            shutil.copy(real_state, os.path.join(folder, "state.json"))
            names = os.path.join(os.path.dirname(real_state), "names.txt")
            if os.path.exists(names):
                shutil.copy(names, os.path.join(folder, "names.txt"))
            ok = plug.wait(lambda: plug.values.get("FStromErzeugung") == "0,30 MW" and plug.values.get("FVerbunden") == "ja")
            check("echte Mod-Datei gelesen", ok, (plug.values.get("FPlanet"), plug.values.get("FStatus")))
            check("echte Datei: Strom vom Radar", plug.values.get("FStromErzeugung") == "0,30 MW",
                  plug.values.get("FStromErzeugung"))

        check("keine Fehler im Plugin", not plug.errors, plug.errors[:3])
        plug.stop()

        # 13) Neustart: die gewählten Plätze kommen aus den TouchDeck-Werten zurück
        mod3 = FakeMod(folder, session="neu")
        mod3.write()
        mod3.items(ITEMS, LABELS)
        plug2 = PluginProcess(settings, td_values=saved)
        ok = plug2.wait(lambda: plug2.values.get("FItem2") == "Wasser: 1200/min", 6)
        check("Auswahl übersteht Neustart", ok, plug2.values.get("FItem2"))
        check("keine Fehler nach Neustart", not plug2.errors, plug2.errors[:3])
        plug2.stop()
    finally:
        if game:
            game.kill()
        shutil.rmtree(tmp, ignore_errors=True)
    passed = sum(RESULTS)
    print(f"\n{passed} von {len(RESULTS)} bestanden")
    sys.exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
