#!/usr/bin/env python3
"""TouchDeck-Plugin „RimWorld“.

Erweitertes Plugin: TouchDeck startet dieses Programm und tauscht mit ihm JSON-Zeilen über
stdin/stdout aus (siehe Wiki › Advanced plugins). Nur Python-Standardbibliothek.

Der RimWorld-Mod „TouchDeck Bridge“ öffnet einen kleinen TCP-Server (Standard 127.0.0.1:34200).
Dieses Plugin verbindet sich als Client, baut die Verbindung bei Abbruch selbst wieder auf,
setzt Werte und Live-Anzeigen aus dem Zustand des Spiels, meldet Ereignisse als Auslöser und
schickt Befehle (Pause, Tempo, Speichern …), auf die der Mod mit „ack“ antwortet.
Protokoll: mod/TouchDeckBridge/Source/TouchDeckBridge/Protocol/Protocol.cs. Nichts geht ins Internet.
"""

import ipaddress
import json
import os
import socket
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

PROTO = 1
VERSION = "0.1.0"
MAX_LINE = 64 * 1024          # wie Proto.MaxLine im Mod
VALUE_LIMIT = 1000            # TouchDeck kürzt Werte auf 1000 Zeichen (store.rs, set_variable)
DEAD_AFTER = float(os.environ.get("RIMWORLD_DEAD_AFTER") or 12.0)   # Herzschlag alle 5 s; so lange ohne Daten = tot
MIN_REMOTE_SECRET = 12
NAMES = 8                     # RWKolonist1 … RWKolonist8

# --------------------------------------------------------------------------
# Texte (Sprache aus der Systemumgebung, TouchDeck folgt standardmäßig ebenfalls)
# --------------------------------------------------------------------------

_LOCALE = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES")
           or os.environ.get("LANG") or "").lower()
DE = _LOCALE.startswith("de")

