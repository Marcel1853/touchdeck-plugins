#!/usr/bin/env python3
"""Example of an advanced TouchDeck plugin (full rights, only in advanced mode).

TouchDeck starts this program itself and talks to it with JSON lines:
messages from TouchDeck arrive on stdin, answers go to stdout (one line per message).
Everything written to stderr shows up in the TouchDeck log.
"""
import json
import subprocess
import sys
import threading
import time

lock = threading.Lock()
settings = {}


def send(msg):
    with lock:
        sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def log(text, level="info"):
    send({"type": "log", "level": level, "message": text})


def load_average():
    with open("/proc/loadavg", encoding="utf-8") as f:
        return float(f.read().split()[0])


def action_load(params):
    return f"Load: {load_average():.2f}"


def action_command(params):
    cmd = params.get("command") or "uptime -p"
    out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
    text = (out.stdout or out.stderr).strip()[:500]
    if params.get("value"):
        send({"type": "setValue", "name": params["value"], "value": text})
    return text


ACTIONS = {"load": action_load, "command": action_command}


def watch():
    """Runs in the background: writes the load into a value and reports high load."""
    was_high = False
    while True:
        load = load_average()
        send({"type": "setValue", "name": "System.Load", "value": f"{load:.2f}"})
        high = load >= float(settings.get("threshold") or 4)
        if high and not was_high:
            send({"type": "fire", "trigger": "high", "data": {"Load": f"{load:.2f}"}})
        was_high = high
        time.sleep(10)


for line in sys.stdin:
    msg = json.loads(line)
    kind = msg.get("type")
    if kind == "start":
        settings = msg.get("settings") or {}
        threading.Thread(target=watch, daemon=True).start()
        log(f"Python example started (TouchDeck {msg.get('touchdeck')})")
    elif kind == "action":
        try:
            result = ACTIONS[msg["id"]](msg.get("params") or {})
            send({"type": "result", "requestId": msg["requestId"], "ok": True, "message": result})
        except Exception as err:  # report errors to TouchDeck instead of crashing
            send({"type": "result", "requestId": msg["requestId"], "ok": False, "error": str(err)})
    elif kind == "stop":
        break
