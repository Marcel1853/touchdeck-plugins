#!/usr/bin/env python3
"""Fake-Mod: spielt das Protokoll von „TouchDeck Bridge“ nach, ohne Captain of Industry.

Für die Tests (tests/test_plugin.py) und zum Ausprobieren des Plugins in TouchDeck ohne Spiel:
    python3 tests/fake_mod.py [--port 34202] [--secret …]
Dann antwortet ein kleiner Fake-Inselzustand auf alle Befehle (Pause, Tempo, Kamera …),
die Zeit läuft weiter, und alle 20 s kommt eine Meldung.
"""
import argparse
import json
import socket
import threading
import time

SPEEDS = [1, 2, 3, 5]


def base_state():
    return {
        "inGame": True, "year": 3, "month": 7, "day": 12, "monthName": "Juli",
        "paused": False, "speed": 1, "speeds": SPEEDS, "speedLevel": 1,
        "powerCapacity": 12000, "powerDemand": 9400, "powerUsed": 9400,
        "computingCapacity": 48, "computingDemand": 52,
        "unity": 152, "unityCap": 400.0, "unityMonth": -2.5,
        "workersFree": -6,
        "population": 1240, "populationDiff": 12, "homeless": 0, "housingFree": 35, "housing": 1275,
        "foodMonths": 2, "starving": False, "starvedLastMonth": 0,
        "disease": "", "diseaseMonths": 0,
        "research": "Dampfturbine", "researchProgress": 64, "researchQueue": 2, "researchLab": True,
        "goods": [
            {"id": "IronOre", "name": "Eisenerz", "stock": 1800, "capacity": 2400, "perMonth": 340, "pinned": False},
            {"id": "Diesel", "name": "Diesel", "stock": 90, "capacity": 600, "perMonth": -120, "pinned": True},
            {"id": "ConstructionParts", "name": "Bauteile", "stock": 400, "capacity": 400, "perMonth": 0, "pinned": True},
            {"id": "Food-Bread", "name": "kaputt", "stock": 1},
        ],
        "goodSlots": [
            {"id": "Diesel", "name": "Diesel", "stock": 90, "capacity": 600, "perMonth": -120, "pinned": True},
            {"id": "ConstructionParts", "name": "Bauteile", "stock": 400, "capacity": 400, "perMonth": 0, "pinned": True},
            {"id": "IronOre", "name": "Eisenerz", "stock": 1800, "capacity": 2400, "perMonth": 340, "pinned": False},
        ],
        "alerts": [
            {"text": "Kein Treibstoff", "style": "critical", "count": 4},
            {"text": "Lager voll", "style": "warning", "count": 2},
            {"text": "Forschung abgeschlossen", "style": "success", "count": 1},
        ],
        "history": [
            {"text": "Kein Treibstoff", "kind": "critical", "count": 3, "year": 3, "month": 7, "today": True, "canJump": True},
            {"text": "Dampfkessel", "kind": "research", "count": 1, "year": 3, "month": 6, "today": False, "canJump": False},
            {"text": "18", "kind": "refugees", "count": 1, "year": 3, "month": 5, "today": False, "canJump": False},
        ],
        "unreadMessages": 1,
    }