TEXTS = {
    "yes": ("ja", "yes"),
    "no": ("nein", "no"),
    "on": ("an", "on"),
    "off": ("aus", "off"),
    "none": ("–", "–"),
    # Verbindung
    "st_connecting": ("Verbinde mit RimWorld …", "Connecting to RimWorld …"),
    "st_offline": ("RimWorld nicht erreichbar", "RimWorld not reachable"),
    "st_menu": ("Hauptmenü (kein Spiel geladen)", "Main menu (no game loaded)"),
    "st_running": ("läuft", "running"),
    "st_paused": ("pausiert", "paused"),
    "st_denied_secret": ("Geheimwort falsch", "Wrong secret"),
    "st_denied_proto": ("Mod-Version passt nicht", "Mod version does not match"),
    "st_denied_full": ("Zu viele Verbindungen", "Too many connections"),
    "st_bad_settings": ("Einstellungen ungültig (siehe Log)", "Invalid settings (see log)"),
    # Tempo (TimeSpeed im Spiel: 0 Pause, 1 normal, 2 schnell, 3 superschnell, 4 ultraschnell)
    "speed_0": ("Pause", "Paused"),
    "speed_1": ("1× normal", "1× normal"),
    "speed_2": ("2× schnell", "2× fast"),
    "speed_3": ("3× superschnell", "3× superfast"),
    "speed_4": ("4× ultraschnell", "4× ultrafast"),
    "draft_text": ("{n}/{m} eingezogen", "{n}/{m} drafted"),
    "danger_none": ("ruhig", "calm"),
    "danger_low": ("Gefahr", "danger"),
    "danger_high": ("große Gefahr", "high danger"),
    "mood_text": ("{v} % ({name})", "{v} % ({name})"),
    # Antworten des Mods (Codes aus GameCommands.cs)
    "state": ("Zustand neu angefordert", "State requested"),
    "paused": ("Spiel pausiert", "Game paused"),
    "resumed": ("Spiel läuft weiter", "Game running again"),
    "force_paused": ("Pause aufgehoben, aber ein Fenster im Spiel hält es noch an",
                     "Unpaused, but a window in the game still holds it"),
    "speed": ("Tempo {value}", "Speed {value}"),
    "speed_force_paused": ("Tempo {value} (ein Fenster im Spiel hält es noch an)",
                           "Speed {value} (a window in the game still holds it)"),
    "no_control": ("Das Spiel lässt das gerade nicht zu: {value}", "The game does not allow that right now: {value}"),
    "speed4_dev": ("Tempo 4 gibt es in RimWorld nur im Entwicklermodus", "Speed 4 only exists in RimWorld's dev mode"),
    "saved": ("Gespeichert als {name}", "Saved as {name}"),
    "save_disabled": ("Speichern geht gerade nicht", "Saving is not possible right now"),
    "save_failed": ("Speichern fehlgeschlagen: {value}", "Saving failed: {value}"),
    "screenshot": ("Screenshot: {path}", "Screenshot: {path}"),
    "drafted": ("{count} Kolonisten eingezogen", "{count} colonists drafted"),
    "undrafted": ("{count} Kolonisten freigegeben", "{count} colonists released"),
    "no_colonists": ("Keine Kolonisten auf dieser Karte, die man einziehen kann", "No draftable colonists on this map"),
    "no_colonist": ("Kolonist {value} gibt es nicht (es gibt {count})", "There is no colonist {value} (there are {count})"),
    "jumped": ("Kamera bei {name}", "Camera at {name}"),
    "no_letter": ("Kein Brief da", "No letter"),
    "no_target": ("Brief „{name}“ hat keinen Ort", "Letter “{name}” has no location"),
    "letter_jumped": ("Kamera beim Brief „{name}“", "Camera at letter “{name}”"),
    "letter_opened": ("Brief „{name}“ geöffnet", "Letter “{name}” opened"),
    "message_shown": ("Nachricht im Spiel gezeigt", "Message shown in game"),
    "empty_text": ("Kein Text angegeben", "No text given"),
    "tab_opened": ("{name} geöffnet", "{name} opened"),
    "tab_closed": ("{name} geschlossen", "{name} closed"),
    "no_tab": ("Reiter „{value}“ gibt es nicht", "There is no tab “{value}”"),
    "research_set": ("Forschung: {name}", "Research: {name}"),
    "research_unknown": ("Forschung „{value}“ nicht gefunden", "Research “{value}” not found"),
    "research_ambiguous": ("„{value}“ passt zu mehreren: {list}", "“{value}” matches several: {list}"),
    "research_done": ("Schon erforscht: {name}", "Already researched: {name}"),
    "research_locked": ("{name} kann noch nicht erforscht werden", "{name} cannot be researched yet"),
    "no_game": ("Kein Spiel geladen (Hauptmenü oder Ladebildschirm)", "No game loaded (main menu or loading screen)"),
    "busy": ("Der Mod ist gerade beschäftigt, bitte gleich nochmal", "The mod is busy, please try again"),
    "bad_value": ("Ungültiger Wert: {value}", "Invalid value: {value}"),
    "unknown_command": ("Der Mod kennt den Befehl „{value}“ nicht (Mod zu alt?)",
                        "The mod does not know the command “{value}” (mod too old?)"),
    "error": ("Fehler im Mod: {value}", "Error in the mod: {value}"),
    # Aktionen
    "not_connected": ("RimWorld nicht erreichbar. Läuft das Spiel mit dem Mod „TouchDeck Bridge“? ({status})",
                      "RimWorld not reachable. Is the game running with the mod “TouchDeck Bridge”? ({status})"),
    "timeout": ("Keine Antwort von RimWorld innerhalb von {s} s", "No answer from RimWorld within {s} s"),
    "lost": ("Verbindung zu RimWorld während des Befehls verloren", "Connection to RimWorld lost during the command"),
    "unknown": ("Unbekannte Aktion: {id}", "Unknown action: {id}"),
    "failed": ("Unerwarteter Fehler, Details im Log.", "Unexpected error, see the log for details."),
}


