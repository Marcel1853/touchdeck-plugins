#!/usr/bin/env python3
"""TouchDeck-Plugin „Factorio“.

Erweitertes Plugin: TouchDeck startet dieses Programm und tauscht mit ihm JSON-Zeilen über
stdin/stdout aus (siehe Wiki › Advanced plugins). Nur Python-Standardbibliothek.

Der Factorio-Mod „TouchDeck Bridge“ schreibt state.json und names.txt nach
script-output/touchdeck-bridge/. Dieses Plugin achtet auf Änderungen dieser Dateien, setzt Werte,
Live-Anzeigen (mit Zahl für Graphen) und Auslöser. Befehle ans Spiel laufen über Tastenkürzel des
Mods, die TouchDeck mit seiner eingebauten Aktion „Tastenkürzel“ drückt; das Plugin wartet auf die
Antwort des Spiels. Text wird nie getippt (kommt mit IBus in Factorio-Textfeldern nicht an).
Nichts geht ins Netz.
"""

import json
import os
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from item_slots import ItemSlots  # noqa: E402  (liegt neben plugin.py)

# --------------------------------------------------------------------------
# Texte (Sprache aus der Systemumgebung, TouchDeck folgt standardmäßig ebenfalls)
# --------------------------------------------------------------------------

_LOCALE = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES")
           or os.environ.get("LANG") or "").lower()
DE = _LOCALE.startswith("de")

TEXTS = {
    # Zustand
    "st_running": ("läuft", "running"),
    "st_paused": ("pausiert", "paused"),
    "st_halted": ("angehalten (Menü oder Forschungsbaum)", "halted (menu or research screen)"),
    "st_menu": ("keine Daten (Menü, Ladebildschirm oder Mod aus?)", "no data (menu, loading screen or mod off?)"),
    "st_off": ("Factorio aus", "Factorio not running"),
    "st_nofolder": ("Mod-Ordner nicht gefunden", "mod folder not found"),
    "yes": ("ja", "yes"),
    "no": ("nein", "no"),
    "on": ("an", "on"),
    "off": ("aus", "off"),
    "none": ("–", "–"),
    # Stromquellen (Reihen im Graphen, Schlüssel aus scripts/power.lua des Mods)
    "src_steam": ("Dampf", "Steam"),
    "src_turbine": ("Turbinen", "Turbines"),
    "src_solar": ("Solar", "Solar"),
    "src_accumulator": ("Akkus", "Accumulators"),
    "src_burner": ("Brennstoff", "Burner"),
    "src_fusion": ("Fusion", "Fusion"),
    "src_lightning": ("Blitze", "Lightning"),
    "src_interface": ("Schnittstelle", "Interface"),
    "src_other": ("Sonstige", "Other"),
    # Produktions-Seite
    "made": ("Produktion", "Production"),
    "used": ("Verbrauch", "Consumption"),
    "slot_auto": ("Platz {n}: automatisch ({name})", "Slot {n}: automatic ({name})"),
    "slot_set": ("Platz {n}: {name}", "Slot {n}: {name}"),
    "slots_auto": ("Alle Plätze automatisch", "All slots automatic"),
    "slot_range": ("Platz {n} gibt es nicht (1 bis {m}).", "Slot {n} does not exist (1 to {m})."),
    "no_items": ("Noch keine Produktionsdaten vom Spiel.", "No production data from the game yet."),
    "item_unknown": ("„{value}“ wird gerade nicht hergestellt oder verbraucht. Treffer: {list}",
                     "“{value}” is not being produced or consumed right now. Matches: {list}"),
    # UTLogistics (optional)
    "utl_off": ("UTLogistics nicht aktiv", "UTLogistics not active"),
    "utl_on": ("UTLogistics {version}", "UTLogistics {version}"),
    "utl_trains": ("{idle} frei · {busy} unterwegs", "{idle} idle · {busy} on the way"),
    "utl_alerts": ("{n} Warnungen (10 min)", "{n} alerts (10 min)"),
    "utl_free": ("Frei", "Idle"),
    "utl_busy": ("Unterwegs", "On the way"),
    "alert_no_train": ("Kein freier Zug", "No free train"),
    "alert_cargo": ("Restladung im Zug", "Leftover cargo"),
    "alert_missing": ("Anbieter hatte zu wenig", "Provider was short"),
    "alert_no_path": ("Zug findet keinen Weg", "Train has no path"),
    "alert_fuel": ("Treibstoff/Tanken", "Fuel problem"),
    "alert_canceled": ("Lieferung abgebrochen", "Delivery canceled"),
    "alert_stuck": ("Zug steckt fest", "Train stuck"),
    "utl_rate": ("{n} Lieferungen/h", "{n} deliveries/h"),
    "utl_waiting": ("{n} Anfragen ohne Zug", "{n} requests without a train"),
    "utl_waiting_one": ("{name} · {network} · seit {minutes} min", "{name} · {network} · for {minutes} min"),
    "no_grid": ("kein Netz", "no grid"),
    "platform": ("Plattform {name}", "Platform {name}"),
    # Antworten des Mods (Codes aus scripts/commands.lua)
    "paused": ("Spiel angehalten", "Game paused"),
    "resumed": ("Spiel läuft weiter", "Game running again"),
    "speed": ("Geschwindigkeit {value}×", "Speed {value}×"),
    "saved": ("Gespeichert als {name}", "Saved as {name}"),
    "screenshot": ("Screenshot: {path}", "Screenshot: {path}"),
    "chat": ("Nachricht gesendet", "Message sent"),
    "research-queued": ("In Warteschlange: {name}", "Queued: {name}"),
    "research-cancelled": ("Forschung abgebrochen: {name}", "Research cancelled: {name}"),
    "centered": ("Zurück beim Spieler", "Back at the player"),
    "refreshed": ("Daten neu geschrieben", "Data written again"),
    "bad-value": ("Ungültiger Wert: {value}", "Invalid value: {value}"),
    "bad-speed": ("Geschwindigkeit muss zwischen 0,01 und 100 liegen: {value}",
                  "Speed must be between 0.01 and 100: {value}"),
    "empty-chat": ("Kein Text für den Chat", "No text for the chat"),
    "research-unknown": ("Forschung nicht gefunden: {value}", "Research not found: {value}"),
    "research-done": ("Schon erforscht: {name}", "Already researched: {name}"),
    "research-failed": ("Kann nicht eingereiht werden: {name}", "Cannot be queued: {name}"),
    "no-suggestion": ("Kein Forschungsvorschlag {value} (gerade nichts einreihbar)",
                      "No research suggestion {value} (nothing can be queued right now)"),
    "no-research": ("Gerade läuft keine Forschung", "No research is running"),
    "no-player": ("Geht nur mit einem Spieler", "Only works with a player"),
    "not-admin": ("Nur für Admins (Mehrspieler)", "Admins only (multiplayer)"),
    "unknown-command": ("Unbekannter Befehl: {value}", "Unknown command: {value}"),
    # Aktionen
    "not_connected": ("Factorio liefert keine Daten: {status}. Läuft das Spiel mit dem Mod „TouchDeck Bridge“?",
                      "Factorio sends no data: {status}. Is the game running with the mod “TouchDeck Bridge”?"),
    "timeout_menu": ("Keine Antwort vom Spiel. Ist das Esc-Menü offen oder lädt das Spiel?",
                     "No answer from the game. Is the Esc menu open or is the game loading?"),
    "timeout_off": ("Keine Antwort: Factorio läuft nicht.", "No answer: Factorio is not running."),
    "timeout": ("Keine Antwort vom Spiel innerhalb von {s} s. Ist das Factorio-Fenster erreichbar und der Mod aktiv?",
                "No answer from the game within {s} s. Is the Factorio window reachable and the mod active?"),
    "unknown": ("Unbekannte Aktion: {id}", "Unknown action: {id}"),
    "failed": ("Unerwarteter Fehler, Details im Log.", "Unexpected error, see the log for details."),
}


