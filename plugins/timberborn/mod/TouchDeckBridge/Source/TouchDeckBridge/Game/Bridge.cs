// Verbindet Server und Spiel. Ein unsichtbares Unity-Objekt (BridgeRunner) läuft in jedem Bild im
// Hauptthread – im Hauptmenü, im Spiel und bei Pause. Nur dort werden Befehle ausgeführt und der Zustand
// eingesammelt. Der Netzwerk-Thread bekommt fertige Textzeilen und fasst das Spiel nie an.
//
// Der Server läuft vom Spielstart bis zum Beenden, auch im Hauptmenü. Ist ein Spielstand geladen, meldet
// sich GameLink an (Bindito-Singleton im Kontext „Game“) und liefert Zustand und Befehle.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using Timberborn.ModManagerScene;
using TouchDeckBridge.Protocol;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace TouchDeckBridge
{
    /** Einstiegspunkt: Das Spiel ruft StartMod einmal nach dem Laden aller Mods auf. */
    public class ModStarter : IModStarter
    {
        public void StartMod(IModEnvironment modEnvironment)
        {
            Bridge.Init(modEnvironment.ModPath);
        }
    }

    public static class Bridge
    {
        public const string Version = "0.1.0";
        static readonly CommandQueue Queue = new CommandQueue();
        static readonly Deduper Dedup = new Deduper(4000);
        static readonly Stopwatch Clock = Stopwatch.StartNew();
        static BridgeServer server;
        static long nextStateMs;
        static long nextSettingsCheckMs;
        static bool forceState;

        public static BridgeSettings Settings = new BridgeSettings();
        /** Geladener Spielstand, sonst null (Hauptmenü, Karteneditor). */
        public static GameLink Game;

        public static void Log(string msg) => Debug.Log("[TouchDeck Bridge] " + msg);
        public static void Warn(string msg) => Debug.LogWarning("[TouchDeck Bridge] " + msg);

        public static void Init(string modPath)
        {
            Settings = BridgeSettings.LoadOrCreate(Path.Combine(modPath ?? "", "settings.json"), Warn);
            try
            {
                var go = new GameObject("TouchDeckBridge");
                UnityEngine.Object.DontDestroyOnLoad(go);
                go.AddComponent<BridgeRunner>();
            }
            catch (Exception e)
            {
                Debug.LogError("[TouchDeck Bridge] could not create runner: " + e);
            }
            Restart();
        }

        static void Restart()
        {
            try
            {
                server?.Stop();
            }
            catch (Exception e)
            {
                Warn("stop failed: " + e.Message);
            }
            server = null;
            if (!Settings.Enabled)
            {
                Log("server off (settings.json: \"enabled\": false)");
                return;
            }
            var cfg = Settings.ToConfig();
            foreach (var p in cfg.Problems) Warn(p);
            if (cfg.Blocked) return;
            try
            {
                server = new BridgeServer(cfg, Queue, Log, Version, GameVersion());
                server.Start();
                forceState = true;
            }
            catch (Exception e)
            {
                server = null;
                Warn("could not start server on " + cfg.AddressText + ":" + cfg.Port + ": " + e.Message);
            }
        }

        static string GameVersion()
        {
            try
            {
                return Timberborn.Versioning.GameVersions.CurrentVersion.ToString();
            }
            catch (Exception)
            {
                return "?";
            }
        }

        /** settings.json geändert? Dann neu einlesen und den Server nur bei geänderten Werten neu starten. */
        static void CheckSettings()
        {
            if (!Settings.Changed()) return;
            var old = Settings;
            Settings = BridgeSettings.LoadOrCreate(old.FilePath, Warn);
            Log("settings.json reloaded");
            var running = server != null && server.Running;
            if (Settings.Enabled == old.Enabled && running && server.Config.SameAs(Settings.ToConfig())) return;
            if (!Settings.Enabled && server == null) return;
            Restart();
        }

        /** Ereignis an alle Clients (Hauptthread). Gleiche Meldungen innerhalb von 4 s fallen weg. */
        public static void Emit(string name, Dictionary<string, object> data, string dedupKey = null)
        {
            try
            {
                if (server == null || server.ClientCount == 0) return;
                if (!Dedup.Allow(name + "|" + (dedupKey ?? Json.Serialize(data)), Clock.ElapsedMilliseconds)) return;
                server.Broadcast(Proto.Event(name, data));
                forceState = true;   // Zustand gleich mitschicken (z. B. neuer Verlauf, neue Bevölkerung)
            }
            catch (Exception e)
            {
                Warn("event " + name + " failed: " + e.Message);
            }
        }

        public static void RequestState() => forceState = true;

        /** Spiel wird beendet: Port freigeben. */
        public static void Shutdown()
        {
            server?.Stop();
            server = null;
        }

        /** Einmal pro Bild aus BridgeRunner.Update (Hauptthread). */
        internal static void Tick()
        {
            var now = Clock.ElapsedMilliseconds;
            if (now >= nextSettingsCheckMs)
            {
                nextSettingsCheckMs = now + 2000;
                CheckSettings();
            }
            if (server == null) return;
            // Befehle: höchstens 8 pro Bild, damit nichts ruckelt
            for (var i = 0; i < 8 && Queue.TryTake(out var cmd); i++)
            {
                try
                {
                    if (Game == null)
                    {
                        if (cmd.Name == "refresh") cmd.Reply(true, "refreshed");
                        else cmd.Reply(false, "no_game");
                    }
                    else Game.Run(cmd);
                }
                catch (Exception e)
                {
                    Warn("command " + cmd.Name + " failed: " + e);
                    cmd.Reply(false, "error", new Dictionary<string, object> { ["value"] = e.Message });
                }
            }
            if (!forceState && now < nextStateMs) return;
            if (server.ClientCount == 0 && !forceState)
            {
                nextStateMs = now + 1000;
                return;
            }
            forceState = false;
            nextStateMs = now + Settings.IntervalClamped;
            Dictionary<string, object> state;
            try
            {
                state = Game != null ? Game.Collect() : new Dictionary<string, object> { ["inGame"] = false };
            }
            catch (Exception e)
            {
                if (!collectFailedLogged) Warn("collecting state failed: " + e);
                collectFailedLogged = true;
                state = new Dictionary<string, object> { ["inGame"] = false, ["error"] = e.Message };
            }
            server.PublishState(Proto.State(state));
        }

        static bool collectFailedLogged;
    }

    /** Unsichtbares Unity-Objekt: Update läuft in jedem Bild im Hauptthread, auch im Hauptmenü und bei Pause. */
    public class BridgeRunner : MonoBehaviour
    {
        bool failed;

        void Update()
        {
            try
            {
                Bridge.Tick();
            }
            catch (Exception e)
            {
                if (!failed) Debug.LogError("[TouchDeck Bridge] " + e);
                failed = true;
            }
        }

        void OnApplicationQuit()
        {
            try { Bridge.Shutdown(); } catch (Exception) { }
        }
    }

    /**
     * Einstellungen aus settings.json im Mod-Ordner. Timberborn hat kein Einstellungsmenü für Mods, deshalb
     * legt der Mod die Datei beim ersten Start mit Standardwerten an. Änderungen gelten ohne Neustart.
     */
    public class BridgeSettings
    {
        public string FilePath = "";
        public bool Enabled = true;
        public string Address = ServerConfig.DefaultAddress;
        public string Port = ServerConfig.DefaultPort.ToString();
        public string Secret = "";
        public int IntervalMs = 500;
        DateTime stamp;

        public int IntervalClamped => Math.Max(200, Math.Min(5000, IntervalMs));

        public ServerConfig ToConfig() => ServerConfig.From(Address, Port, Secret);

        public bool Changed()
        {
            try
            {
                return FilePath.Length > 0 && File.Exists(FilePath) && File.GetLastWriteTimeUtc(FilePath) != stamp;
            }
            catch (Exception)
            {
                return false;
            }
        }

        public static BridgeSettings LoadOrCreate(string path, Action<string> warn)
        {
            var s = new BridgeSettings { FilePath = path ?? "" };
            try
            {
                if (!File.Exists(s.FilePath))
                {
                    File.WriteAllText(s.FilePath, Default());
                }
                s.stamp = File.GetLastWriteTimeUtc(s.FilePath);
                var o = Json.TryParseObject(File.ReadAllText(s.FilePath));
                if (o == null)
                {
                    warn("settings.json is not valid JSON, using defaults");
                    return s;
                }
                s.Enabled = Json.Bool(o, "enabled", true);
                s.Address = Json.Str(o, "address", ServerConfig.DefaultAddress);
                s.Port = o.TryGetValue("port", out var p) && p != null ? Convert.ToString(p, System.Globalization.CultureInfo.InvariantCulture) : s.Port;
                s.Secret = Json.Str(o, "secret", "");
                s.IntervalMs = (int)Json.Num(o, "intervalMs", 500);
            }
            catch (Exception e)
            {
                warn("could not read " + s.FilePath + ": " + e.Message + " (using defaults)");
            }
            return s;
        }

        static string Default() =>
            "{\n" +
            "  \"enabled\": true,\n" +
            "  \"address\": \"127.0.0.1\",\n" +
            "  \"port\": " + ServerConfig.DefaultPort + ",\n" +
            "  \"secret\": \"\",\n" +
            "  \"intervalMs\": 500,\n" +
            "  \"_help\": \"address 127.0.0.1 = only this PC; 0.0.0.0 = all network cards (TouchDeck on another PC, secret with at least 12 characters required). Changes apply without restarting the game.\"\n" +
            "}\n";
    }
}
