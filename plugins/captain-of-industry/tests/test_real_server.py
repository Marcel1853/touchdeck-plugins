#!/usr/bin/env python3
"""Plugin gegen den echten C#-Server des Mods (ohne Spiel): prüft, dass beide wirklich dasselbe Protokoll sprechen.

Aufruf:  python3 tests/test_real_server.py
Braucht dotnet (zum Übersetzen) und mono (zum Starten); fehlt eins, wird der Test übersprungen.
Der Server läuft im Modus „--serve“ des Test-Programms (mod/TouchDeckBridge/Source/Tests/ProtocolTests.cs).
"""
import os
import shutil
import socket
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TESTS = os.path.join(ROOT, "mod", "TouchDeckBridge", "Source", "Tests")
sys.path.insert(0, HERE)
from test_plugin import PluginProcess  # noqa: E402


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@unittest.skipUnless(shutil.which("dotnet") and shutil.which("mono"), "dotnet oder mono fehlt")
class RealServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["dotnet", "build", "-nologo", "-v", "q", "Tests.csproj"], cwd=TESTS, check=True,
                       stdout=subprocess.DEVNULL)
        cls.port = free_port()
        cls.server = subprocess.Popen(["mono", os.path.join(TESTS, "bin", "Tests.exe"), "--serve", str(cls.port)],
                                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        line = cls.server.stdout.readline()
        assert line.startswith("ready"), line

    @classmethod
    def tearDownClass(cls):
        cls.server.kill()
        cls.server.wait()
        cls.server.stdout.close()
        shutil.rmtree(os.path.join(TESTS, "bin"), ignore_errors=True)
        shutil.rmtree(os.path.join(TESTS, "obj"), ignore_errors=True)

    def test_plugin_with_real_server(self):
        pl = PluginProcess({"host": "127.0.0.1", "port": self.port})
        try:
            pl.wait(lambda: pl.values.get("COIVerbunden") == "ja", what="verbunden mit C#-Server")
            pl.wait(lambda: pl.values.get("COIEinwohner") == "480", what="Zustand vom C#-Server")
            self.assertEqual(pl.values["COIDatum"], "Jahr 5 · März")
            self.assertEqual(pl.values["COITempo"], "2")
            self.assertEqual(pl.values["COIWare_Coal"], "50")
            self.assertEqual(pl.values["COIVerlauf1"], "Zoë „Ärni“ hat keinen Strom (Jahr 5)")
            self.assertEqual(pl.lives["power"], {"text": "Strom 2,5 MW / 2,5 MW\nStrom fehlt: 500 kW", "value": 100, "on": True,
                                               "number": 2500, "series": {"Bedarf": 3000, "Kapazität": 2500}})
            self.assertEqual(pl.lives["workers"]["text"], "2 Arbeiter fehlen")
            self.assertEqual(pl.lives["alert1"], {"text": "Kein Strom\n4×", "value": None, "on": True})
            self.assertEqual(pl.lives["good1"]["text"], "📌 Kohle\n50/100 · +25/Monat")
            r = pl.action("pause")
            self.assertEqual(r.get("message"), "Spiel pausiert", r)
            pl.wait(lambda: pl.values.get("COIPause") == "an", what="Pause aus dem Zustand")
            r = pl.action("history", {"n": 1})
            self.assertEqual(r.get("message"), "Kamera bei „Zoë „Ärni“ hat keinen Strom“", r)
            pl.wait(lambda: any(f[0] == "notification" for f in pl.fired), what="Meldungs-Auslöser")
            note = [d for trig, d in pl.fired if trig == "notification"][0]
            self.assertEqual(note["Text"], "Lkw „Kalle“ hat keinen Treibstoff\nZeile 2")
            self.assertEqual(note["Art"], "critical")
            r = pl.action("save")
            self.assertFalse(r["ok"])
            self.assertIn("kennt den Befehl „save“ nicht", r["error"])
        finally:
            pl.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