def t(key, **kw):
    de, en = TEXTS[key]
    try:
        return (de if DE else en).format(**kw)
    except (KeyError, IndexError):
        return de if DE else en


VALUE_LIMIT = 1000        # TouchDeck kürzt Werte auf 1000 Zeichen (store.rs, set_variable)
MAX_FILE = 256 * 1024     # größere Dateien sind sicher nicht vom Mod
STATE_VERSION = 1         # State.VERSION im Mod
SUGGESTIONS = 3
ALL_VALUES = ["FSpielzeit", "FTick", "FGeschwindigkeit", "FPause", "FForschung", "FForschungProzent",
              "FWarteschlange", "FEvolution", "FRaketen", "FSpieler", "FPlanet", "FVorschlag1",
              "FVorschlag2", "FVorschlag3", "FStromErzeugung", "FStromVerbrauch"]
ITEM_SLOTS = 8
ALL_VALUES += [f"FItem{i}" for i in range(1, ITEM_SLOTS + 1)]
UTL_VALUES = ["FUtlZuegeFrei", "FUtlUnterwegs", "FUtlStationen", "FUtlNetze", "FUtlLieferungen", "FUtlAuslastung",
              "FUtlLieferungenStunde", "FUtlOhneZug", "FUtlOhneZugText",
              "FUtlWarnungen", "FUtlWarnung", "FUtlWare1", "FUtlWare2", "FUtlWare3"]
ALL_VALUES += UTL_VALUES + ["FUtlStatus"]
LIVES = (["research", "speed", "evolution", "power", "consumption"] + [f"item{i}" for i in range(1, ITEM_SLOTS + 1)]
         + ["utl_trains", "utl_alerts", "utl_goods", "utl_rate", "utl_unserved"])


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

def to_number(value, default, lo, hi):
    try:
        n = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default
    if n != n:  # NaN
        return default
    return max(lo, min(hi, n))


