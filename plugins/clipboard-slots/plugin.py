#!/usr/bin/env python3
"""TouchDeck-Plugin „Zwischenablage-Slots“ (Clipboard Slots).

Erweitertes Plugin: TouchDeck startet dieses Programm und tauscht mit ihm
JSON-Zeilen über stdin/stdout aus (siehe Wiki › Advanced plugins).
Nur Python-Standardbibliothek. Für die Zwischenablage wird ein vorhandenes
Programm genutzt: xclip, xsel oder wl-clipboard (wl-copy / wl-paste).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# --------------------------------------------------------------------------
# Texte (Sprache aus der Systemumgebung, TouchDeck folgt standardmäßig ebenfalls)
# --------------------------------------------------------------------------

_LOCALE = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES")
           or os.environ.get("LANG") or "").lower()
DE = _LOCALE.startswith("de")

TEXTS = {
    "no_tool": ("Kein Zwischenablage-Programm gefunden. Bitte installieren: sudo apt install xclip",
                "No clipboard tool found. Please install one: sudo apt install xclip"),
    "no_text": ("Die Zwischenablage enthält keinen Text.",
                "The clipboard does not contain any text."),
    "too_long": ("Text ist zu lang ({n} Zeichen, erlaubt sind {m}). Grenze in den Plugin-Einstellungen änderbar.",
                 "Text is too long ({n} characters, {m} allowed). The limit can be changed in the plugin settings."),
    "slot_range": ("Slot {n} gibt es nicht (erlaubt: 1 bis {m}). Anzahl in den Plugin-Einstellungen änderbar.",
                   "Slot {n} does not exist (allowed: 1 to {m}). The number can be changed in the plugin settings."),
    "slot_saved": ("Slot {n} gespeichert ({c} Zeichen)", "Slot {n} saved ({c} characters)"),
    "slot_empty": ("Slot {n} ist leer.", "Slot {n} is empty."),
    "slot_loaded": ("Slot {n} liegt in der Zwischenablage", "Slot {n} is in the clipboard"),
    "slot_cleared": ("Slot {n} geleert", "Slot {n} cleared"),
    "slots_cleared": ("Alle Slots geleert", "All slots cleared"),
    "auto_on": ("Auto-Speichern an, nächster Slot: {n}", "Auto-save on, next slot: {n}"),
    "auto_off": ("Auto-Speichern aus", "Auto-save off"),
    "hist_off": ("Der Verlauf ist in den Plugin-Einstellungen ausgeschaltet.",
                 "The history is switched off in the plugin settings."),
    "hist_missing": ("Verlaufseintrag {n} gibt es nicht (vorhanden: {m}).",
                     "History entry {n} does not exist ({m} available)."),
    "hist_loaded": ("Verlaufseintrag {n} liegt in der Zwischenablage",
                    "History entry {n} is in the clipboard"),
    "hist_cleared": ("Verlauf geleert", "History cleared"),
    "clip_cleared": ("Zwischenablage geleert", "Clipboard cleared"),
    "need_name": ("Bitte einen Wert auswählen.", "Please choose a value."),
    "to_value": ("In Wert „{name}“ geschrieben ({c} Zeichen)", "Written to value “{name}” ({c} characters)"),
    "to_value_cut": ("In Wert „{name}“ geschrieben, auf 1000 Zeichen gekürzt (TouchDeck-Grenze für Werte)",
                     "Written to value “{name}”, cut to 1000 characters (TouchDeck limit for values)"),
    "from_value": ("Wert „{name}“ liegt in der Zwischenablage", "Value “{name}” is in the clipboard"),
    "value_empty": ("Wert „{name}“ ist leer oder existiert nicht.", "Value “{name}” is empty or does not exist."),
    "value_timeout": ("TouchDeck hat den Wert „{name}“ nicht rechtzeitig geliefert.",
                      "TouchDeck did not deliver the value “{name}” in time."),
    "not_url": ("In der Zwischenablage steht kein Link.", "The clipboard does not contain a link."),
    "transformed": ("Text umgewandelt", "Text converted"),
    "url_clean": ("Link bereinigt", "Link cleaned"),
    "url_same": ("Link hatte kein Tracking, nichts geändert", "Link had no tracking, nothing changed"),
    "set_failed": ("Die Zwischenablage konnte nicht gesetzt werden.",
                   "The clipboard could not be set."),
    "unknown": ("Unbekannte Aktion: {id}", "Unknown action: {id}"),
    "failed": ("Unerwarteter Fehler, Details im Log.", "Unexpected error, see the log for details."),
}


def t(key, **kw):
    de, en = TEXTS[key]
    return (de if DE else en).format(**kw)


VALUE_LIMIT = 1000  # TouchDeck kürzt Werte auf 1000 Zeichen (store.rs, set_variable)


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
# Zwischenablage-Zugriff
# --------------------------------------------------------------------------

class Clipboard:
    """Dünne Hülle um xclip / xsel / wl-clipboard."""

    def __init__(self):
        self.kind = self._detect()

    @staticmethod
    def _detect():
        if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wl-paste") and shutil.which("wl-copy"):
            return "wl"
        if shutil.which("xclip"):
            return "xclip"
        if shutil.which("xsel"):
            return "xsel"
        if shutil.which("wl-paste") and shutil.which("wl-copy"):
            return "wl"
        return None

    @staticmethod
    def _run(cmd):
        try:
            p = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, timeout=2)
        except (subprocess.TimeoutExpired, OSError):
            return None
        if p.returncode != 0:
            return None
        return p.stdout.decode("utf-8", errors="replace")

    def read(self):
        """Gibt den Text zurück oder None, wenn kein Text vorliegt (leer / Bild / Fehler)."""
        if self.kind == "xclip":
            for target in ("UTF8_STRING", "STRING"):
                text = self._run(["xclip", "-selection", "clipboard", "-o", "-t", target])
                if text is not None:
                    return text
            return None
        if self.kind == "xsel":
            return self._run(["xsel", "--clipboard", "--output"])
        if self.kind == "wl":
            return self._run(["wl-paste", "--no-newline", "--type", "text"])
        return None

    def write(self, text):
        if self.kind == "xclip":
            cmd = ["xclip", "-selection", "clipboard", "-i"]
        elif self.kind == "xsel":
            cmd = ["xsel", "--clipboard", "--input"]
        elif self.kind == "wl":
            cmd = ["wl-copy"] if text else ["wl-copy", "--clear"]
        else:
            raise UserError(t("no_tool"))
        try:
            # Die Werkzeuge bleiben im Hintergrund, bis jemand anderes die Zwischenablage übernimmt.
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
            p.communicate(text.encode("utf-8"), timeout=3)
        except (subprocess.TimeoutExpired, OSError) as e:
            raise UserError(f"{t('set_failed')} ({e})")


# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------

def to_int(value, default, lo, hi):
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        n = default
    return max(lo, min(hi, n))


def to_bool(value, default):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "1", "yes", "ja", "on"):
            return True
        if v in ("false", "0", "no", "nein", "off"):
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def preview(text, limit):
    one = re.sub(r"\s+", " ", text).strip()
    return one if len(one) <= limit else one[: limit - 1] + "…"


TRACKING_PARAMS = {
    "fbclid", "gclid", "dclid", "msclkid", "yclid", "igshid", "mc_cid", "mc_eid",
    "_hsenc", "_hsmi", "mkt_tok", "ref_src",
}


def clean_url(text):
    """Entfernt bekannte Tracking-Parameter. Gibt None zurück, wenn es kein Link ist."""
    raw = text.strip()
    if not re.match(r"^https?://\S+$", raw, re.IGNORECASE):
        return None
    parts = urlsplit(raw)
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if not (k.lower().startswith("utm_") or k.lower() in TRACKING_PARAMS)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


def data_file():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    folder = os.path.join(base, "touchdeck-clipboard-slots")
    return folder, os.path.join(folder, "slots.json")


# --------------------------------------------------------------------------
# Plugin
# --------------------------------------------------------------------------

class Plugin:
    def __init__(self):
        self.lock = threading.RLock()
        self.stop_evt = threading.Event()
        self.clip = Clipboard()
        self.started = False
        self.last = None          # zuletzt gesehener Zwischenablage-Text
        self.history = []         # neuester Eintrag zuerst, nur im Arbeitsspeicher
        self.slots = {}           # int -> str
        self.pending = {}         # requestId -> {"evt": Event, "value": ...}
        self.pending_lock = threading.Lock()
        self.req_counter = 0
        self.slot_count = 12
        self.auto_slots = 0       # 0 = alle Slots
        self.auto = False         # Auto-Speichern: jede neue Kopie in den nächsten Slot (Ringpuffer)
        self.next_slot = 1
        self.persist = True
        self.use_history = True
        self.history_size = 20
        self.max_len = 10000
        self.interval = 1.0

    # ---------------- Start / Stopp ----------------

    def start(self, msg):
        if self.started:
            return
        self.started = True
        s = msg.get("settings") or {}
        self.slot_count = to_int(s.get("slots"), 12, 1, 50)
        self.auto_slots = to_int(s.get("autoSlots"), 0, 0, 50)
        self.persist = to_bool(s.get("persist"), True)
        self.use_history = to_bool(s.get("history"), True)
        self.history_size = to_int(s.get("historySize"), 20, 1, 100)
        self.max_len = to_int(s.get("maxLength"), 10000, 1, 1_000_000)
        self.interval = to_int(s.get("interval"), 1000, 300, 10000) / 1000.0

        if self.persist:
            self.load_slots()

        if not self.clip.kind:
            log(t("no_tool"), "error")
            send({"type": "notify", "title": "Clipboard Slots", "body": t("no_tool")})
        else:
            log(f"Zwischenablage über {self.clip.kind}" if DE else f"Clipboard via {self.clip.kind}")
            text = self.clip.read()
            with self.lock:
                self.last = text
                if text is not None:
                    self.ingest(text, fire=False)
                else:
                    self.publish_clip("")
            threading.Thread(target=self.poll_loop, daemon=True).start()
        self.publish_slots()
        self.publish_auto()

    def shutdown(self):
        self.stop_evt.set()

    # ---------------- Slots speichern / laden ----------------

    def load_slots(self):
        _, path = data_file()
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw.get("slots"), dict):      # Format ab 1.2.0
                self.auto = to_bool(raw.get("auto"), False)
                self.next_slot = to_int(raw.get("next"), 1, 1, 50)
                raw = raw["slots"]
            for k, v in raw.items():                     # altes Format: nur {"1": "text"}
                if isinstance(v, str) and str(k).isdigit():
                    self.slots[int(k)] = v
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as e:
            log(f"slots.json konnte nicht gelesen werden: {e}", "warn")

    def save_slots(self):
        if not self.persist:
            return
        folder, path = data_file()
        try:
            os.makedirs(folder, mode=0o700, exist_ok=True)
            tmp = path + ".tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"slots": {str(k): v for k, v in sorted(self.slots.items())},
                           "auto": self.auto, "next": self.next_slot}, f, ensure_ascii=False)
            os.replace(tmp, path)
        except OSError as e:
            log(f"slots.json konnte nicht geschrieben werden: {e}", "warn")

    # ---------------- Werte für Live-Anzeigen ----------------

    def publish_clip(self, text):
        send({"type": "setValue", "name": "Clip", "value": preview(text, 60)})
        send({"type": "setValue", "name": "ClipLength", "value": str(len(text))})
        send({"type": "setValue", "name": "ClipCount", "value": str(len(self.history))})

    def auto_range(self):
        return min(self.auto_slots or self.slot_count, self.slot_count)

    def publish_auto(self):
        if self.next_slot > self.auto_range():
            self.next_slot = 1
        send({"type": "setValue", "name": "AutoSave", "value": "an" if self.auto else "aus"})
        send({"type": "setValue", "name": "NextSlot", "value": str(self.next_slot)})

    def publish_slots(self):
        for n in range(1, self.slot_count + 1):
            send({"type": "setValue", "name": f"Slot{n}", "value": preview(self.slots.get(n, ""), 40)})

    # ---------------- Zwischenablage beobachten ----------------

    def poll_loop(self):
        while not self.stop_evt.wait(self.interval):
            try:
                with self.lock:
                    text = self.clip.read()
                    if text is None or text == self.last:
                        continue
                    self.last = text
                    self.ingest(text, fire=True)
            except Exception:
                log(traceback.format_exc(), "error")

    def ingest(self, text, fire):
        """Neuer Zwischenablage-Inhalt: Verlauf, Werte und optional Trigger. Aufruf mit Lock."""
        too_long = len(text) > self.max_len
        usable = bool(text.strip()) and not too_long
        if self.use_history and usable:
            if text in self.history:
                self.history.remove(text)
            self.history.insert(0, text)
            del self.history[self.history_size:]
        self.publish_clip(text if not too_long else "")
        if fire and usable and self.auto:
            self.auto_store(text)
        if fire and usable:
            send({"type": "fire", "trigger": "changed", "data": {"Text": text, "Length": len(text)}})

    def auto_store(self, text):
        """Neue Kopie in den nächsten Slot legen (Ringpuffer). Texte, die schon in einem Slot liegen, werden übersprungen."""
        if text in self.slots.values():
            return
        n = self.next_slot if self.next_slot <= self.auto_range() else 1
        self.slots[n] = text
        self.next_slot = n + 1 if n + 1 <= self.auto_range() else 1
        self.save_slots()
        send({"type": "setValue", "name": f"Slot{n}", "value": preview(text, 40)})
        self.publish_auto()

    def set_clipboard(self, text, record):
        """Schreibt in die Zwischenablage und prüft, dass es angekommen ist. Aufruf mit Lock."""
        self.clip.write(text)
        if text:
            for _ in range(20):
                if self.clip.read() == text:
                    break
                time.sleep(0.05)
            else:
                raise UserError(t("set_failed"))
        self.last = text
        if record:
            self.ingest(text, fire=False)
        else:
            self.publish_clip(text)

    def current_text(self):
        if not self.clip.kind:
            raise UserError(t("no_tool"))
        text = self.clip.read()
        if text is None or text == "":
            raise UserError(t("no_text"))
        return text

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

    def slot_no(self, params):
        n = to_int(params.get("slot"), 1, -10**6, 10**6)
        if n < 1 or n > self.slot_count:
            raise UserError(t("slot_range", n=n, m=self.slot_count))
        return n

    def dispatch(self, action, p):
        if action == "save-slot":
            n = self.slot_no(p)
            with self.lock:
                text = self.current_text()
                if len(text) > self.max_len:
                    raise UserError(t("too_long", n=len(text), m=self.max_len))
                self.slots[n] = text
                self.save_slots()
            send({"type": "setValue", "name": f"Slot{n}", "value": preview(text, 40)})
            return t("slot_saved", n=n, c=len(text))

        if action == "load-slot":
            n = self.slot_no(p)
            with self.lock:
                text = self.slots.get(n, "")
                if not text:
                    raise UserError(t("slot_empty", n=n))
                self.require_tool()
                self.set_clipboard(text, record=False)
            return t("slot_loaded", n=n)

        if action == "copy-history":
            if not self.use_history:
                raise UserError(t("hist_off"))
            n = to_int(p.get("entry"), 2, 1, 100)
            with self.lock:
                if n > len(self.history):
                    raise UserError(t("hist_missing", n=n, m=len(self.history)))
                self.require_tool()
                self.set_clipboard(self.history[n - 1], record=False)
            return t("hist_loaded", n=n)

        if action == "clip-to-value":
            name = str(p.get("name") or "").strip()
            if not name:
                raise UserError(t("need_name"))
            with self.lock:
                text = self.current_text()
            send({"type": "setValue", "name": name, "value": text})
            if len(text) > VALUE_LIMIT:
                return t("to_value_cut", name=name)
            return t("to_value", name=name, c=len(text))

        if action == "value-to-clip":
            name = str(p.get("name") or "").strip()
            if not name:
                raise UserError(t("need_name"))
            value = self.get_value(name)
            if value is None or str(value) == "":
                raise UserError(t("value_empty", name=name))
            with self.lock:
                self.require_tool()
                self.set_clipboard(str(value), record=True)
            return t("from_value", name=name)

        if action == "transform":
            mode = p.get("mode") or "trim"
            with self.lock:
                text = self.current_text()
                if mode == "trim":
                    new, msg = text.strip(), t("transformed")
                elif mode == "oneline":
                    new, msg = re.sub(r"\s*[\r\n]+\s*", " ", text).strip(), t("transformed")
                elif mode == "upper":
                    new, msg = text.upper(), t("transformed")
                elif mode == "lower":
                    new, msg = text.lower(), t("transformed")
                elif mode == "clean-url":
                    new = clean_url(text)
                    if new is None:
                        raise UserError(t("not_url"))
                    msg = t("url_clean") if new != text.strip() else t("url_same")
                else:
                    raise UserError(t("unknown", id=f"transform/{mode}"))
                if new != text:
                    self.set_clipboard(new, record=True)
            return msg

        if action == "auto-mode":
            mode = p.get("mode") or "toggle"
            with self.lock:
                self.auto = (not self.auto) if mode == "toggle" else (mode == "on")
                self.save_slots()
                self.publish_auto()
                return t("auto_on", n=self.next_slot) if self.auto else t("auto_off")

        if action == "clear":
            what = p.get("what") or "history"
            with self.lock:
                if what == "history":
                    self.history.clear()
                    self.publish_clip(self.last or "")
                    return t("hist_cleared")
                if what == "clipboard":
                    self.require_tool()
                    self.set_clipboard("", record=False)
                    return t("clip_cleared")
                if what == "slot":
                    n = self.slot_no(p)
                    self.slots.pop(n, None)
                    self.save_slots()
                    send({"type": "setValue", "name": f"Slot{n}", "value": ""})
                    return t("slot_cleared", n=n)
                if what == "all-slots":
                    self.slots.clear()
                    self.next_slot = 1
                    self.save_slots()
                    self.publish_slots()
                    self.publish_auto()
                    return t("slots_cleared")
            raise UserError(t("unknown", id=f"clear/{what}"))

        raise UserError(t("unknown", id=action))

    def require_tool(self):
        if not self.clip.kind:
            raise UserError(t("no_tool"))

    # ---------------- Werte von TouchDeck abfragen ----------------

    def get_value(self, name):
        with self.pending_lock:
            self.req_counter += 1
            rid = f"cs_{self.req_counter}"
            slot = {"evt": threading.Event(), "value": None}
            self.pending[rid] = slot
        send({"type": "getValue", "requestId": rid, "name": name})
        got = slot["evt"].wait(10)
        with self.pending_lock:
            self.pending.pop(rid, None)
        if not got:
            raise UserError(t("value_timeout", name=name))
        return slot["value"]

    def on_value(self, msg):
        with self.pending_lock:
            slot = self.pending.get(msg.get("requestId"))
        if slot:
            slot["value"] = msg.get("value")
            slot["evt"].set()


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
