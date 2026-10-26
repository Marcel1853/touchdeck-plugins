#!/usr/bin/env python3
"""Fake-Mod: spielt das Protokoll von „TouchDeck Bridge“ nach, ohne RimWorld.

Für die Tests (tests/test_plugin.py) und zum Ausprobieren des Plugins in TouchDeck ohne Spiel:
    python3 tests/fake_mod.py [--port 34200] [--secret …]
Dann antwortet ein kleiner Fake-Kolonie-Zustand auf alle Befehle (Pause, Tempo, Einziehen …),
und alle 20 s kommt ein Brief.
"""
import argparse
import json
import socket
import threading
import time


def base_state():
    return {
        "inGame": True, "tick": 123456, "speed": 1, "paused": False, "forcePaused": False, "devMode": False,
        "date": "5. Aprimay 5501", "hour": 14, "colony": "Neu-Hoffnung", "map": "Neu-Hoffnung", "save": "Kolonie 1",
        "colonists": 3, "prisoners": 1, "moodMin": 31.0, "moodAvg": 58.0, "moodMinName": "Engie",
        "draftable": 3, "drafted": 0, "names": ["Engie", "Tom", "Ölaf \"der Große\""],
        "silver": 1234, "steel": 450, "components": 12, "medicine": 7, "nutrition": 88.0,
        "weather": "Klar", "tempC": 21.5, "temp": "22°C", "research": "Elektrizität", "researchPct": 42.0,
        "danger": "none", "letters": 2, "lastLetter": "Händler",
        "events": [{"id": 41, "title": "Händler", "kind": "NeutralEvent", "threat": "", "ago": "2 Std."},
                   {"id": 40, "title": "Überfall", "kind": "ThreatBig", "threat": "big", "ago": "1 Tag"},
                   {"id": 37, "title": "Tod: Tom", "kind": "Death", "threat": "", "ago": "3 Tage"}],
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

        if cmd == "state":
            ack(True, "state")
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
            cur = st["speed"]
            target = {"up": min(cur + 1, 3), "down": max(cur - 1, 1)}.get(args.get("op"), int(args.get("value", 1)))
            if target == 4 and not st["devMode"]:
                ack(False, "speed4_dev")
                return
            st["speed"], st["paused"] = target, False
            ack(True, "speed", value=target)
        elif cmd == "save":
            ack(True, "saved", name=args.get("name") or "TouchDeck-Quicksave")
        elif cmd == "screenshot":
            ack(True, "screenshot", path="/tmp/RimWorld/Screenshots/TouchDeck_test.png")
        elif cmd == "draft":
            draft = {"on": True, "off": False}.get(args.get("op"), st["drafted"] < st["draftable"])
            st["drafted"] = st["draftable"] if draft else 0
            ack(True, "drafted" if draft else "undrafted", count=st["draftable"])
        elif cmd == "jump":
            n = int(args.get("n", 1))
            if not 1 <= n <= len(st["names"]):
                ack(False, "no_colonist", value=n, count=len(st["names"]))
            else:
                ack(True, "jumped", name=st["names"][n - 1])
        elif cmd == "cycle":
            ack(True, "jumped", name=st["names"][0])
        elif cmd == "letter":
            lid = int(args.get("id") or 0)
            title = next((e["title"] for e in st["events"] if e["id"] == lid), None) if lid else st["lastLetter"]
            if title is None:
                ack(False, "letter_gone")
                return
            ack(True, "letter_opened" if args.get("op") == "open" else "letter_jumped", name=title)
        elif cmd == "message":
            ack(bool(args.get("text")), "message_shown" if args.get("text") else "empty_text")
        elif cmd == "tab":
            ack(True, "tab_opened", name=args.get("name"))
        elif cmd == "research":
            st["research"], st["researchPct"] = args.get("name"), 0.0
            ack(True, "research_set", name=args.get("name"))
        else:
            ack(False, "unknown_command", value=cmd)
            return
        self.push_state()


def main():
    ap = argparse.ArgumentParser(description="Fake-Mod für das TouchDeck-Plugin „rimworld“")
    ap.add_argument("--port", type=int, default=34200)
    ap.add_argument("--secret", default="")
    a = ap.parse_args()
    mod = FakeMod(a.port, a.secret)
    print(f"Fake-Mod läuft auf 127.0.0.1:{mod.port} (Strg+C beendet)")
    titles = [("Händler", "NeutralEvent", ""), ("Überfall!", "ThreatBig", "big"), ("Krankheit", "NegativeEvent", "")]
    i = 0
    try:
        while True:
            time.sleep(20)
            title, kind, threat = titles[i % len(titles)]
            i += 1
            mod.state["lastLetter"] = title
            mod.state["danger"] = "high" if threat else "none"
            mod.event("letter", {"title": title, "kind": kind, "text": f"Testbrief {i}", "threat": threat})
            mod.push_state()
            print("Brief:", title)
    except KeyboardInterrupt:
        mod.close()


if __name__ == "__main__":
    main()