def fmt_number(n, decimals=1):
    """1 → „1“, 0.5 → „0.5“ (Punkt, damit TouchDeck-Bedingungen rechnen können)."""
    s = f"{n:.{decimals}f}".rstrip("0").rstrip(".")
    return s or "0"


def fmt_mw(watts):
    """300000 → „0,3 MW“ (Komma auf Deutsch), unter 1 MW mit zwei Stellen."""
    mw = watts / 1e6
    text = f"{mw:.2f}" if mw < 1 else f"{mw:.1f}" if mw < 1000 else f"{mw:.0f}"
    return (text.replace(".", ",") if DE else text) + " MW"


def fmt_rate(n):
    """Menge pro Minute: unter 10 mit einer Nachkommastelle (Komma auf Deutsch)."""
    text = f"{n:.1f}".rstrip("0").rstrip(".") if n < 10 else f"{n:.0f}"
    return text.replace(".", ",") if DE else text


def fmt_int(n):
    """1234567 → „1.234.567“ (Deutsch) bzw. „1,234,567“."""
    text = f"{int(round(n)):,}"
    return text.replace(",", ".") if DE else text


def fmt_time(ticks):
    sec = int(ticks // 60)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def factorio_running():
    """Läuft ein Prozess namens factorio? (nur /proc lesen, kein Fremdprogramm)"""
    try:
        for pid in os.listdir("/proc"):
            if pid.isdigit():
                try:
                    with open(f"/proc/{pid}/comm", "r", encoding="utf-8", errors="replace") as f:
                        if f.read().strip().lower().startswith("factorio"):
                            return True
                except OSError:
                    continue
    except OSError:
        pass
    return False


def candidate_folders(setting):
    if setting:
        return [os.path.expanduser(setting)]
    home = os.path.expanduser("~")
    return [os.path.join(home, ".factorio", "script-output", "touchdeck-bridge"),
            os.path.join(home, ".var", "app", "com.valvesoftware.Steam", ".factorio", "script-output",
                         "touchdeck-bridge")]


def read_small(path):
    """Datei lesen, wenn sie klein genug ist; None bei Fehlern."""
    try:
        if os.path.getsize(path) > MAX_FILE:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def parse_names(text):
    out = {}
    for line in (text or "").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            out[key.strip()] = value.strip()
    return out


def as_list(v):
    # helpers.table_to_json schreibt leere Tabellen als {}
    return v if isinstance(v, list) else []


# --------------------------------------------------------------------------
# Plugin
# --------------------------------------------------------------------------

class Plugin:
    def __init__(self):
        self.lock = threading.RLock()
        self.cond = threading.Condition(self.lock)
        self.stop_evt = threading.Event()
        self.started = False
        self.folder_setting = ""
        self.interval = 0.25
        self.timeout = 5.0
        self.folder = None          # gefundener Ordner
        self.state = None           # letzter gültiger Inhalt von state.json
        self.state_mtime = 0.0
        self.state_seen = 0.0       # time.time(), als state.json zuletzt neu war
        self.names = {}
        self.names_mtime = 0.0
        self.session = None
        self.last_seq = None        # zuletzt verarbeitetes Ereignis (None = noch keine Grundlinie)
        self.acks = []              # [(Ankunftszeit, Ereignis)]
        self.values = {}            # zuletzt gesendete Werte
        self.lives = {}
        self.connected = None
        self.status = None
        self.running_cache = (0.0, False)
        self.slots = ItemSlots(ITEM_SLOTS)
        self.items_mtime = 0.0
        self.labels = {}
        self.labels_mtime = 0.0
        self.utl = None             # letzter Inhalt von utl.json
        self.utl_mtime = 0.0
        self.utl_alert_tick = None  # Tick der zuletzt gemeldeten UTL-Warnung (None = Grundlinie)
        self.utl_alerts = []        # [(Tick, voller Text)] aus utl-alerts.txt, neueste zuerst
        self.utl_alerts_mtime = 0.0
        self.utl_waiting = None     # Anzahl Anfragen ohne Zug beim letzten Stand (None = Grundlinie)
        self.pending = {}           # requestId → {"evt", "value"} für getValue
        self.req_counter = 0

    # ---------------- Start / Stopp ----------------

    def start(self, msg):
        if self.started:
            return
        self.started = True
        s = msg.get("settings") or {}
        self.folder_setting = str(s.get("folder") or "").strip()
        self.interval = to_number(s.get("interval"), 250, 100, 5000) / 1000.0
        self.timeout = to_number(s.get("timeout"), 5, 2, 60)
        with self.lock:
            self.set_connected(False, t("st_off"), fire=False)
            self.reset_values()
        threading.Thread(target=self.watch_loop, daemon=True).start()

    def shutdown(self):
        self.stop_evt.set()

    # ---------------- Werte und Live-Anzeigen ----------------

    def set_value(self, name, value, always=False):
        """always: auch senden, wenn unverändert (FMeldung überschreiben auch Events des Profils)."""
        value = str(value)[:VALUE_LIMIT]
        if always or self.values.get(name) != value:
            self.values[name] = value
            send({"type": "setValue", "name": name, "value": value})

    def set_live(self, lid, text, value=None, on=None, number=None, series=None):
        """value: 0–100 für den Balken; number: echte Zahl für Graphen (z. B. MW);
        series: Name → Zahl für mehrere Reihen in einem Graphen (TouchDeck nimmt höchstens 12)."""
        live = {"text": text, "value": value}
        if number is not None:
            live["number"] = number
        if series is not None:
            live["series"] = series
        if on is not None:
            live["on"] = on
        if self.lives.get(lid) != live:
            self.lives[lid] = live
            send({"type": "call", "requestId": f"live_{lid}_{time.monotonic_ns()}", "op": "live.set",
                  "args": {"id": lid, "value": live}})

    def reset_values(self):
        for name in ALL_VALUES:
            self.set_value(name, t("none"))
        for lid in LIVES:
            self.set_live(lid, t("none"), None, False)

    def set_connected(self, connected, status, fire=True):
        status_changed = status != self.status
        self.status = status
        self.set_value("FStatus", status)
        self.set_value("FVerbunden", t("yes") if connected else t("no"))
        if status_changed or connected != self.connected:
            self.set_live("status", status, None, bool(connected))
        if connected != self.connected:
            was = self.connected
            self.connected = connected
            if fire and was is not None:
                send({"type": "fire", "trigger": "connected" if connected else "disconnected", "data": {}})
            if not connected:
                self.reset_values()
            with self.cond:
                self.cond.notify_all()

    # ---------------- Dateien beobachten ----------------

    def find_folder(self):
        best, best_time = None, -1.0
        for folder in candidate_folders(self.folder_setting):
            try:
                m = os.path.getmtime(os.path.join(folder, "state.json"))
            except OSError:
                continue
            if m > best_time:
                best, best_time = folder, m
        return best

    def is_running(self):
        now = time.monotonic()
        stamp, running = self.running_cache
        if now - stamp > 2.0:
            running = factorio_running()
            self.running_cache = (now, running)
        return running

    def watch_loop(self):
        self.load_picks()
        while not self.stop_evt.wait(self.interval):
            try:
                self.poll()
            except Exception:
                log(traceback.format_exc(), "error")

    def poll(self):
        with self.lock:
            if not self.folder or not os.path.isdir(self.folder):
                self.folder = self.find_folder()
            if self.folder:
                self.check_names()
                self.check_state()
                self.check_items()
                self.check_utl()
            self.update_connection()

    def check_names(self):
        path = os.path.join(self.folder, "names.txt")
        try:
            m = os.path.getmtime(path)
        except OSError:
            return
        if m != self.names_mtime:
            text = read_small(path)
            if text is not None:
                self.names_mtime = m
                self.names = parse_names(text)
                if self.state and self.state_seen:
                    self.apply_state(self.state)

    def check_state(self):
        path = os.path.join(self.folder, "state.json")
        try:
            m = os.path.getmtime(path)
        except OSError:
            return
        if m == self.state_mtime:
            return
        text = read_small(path)
        try:
            state = json.loads(text) if text else None
        except ValueError:
            state = None   # halb geschrieben? Beim nächsten Durchlauf erneut versuchen
        if not isinstance(state, dict) or state.get("v") != STATE_VERSION:
            if isinstance(state, dict):
                log(f"state.json hat Version {state.get('v')!r}, erwartet {STATE_VERSION}", "warn")
                self.state_mtime = m
            return
        self.state_mtime = m
        # Alte Datei aus einer früheren Sitzung zählt nicht als Lebenszeichen.
        if self.state is None and time.time() - m > self.timeout:
            self.state = state
            self.take_events(state, baseline=True)
            return
        self.state = state
        self.state_seen = time.monotonic()
        self.take_events(state, baseline=False)
        self.apply_state(state)

    def check_items(self):
        """items.json (alle 5 s vom Mod) und labels.txt (übersetzte Namen)."""
        changed = False
        path = os.path.join(self.folder, "labels.txt")
        try:
            m = os.path.getmtime(path)
        except OSError:
            m = None
        if m is not None and m != self.labels_mtime:
            text = read_small(path)
            if text is not None:
                self.labels_mtime = m
                self.labels = parse_names(text)
                changed = True
        path = os.path.join(self.folder, "items.json")
        try:
            m = os.path.getmtime(path)
        except OSError:
            m = None
        if m is not None and m != self.items_mtime:
            text = read_small(path)
            try:
                data = json.loads(text) if text else None
            except ValueError:
                data = None   # halb geschrieben: beim nächsten Durchlauf erneut
            if isinstance(data, dict) and data.get("v") == 1:
                self.items_mtime = m
                self.slots.update(as_list(data.get("items")), self.labels)
                changed = True
        if changed:
            self.slots.labels = dict(self.labels)
            if self.state_seen:
                self.publish_items()
                if self.utl:
                    self.publish_utl()
                if self.state:
                    self.apply_state(self.state)   # Verbraucher-Namen im Strom-Graphen

    def check_utl(self):
        path = os.path.join(self.folder, "utl-alerts.txt")
        try:
            m = os.path.getmtime(path)
        except OSError:
            m = None
        if m is not None and m != self.utl_alerts_mtime:
            text = read_small(path)
            if text is not None:
                self.utl_alerts_mtime = m
                alerts = []
                for line in text.splitlines():
                    tick, sep, message = line.partition("\t")
                    if sep and tick.strip().isdigit():
                        alerts.append((int(tick), message.strip()))
                self.utl_alerts = alerts
                if self.utl and self.state_seen:
                    self.publish_utl()
        path = os.path.join(self.folder, "utl.json")
        try:
            m = os.path.getmtime(path)
        except OSError:
            return
        if m == self.utl_mtime:
            return
        text = read_small(path)
        try:
            data = json.loads(text) if text else None
        except ValueError:
            return   # halb geschrieben: beim nächsten Durchlauf erneut
        if not isinstance(data, dict) or data.get("v") != 1:
            return
        self.utl_mtime = m
        self.utl = data
        if self.state_seen:
            self.publish_utl()

    def alert_text(self, alert):
        """Voller Text aus utl-alerts.txt (gleicher Tick), sonst kurzer eigener Text je Art."""
        tick = alert.get("tick")
        for t_tick, message in self.utl_alerts:
            if t_tick == tick and message:
                return message
        icon = str(alert.get("icon") or "")
        return t("alert_" + icon) if ("alert_" + icon) in TEXTS else str(alert.get("group") or icon or "?")

    def good_name(self, entry):
        return self.labels.get(f"{entry.get('k')}.{entry.get('n')}") or str(entry.get("n") or "?")

    def publish_utl(self):
        d = self.utl or {}
        if not d.get("active"):
            self.set_value("FUtlStatus", t("utl_off"))
            for name in UTL_VALUES:
                self.set_value(name, t("none"))
            for lid in ("utl_trains", "utl_alerts", "utl_goods", "utl_rate", "utl_unserved"):
                self.set_live(lid, t("utl_off"), None, False)
            return
        num = lambda k: to_number(d.get(k), 0, 0, 1e12)
        idle, busy, hour = int(num("idle")), int(num("deliveries")), int(num("hour"))
        self.set_value("FUtlStatus", t("utl_on", version=d.get("version") or ""))
        self.set_value("FUtlZuegeFrei", idle)
        self.set_value("FUtlUnterwegs", busy)
        self.set_value("FUtlStationen", int(num("stations")))
        self.set_value("FUtlNetze", int(num("networks")) if d.get("networks") is not None else t("none"))
        self.set_value("FUtlLieferungen", fmt_int(num("total")))
        self.set_value("FUtlLieferungenStunde", hour)
        util = d.get("utilization")
        util_pct = to_number(util, 0, 0, 1) * 100 if isinstance(util, (int, float)) else None
        self.set_value("FUtlAuslastung", f"{fmt_number(util_pct, 0)} %" if util_pct is not None else t("none"))

        recent = int(num("alerts_recent"))
        last = d.get("last_alert") if isinstance(d.get("last_alert"), dict) else None
        last_text = self.alert_text(last) if last else t("none")
        self.set_value("FUtlWarnungen", recent)
        self.set_value("FUtlWarnung", last_text)

        goods = [g for g in as_list(d.get("goods")) if isinstance(g, dict) and g.get("n")]
        series = {}
        for g in goods:
            name = self.good_name(g)[:40]
            series[name] = round(series.get(name, 0) + to_number(g.get("hour"), 0, 0, 1e12), 1)
        for i in range(3):
            if i < len(goods):
                self.set_value(f"FUtlWare{i + 1}",
                               f"{self.good_name(goods[i])}: {fmt_int(to_number(goods[i].get('hour'), 0, 0, 1e12))}/h")
            else:
                self.set_value(f"FUtlWare{i + 1}", t("none"))

        # Anfragen ohne Zug (älteste zuerst); Minuten aus dem Tick des Spiels
        waiting = [u for u in as_list(d.get("unserved")) if isinstance(u, dict)]
        tick_now = to_number((self.state or {}).get("tick"), 0, 0, 1e15)
        if waiting:
            u = waiting[0]
            minutes = max(0, int((tick_now - to_number(u.get("since"), tick_now, 0, 1e15)) // 3600))
            self.set_value("FUtlOhneZugText", t("utl_waiting_one", name=self.good_name(u),
                                                 network=u.get("network") or "–", minutes=minutes))
        else:
            self.set_value("FUtlOhneZugText", t("none"))
        self.set_value("FUtlOhneZug", len(waiting))

        self.set_live("utl_trains", t("utl_trains", idle=idle, busy=busy), None, busy > 0, busy,
                      {t("utl_free"): idle, t("utl_busy"): busy})
        self.set_live("utl_alerts", last_text if recent else t("utl_alerts", n=0), None, recent > 0, recent)
        top = next(iter(sorted(series.items(), key=lambda kv: -kv[1])), None)
        self.set_live("utl_goods", f"{top[0]}: {fmt_int(top[1])}/h" if top else t("none"), None, bool(series),
                      round(sum(series.values()), 1), series)
        self.set_live("utl_rate", t("utl_rate", n=hour), None, hour > 0, hour)
        self.set_live("utl_unserved", t("utl_waiting", n=len(waiting)), None, bool(waiting), len(waiting))

        # Auslöser: neue Warnung (voller Text) und neu hinzugekommene Anfragen ohne Zug
        tick = last.get("tick") if last else None
        if isinstance(tick, (int, float)):
            if self.utl_alert_tick is not None and tick > self.utl_alert_tick:
                send({"type": "fire", "trigger": "utl_alert",
                      "data": {"Warnung": last_text, "Alert": last_text}})
            self.utl_alert_tick = tick
        if self.utl_waiting is not None and len(waiting) > self.utl_waiting:
            text = self.values.get("FUtlOhneZugText", "")
            send({"type": "fire", "trigger": "utl_unserved",
                  "data": {"Anzahl": len(waiting), "Count": len(waiting), "Text": text}})
        self.utl_waiting = len(waiting)

    def publish_items(self):
        made, used = t("made"), t("used")
        for i, (key, auto) in enumerate(self.slots.resolve(), start=1):
            if not key:
                self.set_value(f"FItem{i}", t("none"))
                self.set_live(f"item{i}", t("none"), None, False)
                continue
            p, c = self.slots.rate(key)
            name = self.slots.label(key)
            self.set_value(f"FItem{i}", f"{name}: {fmt_rate(p)}/min")
            # „an“ = von Hand gewählt; Reihen: Produktion und Verbrauch pro Minute
            self.set_live(f"item{i}", f"{name} {fmt_rate(p)}/min", None, not auto, p, {made: p, used: c})

    # ---------------- Auswahl der Plätze (in TouchDeck-Werten gemerkt) ----------------

    def get_value(self, name, timeout=2.0):
        """Wert aus TouchDeck lesen; None bei Zeitüberschreitung (dann ist ok False)."""
        with self.lock:
            self.req_counter += 1
            rid = f"fv_{self.req_counter}"
            slot = {"evt": threading.Event(), "value": None}
            self.pending[rid] = slot
        send({"type": "getValue", "requestId": rid, "name": name})
        ok = slot["evt"].wait(timeout)
        with self.lock:
            self.pending.pop(rid, None)
        return slot["value"], ok

    def on_value(self, msg):
        slot = self.pending.get(msg.get("requestId"))
        if slot:
            slot["value"] = msg.get("value")
            slot["evt"].set()

    def load_picks(self):
        for i in range(ITEM_SLOTS):
            v, ok = self.get_value(f"FItemWahl{i + 1}")
            if not ok:
                log("TouchDeck hat die gemerkte Auswahl nicht geliefert; alle Plätze automatisch.", "warn")
                return
            v = str(v or "")
            self.slots.picks[i] = v if v.startswith(("item.", "fluid.")) else ""

    def save_pick(self, i):
        self.set_value(f"FItemWahl{i + 1}", self.slots.picks[i])

    def item_action(self, p):
        op = str(p.get("op") or "next")
        with self.lock:
            if not self.slots.order:
                raise UserError(t("no_items"))
            if op == "all_auto":
                self.slots.all_auto()
                for i in range(ITEM_SLOTS):
                    self.save_pick(i)
                self.publish_items()
                return t("slots_auto")
            n = int(to_number(p.get("slot"), 1, -1e6, 1e6))
            if not 1 <= n <= ITEM_SLOTS:
                raise UserError(t("slot_range", n=n, m=ITEM_SLOTS))
            i = n - 1
            if op in ("next", "prev"):
                self.slots.step(i, 1 if op == "next" else -1)
            elif op == "auto":
                self.slots.auto(i)
            elif op == "set":
                value = str(p.get("value") or "").strip()
                key, hits = self.slots.set(i, value) if value else (None, [])
                if not key:
                    raise UserError(t("item_unknown", value=value, list=", ".join(hits) or t("none")))
            else:
                raise UserError(t("unknown", id=f"item/{op}"))
            self.save_pick(i)
            self.publish_items()
            key, auto = self.slots.resolve()[i]
            name = self.slots.label(key) if key else t("none")
            return t("slot_auto", n=n, name=name) if auto else t("slot_set", n=n, name=name)

    def update_connection(self):
        fresh = self.state is not None and time.monotonic() - self.state_seen <= self.timeout
        paused = bool(self.state and self.state.get("paused"))
        if not self.folder:
            running = self.is_running()
            self.set_connected(False, t("st_menu") if running else t("st_nofolder"))
        elif fresh and not paused:
            self.set_connected(True, t("st_running"))
        elif self.state_seen and self.is_running():
            # Spiel steht (pausiert, Esc-Menü, Forschungsbaum, Ladebildschirm): Im Einzelspieler läuft
            # dann kein Mod-Code. Die letzten Werte bleiben stehen, nichts wird „getrennt“.
            self.set_connected(True, t("st_paused") if paused else t("st_halted"))
        elif self.is_running():
            self.set_connected(False, t("st_menu"))
        else:
            self.set_connected(False, t("st_off"))

    # ---------------- Zustand übernehmen ----------------

    def tech_name(self, internal):
        """Übersetzter Name aus names.txt, sonst der interne Name."""
        if not internal:
            return t("none")
        name = self.names.get("tech." + internal)
        if not name and internal == (self.state or {}).get("research"):
            name = self.names.get("research")
        return name or internal

    def apply_state(self, s):
        speed = to_number(s.get("speed"), 1, 0, 1000)
        paused = bool(s.get("paused"))
        research = str(s.get("research") or "")
        progress = to_number(s.get("progress"), 0, 0, 1)
        evo = to_number(s.get("evolution"), -1, -1, 1)
        surface = s.get("surface") if isinstance(s.get("surface"), dict) else {}

        self.set_value("FSpielzeit", fmt_time(to_number(s.get("played"), 0, 0, 1e15)))
        self.set_value("FTick", int(to_number(s.get("tick"), 0, 0, 1e15)))
        self.set_value("FGeschwindigkeit", fmt_number(speed, 2))
        self.set_value("FPause", t("on") if paused else t("off"))
        name = (self.names.get("research") or self.tech_name(research)) if research else t("none")
        percent = int(progress * 100) if research else 0
        self.set_value("FForschung", name)
        self.set_value("FForschungProzent", percent)
        self.set_value("FWarteschlange", int(to_number(s.get("queue"), 0, 0, 1e6)))
        self.set_value("FEvolution", fmt_number(evo * 100, 1) if evo >= 0 else t("none"))
        self.set_value("FRaketen", int(to_number(s.get("rockets"), 0, 0, 1e12)))
        self.set_value("FSpieler", int(to_number(s.get("players"), 0, 0, 1e6)))
        place = self.names.get("place") or surface.get("platform") or surface.get("planet") or surface.get("name") or ""
        self.set_value("FPlanet", place or t("none"))
        suggest = as_list(s.get("suggest"))
        for i in range(SUGGESTIONS):
            self.set_value(f"FVorschlag{i + 1}", self.tech_name(suggest[i]) if i < len(suggest) else t("none"))

        self.set_live("research", f"{name} {percent} %" if research else t("none"), percent if research else None,
                      bool(research), percent if research else None)
        self.set_live("speed", f"{fmt_number(speed, 2)}×", None, abs(speed - 1) > 1e-6, speed)
        self.set_live("evolution", f"{fmt_number(evo * 100, 1)} %" if evo >= 0 else t("none"),
                      evo * 100 if evo >= 0 else None, evo >= 0.5, round(evo * 100, 2) if evo >= 0 else None)

        power = s.get("power") if isinstance(s.get("power"), dict) else None
        if power:
            made = to_number(power.get("production"), 0, 0, 1e15)
            used = to_number(power.get("consumption"), 0, 0, 1e15)
            self.set_value("FStromErzeugung", fmt_mw(made))
            self.set_value("FStromVerbrauch", fmt_mw(used))
            # Balken: wie viel der erzeugten Leistung verbraucht wird
            share = min(100.0, used / made * 100) if made > 0 else None
            self.set_live("power", fmt_mw(made), share, made > 0, round(made / 1e6, 3), self.power_series(power))
            self.set_live("consumption", fmt_mw(used), share, used > 0, round(used / 1e6, 3), self.consumer_series(power))
        else:
            self.set_value("FStromErzeugung", t("none"))
            self.set_value("FStromVerbrauch", t("none"))
            self.set_live("power", t("no_grid"), None, False)
            self.set_live("consumption", t("no_grid"), None, False)

    def power_series(self, power):
        """Erzeugung je Quelle in MW, mit übersetzten Namen (gestapelt = Gesamterzeugung)."""
        raw = power.get("sources") if isinstance(power.get("sources"), dict) else {}
        out = {}
        for key, watts in raw.items():
            label = t("src_" + key) if ("src_" + key) in TEXTS else str(key)[:40]
            mw = round(to_number(watts, 0, 0, 1e15) / 1e6, 3)
            if mw > 0:
                out[label] = round(out.get(label, 0) + mw, 3)
        return dict(sorted(out.items(), key=lambda kv: -kv[1])[:12])

    def consumer_series(self, power):
        """Verbrauch je Gebäude in MW (die größten sechs, Rest „Sonstige“), Namen aus labels.txt."""
        raw = power.get("consumers") if isinstance(power.get("consumers"), dict) else {}
        out = {}
        for name, watts in raw.items():
            label = t("src_other") if name == "other" else (self.labels.get("entity." + name) or str(name))[:40]
            mw = round(to_number(watts, 0, 0, 1e15) / 1e6, 3)
            if mw > 0:
                out[label] = round(out.get(label, 0) + mw, 3)
        return dict(sorted(out.items(), key=lambda kv: -kv[1])[:12])

    # ---------------- Ereignisse ----------------

    def take_events(self, s, baseline):
        session = s.get("session")
        seq = int(to_number(s.get("seq"), 0, 0, 1e12))
        if baseline or self.last_seq is None or session != self.session or seq < self.last_seq:
            # Plugin-Start oder anderer Spielstand: nur merken, nichts Altes auslösen.
            if session != self.session:
                self.utl_alert_tick = None
                self.utl_waiting = None
            self.session, self.last_seq = session, seq
            return
        events = [e for e in as_list(s.get("events")) if isinstance(e, dict)]
        for e in sorted(events, key=lambda e: to_number(e.get("seq"), 0, 0, 1e12)):
            n = int(to_number(e.get("seq"), 0, 0, 1e12))
            if n <= self.last_seq:
                continue
            self.last_seq = n
            self.handle_event(e)

    def handle_event(self, e):
        kind = e.get("type")
        if kind == "ack":
            message = self.ack_message(e)
            ok = bool(e.get("ok"))
            self.set_value("FMeldung", message, always=True)
            with self.cond:
                now = time.monotonic()
                self.acks = [a for a in self.acks if now - a[0] < 30][-19:] + [(now, e, message)]
                self.cond.notify_all()
            send({"type": "fire", "trigger": "command_done",
                  "data": {"Befehl": str(e.get("cmd") or ""), "Ok": t("yes") if ok else t("no"),
                           "Meldung": message, "Command": str(e.get("cmd") or ""), "Message": message}})
        elif kind in ("research_finished", "research_started"):
            internal = str(e.get("name") or "")
            if kind == "research_finished":
                display = self.names.get("finished") or self.tech_name(internal)
            else:
                display = self.tech_name(internal)
            send({"type": "fire", "trigger": kind, "data": {"Name": display, "Intern": internal}})
        elif kind == "rocket_launched":
            send({"type": "fire", "trigger": kind, "data": {"Anzahl": e.get("count", 0), "Count": e.get("count", 0)}})
        elif kind == "player_died":
            me = bool(e.get("me"))
            send({"type": "fire", "trigger": kind,
                  "data": {"Spieler": str(e.get("player") or ""), "Player": str(e.get("player") or ""),
                           "Ich": t("yes") if me else t("no")}})
        elif kind == "evolution_step":
            send({"type": "fire", "trigger": kind,
                  "data": {"Prozent": e.get("percent", 0), "Percent": e.get("percent", 0),
                           "Flaeche": str(e.get("surface") or ""), "Surface": str(e.get("surface") or "")}})

    def ack_message(self, e):
        code = str(e.get("code") or "")
        if code not in TEXTS:
            return code
        args = {k: e.get(k, "") for k in ("value", "path", "text")}
        args["name"] = self.tech_name(str(e.get("name") or "")) if code.startswith("research") else str(e.get("name") or "")
        if code == "screenshot" and self.folder:
            args["path"] = os.path.join(os.path.dirname(self.folder), str(e.get("path") or ""))
        if code == "speed":
            args["value"] = fmt_number(to_number(e.get("value"), 1, 0, 1000), 2)
        return t(code, **args)

    # ---------------- Aktionen ----------------

    def run_action(self, msg):
        rid = msg.get("requestId")
        try:
            message = self.dispatch(msg.get("id"), msg.get("params") or {})
            send({"type": "result", "requestId": rid, "ok": True, "message": message})
        except UserError as e:
            send({"type": "result", "requestId": rid, "ok": False, "error": str(e)})
        except Exception:
            log(traceback.format_exc(), "error")
            send({"type": "result", "requestId": rid, "ok": False, "error": t("failed")})

    def dispatch(self, action, p):
        if action == "await":
            cmd = str(p.get("cmd") or "")
            return self.await_ack(cmd, to_number(p.get("seconds"), 3, 0.5, 30))
        if action == "item":
            return self.item_action(p)
        raise UserError(t("unknown", id=action))

    def await_ack(self, cmd, seconds):
        start = time.monotonic()
        # Antworten, die kurz vor dem Warten kamen, zählen auch (Tastendruck → Mod → Datei).
        since = start - 1.5
        deadline = start + seconds
        with self.cond:
            while True:
                for i, (when, e, message) in enumerate(self.acks):
                    if when >= since and (not cmd or e.get("cmd") == cmd):
                        del self.acks[i]
                        if e.get("ok"):
                            return message
                        raise UserError(message)
                left = deadline - time.monotonic()
                if left <= 0:
                    break
                self.cond.wait(min(left, self.interval))
                self.poll()
        if not self.is_running():
            raise UserError(t("timeout_off"))
        if not self.connected or self.status == t("st_halted"):
            raise UserError(t("timeout_menu"))
        raise UserError(t("timeout", s=fmt_number(seconds, 1)))


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
        elif kind == "value":
            plugin.on_value(msg)
        elif kind == "stop":
            break
    plugin.shutdown()
    pool.shutdown(wait=False, cancel_futures=True)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