class FakeMod:
    def __init__(self, port=0, secret="", answer=True):
        self.secret = secret
        self.answer = answer            # False: Befehle nie beantworten (Timeout-Test)
        self.heartbeat = True           # False: keine Herzschläge (Toter-Mod-Test)
        self.state = base_state()
        self.received = []              # alle Nachrichten vom Plugin
        self.hellos = []
        self.clients = []
        self.lock = threading.Lock()
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", port))
        self.srv.listen(4)
        self.port = self.srv.getsockname()[1]
        self.running = True
        threading.Thread(target=self.accept_loop, daemon=True).start()
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()

    # ---------------- Senden ----------------

    def send_raw(self, data):
        with self.lock:
            clients = list(self.clients)
        for c in clients:
            try:
                c.sendall(data)
            except OSError:
                pass

    def send(self, msg):
        self.send_raw((json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8"))

    def push_state(self):
        self.send({"type": "state", "state": self.state})

    def event(self, name, data):
        self.send({"type": "event", "event": name, "data": data})

    def drop_clients(self):
        """Verbindung hart trennen (wie Spiel abgestürzt)."""
        with self.lock:
            clients, self.clients = self.clients, []
        for c in clients:
            try:
                c.shutdown(socket.SHUT_RDWR)
                c.close()
            except OSError:
                pass

    def close(self):
        self.running = False
        self.drop_clients()
        try:
            self.srv.close()
        except OSError:
            pass

    # ---------------- Server ----------------

    def accept_loop(self):
        while self.running:
            try:
                conn, _ = self.srv.accept()
            except OSError:
                return
            threading.Thread(target=self.client_loop, args=(conn,), daemon=True).start()

    def heartbeat_loop(self):
        while self.running:
            time.sleep(1.0)
            if self.heartbeat:
                self.send_raw(b'{"type":"hb"}\n')

    def client_loop(self, conn):
        f = conn.makefile("rb")
        try:
            hello = json.loads(f.readline().decode("utf-8"))
        except (ValueError, OSError):
            f.close()
            conn.close()
            return
        self.hellos.append(hello)
        if hello.get("type") != "hello" or hello.get("proto") != 1:
            conn.sendall(b'{"type":"denied","reason":"proto"}\n')
            f.close()
            conn.close()
            return
        if self.secret and hello.get("secret") != self.secret:
            conn.sendall(b'{"type":"denied","reason":"secret"}\n')
            f.close()
            conn.close()
            return
        with self.lock:
            self.clients.append(conn)
        conn.sendall(b'{"type":"welcome","proto":1,"mod":"0.1.0","game":"fake"}\n')
        conn.sendall((json.dumps({"type": "state", "state": self.state}, ensure_ascii=False) + "\n").encode("utf-8"))
        try:
            for raw in f:
                try:
                    msg = json.loads(raw.decode("utf-8"))
                except ValueError:
                    continue
                self.received.append(msg)
                if msg.get("type") == "cmd" and self.answer:
                    self.handle(conn, msg)
        except OSError:
            pass
        with self.lock:
            if conn in self.clients:
                self.clients.remove(conn)
        f.close()
        conn.close()

    def handle(self, conn, msg):
        cmd, args, st = msg.get("cmd"), msg.get("args") or {}, self.state

        def ack(ok, code, **a):
            line = {"type": "ack", "id": msg.get("id"), "ok": ok, "code": code, "args": a, "msg": code}
            conn.sendall((json.dumps(line, ensure_ascii=False) + "\n").encode("utf-8"))

        if cmd == "refresh":
            ack(True, "refreshed")
            self.push_state()
            return
        if not st.get("inGame"):
            ack(False, "no_game")
            return
        if cmd == "pause":
            op = args.get("op", "toggle")
            st["paused"] = op == "on" or (op == "toggle" and not st["paused"])
            ack(True, "paused" if st["paused"] else "resumed")
        elif cmd == "speed":
            cur = st["speedLevel"]
            level = {"up": min(cur + 1, len(SPEEDS)), "down": max(cur - 1, 1)}.get(args.get("op"), int(args.get("value", 1)))
            if not 1 <= level <= len(SPEEDS):
                ack(False, "bad_speed", value=level, max=len(SPEEDS))
                return
            st["speedLevel"], st["speed"], st["paused"] = level, SPEEDS[level - 1], False
            ack(True, "speed", value=level, factor=SPEEDS[level - 1])
        elif cmd == "save":
            ack(True, "saved", name=args.get("name") or "TouchDeck-Quicksave")
        elif cmd == "history":
            n = int(args.get("n", 1))
            notes = st["history"]
            if not 1 <= n <= len(notes):
                ack(False, "no_history", value=n)
            elif not notes[n - 1]["canJump"]:
                ack(False, "no_place", name=notes[n - 1]["text"])
            else:
                ack(True, "jumped", name=notes[n - 1]["text"])
        elif cmd == "alert":
            n = int(args.get("n", 1))
            alerts = st["alerts"]
            if not 1 <= n <= len(alerts):
                ack(False, "no_alert", value=n)
            else:
                ack(True, "jumped", name=alerts[n - 1]["text"], index=1, count=alerts[n - 1]["count"])
        else:
            ack(False, "unknown_command", value=cmd)
            return
        self.push_state()


def main():
    ap = argparse.ArgumentParser(description="Fake-Mod für das TouchDeck-Plugin „captain-of-industry“")
    ap.add_argument("--port", type=int, default=34202)
    ap.add_argument("--secret", default="")
    a = ap.parse_args()
    mod = FakeMod(a.port, a.secret)
    print(f"Fake-Mod läuft auf 127.0.0.1:{mod.port} (Strg+C beendet)")
    texts = [("Kein Treibstoff", "critical"), ("Lager voll", "warning"), ("Keine Arbeiter", "critical")]
    i = 0
    try:
        while True:
            for _ in range(20):
                time.sleep(1)
                st = mod.state
                if not st["paused"]:
                    # Zeit läuft: ein Tag pro Sekunde und Tempostufe
                    st["day"] += st["speed"]
                    if st["day"] > 30:
                        st["day"] -= 30
                        st["month"] += 1
                        if st["month"] > 12:
                            st["month"] = 1
                            st["year"] += 1
                            mod.event("new_year", {"year": st["year"]})
                        st["monthName"] = f"Monat {st['month']}"
                    st["researchProgress"] = (st["researchProgress"] + 1) % 100
                    mod.push_state()
            text, style = texts[i % len(texts)]
            i += 1
            note = {"text": text, "kind": style, "count": 1, "year": mod.state["year"], "month": mod.state["month"],
                    "today": True, "canJump": True}
            mod.state["history"] = [note] + mod.state["history"][:7]
            mod.event("notification", {"text": text, "style": style})
            mod.push_state()
            print("Meldung:", text)
    except KeyboardInterrupt:
        mod.close()


if __name__ == "__main__":
    main()
