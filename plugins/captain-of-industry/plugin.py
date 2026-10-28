#!/usr/bin/env python3
"""TouchDeck-Plugin „Captain of Industry“.

Erweitertes Plugin: TouchDeck startet dieses Programm und tauscht mit ihm JSON-Zeilen über
stdin/stdout aus (siehe Wiki › Advanced plugins). Nur Python-Standardbibliothek.

Der Mod „TouchDeck Bridge“ für Captain of Industry öffnet einen kleinen TCP-Server (Standard
127.0.0.1:34202). Dieses Plugin verbindet sich als Client, baut die Verbindung bei Abbruch selbst wieder
auf, setzt Werte und Live-Anzeigen aus dem Zustand des Spiels, meldet Ereignisse als Auslöser und schickt
Befehle (Pause, Tempo, Speichern, Kamera …), auf die der Mod mit „ack“ antwortet.
Protokoll: mod/TouchDeckBridge/Source/TouchDeckBridge/Protocol/Protocol.cs. Nichts geht ins Internet.

Bewusst ohne Desktop-Benachrichtigungen: Warnungen zeigen die Buttons (rot), nicht der PC.
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
DEFAULT_PORT = 34202
MAX_LINE = 64 * 1024          # wie Proto.MaxLine im Mod
VALUE_LIMIT = 1000            # TouchDeck kürzt Werte auf 1000 Zeichen (store.rs, set_variable)
DEAD_AFTER = float(os.environ.get("COI_DEAD_AFTER") or 12.0)   # Herzschlag alle 5 s; so lange ohne Daten = tot
MIN_REMOTE_SECRET = 12
HISTORY = 8                   # COIVerlauf1 … COIVerlauf8 (neue Meldungen und Nachrichten, neueste zuerst)
ALERTS = 8                    # COIWarnung1 … COIWarnung8 (aktive Meldungen, kritische zuerst)
GOODS = 8                     # Live-Anzeigen good1 … good8 (angeheftete Waren, dann größter Bestand)
LOW_FOOD = 3                  # Nahrung „knapp“ unter so vielen Monaten (wie GameLink.LowFoodMonths)

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
    "st_connecting": ("Verbinde mit Captain of Industry …", "Connecting to Captain of Industry …"),
    "st_offline": ("Captain of Industry nicht erreichbar", "Captain of Industry not reachable"),
    "st_menu": ("Hauptmenü (kein Spiel geladen)", "Main menu (no game loaded)"),
    "st_running": ("läuft", "running"),
    "st_paused": ("pausiert", "paused"),
    "st_denied_secret": ("Geheimwort falsch", "Wrong secret"),
    "st_denied_proto": ("Mod-Version passt nicht", "Mod version does not match"),
    "st_denied_full": ("Zu viele Verbindungen", "Too many connections"),
    "st_bad_settings": ("Einstellungen ungültig (siehe Log)", "Invalid settings (see log)"),
    # Anzeigen
    "paused_live": ("Pause", "Paused"),
    "speed_live": ("Tempo {level} (×{factor})", "Speed {level} (×{factor})"),
    "date": ("Jahr {year} · {month}", "Year {year} · {month}"),
    "month_n": ("Monat {n}", "Month {n}"),
    "power": ("Strom {used} / {cap}", "Power {used} / {cap}"),
    "power_short": ("Strom fehlt: {missing}", "Power missing: {missing}"),
    "power_free": ("{free} frei", "{free} spare"),
    "computing": ("Rechnen {used} / {cap}", "Computing {used} / {cap}"),
    "unity": ("Einheit {n}", "Unity {n}"),
    "per_month": ("{n}/Monat", "{n}/month"),
    "workers_free": ("{n} Arbeiter frei", "{n} workers free"),
    "workers_missing": ("{n} Arbeiter fehlen", "{n} workers missing"),
    "workers_ok": ("Arbeiter passen genau", "Workers exactly enough"),
    "population": ("{n} Einwohner", "{n} people"),
    "homeless": ("{n} obdachlos", "{n} homeless"),
    "housing_free": ("{n} Wohnplätze frei", "{n} homes free"),
    "food": ("Nahrung für {n} Monate", "Food for {n} months"),
    "food1": ("Nahrung für 1 Monat", "Food for 1 month"),
    "starving": ("Hunger! Nahrung fehlt", "Starving! No food"),
    "healthy": ("Keine Krankheit", "No disease"),
    "disease": ("{name}: noch {n} Monate", "{name}: {n} months left"),
    "research": ("{name} · {pct} %", "{name} · {pct} %"),
    "research_none": ("Keine Forschung aktiv", "No research running"),
    "research_nolab": ("Kein Forschungslabor aktiv", "No research lab active"),
    "alerts_none": ("Keine Meldungen", "No alerts"),
    "alerts_count": ("{n} Meldungen", "{n} alerts"),
    "alert_line": ("{text} ({count})", "{text} ({count})"),
    "history_line": ("{text} (Jahr {year})", "{text} (year {year})"),
    "times": ("{n}×", "{n}×"),
    "kind_research": ("Forschung fertig: {text}", "Research done: {text}"),
    "kind_refugees": ("{text} Flüchtlinge aufgenommen", "{text} refugees joined"),
    "kind_explored": ("Ort erkundet", "Location explored"),
    "kind_battle": ("Schiff im Kampf", "Ship in battle"),
    "kind_message": ("Nachricht: {text}", "Message: {text}"),
    "good_line": ("{name}\n{stock}{cap}{trend}", "{name}\n{stock}{cap}{trend}"),
    # Antworten des Mods (Codes aus GameLink.cs)
    "refreshed": ("Zustand neu angefordert", "State requested"),
    "paused": ("Spiel pausiert", "Game paused"),
    "resumed": ("Spiel läuft weiter", "Game running again"),
    "speed": ("Tempo {value} (×{factor})", "Speed {value} (×{factor})"),
    "bad_speed": ("Tempo {value} gibt es nicht (1–{max})", "There is no speed {value} (1–{max})"),
    "saved": ("Speichern als „{name}“ angestoßen", "Saving as “{name}” started"),
    "save_failed": ("Speichern fehlgeschlagen: {value}", "Saving failed: {value}"),
    "jumped": ("Kamera bei „{name}“", "Camera at “{name}”"),
    "no_alert": ("Meldung {value} gibt es gerade nicht", "There is no alert {value} right now"),
    "no_history": ("Eintrag {value} gibt es im Verlauf noch nicht", "There is no entry {value} in the history yet"),
    "no_place": ("„{name}“ hat keinen Ort (mehr)", "“{name}” has no place (any more)"),
    "no_camera": ("Kamera des Spiels nicht gefunden", "Game camera not found"),
    "no_game": ("Kein Spiel geladen (Hauptmenü oder Ladebildschirm)", "No game loaded (main menu or loading screen)"),
    "busy": ("Das Spiel speichert gerade, bitte gleich nochmal", "The game is saving, please try again"),
    "bad_value": ("Ungültiger Wert: {value}", "Invalid value: {value}"),
    "unknown_command": ("Der Mod kennt den Befehl „{value}“ nicht (Mod zu alt?)",
                        "The mod does not know the command “{value}” (mod too old?)"),
    "error": ("Fehler im Mod: {value}", "Error in the mod: {value}"),
    # Aktionen
    "not_connected": ("Captain of Industry nicht erreichbar. Läuft ein Spielstand mit dem Mod „TouchDeck Bridge“? ({status})",
                      "Captain of Industry not reachable. Is a game running with the mod “TouchDeck Bridge”? ({status})"),
    "timeout": ("Keine Antwort vom Spiel innerhalb von {s} s", "No answer from the game within {s} s"),
    "lost": ("Verbindung zum Spiel während des Befehls verloren", "Connection to the game lost during the command"),
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


def fmt_signed(x):
    """+12 / −3,5 (0 ohne Vorzeichen)."""
    x = round(float(x), 1)
    if x > 0:
        return "+" + fmt_dec(x)
    if x < 0:
        return "−" + fmt_dec(-x)
    return "0"


def fmt_power(kw):
    """Strom wie im Spiel: kW, ab 1000 kW als MW, ab 1000 MW als GW."""
    kw = float(kw)
    if abs(kw) >= 1_000_000:
        return f"{fmt_dec(kw / 1_000_000)} GW"
    if abs(kw) >= 1000:
        return f"{fmt_dec(kw / 1000)} MW"
    return f"{fmt_int(kw)} kW"


def fmt_compute(tf):
    """Rechenleistung wie im Spiel in TFLOPS."""
    return f"{fmt_int(tf)} TF"


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


def history_text(e):
    """Text eines Verlaufseintrags je nach Art (Meldung, Forschung, Nachricht …)."""
    kind, text = str(e.get("kind") or ""), str(e.get("text") or "")
    if kind in ("research", "refugees", "explored", "battle"):
        text = t(f"kind_{kind}", text=text)
    elif kind == "message" and text:
        text = t("kind_message", text=text)
    count = to_int(e.get("count"), 1, 1, 10 ** 6)
    return f"{text} ({t('times', n=count)})" if count > 1 else text


# --------------------------------------------------------------------------
# Plugin
# --------------------------------------------------------------------------

ALL_VALUES = ["COIJahr", "COIMonat", "COIDatum", "COITempo", "COIStrom", "COIStromBedarf", "COIStromKapazitaet",
              "COIRechnen", "COIRechnenKapazitaet", "COIEinheit", "COIEinheitMonat", "COIArbeiterFrei",
              "COIEinwohner", "COIObdachlos", "COIWohnraumFrei", "COINahrungMonate", "COIHunger", "COIKrankheit",
              "COIForschung", "COIForschungProzent", "COIWarnungen", "COIUngelesen"] \
    + [f"COIVerlauf{i}" for i in range(1, HISTORY + 1)] + [f"COIWarnung{i}" for i in range(1, ALERTS + 1)]
LIVES = ["status", "date", "speed", "power", "computing", "unity", "workers", "population", "food", "health",
         "research", "alerts"] + [f"good{i}" for i in range(1, GOODS + 1)] \
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
        self.good_values = set()            # gesetzte COIWare_<Id>
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
            self.set_value("COIVerbunden", t("no"))
            self.set_value("COIImSpiel", t("no"))
            self.set_value("COIStatus", t("st_connecting"))
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
        self.set_value("COIPause", t("off"))
        for lid in LIVES:
            if lid != "status":
                self.set_live(lid, t("none"))

    def set_status(self, text):
        self.status = text
        self.set_value("COIStatus", text)
        self.set_live("status", text, None, self.connected and bool(self.state and self.state.get("inGame")))

    def set_connected(self, connected, status):
        was = self.connected
        self.connected = connected
        self.set_value("COIVerbunden", t("yes") if connected else t("no"))
        if not connected:
            self.state = None
            self.set_value("COIImSpiel", t("no"))
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
                    log(f"Verbindung zu Captain of Industry getrennt: {e}", "info")
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
        self.write({"type": "hello", "proto": PROTO, "client": f"touchdeck-coi/{VERSION}", "secret": self.secret})
        buf = b""
        welcomed = False
        while not self.stop_evt.is_set():
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                log(f"Keine Daten vom Spiel seit {DEAD_AFTER:.0f} s, verbinde neu", "warn")
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
                    log(f"Captain of Industry hat die Verbindung abgelehnt: {reason}",
                        "error" if reason in ("secret", "proto") else "warn")
                    return reason
                if kind == "welcome":
                    welcomed = True
                    self.reconnect_wait = 1.0
                    log(f"Verbunden mit Captain of Industry {msg.get('game', '?')}, Mod {msg.get('mod', '?')}")
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
            self.set_value("COIImSpiel", t("no"))
            self.reset_values()
            self.set_status(t("st_menu"))
            return
        self.set_value("COIImSpiel", t("yes"))
        paused = bool(st.get("paused"))
        self.set_status(t("st_paused") if paused else t("st_running"))
        self.apply_time(st, paused)
        self.apply_power(st)
        self.apply_people(st)
        self.apply_research(st)
        self.apply_goods(st)
        self.apply_alerts(st)
        self.apply_history(st)

    def apply_time(self, st, paused):
        year, month = to_int(st.get("year"), 0, 0, 10 ** 6), to_int(st.get("month"), 0, 0, 100)
        month_name = str(st.get("monthName") or "") or t("month_n", n=month)
        date = t("date", year=year, month=month_name)
        self.set_value("COIJahr", str(year))
        self.set_value("COIMonat", str(month))
        self.set_value("COIDatum", date)
        self.set_live("date", date)

        speeds = [to_int(s, 1, 1, 1000) for s in (st.get("speeds") if isinstance(st.get("speeds"), list) else [])] or [1]
        level = to_int(st.get("speedLevel"), 0, 0, len(speeds))
        factor = to_int(st.get("speed"), 1, 0, 1000)
        self.set_value("COITempo", "0" if paused else str(level or factor))
        self.set_value("COIPause", t("on") if paused else t("off"))
        text = t("paused_live") if paused else t("speed_live", level=level or "?", factor=factor)
        bar = None if paused or not level else int(round(100 * level / len(speeds)))
        self.set_live("speed", text, bar, not paused)

    def apply_power(self, st):
        cap, demand, used = num(st.get("powerCapacity")), num(st.get("powerDemand")), num(st.get("powerUsed"))
        if cap is not None and demand is not None:
            used = used if used is not None else min(cap, demand)
            self.set_value("COIStrom", str(int(used)))
            self.set_value("COIStromBedarf", str(int(demand)))
            self.set_value("COIStromKapazitaet", str(int(cap)))
            short = demand > cap
            second = t("power_short", missing=fmt_power(demand - cap)) if short else t("power_free", free=fmt_power(cap - demand))
            bar = int(round(100 * min(1.0, demand / cap))) if cap > 0 else (100 if demand > 0 else 0)
            self.set_live("power", f"{t('power', used=fmt_power(used), cap=fmt_power(cap))}\n{second}", bar, short)
        cap, demand = num(st.get("computingCapacity")), num(st.get("computingDemand"))
        if cap is not None and demand is not None:
            self.set_value("COIRechnen", str(int(demand)))
            self.set_value("COIRechnenKapazitaet", str(int(cap)))
            bar = int(round(100 * min(1.0, demand / cap))) if cap > 0 else None
            self.set_live("computing", t("computing", used=fmt_compute(demand), cap=fmt_compute(cap)), bar, demand > cap)
        unity, per_month = num(st.get("unity")), num(st.get("unityMonth"))
        if unity is not None:
            self.set_value("COIEinheit", str(int(unity)))
            self.set_value("COIEinheitMonat", fmt_dec(per_month or 0))
            cap = num(st.get("unityCap"))
            bar = int(round(100 * min(1.0, unity / cap))) if cap else None
            trend = t("per_month", n=fmt_signed(per_month or 0))
            self.set_live("unity", f"{t('unity', n=fmt_int(unity))}\n{trend}", bar, (per_month or 0) < 0)

    def apply_people(self, st):
        free = num(st.get("workersFree"))
        if free is not None:
            free = int(free)
            self.set_value("COIArbeiterFrei", str(free))
            text = t("workers_free", n=free) if free > 0 else t("workers_missing", n=-free) if free < 0 else t("workers_ok")
            self.set_live("workers", text, None, free < 0)
        people = num(st.get("population"))
        if people is not None:
            homeless, free_homes = to_int(st.get("homeless"), 0, 0, 10 ** 7), to_int(st.get("housingFree"), 0, 0, 10 ** 7)
            diff = to_int(st.get("populationDiff"), 0, -10 ** 7, 10 ** 7)
            self.set_value("COIEinwohner", str(int(people)))
            self.set_value("COIObdachlos", str(homeless))
            self.set_value("COIWohnraumFrei", str(free_homes))
            second = t("homeless", n=homeless) if homeless else t("housing_free", n=free_homes)
            first = t("population", n=fmt_int(people)) + (f" ({fmt_signed(diff)})" if diff else "")
            self.set_live("population", f"{first}\n{second}", None, homeless > 0)
        months = num(st.get("foodMonths"))
        if months is not None:
            months = int(months)
            hungry = bool(st.get("starving"))
            self.set_value("COINahrungMonate", str(months))
            self.set_value("COIHunger", t("yes") if hungry else t("no"))
            text = t("starving") if hungry else t("food1") if months == 1 else t("food", n=months)
            bar = int(round(100 * min(1.0, months / 12)))
            self.set_live("food", text, bar, hungry or months < LOW_FOOD)
        if "disease" in st:
            disease = str(st.get("disease") or "")
            self.set_value("COIKrankheit", disease or t("none"))
            if disease:
                self.set_live("health", t("disease", name=disease, n=to_int(st.get("diseaseMonths"), 0, 0, 1000)), None, True)
            else:
                self.set_live("health", t("healthy"))

    def apply_research(self, st):
        if "research" not in st:
            return
        name = str(st.get("research") or "")
        pct = to_int(st.get("researchProgress"), 0, 0, 100)
        self.set_value("COIForschung", name or t("none"))
        self.set_value("COIForschungProzent", str(pct) if name else t("none"))
        if name:
            self.set_live("research", t("research", name=name, pct=pct), pct, True)
        elif st.get("researchLab") is False:
            self.set_live("research", t("research_nolab"))
        else:
            # Labor da, aber nichts in Arbeit: leicht zu übersehen → rot
            self.set_live("research", t("research_none"), None, True)

    def apply_goods(self, st):
        goods = [g for g in (st.get("goods") if isinstance(st.get("goods"), list) else []) if isinstance(g, dict)]
        seen = set()
        for g in goods:
            gid = str(g.get("id") or "")
            if not gid or not gid.replace("_", "").isalnum() or len(gid) > 30:
                continue
            name = f"COIWare_{gid}"
            seen.add(name)
            self.good_values.add(name)
            self.set_value(name, str(to_int(g.get("stock"), 0, 0, 10 ** 12)))
        for name in self.good_values - seen:
            self.set_value(name, "0")
        slots = [g for g in (st.get("goodSlots") if isinstance(st.get("goodSlots"), list) else []) if isinstance(g, dict)]
        for i in range(1, GOODS + 1):
            if i > len(slots):
                self.set_live(f"good{i}", t("none"))
                continue
            g = slots[i - 1]
            stock, cap = to_int(g.get("stock"), 0, 0, 10 ** 12), to_int(g.get("capacity"), 0, 0, 10 ** 12)
            per_month = num(g.get("perMonth")) or 0
            trend = f" · {t('per_month', n=fmt_signed(per_month))}" if per_month else ""
            cap_text = f"/{fmt_int(cap)}" if cap else ""
            bar = max(0, min(100, int(round(100 * stock / cap)))) if cap else None
            name = ("📌 " if g.get("pinned") else "") + str(g.get("name") or g.get("id") or "")
            # „an“ = Lager voll oder wird leer (Verbrauch größer als Herstellung und kaum noch etwas da)
            on = (cap > 0 and stock >= cap) or (per_month < 0 and stock < -per_month * 2)
            self.set_live(f"good{i}", t("good_line", name=name, stock=fmt_int(stock), cap=cap_text, trend=trend), bar, on)

    def apply_alerts(self, st):
        alerts = [a for a in (st.get("alerts") if isinstance(st.get("alerts"), list) else []) if isinstance(a, dict)]
        self.set_value("COIWarnungen", str(len(alerts)))
        self.set_value("COIUngelesen", str(to_int(st.get("unreadMessages"), 0, 0, 10 ** 6)))
        if alerts:
            first = alerts[0]
            summary = t("alerts_count", n=len(alerts)) + f"\n{first.get('text') or ''} ({to_int(first.get('count'), 0, 0, 10 ** 6)})"
            self.set_live("alerts", summary, None, True)
        else:
            self.set_live("alerts", t("alerts_none"))
        for i in range(1, ALERTS + 1):
            if i <= len(alerts):
                a = alerts[i - 1]
                text, count = str(a.get("text") or ""), to_int(a.get("count"), 0, 0, 10 ** 6)
                self.set_value(f"COIWarnung{i}", t("alert_line", text=text, count=count))
                # Erfolgsmeldungen (grün im Spiel) leuchten nicht
                self.set_live(f"alert{i}", f"{text}\n{t('times', n=count)}", None, a.get("style") != "success")
            else:
                self.set_value(f"COIWarnung{i}", t("none"))
                self.set_live(f"alert{i}", t("none"))

    def apply_history(self, st):
        notes = [e for e in (st.get("history") if isinstance(st.get("history"), list) else []) if isinstance(e, dict)]
        for i in range(1, HISTORY + 1):
            if i <= len(notes):
                e = notes[i - 1]
                text = history_text(e)
                year = to_int(e.get("year"), 0, 0, 10 ** 6)
                self.set_value(f"COIVerlauf{i}", t("history_line", text=text, year=year))
                # „an“ = aus diesem Monat (neu)
                self.set_live(f"note{i}", f"{text}\n{t('date', year=year, month=t('month_n', n=to_int(e.get('month'), 0, 0, 100)))}",
                              None, bool(e.get("today")))
            else:
                self.set_value(f"COIVerlauf{i}", t("none"))
                self.set_live(f"note{i}", t("none"))

    # ---------------- Ereignisse → Auslöser ----------------

    def handle_event(self, name, d):
        def s(key):
            return str(d.get(key) if d.get(key) is not None else "")

        if name == "notification":
            send({"type": "fire", "trigger": "notification", "data": {"Text": s("text"), "Art": s("style"), "Kind": s("style")}})
        elif name == "message":
            text = history_text({"kind": s("kind"), "text": s("text")})
            send({"type": "fire", "trigger": "message", "data": {"Text": text, "Art": s("kind"), "Kind": s("kind")}})
        elif name == "research_finished":
            send({"type": "fire", "trigger": "research_finished", "data": {"Name": s("name")}})
        elif name == "new_year":
            send({"type": "fire", "trigger": "new_year", "data": {"Jahr": s("year"), "Year": s("year")}})
        elif name == "power_short":
            send({"type": "fire", "trigger": "power_short",
                  "data": {"Kapazitaet": s("capacity"), "Capacity": s("capacity"), "Bedarf": s("demand"), "Demand": s("demand")}})
        elif name in ("food_low", "starving"):
            send({"type": "fire", "trigger": name, "data": {"Monate": s("months"), "Months": s("months")}})
        elif name == "disease":
            send({"type": "fire", "trigger": "disease", "data": {"Name": s("name")}})
        elif name == "game_over":
            send({"type": "fire", "trigger": "game_over", "data": {"Text": s("text")}})

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
            return self.command("speed", {"op": op("set"), "value": to_int(p.get("value"), 1, 1, 10)})
        if action == "save":
            return self.command("save", {"name": str(p.get("name") or "")}, timeout=60)
        if action == "alert":
            return self.command("alert", {"n": to_int(p.get("n"), 1, 1, ALERTS)})
        if action == "history":
            return self.command("history", {"n": to_int(p.get("n"), 1, 1, HISTORY)})
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
        return t(code, **{k: str(v) for k, v in args.items()})


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
