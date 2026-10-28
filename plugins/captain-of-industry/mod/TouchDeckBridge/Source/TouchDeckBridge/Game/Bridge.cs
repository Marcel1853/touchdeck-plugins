// Verbindet Server und Spiel. Ein unsichtbares Unity-Objekt (BridgeRunner) läuft in jedem Bild im
// Hauptthread – im Spiel, bei Pause und nach dem Verlassen ins Hauptmenü. Dort werden Befehle ausgeführt.
// Den Zustand sammelt GameLink im Sync-Schritt des Spiels ein (Simulation und Oberfläche sind dann
// abgeglichen, wie bei den Anzeigen des Spiels). Der Netzwerk-Thread bekommt fertige Textzeilen und fasst
// das Spiel nie an.
//
// Captain of Industry lädt Mods erst mit einem Spielstand. Der Server startet deshalb beim ersten Laden und
// läuft bis zum Beenden des Spiels weiter, auch im Hauptmenü (dann mit „inGame“: false).
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using Mafi;
using Mafi.Core.Mods;
using TouchDeckBridge.Protocol;
using UnityEngine;

namespace TouchDeckBridge
{
    /**
     * Einstiegspunkt: Das Spiel legt die Klasse bei jedem Laden eines Spielstands neu an. Der Mod bringt keine
     * Inhalte mit (keine Prototypen). Initialize von DataOnlyMod ist nicht virtuell, deshalb wird IMod hier noch
     * einmal eingebunden und nur Initialize selbst umgesetzt.
     */
    public sealed class TouchDeckBridgeMod : DataOnlyMod, IMod
    {
        public TouchDeckBridgeMod(ModManifest manifest) : base(manifest)
        {
        }

        public override void RegisterPrototypes(ProtoRegistrator registrator)
        {
        }

        void IMod.Initialize(DependencyResolver resolver, bool gameWasLoaded)
        {
            Initialize(resolver, gameWasLoaded);
            try
            {
                Bridge.Init(Manifest.RootDirectoryPath);
                GameLink.Attach(resolver);
            }
            catch (Exception e)
            {
                Bridge.Warn("start failed: " + e);
            }
        }
    }

    public static class Bridge
    {
        public const string Version = "0.1.0";
        static readonly CommandQueue Queue = new CommandQueue();
        static readonly Deduper Dedup = new Deduper(4000);
        static readonly Stopwatch Clock = Stopwatch.StartNew();
        static BridgeServer server;
        static bool initialized;
        static long nextStateMs;
        static long nextSettingsCheckMs;
        static long lastPublishMs;
        static bool forceState;
        static bool collectFailedLogged;

        public static BridgeSettings Settings = new BridgeSettings();
        /** Geladener Spielstand, sonst null (Hauptmenü, Ladebildschirm). */
        public static GameLink Game;

        public static void Log(string msg) => Mafi.Log.Info("[TouchDeck Bridge] " + msg);
        public static void Warn(string msg) => Mafi.Log.Warning("[TouchDeck Bridge] " + msg);

        public static long NowMs => Clock.ElapsedMilliseconds;

        public static void Init(string modPath)
        {
            if (initialized) return;
            initialized = true;
            Settings = BridgeSettings.LoadOrCreate(Path.Combine(modPath ?? "", "settings.json"), Warn);
            try
            {
                var go = new GameObject("TouchDeckBridge");
                UnityEngine.Object.DontDestroyOnLoad(go);
                go.AddComponent<BridgeRunner>();
            }
            catch (Exception e)
            {
                Warn("could not create runner: " + e);
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
                return Application.version ?? "?";
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

        /** Ereignis an alle Clients. Gleiche Ereignisse innerhalb von 4 s fallen weg. */
        public static void Emit(string name, Dictionary<string, object> data, string dedupKey = null)
        {
            try
            {
                if (server == null || server.ClientCount == 0) return;
                if (!Dedup.Allow(name + "|" + (dedupKey ?? Json.Serialize(data)), NowMs)) return;
                server.Broadcast(Proto.Event(name, data));
                forceState = true;   // Zustand gleich mitschicken (z. B. neuer Verlauf)
            }
            catch (Exception e)
            {
                Warn("event " + name + " failed: " + e.Message);
            }
        }

        public static void RequestState() => forceState = true;

        /** Ist wieder ein Zustand fällig? (Jemand verbunden und Zeit um, oder ausdrücklich angefordert.) */
        public static bool StateDue()
        {
            if (server == null) return false;
            var now = NowMs;
            if (forceState) return true;
            return server.ClientCount > 0 && now >= nextStateMs;
        }

        /** Zustand an alle Clients (der Server schickt ihn nur, wenn er sich geändert hat). */
        public static void Publish(Func<Dictionary<string, object>> collect)
        {
            if (server == null) return;
            forceState = false;
            nextStateMs = NowMs + Settings.IntervalClamped;
            lastPublishMs = NowMs;
            Dictionary<string, object> state;
            try
            {
                state = collect();
            }
            catch (Exception e)
            {
                if (!collectFailedLogged) Warn("collecting state failed: " + e);
                collectFailedLogged = true;
                state = new Dictionary<string, object> { ["inGame"] = false, ["error"] = e.Message };
            }
            server.PublishState(Proto.State(state));
        }

        /** Spiel wird beendet: Port freigeben. */
        public static void Shutdown()
        {
            server?.Stop();
            server = null;
        }

        /** Einmal pro Bild aus BridgeRunner.Update (Hauptthread). */
        internal static void Tick()
        {
            var now = NowMs;
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
            var game = Game;
            if (game != null && game.Terminated)
            {
                Game = null;
                game = null;
                forceState = true;
            }
            if (!StateDue()) return;
            if (game == null)
            {
                Publish(() => new Dictionary<string, object> { ["inGame"] = false });
                return;
            }
            // Normalerweise sammelt GameLink im Sync-Schritt. Kommt der eine Weile nicht (Ladebildschirm,
            // Spiel hängt), hier sammeln, damit das Plugin trotzdem einen Herzschlag mit Zustand bekommt.
            if (now - lastPublishMs > 3000) Publish(game.Collect);
        }
    }

    /** Unsichtbares Unity-Objekt: Update läuft in jedem Bild im Hauptthread, auch bei Pause und im Hauptmenü. */
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
                if (!failed) Bridge.Warn(e.ToString());
                failed = true;
            }
        }

        void OnApplicationQuit()
        {
            try { Bridge.Shutdown(); } catch (Exception) { }
        }
    }

    /**
     * Einstellungen aus settings.json im Mod-Ordner. Die Einstellungen von Captain of Industry für Mods werden im
     * Spielstand gespeichert – Adresse und Port gehören aber zum PC, deshalb eine eigene Datei. Der Mod legt sie
     * beim ersten Start mit Standardwerten an. Änderungen gelten ohne Neustart.
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
