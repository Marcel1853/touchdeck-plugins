#!/usr/bin/env python3
"""Fake-Mod: spielt das Protokoll von „TouchDeck Bridge“ nach, ohne Timberborn.

Für die Tests (tests/test_plugin.py) und zum Ausprobieren des Plugins in TouchDeck ohne Spiel:
    python3 tests/fake_mod.py [--port 34201] [--secret …]
Dann antwortet ein kleiner Fake-Siedlungs-Zustand auf alle Befehle (Pause, Tempo, Kamera …),
die Zeit läuft weiter, und alle 20 s kommt eine Meldung.
"""
import argparse
import json
import socket
import threading
import time

SPEEDS = {1: 1, 2: 3, 3: 7}


def base_state():
    return {
        "inGame": True, "speed": 1.0, "speedLevel": 1, "paused": False, "cycle": 4, "day": 3, "hour": 14.5,
        "daytime": True, "settlement": "Biberbach", "faction": "Folktails", "factionId": "Folktails",
        "weather": "temperate", "weatherName": "Gemäßigtes Wetter", "cycleLength": 13, "hazardDays": 4,
        "hazardIn": 5.5, "hazardLeft": -1, "hazardNext": "", "hazardNextName": "",
        "adults": 18, "children": 5, "bots": 2, "beavers": 23, "population": 25, "homeless": 2, "freeBeds": 0,
        "beds": 21, "unemployed": 3, "freeJobs": 0, "contaminated": 0, "wellbeing": 7, "science": 1234,
        "food": 412, "foodDays": 9.5, "water": 160, "waterDays": 2.4,
        "goods": [
            {"id": "Water", "name": "Wasser", "group": "Water", "stock": 160, "capacity": 600, "perDay": -66.0, "daysLeft": 2.4},
            {"id": "Log", "name": "Rohholz", "group": "Materials", "stock": 230, "capacity": 300, "perDay": 12.5, "daysLeft": -1},
            {"id": "Plank", "name": "Brett", "group": "Materials", "stock": 90, "capacity": 90, "perDay": 0, "daysLeft": -1},
            {"id": "Gear", "name": "Zahnrad", "group": "Materials", "stock": 0, "capacity": 40, "perDay": -1.5, "daysLeft": 0},
            {"id": "Berries", "name": "Beeren", "group": "Food", "stock": 412, "capacity": 800, "perDay": -43.4, "daysLeft": 9.5},
        ],
        "notifications": [
            {"text": "Der Biber „Kalle“ ist gestorben.", "cycle": 4, "day": 3, "today": True, "canJump": True},
            {"text": "Ein neuer Biber wurde geboren.", "cycle": 4, "day": 2, "today": False, "canJump": True},
            {"text": "Wassertank ist leer", "cycle": 3, "day": 12, "today": False, "canJump": False},
        ],
        "alerts": [
            {"text": "Arbeitslos", "count": 3},
            {"text": "Obdachlos", "count": 2},
        ],
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
            st["speed"] = 0.0 if st["paused"] else float(SPEEDS[st["speedLevel"]])
            ack(True, "paused" if st["paused"] else "resumed")
        elif cmd == "speed":
            cur = st["speedLevel"]
            level = {"up": min(cur + 1, 3), "down": max(cur - 1, 1)}.get(args.get("op"), int(args.get("value", 1)))
            if level not in SPEEDS:
                ack(False, "bad_speed", value=level)
                return
            st["speedLevel"], st["speed"], st["paused"] = level, float(SPEEDS[level]), False
            ack(True, "speed", value=level, factor=float(SPEEDS[level]))
        elif cmd == "save":
            ack(True, "saved", name=args.get("name") or "TouchDeck-Quicksave")
        elif cmd == "notification":
            n = int(args.get("n", 1))
            notes = st["notifications"]
            if not 1 <= n <= len(notes):
                ack(False, "no_notification", value=n)
            elif not notes[n - 1]["canJump"]:
                ack(False, "gone", name=notes[n - 1]["text"])
            else:
                ack(True, "jumped", name=notes[n - 1]["text"])
        elif cmd == "alert":
            n = int(args.get("n", 1))
            alerts = st["alerts"]
            if not 1 <= n <= len(alerts):
                ack(False, "no_alert", value=n)
            else:
                ack(True, "jumped", name=alerts[n - 1]["text"], index=1, count=alerts[n - 1]["count"])
        elif cmd == "message":
            ack(bool(args.get("text")), "message_shown" if args.get("text") else "empty")
        else:
            ack(False, "unknown_command", value=cmd)
            return
        self.push_state()


def main():
    ap = argparse.ArgumentParser(description="Fake-Mod für das TouchDeck-Plugin „timberborn“")
    ap.add_argument("--port", type=int, default=34201)
    ap.add_argument("--secret", default="")
    a = ap.parse_args()
    mod = FakeMod(a.port, a.secret)
    print(f"Fake-Mod läuft auf 127.0.0.1:{mod.port} (Strg+C beendet)")
    texts = ["Ein neuer Biber wurde geboren.", "Dürre steht bevor", "Der Biber „Lotte“ ist gestorben."]
    i = 0
    try:
        while True:
            for _ in range(20):
                time.sleep(1)
                st = mod.state
                if not st["paused"]:
                    # Zeit läuft: eine Stunde pro Sekunde und Tempostufe
                    st["hour"] += SPEEDS[st["speedLevel"]]
                    if st["hour"] >= 24:
                        st["hour"] -= 24
                        st["day"] += 1
                        if st["hazardIn"] >= 1:
                            st["hazardIn"] -= 1
                    st["daytime"] = 6 <= st["hour"] < 21
                    mod.push_state()
            text = texts[i % len(texts)]
            i += 1
            note = {"text": text, "cycle": mod.state["cycle"], "day": mod.state["day"], "today": True, "canJump": True}
            mod.state["notifications"] = [note] + mod.state["notifications"][:7]
            mod.event("notification", {"text": text, "cycle": note["cycle"], "day": note["day"]})
            mod.push_state()
            print("Meldung:", text)
    except KeyboardInterrupt:
        mod.close()


if __name__ == "__main__":
    main()
