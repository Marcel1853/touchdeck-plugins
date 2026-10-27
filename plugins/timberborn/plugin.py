#!/usr/bin/env python3
"""TouchDeck-Plugin „Timberborn“.

Erweitertes Plugin: TouchDeck startet dieses Programm und tauscht mit ihm JSON-Zeilen über
stdin/stdout aus (siehe Wiki › Advanced plugins). Nur Python-Standardbibliothek.

Der Timberborn-Mod „TouchDeck Bridge“ öffnet einen kleinen TCP-Server (Standard 127.0.0.1:34201).
Dieses Plugin verbindet sich als Client, baut die Verbindung bei Abbruch selbst wieder auf,
setzt Werte und Live-Anzeigen aus dem Zustand des Spiels, meldet Ereignisse als Auslöser und
schickt Befehle (Pause, Tempo, Speichern, Kamera …), auf die der Mod mit „ack“ antwortet.
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
VERSION = "0.1.1"
DEFAULT_PORT = 34201
MAX_LINE = 64 * 1024          # wie Proto.MaxLine im Mod
VALUE_LIMIT = 1000            # TouchDeck kürzt Werte auf 1000 Zeichen (store.rs, set_variable)
DEAD_AFTER = float(os.environ.get("TIMBERBORN_DEAD_AFTER") or 12.0)   # Herzschlag alle 5 s; so lange ohne Daten = tot
MIN_REMOTE_SECRET = 12
HISTORY = 8                   # TBMeldung1 … TBMeldung8 (Nachrichtenverlauf, neueste zuerst)
ALERTS = 8                    # TBWarnung1 … TBWarnung8 (aktive Warnungen, die meisten zuerst)
SPEEDS = {0: 0, 1: 1, 2: 3, 3: 7}   # Stufe → Faktor, wie die Tempo-Knöpfe im Spiel
LOW_DAYS = 3                  # Wasser/Nahrung „knapp“ unter so vielen Tagen; Gefahr „steht bevor“ ab so vielen Tagen
# Waren mit eigener Live-Anzeige (Seite „Vorräte“); alle anderen gibt es als Wert TBWare_<Id>
GOOD_LIVES = ["Log", "Plank", "Gear", "TreatedPlank", "MetalBlock", "ScrapMetal", "Biofuel", "Dirt",
              "Explosives", "Paper", "Book", "PunchCard"]

# --------------------------------------------------------------------------
# Texte (Sprache aus der Systemumgebung, TouchDeck folgt standardmäßig ebenfalls)
# --------------------------------------------------------------------------

_LOCALE = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES")
           or os.environ.get("LANG") or "").lower()
DE = _LOCALE.startswith("de")
if not _LOCALE and os.name == "nt":
    try:
        import ctypes
        DE = (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF) == 0x07
    except (AttributeError, OSError):
        pass

TEXTS = {
    "yes": ("ja", "yes"),
    "no": ("nein", "no"),
    "on": ("an", "on"),
    "off": ("aus", "off"),
    "none": ("–", "–"),
    # Verbindung
    "st_connecting": ("Verbinde mit Timberborn …", "Connecting to Timberborn …"),
    "st_offline": ("Timberborn nicht erreichbar", "Timberborn not reachable"),
    "st_menu": ("Hauptmenü (kein Spiel geladen)", "Main menu (no game loaded)"),
    "st_running": ("läuft", "running"),
    "st_paused": ("pausiert", "paused"),
    "st_denied_secret": ("Geheimwort falsch", "Wrong secret"),
    "st_denied_proto": ("Mod-Version passt nicht", "Mod version does not match"),
    "st_denied_full": ("Zu viele Verbindungen", "Too many connections"),
    "st_bad_settings": ("Einstellungen ungültig (siehe Log)", "Invalid settings (see log)"),
    # Anzeigen
    "speed_0": ("Pause", "Paused"),
    "speed_1": ("Tempo 1 (×1)", "Speed 1 (×1)"),
    "speed_2": ("Tempo 2 (×3)", "Speed 2 (×3)"),
    "speed_3": ("Tempo 3 (×7)", "Speed 3 (×7)"),
    "date": ("Zyklus {cycle} · Tag {day}", "Cycle {cycle} · Day {day}"),
    "night": ("Nacht", "night"),
    "days": ("{n} Tage", "{n} days"),
    "day1": ("1 Tag", "1 day"),
    "days_in": ("{n} Tagen", "{n} days"),
    "hazard_in": ("{name} in {days}", "{name} in {days}"),
    "hazard_unknown": ("Gefahr in {days}", "Hazard in {days}"),
    "hazard_left": ("{name}: noch {days}", "{name}: {days} left"),
    "no_hazard": ("Keine Gefahr in diesem Zyklus", "No hazard this cycle"),
    "beavers": ("{n} Biber", "{n} beavers"),
    "beavers_detail": ("{adults} erw. · {children} Kinder · {bots} Bots", "{adults} adults · {children} kids · {bots} bots"),
    "homeless": ("{n} obdachlos", "{n} homeless"),
    "free_beds": ("{n} Betten frei", "{n} beds free"),
    "unemployed": ("{n} arbeitslos", "{n} unemployed"),
    "free_jobs": ("{n} Stellen frei", "{n} jobs free"),
    "contaminated": ("{n} verseucht", "{n} contaminated"),
    "wellbeing": ("Zufriedenheit {n}", "Well-being {n}"),
    "science": ("{n} Wissenschaft", "{n} science"),
    "supply": ("{stock} · {days}", "{stock} · {days}"),
    "supply_ok": ("{stock} · reicht", "{stock} · enough"),
    "per_day": ("{n}/Tag", "{n}/day"),
    "alerts_none": ("Keine Warnungen", "No alerts"),
    "alerts_count": ("{n} Warnungen", "{n} alerts"),
    "alert_line": ("{text} ({count})", "{text} ({count})"),
    "note_line": ("{text} (Z{cycle} T{day})", "{text} (C{cycle} D{day})"),
    # Antworten des Mods (Codes aus GameLink.cs)
    "refreshed": ("Zustand neu angefordert", "State requested"),
    "paused": ("Spiel pausiert", "Game paused"),
    "resumed": ("Spiel läuft weiter", "Game running again"),
    "speed": ("Tempo {value} (×{factor})", "Speed {value} (×{factor})"),
    "bad_speed": ("Tempo {value} gibt es nicht (1–3)", "There is no speed {value} (1–3)"),
    "saved": ("Gespeichert als {name}", "Saved as {name}"),
    "save_failed": ("Speichern fehlgeschlagen: {value}", "Saving failed: {value}"),
    "jumped": ("Kamera bei „{name}“", "Camera at “{name}”"),
    "no_notification": ("Meldung {value} gibt es noch nicht", "There is no notification {value} yet"),
    "no_alert": ("Warnung {value} gibt es gerade nicht", "There is no alert {value} right now"),
    "gone": ("„{name}“ gibt es nicht mehr", "“{name}” no longer exists"),
    "message_shown": ("Nachricht im Spiel gezeigt", "Message shown in game"),
    "empty": ("Kein Text angegeben", "No text given"),
    "no_game": ("Kein Spiel geladen (Hauptmenü oder Ladebildschirm)", "No game loaded (main menu or loading screen)"),
    "busy": ("Der Mod ist gerade beschäftigt, bitte gleich nochmal", "The mod is busy, please try again"),
    "bad_value": ("Ungültiger Wert: {value}", "Invalid value: {value}"),
    "unknown_command": ("Der Mod kennt den Befehl „{value}“ nicht (Mod zu alt?)",
                        "The mod does not know the command “{value}” (mod too old?)"),
    "error": ("Fehler im Mod: {value}", "Error in the mod: {value}"),
    # Aktionen
    "not_connected": ("Timberborn nicht erreichbar. Läuft das Spiel mit dem Mod „TouchDeck Bridge“? ({status})",
                      "Timberborn not reachable. Is the game running with the mod “TouchDeck Bridge”? ({status})"),
    "timeout": ("Keine Antwort von Timberborn innerhalb von {s} s", "No answer from Timberborn within {s} s"),
    "lost": ("Verbindung zu Timberborn während des Befehls verloren", "Connection to Timberborn lost during the command"),
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


def fmt_dec(x):
    """2.5 → „2,5“ (Deutsch); ganze Zahlen ohne Nachkommastelle."""
    x = round(float(x), 1)
    text = str(int(x)) if x == int(x) else f"{x:.1f}"
    return text.replace(".", ",") if DE else text


def fmt_days(x, dative=False):
    """Tage als Text: „1 Tag“, „2,5 Tage“ (nach „in“: „2,5 Tagen“)."""
    x = round(float(x), 1)
    return t("day1") if x == 1 else t("days_in" if dative else "days", n=fmt_dec(x))


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
    port = to_int(raw_port, DEFAULT_PORT, 0, 70000) if raw_port not in (None, "") else DEFAULT_PORT
    if not 1024 <= port <= 65535:
        problems.append(f"port: {raw_port} liegt nicht zwischen 1024 und 65535, nehme {DEFAULT_PORT}")
        port = DEFAULT_PORT
    secret = str(settings.get("secret") or "").strip()
    if not loopback and len(secret) < MIN_REMOTE_SECRET:
        problems.append(f"secret: für {host} ist ein Geheimwort mit mindestens {MIN_REMOTE_SECRET} Zeichen nötig "
                        "(genauso wie in settings.json des Mods)")
    return host, port, secret, problems


# --------------------------------------------------------------------------
# Plugin
# --------------------------------------------------------------------------

ALL_VALUES = ["TBZyklus", "TBTag", "TBUhrzeit", "TBDatum", "TBTempo", "TBWetter", "TBGefahrIn", "TBGefahrArt",
              "TBGefahrRest", "TBGefahrDauer", "TBBiber", "TBErwachsene", "TBKinder", "TBBots", "TBBevoelkerung",
              "TBObdachlos", "TBBettenFrei", "TBArbeitslos", "TBStellenFrei", "TBVerseucht", "TBZufriedenheit",
              "TBWissenschaft", "TBWasser", "TBWasserTage", "TBNahrung", "TBNahrungTage", "TBWarnungen",
              "TBFraktion", "TBSiedlung"] \
    + [f"TBMeldung{i}" for i in range(1, HISTORY + 1)] + [f"TBWarnung{i}" for i in range(1, ALERTS + 1)]
LIVES = ["status", "date", "speed", "weather", "population", "homeless", "unemployed", "contaminated", "wellbeing",
         "science", "water", "food", "alerts"] + [f"good_{g}" for g in GOOD_LIVES] \
    + [f"note{i}" for i in range(1, HISTORY + 1)] + [f"alert{i}" for i in range(1, ALERTS + 1)]


class Plugin:
    def __init__(self):
        self.lock = threading.RLock()
        self.cond = threading.Condition(self.lock)
        self.stop_evt = threading.Event()
        self.started = False
        self.host, self.port, self.secret = "127.0.0.1", DEFAULT_PORT, ""
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
        self.good_values = set()            # gesetzte TBWare_<Id>
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
            self.set_value("TBVerbunden", t("no"))
            self.set_value("TBImSpiel", t("no"))
            self.set_value("TBStatus", t("st_connecting"))
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
        for name in self.good_values:
            self.set_value(name, t("none"))
        self.set_value("TBPause", t("off"))
        for lid in LIVES:
            if lid != "status":
                self.set_live(lid, t("none"))

    def set_status(self, text):
        self.status = text
        self.set_value("TBStatus", text)
        self.set_live("status", text, None, self.connected and bool(self.state and self.state.get("inGame")))

    def set_connected(self, connected, status):
        was = self.connected
        self.connected = connected
        self.set_value("TBVerbunden", t("yes") if connected else t("no"))
        if not connected:
            self.state = None
            self.set_value("TBImSpiel", t("no"))
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
                    log(f"Verbindung zu Timberborn getrennt: {e}", "info")
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
        self.write({"type": "hello", "proto": PROTO, "client": f"touchdeck-timberborn/{VERSION}", "secret": self.secret})
        buf = b""
        welcomed = False
        while not self.stop_evt.is_set():
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                log(f"Keine Daten von Timberborn seit {DEAD_AFTER:.0f} s, verbinde neu", "warn")
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
                    log(f"Timberborn hat die Verbindung abgelehnt: {reason}", "error" if reason in ("secret", "proto") else "warn")
                    return reason
                if kind == "welcome":
                    welcomed = True
                    self.reconnect_wait = 1.0
                    log(f"Verbunden mit Timberborn {msg.get('game', '?')}, Mod {msg.get('mod', '?')}")
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
            self.set_value("TBImSpiel", t("no"))
            self.reset_values()
            self.set_status(t("st_menu"))
            return
        self.set_value("TBImSpiel", t("yes"))
        paused = bool(st.get("paused"))
        self.set_status(t("st_paused") if paused else t("st_running"))
        self.apply_time(st, paused)
        self.apply_weather(st)
        self.apply_population(st)
        self.apply_goods(st)
        self.apply_history(st)
        self.apply_alerts(st)
        self.set_value("TBFraktion", str(st.get("faction") or t("none")))
        self.set_value("TBSiedlung", str(st.get("settlement") or t("none")))

    def apply_time(self, st, paused):
        cycle, day = to_int(st.get("cycle"), 0, 0, 10 ** 6), to_int(st.get("day"), 0, 0, 10 ** 6)
        hour = num(st.get("hour"))
        clock = f"{int(hour):02d}:{int((hour % 1) * 60):02d}" if hour is not None else t("none")
        date = t("date", cycle=cycle, day=day)
        self.set_value("TBZyklus", str(cycle))
        self.set_value("TBTag", str(day))
        self.set_value("TBUhrzeit", clock)
        self.set_value("TBDatum", date)
        night = st.get("daytime") is False
        self.set_live("date", f"{date}\n{clock}" + (f" · {t('night')}" if night else ""), None, night)

        level = to_int(st.get("speedLevel"), 1, 0, 3)
        self.set_value("TBTempo", "0" if paused else str(level))
        self.set_value("TBPause", t("on") if paused else t("off"))
        self.set_live("speed", t("speed_0") if paused else t(f"speed_{level}"), None, not paused)

    def apply_weather(self, st):
        name = str(st.get("weatherName") or "")
        self.set_value("TBWetter", name or t("none"))
        until, left = num(st.get("hazardIn")), num(st.get("hazardLeft"))
        duration = to_int(st.get("hazardDays"), 0, 0, 10 ** 4)
        next_name = str(st.get("hazardNextName") or "")
        self.set_value("TBGefahrDauer", str(duration) if duration else t("none"))
        self.set_value("TBGefahrArt", next_name or "?")
        cycle_len = max(1, to_int(st.get("cycleLength"), 1, 1, 10 ** 4))
        if left is not None and left >= 0:
            # Gefahr läuft: Balken = wie viel davon noch übrig ist
            self.set_value("TBGefahrIn", "0")
            self.set_value("TBGefahrRest", fmt_dec(left))
            bar = max(0, min(100, int(round(100 * left / duration)))) if duration else None
            self.set_live("weather", t("hazard_left", name=next_name or name, days=fmt_days(left)), bar, True)
        elif until is not None and until >= 0:
            self.set_value("TBGefahrIn", fmt_dec(until))
            self.set_value("TBGefahrRest", t("none"))
            days = fmt_days(until, dative=True)
            text = t("hazard_in", name=next_name, days=days) if next_name else t("hazard_unknown", days=days)
            # Balken = Rest der ruhigen Zeit; „an“, sobald das Spiel die Gefahr ankündigt
            bar = max(0, min(100, int(round(100 * until / cycle_len))))
            self.set_live("weather", text, bar, until <= LOW_DAYS)
        else:
            self.set_value("TBGefahrIn", t("none"))
            self.set_value("TBGefahrRest", t("none"))
            self.set_live("weather", t("no_hazard"))

    def apply_population(self, st):
        def n(key):
            return to_int(st.get(key), 0, 0, 10 ** 6)

        beavers, adults, children, bots = n("beavers"), n("adults"), n("children"), n("bots")
        self.set_value("TBBiber", str(beavers))
        self.set_value("TBErwachsene", str(adults))
        self.set_value("TBKinder", str(children))
        self.set_value("TBBots", str(bots))
        self.set_value("TBBevoelkerung", str(n("population")))
        self.set_live("population", f"{t('beavers', n=beavers)}\n{t('beavers_detail', adults=adults, children=children, bots=bots)}")

        homeless, free_beds = n("homeless"), n("freeBeds")
        self.set_value("TBObdachlos", str(homeless))
        self.set_value("TBBettenFrei", str(free_beds))
        self.set_live("homeless", f"{t('homeless', n=homeless)}\n{t('free_beds', n=free_beds)}", None, homeless > 0)

        unemployed, free_jobs = n("unemployed"), n("freeJobs")
        self.set_value("TBArbeitslos", str(unemployed))
        self.set_value("TBStellenFrei", str(free_jobs))
        self.set_live("unemployed", f"{t('unemployed', n=unemployed)}\n{t('free_jobs', n=free_jobs)}", None, unemployed > 0)

        contaminated = n("contaminated")
        self.set_value("TBVerseucht", str(contaminated))
        self.set_live("contaminated", t("contaminated", n=contaminated), None, contaminated > 0)

        wellbeing = num(st.get("wellbeing"))
        self.set_value("TBZufriedenheit", str(int(wellbeing)) if wellbeing is not None else t("none"))
        self.set_live("wellbeing", t("wellbeing", n=int(wellbeing)) if wellbeing is not None else t("none"))

        science = n("science")
        self.set_value("TBWissenschaft", str(science))
        self.set_live("science", t("science", n=fmt_int(science)))

    def apply_goods(self, st):
        for key, value, days_value, live in (("water", "TBWasser", "TBWasserTage", "water"),
                                             ("food", "TBNahrung", "TBNahrungTage", "food")):
            stock = to_int(st.get(key), 0, 0, 10 ** 9)
            days = num(st.get(key + "Days"))
            self.set_value(value, str(stock))
            if days is not None and days >= 0:
                self.set_value(days_value, fmt_dec(days))
                self.set_live(live, t("supply", stock=fmt_int(stock), days=fmt_days(days)), None, days < LOW_DAYS)
            else:
                # Vorrat wird nicht weniger (oder noch keine Statistik vom Spiel)
                self.set_value(days_value, t("none"))
                self.set_live(live, t("supply_ok", stock=fmt_int(stock)), None, stock == 0)

        goods = [g for g in (st.get("goods") if isinstance(st.get("goods"), list) else []) if isinstance(g, dict)]
        seen = set()
        for g in goods:
            gid = str(g.get("id") or "")
            if not gid.replace("_", "").isalnum():
                continue
            stock, cap = to_int(g.get("stock"), 0, 0, 10 ** 9), to_int(g.get("capacity"), 0, 0, 10 ** 9)
            name = f"TBWare_{gid}"
            seen.add(name)
            self.good_values.add(name)
            self.set_value(name, str(stock))
            if gid in GOOD_LIVES:
                per_day = num(g.get("perDay"))
                trend = f" · {t('per_day', n=('+' if per_day > 0 else '') + fmt_dec(per_day))}" if per_day else ""
                bar = max(0, min(100, int(round(100 * stock / cap)))) if cap else None
                self.set_live(f"good_{gid}", f"{g.get('name') or gid}\n{fmt_int(stock)}/{fmt_int(cap)}{trend}", bar,
                              cap > 0 and stock >= cap)
        for name in self.good_values - seen:
            self.set_value(name, "0")
        for gid in GOOD_LIVES:
            if f"TBWare_{gid}" not in seen:
                self.set_live(f"good_{gid}", t("none"))

    def apply_history(self, st):
        notes = [e for e in (st.get("notifications") if isinstance(st.get("notifications"), list) else []) if isinstance(e, dict)]
        for i in range(1, HISTORY + 1):
            if i <= len(notes):
                e = notes[i - 1]
                text = str(e.get("text") or "")
                cycle, day = to_int(e.get("cycle"), 0, 0, 10 ** 6), to_int(e.get("day"), 0, 0, 10 ** 6)
                self.set_value(f"TBMeldung{i}", t("note_line", text=text, cycle=cycle, day=day))
                # „an“ = von heute (neu)
                self.set_live(f"note{i}", f"{text}\n{t('date', cycle=cycle, day=day)}", None, bool(e.get("today")))
            else:
                self.set_value(f"TBMeldung{i}", t("none"))
                self.set_live(f"note{i}", t("none"))

    def apply_alerts(self, st):
        alerts = [a for a in (st.get("alerts") if isinstance(st.get("alerts"), list) else []) if isinstance(a, dict)]
        total = sum(to_int(a.get("count"), 0, 0, 10 ** 6) for a in alerts)
        self.set_value("TBWarnungen", str(len(alerts)))
        if alerts:
            first = alerts[0]
            summary = t("alerts_count", n=len(alerts)) + f"\n{first.get('text') or ''} ({to_int(first.get('count'), 0, 0, 10 ** 6)})"
            self.set_live("alerts", summary, None, total > 0)
        else:
            self.set_live("alerts", t("alerts_none"))
        for i in range(1, ALERTS + 1):
            if i <= len(alerts):
                a = alerts[i - 1]
                text, count = str(a.get("text") or ""), to_int(a.get("count"), 0, 0, 10 ** 6)
                self.set_value(f"TBWarnung{i}", t("alert_line", text=text, count=count))
                self.set_live(f"alert{i}", f"{text}\n{count}×", None, True)
            else:
                self.set_value(f"TBWarnung{i}", t("none"))
                self.set_live(f"alert{i}", t("none"))

    # ---------------- Ereignisse → Auslöser ----------------

    def handle_event(self, name, d):
        def s(key):
            return str(d.get(key) if d.get(key) is not None else "")

        if name == "notification":
            send({"type": "fire", "trigger": "notification",
                  "data": {"Text": s("text"), "Zyklus": s("cycle"), "Cycle": s("cycle"), "Tag": s("day"), "Day": s("day")}})
        elif name in ("hazard_approaching", "hazard_started", "hazard_ended"):
            send({"type": "fire", "trigger": name,
                  "data": {"Art": s("kind"), "Kind": s("kind"), "Name": s("name"), "Tage": s("days"), "Days": s("days"),
                           "Zyklus": s("cycle"), "Cycle": s("cycle")}})
        elif name == "cycle_started":
            send({"type": "fire", "trigger": "cycle_started", "data": {"Zyklus": s("cycle"), "Cycle": s("cycle")}})
        elif name == "beaver_born":
            send({"type": "fire", "trigger": "beaver_born", "data": {}})
        elif name == "character_died":
            send({"type": "fire", "trigger": "character_died", "data": {"Name": s("name"), "Alter": s("age"), "Age": s("age")}})
        elif name == "alert":
            send({"type": "fire", "trigger": "alert", "data": {"Text": s("text")}})
        elif name == "game_over":
            send({"type": "fire", "trigger": "game_over", "data": {}})

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
            return self.command("speed", {"op": op("set"), "value": to_int(p.get("value"), 1, 1, 3)})
        if action == "save":
            return self.command("save", {"name": str(p.get("name") or "")}, timeout=60)
        if action == "notification":
            return self.command("notification", {"n": to_int(p.get("n"), 1, 1, HISTORY)})
        if action == "alert":
            return self.command("alert", {"n": to_int(p.get("n"), 1, 1, ALERTS)})
        if action == "message":
            return self.command("message", {"text": str(p.get("text") or ""), "kind": str(p.get("kind") or "info")})
        if action == "refresh":
            return self.command("refresh", {})
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
        if code == "speed":
            kw["factor"] = fmt_dec(num(args.get("factor")) or SPEEDS.get(to_int(args.get("value"), 1, 1, 3), 1))
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
