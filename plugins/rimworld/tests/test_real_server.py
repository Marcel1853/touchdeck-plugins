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
            pl.wait(lambda: pl.values.get("RWVerbunden") == "ja", what="verbunden mit C#-Server")
            pl.wait(lambda: pl.values.get("RWStimmungMin") == "47", what="Zustand vom C#-Server")
            self.assertEqual(pl.values["RWKolonist2"], "Ärni")
            self.assertEqual(pl.values["RWBedrohung"], "Gefahr")
            self.assertEqual(pl.lives["mood"], {"text": "47 % (Zoë)", "value": 47, "on": False})
            self.assertTrue(pl.lives["danger"]["on"])
            r = pl.action("pause")
            self.assertEqual(r.get("message"), "Spiel pausiert", r)
            pl.wait(lambda: pl.values.get("RWPause") == "an", what="Pause aus dem Zustand")
            r = pl.action("letter")
            self.assertEqual(r.get("message"), "Kamera beim Brief „Überfall“", r)
            pl.wait(lambda: any(f[0] == "raid" for f in pl.fired), what="Überfall-Auslöser")
            letter = [d for trig, d in pl.fired if trig == "letter"][0]
            self.assertEqual(letter["Titel"], "Überfall „Piraten“")
            self.assertEqual(letter["Text"], "Zeile 1\nZeile 2")
            r = pl.action("screenshot")
            self.assertFalse(r["ok"])
            self.assertIn("kennt den Befehl „screenshot“ nicht", r["error"])
        finally:
            pl.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