def t(key, **kw):
    de, en = TEXTS[key]
    try:
        return (de if DE else en).format(**kw)
    except (KeyError, IndexError):
        return de if DE else en


class UserError(Exception):
    """Fehler, den der Nutzer verstehen und selbst beheben kann."""


# --------------------------------------------------------------------------
# Kommunikation mit TouchDeck
# --------------------------------------------------------------------------

_out_lock = threading.Lock()


def send(msg):
    line = json.dumps(msg, ensure_ascii=False) + "\n"
    with _out_lock:
        try:
            sys.stdout.write(line)
            sys.stdout.flush()
        except (BrokenPipeError, ValueError):
            os._exit(0)


def log(message, level="info"):
    send({"type": "log", "level": level, "message": str(message)})


# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------

def to_int(value, default, lo, hi):
    try:
        n = int(float(str(value).replace(",", ".").strip()))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def fmt_int(n):
    """1234567 → „1.234.567“ (Deutsch) bzw. „1,234,567“."""
    try:
        text = f"{int(round(float(n))):,}"
    except (TypeError, ValueError):
        return t("none")
    return text.replace(",", ".") if DE else text


def num(v):
    """Zahl aus dem Zustand oder None (null, Text, NaN)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
        return None
    return v


def check_settings(settings):
    """Host, Port und Geheimwort prüfen. Gibt (host, port, secret, Fehlerliste) zurück."""
    problems = []
    host = str(settings.get("host") or "").strip() or "127.0.0.1"
    try:
        ip = ipaddress.ip_address(host)
        loopback = ip.is_loopback
    except ValueError:
        # Rechnername (z. B. „spiele-pc.local“): erlaubt, zählt aber als entfernt
        loopback = host.lower() == "localhost"
        if not host.replace("-", "").replace(".", "").isalnum():
            problems.append(f"host: ungültiger Rechnername „{host}“, nehme 127.0.0.1")
            host, loopback = "127.0.0.1", True
    raw_port = settings.get("port")
    port = to_int(raw_port, 34200, 0, 70000) if raw_port not in (None, "") else 34200
    if not 1024 <= port <= 65535:
        problems.append(f"port: {raw_port} liegt nicht zwischen 1024 und 65535, nehme 34200")
        port = 34200
    secret = str(settings.get("secret") or "").strip()
    if not loopback and len(secret) < MIN_REMOTE_SECRET:
        problems.append(f"secret: für {host} ist ein Geheimwort mit mindestens {MIN_REMOTE_SECRET} Zeichen nötig "
                        "(genauso wie in den Mod-Einstellungen)")
    return host, port, secret, problems


# --------------------------------------------------------------------------
# Plugin
# --------------------------------------------------------------------------

ALL_VALUES = ["RWDatum", "RWUhrzeit", "RWTempo", "RWPause", "RWKolonisten", "RWStimmungMin", "RWStimmungSchnitt",
              "RWSilber", "RWForschung", "RWForschungProzent", "RWWetter", "RWTemperatur", "RWKarte", "RWKolonie",
              "RWSpielstand", "RWGefangene", "RWEingezogen", "RWBedrohung", "RWStahl", "RWKomponenten", "RWMedizin",
              "RWNahrung", "RWBrief"] + [f"RWKolonist{i}" for i in range(1, NAMES + 1)]
LIVES = ["status", "mood", "research", "speed", "silver", "danger", "draft", "date"]


class Plugin:
    def __init__(self):
        self.lock = threading.RLock()
        self.cond = threading.Condition(self.lock)
        self.stop_evt = threading.Event()
        self.started = False
        self.host, self.port, self.secret = "127.0.0.1", 34200, ""
        self.cmd_timeout = 5.0
        self.sock = None
        self.sock_lock = threading.Lock()   # Schreiben auf den Socket
        self.connected = False              # Hallo bestätigt
        self.status = None
        self.state = None                   # letzter Zustand vom Mod
        self.acks = {}                      # id → ack
        self.next_id = 0
        self.values = {}
        self.lives = {}
        self.reconnect_wait = 1.0

    # ---------------- Start / Stopp ----------------

    def start(self, msg):
        if self.started:
            return
        self.started = True
        settings = msg.get("settings") or {}
        self.host, self.port, self.secret, problems = check_settings(settings)
        self.cmd_timeout = float(to_int(settings.get("timeout"), 5, 2, 60))
        for p in problems:
            log(p, "error" if p.startswith("secret") else "warn")
        with self.lock:
            self.set_value("RWVerbunden", t("no"))
            self.set_value("RWImSpiel", t("no"))
            self.set_value("RWStatus", t("st_connecting"))
            self.reset_values()
        if any(p.startswith("secret") for p in problems):
            with self.lock:
                self.set_status(t("st_bad_settings"))
            return
        threading.Thread(target=self.connect_loop, daemon=True).start()

    def shutdown(self):
        self.stop_evt.set()
        self.close_socket()

    # ---------------- Werte und Live-Anzeigen ----------------

    def set_value(self, name, value):
        value = str(value)[:VALUE_LIMIT]
        if self.values.get(name) != value:
            self.values[name] = value
            send({"type": "setValue", "name": name, "value": value})

    def set_live(self, lid, text, value=None, on=False):
        """value: 0–100 für den Balken (None = kein Balken)."""
        live = {"text": str(text), "value": value, "on": bool(on)}
        if self.lives.get(lid) != live:
            self.lives[lid] = live
            send({"type": "call", "requestId": f"live_{lid}_{time.monotonic_ns()}", "op": "live.set",
                  "args": {"id": lid, "value": live}})

    def reset_values(self):
        for name in ALL_VALUES:
            self.set_value(name, t("none"))
        self.set_value("RWPause", t("off"))
        for lid in LIVES:
            if lid != "status":
                self.set_live(lid, t("none"))

    def set_status(self, text):
        self.status = text
        self.set_value("RWStatus", text)
        self.set_live("status", text, None, self.connected and bool(self.state and self.state.get("inGame")))

    def set_connected(self, connected, status):
        was = self.connected
        self.connected = connected
        self.set_value("RWVerbunden", t("yes") if connected else t("no"))
        if not connected:
            self.state = None
            self.set_value("RWImSpiel", t("no"))
            self.reset_values()
            # wartende Befehle sofort beenden
            self.cond.notify_all()
        self.set_status(status)
        if connected != was:
            send({"type": "fire", "trigger": "connected" if connected else "disconnected", "data": {}})

    # ---------------- Verbindung ----------------

    def close_socket(self):
        with self.sock_lock:
            s, self.sock = self.sock, None
        if s:
            try:
                s.close()
            except OSError:
                pass

    def write(self, msg):
        line = (json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8")
        with self.sock_lock:
            if not self.sock:
                raise OSError("not connected")
            self.sock.sendall(line)

    def connect_loop(self):
        while not self.stop_evt.is_set():
            reason = None
            try:
                reason = self.session()
            except OSError as e:
                if self.connected:
                    log(f"Verbindung zu RimWorld getrennt: {e}", "info")
            except Exception:
                log(traceback.format_exc(), "error")
            self.close_socket()
            with self.lock:
                if reason == "secret":
                    self.set_connected(False, t("st_denied_secret"))
                elif reason == "proto":
                    self.set_connected(False, t("st_denied_proto"))
                elif reason == "full":
                    self.set_connected(False, t("st_denied_full"))
                else:
                    self.set_connected(False, t("st_offline"))
            # Abgelehnt: länger warten, sonst schnell wieder versuchen (bis 10 s)
            wait = 30.0 if reason in ("secret", "proto") else self.reconnect_wait
            self.reconnect_wait = min(self.reconnect_wait * 2, 10.0)
            self.stop_evt.wait(wait)

    def session(self):
        """Eine Verbindung vom Aufbau bis zum Ende. Rückgabe: Grund der Ablehnung oder None."""
        sock = socket.create_connection((self.host, self.port), timeout=3)
        sock.settimeout(DEAD_AFTER)
        with self.sock_lock:
            self.sock = sock
        self.write({"type": "hello", "proto": PROTO, "client": f"touchdeck-rimworld/{VERSION}", "secret": self.secret})
        buf = b""
        welcomed = False
        while not self.stop_evt.is_set():
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                log(f"Keine Daten von RimWorld seit {DEAD_AFTER:.0f} s, verbinde neu", "warn")
                return None
            if not chunk:
                return None
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                if len(raw) > MAX_LINE:
                    log("Zu lange Zeile vom Mod verworfen", "warn")
                    continue
                try:
                    msg = json.loads(raw.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    log(f"Kaputte Zeile vom Mod verworfen: {raw[:120]!r}", "warn")
                    continue
                if not isinstance(msg, dict):
                    continue
                kind = msg.get("type")
                if kind == "denied":
                    reason = str(msg.get("reason") or "")
                    log(f"RimWorld hat die Verbindung abgelehnt: {reason}", "error" if reason in ("secret", "proto") else "warn")
                    return reason
                if kind == "welcome":
                    welcomed = True
                    self.reconnect_wait = 1.0
                    log(f"Verbunden mit RimWorld {msg.get('game', '?')}, Mod {msg.get('mod', '?')}")
                    with self.lock:
                        self.set_connected(True, t("st_menu"))
                elif not welcomed:
                    continue
                elif kind == "state":
                    with self.lock:
                        self.apply_state(msg.get("state") if isinstance(msg.get("state"), dict) else {})
                elif kind == "event":
                    self.handle_event(str(msg.get("event") or ""), msg.get("data") if isinstance(msg.get("data"), dict) else {})
                elif kind == "ack":
                    with self.cond:
                        self.acks[str(msg.get("id"))] = msg
                        self.cond.notify_all()
            if len(buf) > MAX_LINE:
                log("Zu lange Zeile vom Mod verworfen", "warn")
                buf = b""
        return None

    # ---------------- Zustand → Werte und Live-Anzeigen ----------------

    def apply_state(self, st):
        self.state = st
        if not st.get("inGame"):
            self.set_value("RWImSpiel", t("no"))
            self.reset_values()
            self.set_status(t("st_menu"))
            return
        self.set_value("RWImSpiel", t("yes"))
        paused = bool(st.get("paused"))
        speed = to_int(st.get("speed"), 1, 0, 4)
        self.set_status(t("st_paused") if paused else t("st_running"))

        date = str(st.get("date") or "")
        hour = num(st.get("hour"))
        self.set_value("RWDatum", date or t("none"))
        self.set_value("RWUhrzeit", f"{int(hour):02d}:00" if hour is not None else t("none"))
        self.set_live("date", f"{date}\n{int(hour):02d}:00" if hour is not None else date)

        self.set_value("RWTempo", str(speed))
        self.set_value("RWPause", t("on") if paused else t("off"))
        speed_text = t("st_paused") if paused else t(f"speed_{speed}")
        self.set_live("speed", speed_text, None, not paused)

        colonists = to_int(st.get("colonists"), 0, 0, 100000)
        self.set_value("RWKolonisten", str(colonists))
        self.set_value("RWGefangene", str(to_int(st.get("prisoners"), 0, 0, 100000)))
        mood_min, mood_avg = num(st.get("moodMin")), num(st.get("moodAvg"))
        self.set_value("RWStimmungMin", str(int(mood_min)) if mood_min is not None else t("none"))
        self.set_value("RWStimmungSchnitt", str(int(mood_avg)) if mood_avg is not None else t("none"))
        if mood_min is not None:
            name = str(st.get("moodMinName") or "")
            # „an“ (Warnfarbe), wenn jemand unter 25 % ist: Gefahr eines Nervenzusammenbruchs
            self.set_live("mood", t("mood_text", v=int(mood_min), name=name) if name else f"{int(mood_min)} %",
                          max(0, min(100, int(mood_min))), mood_min < 25)
        else:
            self.set_live("mood", t("none"))

        drafted, draftable = to_int(st.get("drafted"), 0, 0, 100000), to_int(st.get("draftable"), 0, 0, 100000)
        self.set_value("RWEingezogen", f"{drafted}/{draftable}")
        self.set_live("draft", t("draft_text", n=drafted, m=draftable), None, draftable > 0 and drafted == draftable)

        silver = st.get("silver")
        self.set_value("RWSilber", str(to_int(silver, 0, 0, 10 ** 9)))
        self.set_live("silver", fmt_int(silver))
        self.set_value("RWStahl", str(to_int(st.get("steel"), 0, 0, 10 ** 9)))
        self.set_value("RWKomponenten", str(to_int(st.get("components"), 0, 0, 10 ** 9)))
        self.set_value("RWMedizin", str(to_int(st.get("medicine"), 0, 0, 10 ** 9)))
        self.set_value("RWNahrung", str(to_int(st.get("nutrition"), 0, 0, 10 ** 9)))

        research = str(st.get("research") or "")
        pct = num(st.get("researchPct"))
        self.set_value("RWForschung", research or t("none"))
        self.set_value("RWForschungProzent", str(int(pct)) if pct is not None else t("none"))
        if research and pct is not None:
            self.set_live("research", f"{research} · {int(pct)} %", max(0, min(100, int(pct))), True)
        else:
            self.set_live("research", t("none"))

        self.set_value("RWWetter", str(st.get("weather") or t("none")))
        self.set_value("RWTemperatur", str(st.get("temp") or t("none")))
        self.set_value("RWKarte", str(st.get("map") or t("none")))
        self.set_value("RWKolonie", str(st.get("colony") or t("none")))
        self.set_value("RWSpielstand", str(st.get("save") or t("none")))
        self.set_value("RWBrief", str(st.get("lastLetter") or t("none")))

        danger = str(st.get("danger") or "none")
        if danger not in ("none", "low", "high"):
            danger = "none"
        self.set_value("RWBedrohung", t(f"danger_{danger}"))
        self.set_live("danger", t(f"danger_{danger}"), None, danger != "none")

        names = st.get("names") if isinstance(st.get("names"), list) else []
        for i in range(1, NAMES + 1):
            self.set_value(f"RWKolonist{i}", str(names[i - 1]) if i <= len(names) else t("none"))

    # ---------------- Ereignisse → Auslöser ----------------

    def handle_event(self, name, d):
        def s(key):
            return str(d.get(key) or "")

        if name == "letter":
            data = {"Titel": s("title"), "Title": s("title"), "Typ": s("kind"), "Kind": s("kind"),
                    "Text": s("text"), "Bedrohung": s("threat"), "Threat": s("threat")}
            send({"type": "fire", "trigger": "letter", "data": data})
            # Überfall: Brief mit großer Bedrohung (ThreatBig – Überfälle, Belagerungen, Mechanoiden …)
            if s("threat") == "big":
                send({"type": "fire", "trigger": "raid", "data": {"Titel": s("title"), "Title": s("title"),
                                                                 "Text": s("text")}})
        elif name == "colonist_died":
            send({"type": "fire", "trigger": "colonist_died", "data": {"Name": s("name")}})
        elif name == "mental_break":
            send({"type": "fire", "trigger": "mental_break",
                  "data": {"Name": s("name"), "Art": s("kind"), "Kind": s("kind"), "Intern": s("defName")}})
        elif name == "research_finished":
            send({"type": "fire", "trigger": "research_finished", "data": {"Name": s("name"), "Intern": s("defName")}})

    # ---------------- Aktionen ----------------

    def run_action(self, msg):
        rid = msg.get("requestId")
        try:
            message = self.dispatch(str(msg.get("id") or ""), msg.get("params") or {})
            send({"type": "result", "requestId": rid, "ok": True, "message": message})
        except UserError as e:
            send({"type": "result", "requestId": rid, "ok": False, "error": str(e)})
        except Exception:
            log(traceback.format_exc(), "error")
            send({"type": "result", "requestId": rid, "ok": False, "error": t("failed")})

    def dispatch(self, action, p):
        def op(default):
            return str(p.get("op") or default)

        if action == "pause":
            return self.command("pause", {"op": op("toggle")})
        if action == "speed":
            return self.command("speed", {"op": op("set"), "value": to_int(p.get("value"), 1, 1, 4)})
        if action == "save":
            return self.command("save", {"name": str(p.get("name") or "")}, timeout=60)
        if action == "screenshot":
            return self.command("screenshot", {})
        if action == "draft":
            return self.command("draft", {"op": op("toggle")})
        if action == "jump":
            return self.command("jump", {"n": to_int(p.get("n"), 1, 1, 999)})
        if action == "cycle":
            return self.command("cycle", {"dir": -1 if op("next") == "prev" else 1})
        if action == "letter":
            return self.command("letter", {"op": op("jump")})
        if action == "message":
            return self.command("message", {"text": str(p.get("text") or ""), "kind": str(p.get("kind") or "neutral")})
        if action == "tab":
            return self.command("tab", {"name": str(p.get("name") or "")})
        if action == "research":
            return self.command("research", {"name": str(p.get("name") or "")})
        if action == "refresh":
            return self.command("state", {})
        raise UserError(t("unknown", id=action))

    def command(self, cmd, args, timeout=None):
        timeout = timeout or self.cmd_timeout
        with self.lock:
            if not self.connected:
                raise UserError(t("not_connected", status=self.status or t("st_offline")))
            self.next_id += 1
            cid = f"c{self.next_id}"
        try:
            self.write({"type": "cmd", "id": cid, "cmd": cmd, "args": args})
        except OSError:
            raise UserError(t("not_connected", status=t("st_offline")))
        deadline = time.monotonic() + timeout
        with self.cond:
            while cid not in self.acks:
                if not self.connected:
                    raise UserError(t("lost"))
                left = deadline - time.monotonic()
                if left <= 0:
                    raise UserError(t("timeout", s=int(timeout)))
                self.cond.wait(min(left, 0.5))
            ack = self.acks.pop(cid)
        message = self.ack_message(ack)
        if not ack.get("ok"):
            raise UserError(message)
        return message

    @staticmethod
    def ack_message(ack):
        code = str(ack.get("code") or "")
        args = ack.get("args") if isinstance(ack.get("args"), dict) else {}
        if code not in TEXTS:
            return str(ack.get("msg") or code)
        kw = {k: str(v) for k, v in args.items()}
        if code in ("speed", "speed_force_paused"):
            kw["value"] = t(f"speed_{to_int(args.get('value'), 1, 0, 4)}")
        return t(code, **kw)


# --------------------------------------------------------------------------
# Hauptschleife
# --------------------------------------------------------------------------

def main():
    plugin = Plugin()
    pool = ThreadPoolExecutor(max_workers=4)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            log(f"Ungültige Nachricht: {line[:200]}", "warn")
            continue
        if not isinstance(msg, dict):
            continue
        kind = msg.get("type")
        if kind == "start":
            plugin.start(msg)
        elif kind == "action":
            if not plugin.started:
                plugin.start({})
            pool.submit(plugin.run_action, msg)
        elif kind == "stop":
            break
    plugin.shutdown()
    pool.shutdown(wait=False, cancel_futures=True)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
